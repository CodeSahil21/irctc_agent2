from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_conversation_manager

router = APIRouter(prefix="/conversations", tags=["Conversations"])


@router.get("/{conversation_id}/messages")
async def get_conversation_messages(
    conversation_id: str,
    limit: int = 50,
    conv_manager=Depends(get_conversation_manager),
) -> dict:
    messages = await conv_manager.get_history(conversation_id, limit=limit)
    return {"conversation_id": conversation_id, "messages": messages}


@router.get("/{conversation_id}/context")
async def get_conversation_context(
    conversation_id: str,
    conv_manager=Depends(get_conversation_manager),
) -> dict:
    """Returns summary + recent messages — used by client on conversation resume."""
    context = await conv_manager.build_context(conversation_id)
    return {"conversation_id": conversation_id, **context}


@router.get("/user/{user_email}")
async def get_user_conversations(
    user_email: str,
    limit: int = 20,
    conv_manager=Depends(get_conversation_manager),
) -> dict:
    conversations = await conv_manager.get_recent(user_email, limit=limit)
    return {"user_email": user_email, "conversations": conversations}


@router.post("/{conversation_id}/summarize")
async def trigger_summarize(
    conversation_id: str,
    conv_manager=Depends(get_conversation_manager),
) -> dict:
    """Manually trigger summarization for a conversation."""
    summary = await conv_manager.summarize(conversation_id)
    if summary is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Summarization unavailable or conversation not found.",
        )
    return {"conversation_id": conversation_id, "summary": summary}
