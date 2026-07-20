from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str


@router.post("")
async def chat(payload: ChatRequest) -> dict[str, str]:
    return {"message": payload.message, "status": "queued"}