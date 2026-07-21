import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from anthropic import AsyncAnthropic
from langsmith import Client
from langsmith.wrappers import wrap_anthropic

from app.config.settings import get_settings
from app.services.claude import ClaudeService
from app.telemetry.logging import app_logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Async context manager handling application startup and shutdown events.
    Keeps initialization code decoupled from app instantiation.
    """
    settings = get_settings()

    api_key = settings.langsmith_api_key
    tracing_enabled = settings.langsmith_tracing
    project_name = settings.langsmith_project.strip('"')
    endpoint = settings.langsmith_endpoint

    # 1. Configure LangSmith tracing environment variables
    if tracing_enabled and api_key:
        os.environ["LANGSMITH_TRACING"] = "true"
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGSMITH_API_KEY"] = api_key
        os.environ["LANGSMITH_PROJECT"] = project_name
        os.environ["LANGSMITH_ENDPOINT"] = endpoint
        app_logger.info("LangSmith tracing initialized for project: {project}", project=project_name)
    else:
        app_logger.warning("LangSmith tracing is DISABLED (missing API key or tracing flag is false).")

    # 2. Initialize Anthropic client — wrap once here if tracing enabled
    raw_client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    traced_client = wrap_anthropic(raw_client) if (tracing_enabled and api_key) else raw_client

    # 3. Build ClaudeService once and store on app.state for reuse across all requests
    app.state.claude_service = ClaudeService(
        client=traced_client,
        default_model=settings.anthropic_default_model,
    )

    app_logger.info(
        "Application startup complete | env={env} | model={model}",
        env=settings.app_env,
        model=settings.anthropic_default_model,
    )

    yield

    # 4. Flush LangSmith traces on shutdown
    app_logger.info("Cleaning up resources for {app_name}...", app_name=settings.app_name)
    if tracing_enabled and api_key:
        try:
            app_logger.info("Flushing pending LangSmith traces...")
            Client().flush()
            app_logger.info("LangSmith traces flushed successfully.")
        except Exception as e:
            app_logger.error("Error flushing LangSmith traces: {error}", error=str(e))

    # 5. Close Anthropic HTTP connection pool
    await app.state.claude_service.close()
    app_logger.info("Shutdown complete.")