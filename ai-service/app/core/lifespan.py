import os
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from anthropic import AsyncAnthropic
from langsmith import Client
from langsmith.wrappers import wrap_anthropic

from app.config.settings import get_settings
from app.db.mongo import create_mongo_client, get_db
from app.db.repositories.conversation_repo import setup_indexes as conv_indexes
from app.db.repositories.preference_repo import setup_indexes as pref_indexes
from app.db.repositories.execution_repo import setup_indexes as exec_indexes
from app.graph.builder import create_agent_graph
from app.mcp.client import MCPClient
from app.mcp.discovery import MCPDiscovery
from app.mcp.registry import MCPToolRegistry
from app.mcp.transport import MCPTransport
from app.memory.checkpoints import get_checkpointer
from app.services.claude import ClaudeService
from app.services.conversation_manager import ConversationManager
from app.telemetry.logging import app_logger
from app.websocket.manager import _make_manager


async def _discover_tools_with_retry(discovery: MCPDiscovery, attempts: int = 5) -> None:
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            await discovery.discover()
            if discovery.has_tools():
                return
        except Exception as exc:
            last_error = exc
            app_logger.warning(
                "MCP discovery attempt failed | attempt={attempt} | error={error}",
                attempt=attempt + 1,
                error=str(exc),
            )
        if attempt < attempts - 1:
            await asyncio.sleep(min(0.5 * (attempt + 1), 2.0))

    if not discovery.has_tools():
        app_logger.warning(
            "MCP discovery finished with no tools; continuing startup and relying on lazy refresh",
        )


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

    # 4. Initialize MCP transport, client, discovery, and registry
    transport = MCPTransport(
        base_url=settings.mcp_server_url,
        timeout=settings.mcp_server_timeout,
    )
    mcp_client = MCPClient(transport=transport)
    await mcp_client.connect()

    discovery = MCPDiscovery(client=mcp_client)
    await _discover_tools_with_retry(discovery)

    app.state.mcp_client = mcp_client
    app.state.mcp_registry = MCPToolRegistry(client=mcp_client, discovery=discovery)
    app_logger.info("MCP registry ready | tools={count}", count=discovery.tool_count)

    # 5. Initialize shared Motor client + database (Phase 9)
    mongo_client = create_mongo_client(settings.mongo_url)
    db = get_db(mongo_client, settings.mongo_db)
    app.state.mongo_client = mongo_client
    app.state.db = db

    # Create indexes for all collections
    await conv_indexes(db)
    await pref_indexes(db)
    await exec_indexes(db)
    app_logger.info("MongoDB collections and indexes ready | db={db}", db=settings.mongo_db)

    # 6. Initialize checkpointer — uses its own sync pymongo client
    checkpointer = get_checkpointer(
        mongo_url=settings.mongo_url,
        mongo_db=settings.mongo_db,
    )
    app.state.checkpointer = checkpointer
    app_logger.info("Checkpointer initialized (MongoDBSaver)")

    # 7. Compile the LangGraph agent with checkpointer
    app.state.agent_graph = create_agent_graph(
        claude_service=app.state.claude_service,
        mcp_registry=app.state.mcp_registry,
        checkpointer=checkpointer,
    )
    app_logger.info("Agent graph compiled successfully.")

    # 8. Init ConversationManager (Phase 10)
    app.state.conversation_manager = ConversationManager(
        db=db,
        claude_service=app.state.claude_service,
    )
    app_logger.info("ConversationManager initialized.")

    # 9. Wire Socket.IO event handlers (Phase 13)
    _make_manager(
        agent_graph=app.state.agent_graph,
        conv_manager=app.state.conversation_manager,
    )
    app_logger.info("Socket.IO manager initialized.")

    app_logger.info(
        "Application startup complete | env={env} | model={model}",
        env=settings.app_env,
        model=settings.anthropic_default_model,
    )

    yield

    # Flush LangSmith traces on shutdown
    app_logger.info("Cleaning up resources for {app_name}...", app_name=settings.app_name)
    if tracing_enabled and api_key:
        try:
            app_logger.info("Flushing pending LangSmith traces...")
            Client().flush()
            app_logger.info("LangSmith traces flushed successfully.")
        except Exception as e:
            app_logger.error("Error flushing LangSmith traces: {error}", error=str(e))

    # Disconnect MCP client
    await mcp_client.disconnect()

    # Close shared Motor client (covers both checkpointer and db)
    mongo_client.close()

    # Close checkpointer's dedicated pymongo client
    if hasattr(app.state.checkpointer, "client"):
        app.state.checkpointer.client.close()

    # Close Anthropic HTTP connection pool
    await app.state.claude_service.close()
    app_logger.info("Shutdown complete.")