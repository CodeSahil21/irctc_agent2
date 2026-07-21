import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from anthropic import AsyncAnthropic
from langsmith import Client
from langsmith.wrappers import wrap_anthropic

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
    api_key = (
        getattr(settings, "langsmith_api_key", None) 
        or getattr(settings, "langchain_api_key", None)
    )
    tracing_enabled = (
        getattr(settings, "langsmith_tracing", False) 
        or getattr(settings, "langchain_tracing_v2", False)
    )
    project_name = (
        getattr(settings, "langsmith_project", None) 
        or getattr(settings, "langchain_project", "default")
    )
    endpoint = getattr(settings, "langsmith_endpoint", "https://api.smith.langchain.com")

    # Clean double quotes if they were set in .env
    project_name = project_name.strip('"')

    # 2. Export environment variables directly into os.environ for LangSmith SDK
    if tracing_enabled and api_key:
        os.environ["LANGSMITH_TRACING"] = "true"
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGSMITH_API_KEY"] = api_key
        os.environ["LANGSMITH_PROJECT"] = project_name
        os.environ["LANGSMITH_ENDPOINT"] = endpoint

        app_logger.info(
            "LangSmith tracing initialized for project: {project}", 
            project=project_name
        )
    else:
        app_logger.warning("LangSmith tracing is DISABLED (missing API key or tracing flag is false).")

    # 3. Initialize Anthropic client
    raw_client = AsyncAnthropic(api_key=settings.anthropic_api_key)

    # 4. Wrap client if tracing is enabled
    if tracing_enabled and api_key:
        app.state.claude_client = wrap_anthropic(raw_client)
    else:
        app.state.claude_client = raw_client

    yield  

    app_logger.info("Cleaning up resources for {app_name}...", app_name=settings.app_name)
    if tracing_enabled and api_key:
        try:
            app_logger.info("Flushing pending LangSmith traces...")
            ls_client = Client()
            ls_client.flush()
            app_logger.info("LangSmith traces flushed successfully.")
        except Exception as e:
            app_logger.error("Error flushing LangSmith traces: {error}", error=str(e))

    # 6. Close client connection on shutdown
    await app.state.claude_client.close()
    
    app_logger.info("Shutdown complete.")