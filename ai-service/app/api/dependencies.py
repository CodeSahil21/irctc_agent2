from typing import AsyncGenerator
from fastapi import Depends, Request, HTTPException, status
from app.config.settings import Settings, get_settings
from app.services.claude import ClaudeService
from app.services.chat import ChatService
from anthropic import AsyncAnthropic


# 1. Settings Dependency
def get_app_settings() -> Settings:
    """Injects application configuration settings."""
    return get_settings()


# 2. Redis Client Dependency (Stub)
async def get_redis(request: Request):
    yield None


# 3. Database Session Dependency (Stub)
async def get_db_session() -> AsyncGenerator[None, None]:
    yield None


# 4. Dependency to get Claude Client
def get_claude_client(request: Request) -> AsyncAnthropic:
    client = getattr(request.app.state, "claude_client", None)
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Claude client was not initialized on application state."
        )
    return client


# 5. Dependency to get ChatService (FIXED HERE)
def get_chat_service(request: Request) -> ChatService:
    raw_client = get_claude_client(request)
    # 1. Wrap raw client into ClaudeService
    claude_service = ClaudeService(client=raw_client)
    # 2. Wrap ClaudeService into ChatService
    return ChatService(claude_service=claude_service)


# 6. MCP (Model Context Protocol) Client Dependency (Stub)
async def get_mcp_client(request: Request):
    yield None