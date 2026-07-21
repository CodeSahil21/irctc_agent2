# app/api/routes.py
from fastapi import APIRouter
from app.api.health import router as health_router
from app.api.chat import router as chat_router

# Central API Router
api_router = APIRouter()

# Register endpoint modules here
api_router.include_router(health_router, prefix="/api/v1",tags=["Health"])
api_router.include_router(chat_router, prefix="/api/v1")