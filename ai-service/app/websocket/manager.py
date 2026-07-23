import asyncio
from typing import Optional
import nanoid
import socketio
from langchain_core.messages import HumanMessage
from langgraph.types import Command
from langsmith import traceable

from app.auth.jwt import extract_user_from_token
from app.config.settings import get_settings
from app.core.exceptions import BaseAPIException
from app.websocket import events
from app.websocket.connections import create_session, get_session, remove_session
from app.telemetry.logging import app_logger


def _safe_error_message(exc: Exception) -> str:
    if isinstance(exc, BaseAPIException):
        return exc.message
    return "Something went wrong. Please try again."

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
    @traceable(name="WebSocket Chat Turn", run_type="chain")
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
        user_preferences = None
        if session.user_email:
            conv = await conv_manager.open(
                conversation_id=conversation_id,
                user_email=session.user_email,
                user_name=session.user_name,
            )
            user_preferences = conv.get("preferences")

        try:
            # Only pass fields that have real values.
            # LangGraph merges initial_state into the checkpoint using each
            # field's reducer.  All fields except `messages` use last-write-wins,
            # so passing None for any field OVERWRITES the checkpointed value and
            # causes the agent to "forget" search results, fare, train, etc.
            initial_state = {
                k: v for k, v in {
                    "messages": [HumanMessage(content=content)],
                    "user_email": session.user_email,
                    "user_name": session.user_name,
                    "user_preferences": user_preferences,
                }.items() if v is not None
            }
            _YES = {"yes", "y", "yep", "yeah", "sure", "go ahead", "proceed",
                    "confirm", "ok", "okay", "book it", "do it", "absolutely"}
            _NO  = {"no", "n", "nope", "cancel", "stop", "don't", "dont"}
            content_stripped = content.lower().strip().rstrip("!.").strip()
            is_yes = content_stripped in _YES or content_stripped.startswith(
                ("yes ", "go ahead", "proceed", "confirm and", "yes confirm", "yes book")
            )
            is_no = content_stripped in _NO

            if (is_yes or is_no) and session.interrupted:
                approved = is_yes
                session.interrupted = False
                app_logger.info(
                    "Auto-resuming interrupted graph | approved={approved} | sid={sid}",
                    approved=approved, sid=sid,
                )
                try:
                    result = await agent_graph.ainvoke(
                        Command(resume=approved),
                        config=config,
                    )
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
                    if session.user_email:
                        await conv_manager.save_turn(
                            conversation_id=conversation_id,
                            user_email=session.user_email,
                            user_message=content,
                            assistant_reply=reply,
                            intent=result.get("intent"),
                            result=result,
                            user_name=session.user_name,
                        )
                        await conv_manager.close(session.user_email, prefs=result.get("user_preferences"))
                    session.pending_user_message = None
                    session.pending_message_id = None
                    return
                except Exception as e:
                    app_logger.error("Auto-resume error: {e}", e=str(e), exc_info=True)
                    # Fall through to normal flow if resume fails
                finally:
                    await sio.emit(events.AGENT_TYPING, {"isTyping": False}, to=sid)
                return

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
                    user_name=session.user_name,
                )
                await conv_manager.close(session.user_email, prefs=result.get("user_preferences"))

            session.pending_user_message = None
            session.pending_message_id = None

        except Exception as e:
            app_logger.error("Socket query error: {e}", e=str(e), exc_info=True)
            await sio.emit(events.MESSAGE_ERROR, {"id": msg_id, "error": _safe_error_message(e)}, to=sid)
            session.pending_user_message = None
            session.pending_message_id = None
        finally:
            await sio.emit(events.AGENT_TYPING, {"isTyping": False}, to=sid)

    @sio.on(events.RESUME)
    @traceable(name="WebSocket Resume Turn", run_type="chain")
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
        session.interrupted = False  # clear interrupt state

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
                    user_name=session.user_name,
                )
                await conv_manager.close(session.user_email, prefs=result.get("user_preferences"))

            session.pending_user_message = None
            session.pending_message_id = None

        except Exception as e:
            app_logger.error("Socket resume error: {e}", e=str(e), exc_info=True)
            await sio.emit(events.MESSAGE_ERROR, {"id": msg_id, "error": _safe_error_message(e)}, to=sid)
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
    by watching tool_executor_node output via astream_events.

    New architecture: tool_planner_node no longer exists. The agent_node emits
    pending_tool_calls each loop; tool_executor_node runs them and appends to
    tool_history. We derive tool names and status directly from tool_history
    diffs rather than a pre-declared tool_plan list.

    Returns final result dict, or None if interrupted.
    """
    # Track tool_history length across executor firings so we can emit events
    # for only the NEW entries added by each executor invocation.
    seen_tool_count = 0
    result: dict = {}

    async for event in agent_graph.astream_events(initial_state, config=config, version="v2"):
        kind = event.get("event")
        name = event.get("name", "")
        data = event.get("data", {})

        if kind == "on_chain_start" and name == "agent_node":
            # Emit pending tool names when agent fires a new batch of calls.
            # We don't have results yet — just signal what's about to run.
            input_state = data.get("input") or {}
            pending = input_state.get("pending_tool_calls") or []
            for i, p in enumerate(pending):
                await sio.emit(events.TOOL_START, {
                    "tool": p.get("name", "unknown"),
                    "index": seen_tool_count + i,
                    "total": seen_tool_count + len(pending),
                }, to=sid)

        elif kind == "on_chain_end" and name == "tool_executor_node":
            output = data.get("output") or {}
            history = output.get("tool_history") or []
            # Only process entries added by this executor call
            new_entries = history[seen_tool_count:]
            for i, entry in enumerate(new_entries):
                idx = seen_tool_count + i
                if entry.get("status") == "success":
                    await sio.emit(events.TOOL_DONE, {
                        "tool": entry.get("tool", "unknown"),
                        "index": idx,
                    }, to=sid)
                else:
                    result_payload = entry.get("result") or {}
                    await sio.emit(events.TOOL_FAILED, {
                        "tool": entry.get("tool", "unknown"),
                        "index": idx,
                        "error": str(result_payload.get("message", "failed")),
                    }, to=sid)
            seen_tool_count = len(history)

        elif kind == "on_chain_end" and name == "LangGraph":
            output = data.get("output") or {}
            result = output

    # Check if graph was interrupted (human approval pending).
    # Interrupt is fired when confirmation_required is set but the destructive
    # tool has not run yet (confirmed is False/None).
    tool_history = result.get("tool_history") or []
    destructive_tools = {"book_ticket", "cancel_ticket", "update_booking", "manage_reminder"}
    destructive_ran = any(t.get("tool") in destructive_tools for t in tool_history)

    if result.get("confirmation_required") and not result.get("confirmed") and not destructive_ran:
        session = get_session(sid)
        if session:
            session.interrupted = True
        await sio.emit(events.INTERRUPT, {
            "id": msg_id,
            "prompt": result.get("confirmation_prompt", "Please confirm this action."),
        }, to=sid)
        return None

    return result
