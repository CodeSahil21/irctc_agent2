import json
from typing import Any
from fastapi import APIRouter, Depends, status
from fastapi.responses import StreamingResponse
from langsmith import traceable

from app.api.dependencies import get_chat_service
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat import ChatService
from app.telemetry.logging import app_logger

router = APIRouter()

@router.post(
    "/chat",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Send a message to Claude (Non-streaming)",
    description="Validates input, sends conversation history to ChatService, and returns a JSON response.",
)
# 2. Add @traceable decorator to trace the sync endpoint
@traceable(name="POST /chat", run_type="chain")
async def create_chat_completion(
    request: ChatRequest,
    chat_service: ChatService = Depends(get_chat_service),
) -> ChatResponse:
    """
    HTTP Request -> Validate Request -> Call Service -> Return JSON Response
    """
    history_dicts = (
        [msg.model_dump() for msg in request.conversation_history]
        if request.conversation_history
        else None
    )

    return await chat_service.send_message(
        message=request.message,
        conversation_id=request.conversation_id,
        conversation_history=history_dicts,
        system_prompt=request.system_prompt,
        temperature=request.temperature,
        max_tokens=request.max_tokens,
    )



@router.post(
    "/chat/stream",
    summary="Stream Claude response token-by-token",
    description="Establishes an SSE stream emitting JSON tokens in real-time.",
)

@traceable(name="POST /chat/stream", run_type="chain")
async def stream_chat_completion(
    request: ChatRequest,
    chat_service: ChatService = Depends(get_chat_service),
) -> StreamingResponse:
    """
    HTTP Request -> Validate Request -> Stream Tokens (JSON SSE) -> Finish Signal
    """

    async def event_generator():
        try:
            history_dicts = (
                [msg.model_dump() for msg in request.conversation_history]
                if request.conversation_history
                else None
            )

            # Stream tokens directly as they arrive from ChatService
            async for token in chat_service.stream_message(
                message=request.message,
                conversation_history=history_dicts,
                system_prompt=request.system_prompt,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
            ):
                # Send JSON-encoded frame (handles newlines & quotes cleanly)
                payload = json.dumps({"content": token})
                yield f"data: {payload}\n\n"

            # Signal end of stream
            done_payload = json.dumps({"done": True})
            yield f"data: {done_payload}\n\n"

        except Exception as e:
            app_logger.error(f"Error during streaming execution: {str(e)}", exc_info=True)
            error_payload = json.dumps({"error": str(e)})
            yield f"data: {error_payload}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disables nginx proxy buffering
        },
    )