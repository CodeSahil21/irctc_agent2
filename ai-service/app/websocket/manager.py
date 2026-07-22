# websocket/manager.py
"""
Socket.IO server for Phase 13.

The frontend uses socket.io-client. This server uses python-socketio (AsyncServer)
mounted as ASGI alongside FastAPI — no separate Node process needed.

Event flow per query:
  client → query:send
  server → query:ack
  server → agent:typing {isTyping: true}
  server → tool:start   {tool, index, total}   (per tool)
  server → tool:done    {tool, index}           (per tool success)
  server → tool:failed  {tool, index, error}    (per tool failure)
  server → message:chunk {id, delta}            (streamed reply tokens)
  server → message:complete {message}
  server → agent:typing {isTyping: false}

  On human-approval interrupt:
  server → agent:interrupt {id, prompt}
  client → resume          {id, approved: bool}
"""
import asyncio
import time
from typing import Any, Optional
import nanoid
import socketio
from langchain_core.messages import HumanMessage
from langgraph.types import Command
from langsmith import traceable

from app.auth.jwt import extract_user_from_token
from app.config.settings import get_settings
from app.websocket import events
from app.websocket.connections import create_session, get_session, remove_session
from app.telemetry.logging import app_logger

# Shared AsyncServer — imported by main.py to mount
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins=["http://localhost:3001", "http://localhost:3000"],
    logger=False,
    engineio_logger=False,
)


def _make_manager(agent_graph, conv_manager):
    """
    Wire event handlers onto the sio server.
    Called once from lifespan after all deps are ready.
    """

    @sio.event
    async def connect(sid, environ, auth):
        session = create_session(sid)
        settings = get_settings()

        # Try to extract user from JWT cookie forwarded in auth payload
        token = (auth or {}).get("token")
        jwt_email, jwt_name = extract_user_from_token(token, settings.jwt_secret)

        # JWT claims take priority; fall back to explicit auth fields
        session.conversation_id = (auth or {}).get("conversationId") or f"conv-{sid[:8]}"
        session.user_email = jwt_email or (auth or {}).get("userEmail")
        session.user_name = jwt_name or (auth or {}).get("userName")

        app_logger.info(
            "Socket connected | sid={sid} | conv={conv} | user={user}",
            sid=sid, conv=session.conversation_id, user=session.user_email,
        )

    @sio.event
    async def disconnect(sid):
        remove_session(sid)
        app_logger.info("Socket disconnected | sid={sid}", sid=sid)

    @traceable(name="socket.stream_chunks", run_type="chain")
    async def _stream_chunks(sid: str, reply_id: str, reply: str) -> None:
        chunk_size = 4
        for i in range(0, len(reply), chunk_size):
            delta = reply[i:i + chunk_size]
            await sio.emit(events.MESSAGE_CHUNK, {"id": reply_id, "delta": delta}, to=sid)
            app_logger.info(
                "Socket chunk emitted | sid={sid} | message_id={msg_id} | chunk_index={idx}",
                sid=sid,
                msg_id=reply_id,
                idx=i // chunk_size,
            )
            await asyncio.sleep(0.01)

    @sio.on(events.QUERY_SEND)
    @traceable(name="socket.query_send", run_type="chain")
    async def on_query_send(sid, data):
        """
        data: {id: str, content: str}
        """
        msg_id: str = data.get("id") or nanoid.generate()
        content: str = data.get("content", "").strip()
        if not content:
            return

        session = get_session(sid)
        if not session:
            return

        conversation_id = session.conversation_id or f"conv-{sid[:8]}"
        config = {"configurable": {"thread_id": conversation_id}}
        session.pending_user_message = content
        session.pending_message_id = msg_id

        # Ack immediately
        await sio.emit(events.QUERY_ACK, {"id": msg_id}, to=sid)
        await sio.emit(events.AGENT_TYPING, {"isTyping": True}, to=sid)

        # Open conversation (loads prefs)
        if session.user_email:
            await conv_manager.open(
                conversation_id=conversation_id,
                user_email=session.user_email,
                user_name=session.user_name,
            )

        try:
            initial_state = {
                "messages": [HumanMessage(content=content)],
                "user_email": session.user_email,
                "user_name": session.user_name,
                "travel": {},
            }

            # Stream graph execution with event callbacks
            result = await _run_graph(
                sid=sid,
                msg_id=msg_id,
                agent_graph=agent_graph,
                initial_state=initial_state,
                config=config,
            )

            if result is None:
                # Interrupted — interrupt event already emitted inside _run_graph
                return

            # Extract reply
            reply = ""
            for msg in reversed(result.get("messages", [])):
                if hasattr(msg, "content") and not isinstance(msg, HumanMessage):
                    reply = str(msg.content)
                    break

            # Stream reply as chunks (simulate token streaming from full reply)
            reply_id = nanoid.generate()
            await _stream_chunks(sid, reply_id, reply)

            from app.types.chat import build_complete_message
            complete_msg = build_complete_message(
                msg_id=reply_id,
                content=reply,
                result=result,
            )
            await sio.emit(events.MESSAGE_COMPLETE, {"message": complete_msg}, to=sid)

            # Persist
            if session.user_email:
                await conv_manager.save_turn(
                    conversation_id=conversation_id,
                    user_email=session.user_email,
                    user_message=content,
                    assistant_reply=reply,
                    intent=result.get("intent"),
                    result=result,
                )
                await conv_manager.close(session.user_email)

            session.pending_user_message = None
            session.pending_message_id = None

        except Exception as e:
            app_logger.error("Socket query error: {e}", e=str(e), exc_info=True)
            await sio.emit(events.MESSAGE_ERROR, {"id": msg_id, "error": str(e)}, to=sid)
            session.pending_user_message = None
            session.pending_message_id = None
        finally:
            await sio.emit(events.AGENT_TYPING, {"isTyping": False}, to=sid)

    @sio.on(events.RESUME)
    @traceable(name="socket.resume", run_type="chain")
    async def on_resume(sid, data):
        """
        data: {id: str, approved: bool}
        Resume a paused human-approval interrupt.
        """
        session = get_session(sid)
        if not session:
            return

        approved: bool = bool(data.get("approved", False))
        conversation_id = session.conversation_id or f"conv-{sid[:8]}"
        config = {"configurable": {"thread_id": conversation_id}}
        msg_id = data.get("id") or nanoid.generate()

        await sio.emit(events.AGENT_TYPING, {"isTyping": True}, to=sid)

        try:
            result = await agent_graph.ainvoke(Command(resume=approved), config=config)

            reply = ""
            for msg in reversed(result.get("messages", [])):
                if hasattr(msg, "content") and not isinstance(msg, HumanMessage):
                    reply = str(msg.content)
                    break

            reply_id = nanoid.generate()
            await _stream_chunks(sid, reply_id, reply)

            from app.types.chat import build_complete_message
            complete_msg = build_complete_message(msg_id=reply_id, content=reply, result=result)
            await sio.emit(events.MESSAGE_COMPLETE, {"message": complete_msg}, to=sid)

            if session.user_email and session.pending_user_message:
                await conv_manager.save_turn(
                    conversation_id=conversation_id,
                    user_email=session.user_email,
                    user_message=session.pending_user_message,
                    assistant_reply=reply,
                    intent=result.get("intent"),
                    result=result,
                )
                await conv_manager.close(session.user_email)

            session.pending_user_message = None
            session.pending_message_id = None

        except Exception as e:
            app_logger.error("Socket resume error: {e}", e=str(e), exc_info=True)
            await sio.emit(events.MESSAGE_ERROR, {"id": msg_id, "error": str(e)}, to=sid)
        finally:
            await sio.emit(events.AGENT_TYPING, {"isTyping": False}, to=sid)


