from fastapi import Depends, Request, HTTPException, status
from app.config.settings import Settings, get_settings
from app.services.claude import ClaudeService
from app.services.chat import ChatService


# 1. Settings Dependency
def get_app_settings() -> Settings:
    """Injects application configuration settings."""
    return get_settings()


# 2. ClaudeService Dependency — pulled from app.state (created once in lifespan)
def get_claude_service(request: Request) -> ClaudeService:
    service = getattr(request.app.state, "claude_service", None)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ClaudeService was not initialized on application state.",
        )
    return service


# 3. ChatService Dependency
def get_chat_service(claude_service: ClaudeService = Depends(get_claude_service)) -> ChatService:
    return ChatService(claude_service=claude_service)


# ── Stubs — uncomment and implement when the layer is built ──────────────────

# 4. Redis Client Dependency
async def get_redis(request: Request):
    yield None


# 5. Database Session Dependency
async def get_db_session(request: Request):
    yield None


# 6. MCP Client Dependency
async def get_mcp_client(request: Request):
    yield None