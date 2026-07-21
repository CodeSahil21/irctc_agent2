import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import api_router
from app.config.settings import get_settings
from app.core.handlers import register_exception_handlers
from app.core.lifespan import lifespan
from app.telemetry.logging import app_logger, setup_logging

# 1. Initialize custom logging
setup_logging()

# 2. Load application settings
settings = get_settings()

# 3. Instantiate FastAPI app
app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    lifespan=lifespan,
    docs_url="/docs" if settings.app_env.lower() != "production" else None,
    redoc_url="/redoc" if settings.app_env.lower() != "production" else None,
)

# 4. Configure CORS Middleware (required for web clients and SSE streaming)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict to specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 5. Register central error handlers
register_exception_handlers(app)

# 6. Include API routers
app.include_router(api_router)


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
    )