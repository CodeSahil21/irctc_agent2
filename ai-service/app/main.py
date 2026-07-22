import uvicorn
import socketio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import api_router
from app.config.settings import get_settings
from app.core.handlers import register_exception_handlers
from app.core.lifespan import lifespan
from app.telemetry.logging import app_logger, setup_logging
from app.websocket.manager import sio

setup_logging()

settings = get_settings()

_fastapi_app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    lifespan=lifespan,
    docs_url="/docs" if settings.app_env.lower() != "production" else None,
    redoc_url="/redoc" if settings.app_env.lower() != "production" else None,
)

_fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3001", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


register_exception_handlers(_fastapi_app)

_fastapi_app.include_router(api_router)

app = socketio.ASGIApp(sio, other_asgi_app=_fastapi_app)


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
    )
