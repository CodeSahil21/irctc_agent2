import json
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage
from langsmith import traceable
from langgraph.types import Command

from app.api.dependencies import get_agent_graph, get_chat_service, get_conversation_manager
from app.core.exceptions import BaseAPIException
from app.schemas.chat import AgentRequest, ChatRequest, ChatResponse
from app.services.chat import ChatService
from app.telemetry.logging import app_logger


def _safe_stream_error(exc: Exception) -> str:
    """Return a safe user-facing error string for SSE payloads."""
    if isinstance(exc, BaseAPIException):
        return exc.message
    return "Something went wrong. Please try again."

router = APIRouter()

@router.post(
    "/chat",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Send a message to LLM (Non-streaming)",
    description="Validates input, sends conversation history to ChatService, and returns a JSON response.",
)
@traceable(name="POST /chat", run_type="chain")
async def create_chat_completion(
    request: ChatRequest,
    chat_service: ChatService = Depends(get_chat_service),
) -> ChatResponse:
    """
    HTTP Request -> Validate Request -> Call Service -> Return JSON Response
    """
    message = request.message.strip()
    if not message:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Message cannot be empty.")

    history_dicts = (
        [msg.model_dump() for msg in request.conversation_history]
        if request.conversation_history
        else None
    )

    return await chat_service.send_message(
        message=message,
        conversation_id=request.conversation_id,
        conversation_history=history_dicts,
        system_prompt=request.system_prompt,
        temperature=request.temperature,
        max_tokens=request.max_tokens,
    )



@router.post(
    "/chat/stream",
    summary="Stream LLM response token-by-token",
    description="Establishes an SSE stream emitting JSON tokens in real-time.",
)
async def stream_chat_completion(
    request: ChatRequest,
    chat_service: ChatService = Depends(get_chat_service),
) -> StreamingResponse:
    """
    HTTP Request -> Validate Request -> Stream Tokens (JSON SSE) -> Finish Signal
    """

    async def event_generator():
        try:
            message = request.message.strip()
            if not message:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Message cannot be empty.")

            history_dicts = (
                [msg.model_dump() for msg in request.conversation_history]
                if request.conversation_history
                else None
            )
            async for token in chat_service.stream_message(
                message=message,
                conversation_history=history_dicts,
                system_prompt=request.system_prompt,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
            ):
                payload = json.dumps({"content": token})
                yield f"data: {payload}\n\n"

            # Signal end of stream
            done_payload = json.dumps({"done": True})
            yield f"data: {done_payload}\n\n"

        except Exception as e:
            app_logger.error("Error during streaming execution: {error}", error=str(e), exc_info=True)
            error_payload = json.dumps({"error": _safe_stream_error(e)})
            yield f"data: {error_payload}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  
        },
    )


