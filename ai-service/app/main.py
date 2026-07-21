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

# 1. Initialize custom logging
setup_logging()

# 2. Load application settings
settings = get_settings()

# 3. Instantiate FastAPI app
_fastapi_app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    lifespan=lifespan,
    docs_url="/docs" if settings.app_env.lower() != "production" else None,
    redoc_url="/redoc" if settings.app_env.lower() != "production" else None,
)

# 4. Configure CORS Middleware
_fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 5. Register central error handlers
register_exception_handlers(_fastapi_app)

# 6. Include API routers
_fastapi_app.include_router(api_router)

# 7. Mount Socket.IO alongside FastAPI under the same ASGI app
#    Socket.IO handles /socket.io/*, FastAPI handles everything else.
app = socketio.ASGIApp(sio, other_asgi_app=_fastapi_app)


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
    )