async def _run_graph(
    sid: str,
    msg_id: str,
    agent_graph,
    initial_state: dict,
    config: dict,
) -> Optional[dict]:
    """
    Run the agent graph. Emits tool:start / tool:done / tool:failed events
    by streaming graph node transitions via astream_events.
    Returns final result dict, or None if interrupted.
    """
    tool_index = 0
    tool_plan: list = []
    result: dict = {}

    async for event in agent_graph.astream_events(initial_state, config=config, version="v2"):
        kind = event.get("event")
        name = event.get("name", "")
        data = event.get("data", {})

        if kind == "on_chain_start" and name == "tool_planner_node":
            # Reset tool tracking when planner fires
            tool_index = 0
            tool_plan = []

        elif kind == "on_chain_end" and name == "tool_planner_node":
            output = data.get("output") or {}
            tool_plan = output.get("tool_plan") or []

        elif kind == "on_chain_start" and name == "tool_executor_node":
            if tool_plan and tool_index < len(tool_plan):
                tool_name = tool_plan[tool_index]
                await sio.emit(events.TOOL_START, {
                    "tool": tool_name,
                    "index": tool_index,
                    "total": len(tool_plan),
                }, to=sid)

        elif kind == "on_chain_end" and name == "tool_executor_node":
            output = data.get("output") or {}
            history = output.get("tool_history") or []
            if history:
                last = history[-1]
                if last.get("status") in ("success",):
                    await sio.emit(events.TOOL_DONE, {
                        "tool": last["tool"],
                        "index": tool_index,
                    }, to=sid)
                else:
                    await sio.emit(events.TOOL_FAILED, {
                        "tool": last["tool"],
                        "index": tool_index,
                        "error": str(last.get("result", {}).get("message", "failed")),
                    }, to=sid)
                tool_index += 1

        elif kind == "on_chain_end" and name == "LangGraph":
            # Final graph output
            output = data.get("output") or {}
            result = output

    # Check if graph was interrupted (human approval)
    if result.get("confirmation_required") and not result.get("confirmed"):
        await sio.emit(events.INTERRUPT, {
            "id": msg_id,
            "prompt": result.get("confirmation_prompt", "Please confirm this action."),
        }, to=sid)
        return None

    return result