@router.post(
    "/agent",
    status_code=status.HTTP_200_OK,
    summary="Run the IRCTC LangGraph agent",
    description="Runs the full agent graph: agent loop → tool execution → reflection → response.",
)
@traceable(name="POST /agent", run_type="chain")
async def run_agent(
    request: AgentRequest,
    agent_graph=Depends(get_agent_graph),
    conv_manager=Depends(get_conversation_manager),
) -> dict:
    conversation_id = request.conversation_id or "default"
    config = {"configurable": {"thread_id": conversation_id}}

    # Phase 10 — open conversation (loads prefs, creates/loads conv doc)
    user_preferences = None
    if request.user_email:
        conv = await conv_manager.open(
            conversation_id=conversation_id,
            user_email=request.user_email,
            user_name=request.user_name,
        )
        user_preferences = conv.get("preferences")

    try:
        if request.resume:
            resume_value = request.resume_value if request.resume_value is not None else True
            result = await agent_graph.ainvoke(Command(resume=resume_value), config=config)
        else:
            # Only include fields that have real values — passing None for any
            # field overwrites the checkpointed value (last-write-wins reducer).
            # messages is the only field safe to always include (add_messages reducer).
            initial_state: Dict[str, Any] = {
                "messages": [HumanMessage(content=request.message)],
            }
            if request.user_email is not None:
                initial_state["user_email"] = request.user_email
            if request.user_name is not None:
                initial_state["user_name"] = request.user_name
            if user_preferences is not None:
                initial_state["user_preferences"] = user_preferences
            if request.search_results is not None:
                initial_state["search_results"] = request.search_results
            if request.selected_train is not None:
                initial_state["selected_train"] = request.selected_train
            if request.availability is not None:
                initial_state["availability"] = request.availability
            if request.fare is not None:
                initial_state["fare"] = request.fare
            if request.passengers is not None:
                initial_state["passengers"] = request.passengers
            if request.booking is not None:
                initial_state["booking"] = request.booking
            result = await agent_graph.ainvoke(initial_state, config=config)
    except BaseAPIException:
        raise
    except Exception as e:
        app_logger.error("Agent graph error: {error}", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The agent could not process your request. Please try again.",
        ) from e

    # ── Detect human-approval interrupt ──────────────────────────────────────
    # ainvoke returns normally when the graph hits interrupt() — it does NOT
    # raise an exception.  The signal is: pending_tool_calls is non-empty AND
    # one of them is a destructive tool that requires confirmation.
    _DESTRUCTIVE = {"book_ticket", "cancel_ticket", "update_booking",
                    "manage_reminder", "add_saved_passenger", "delete_saved_passenger"}
    pending_calls = result.get("pending_tool_calls") or []
    needs_approval = any(p.get("name") in _DESTRUCTIVE for p in pending_calls)
    if needs_approval and not result.get("confirmed"):
        # Read the confirmation prompt from the checkpointed interrupt value.
        # Build it ourselves from the pending call if not already in state.
        prompt = result.get("confirmation_prompt") or ""
        if not prompt and pending_calls:
            from app.graph.tool_meta import build_confirmation_prompt
            p = pending_calls[0]
            prompt = build_confirmation_prompt(p["name"], p.get("args") or {})
        return {
            "message": prompt,
            "intent": result.get("intent"),
            "travel_context": result.get("travel"),
            "search_results": result.get("ranked_results") or result.get("search_results"),
            "selected_train": result.get("selected_train"),
            "availability": result.get("availability"),
            "fare": result.get("fare"),
            "booking": result.get("booking"),
            "confirmation_required": True,
            "confirmation_prompt": prompt,
            "interrupted": True,
            "errors": result.get("errors") or [],
        }

    messages = result.get("messages", [])
    reply = ""

    from langchain_core.messages import ToolMessage as _ToolMessage

    last_human_idx = -1
    for i, msg in enumerate(messages):
        if isinstance(msg, HumanMessage):
            last_human_idx = i
    current_turn = messages[last_human_idx + 1:] if last_human_idx >= 0 else messages
    for msg in reversed(current_turn):
        if isinstance(msg, (HumanMessage, _ToolMessage)):
            continue
        c = getattr(msg, "content", None)
        if c and str(c).strip():
            reply = str(c).strip()
            break

    if request.user_email and not request.resume:
        await conv_manager.save_turn(
            conversation_id=conversation_id,
            user_email=request.user_email,
            user_message=request.message,
            assistant_reply=reply,
            intent=result.get("intent"),
            result=result,
            user_name=request.user_name,
        )
        await conv_manager.close(request.user_email, prefs=result.get("user_preferences"))

    interrupted = result.get("confirmation_required") and not result.get("confirmed")

    return {
        "message": reply,
        "intent": result.get("intent"),
        "travel_context": result.get("travel"),
        "search_results": result.get("ranked_results") or result.get("search_results"),
        "selected_train": result.get("selected_train"),
        "availability": result.get("availability"),
        "fare": result.get("fare"),
        "booking": result.get("booking"),
        "confirmation_required": result.get("confirmation_required"),
        "confirmation_prompt": result.get("confirmation_prompt"),
        "interrupted": interrupted,
        "errors": result.get("errors") or [],
    }