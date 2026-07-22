import json
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage
from langsmith import traceable
from langgraph.types import Command

from app.api.dependencies import get_agent_graph, get_chat_service, get_conversation_manager
from app.schemas.chat import AgentRequest, ChatRequest, ChatResponse
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
            error_payload = json.dumps({"error": str(e)})
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
    description="Runs the full agent graph: intent → slot filling → tool planning → execution → response.",
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
            initial_state = {
                "messages": [HumanMessage(content=request.message)],
                "travel": request.travel_context or {},
                "user_email": request.user_email,
                "user_name": request.user_name,
                "user_preferences": user_preferences,
                "search_results": request.search_results,
                "selected_train": request.selected_train,
                "availability": request.availability,
                "fare": request.fare,
                "passengers": request.passengers,
                "booking": request.booking,
            }
            result = await agent_graph.ainvoke(initial_state, config=config)
    except Exception as e:
        app_logger.error("Agent graph error: {error}", error=str(e), exc_info=True)
        raise
    
    messages = result.get("messages", [])
    reply = ""
    for msg in reversed(messages):
        if hasattr(msg, "content") and not isinstance(msg, HumanMessage):
            reply = str(msg.content)
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