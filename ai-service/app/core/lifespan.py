from contextlib import asynccontextmanager
from fastapi import FastAPI
from anthropic import AsyncAnthropic  # Make sure anthropic is installed
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

    # 1. Initialize Claude client and attach to app state
    app.state.claude_client = AsyncAnthropic(
        api_key=settings.anthropic_api_key  
    )

    yield  

    app_logger.info("Cleaning up resources for {app_name}...", app_name=settings.app_name)
    
    # 2. Close client connection on shutdown
    await app.state.claude_client.close()
    
    app_logger.info("Shutdown complete.")