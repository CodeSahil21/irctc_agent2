from fastapi import FastAPI

from .api.chat import router as chat_router
from .api.health import router as health_router
from .api.websocket import router as websocket_router

app = FastAPI(title="AI Service", version="0.1.0")

app.include_router(health_router)
app.include_router(chat_router)
app.include_router(websocket_router)


@app.get("/")
async def root() -> dict[str, str]:
    return {"service": "ai-service", "status": "ok"}