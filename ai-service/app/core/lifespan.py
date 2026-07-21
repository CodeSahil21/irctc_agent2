# core/lifespan.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.config.settings import get_settings
from app.telemetry.logging import app_logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Async context manager handling application startup and shutdown events.
    Keeps initialization code decoupled from app instantiation.
    """
    settings = get_settings()

    app_logger.info(
        "Initializing {app_name} in [{env}] environment...",
        app_name=settings.app_name,
        env=settings.app_env,
    )

    yield  

    app_logger.info("Cleaning up resources for {app_name}...", app_name=settings.app_name)
    # Place cleanup logic here (e.g., closing DB pools, releasing redis clients)
    app_logger.info("Shutdown complete.")