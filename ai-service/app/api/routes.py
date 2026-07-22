from fastapi import APIRouter
from app.api.health import router as health_router
from app.api.chat import router as chat_router
from app.api.conversations import router as conversations_router

api_router = APIRouter()

api_router.include_router(health_router, prefix="/api/v1", tags=["Health"])
api_router.include_router(chat_router, prefix="/api/v1")
api_router.include_router(conversations_router, prefix="/api/v1")