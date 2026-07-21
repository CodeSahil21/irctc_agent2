from fastapi import FastAPI
from app.config.settings import get_settings
from app.telemetry.logging import setup_logging, app_logger
from app.core.lifespan import lifespan  # or wherever your lifespan.py lives!
from app.api.routes import api_router
from app.core.handlers import register_exception_handlers

# 1. Initialize custom logging
setup_logging()

# 2. Load application settings
settings = get_settings()

# 3. Instantiate FastAPI app directly
app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    lifespan=lifespan,
    docs_url="/docs" if settings.app_env.lower() != "production" else None,
    redoc_url="/redoc" if settings.app_env.lower() != "production" else None,
)

# Register central error handlers
register_exception_handlers(app)

# 4. Include API routers
app.include_router(api_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)