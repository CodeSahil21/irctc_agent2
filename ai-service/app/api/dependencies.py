from typing import AsyncGenerator
from fastapi import Request
from app.config.settings import Settings, get_settings


# 1. Settings Dependency
def get_app_settings() -> Settings:
    """Injects application configuration settings."""
    return get_settings()


# 2. Redis Client Dependency (Stub)
async def get_redis(request: Request):
    """
    Provides a Redis client instance from app state.
    (Will be populated when Redis connection pool is added to lifespan.py)
    """
    # return request.app.state.redis
    yield None


# 3. Database Session Dependency (Stub)
async def get_db_session() -> AsyncGenerator[None, None]:
    """
    Yields an async database session per request and handles cleanup.
    """
    # async with AsyncSessionLocal() as session:
    #     yield session
    yield None


# 4. LLM / Agent Client Dependency (Stub)
async def get_claude_client(request: Request):
    """
    Provides an initialized Anthropic/Claude client instance.
    """
    # return request.app.state.claude_client
    yield None


# 5. MCP (Model Context Protocol) Client Dependency (Stub)
async def get_mcp_client(request: Request):
    """
    Provides an MCP client for external tool execution.
    """
    # return request.app.state.mcp_client
    yield None