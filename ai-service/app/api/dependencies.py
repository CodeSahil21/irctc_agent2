from fastapi import Depends, Request, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.config.settings import Settings, get_settings
from app.mcp.client import MCPClient
from app.mcp.registry import MCPToolRegistry
from app.services.openai_service import OpenAIService
from app.services.chat import ChatService


def get_app_settings() -> Settings:
    """Injects application configuration settings."""
    return get_settings()

def get_llm_service(request: Request) -> OpenAIService:
    service = getattr(request.app.state, "llm_service", None)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OpenAIService was not initialized on application state.",
        )
    return service


def get_chat_service(llm_service: OpenAIService = Depends(get_llm_service)) -> ChatService:
    return ChatService(llm_service=llm_service)

def get_agent_graph(request: Request):
    graph = getattr(request.app.state, "agent_graph", None)
    if graph is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Agent graph was not initialized on application state.",
        )
    return graph

def get_mcp_client(request: Request) -> MCPClient:
    client = getattr(request.app.state, "mcp_client", None)
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="MCPClient was not initialized on application state.",
        )
    return client

def get_mcp_registry(request: Request) -> MCPToolRegistry:
    registry = getattr(request.app.state, "mcp_registry", None)
    if registry is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="MCPToolRegistry was not initialized on application state.",
        )
    return registry

def get_checkpointer(request: Request):
    checkpointer = getattr(request.app.state, "checkpointer", None)
    if checkpointer is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Checkpointer was not initialized on application state.",
        )
    return checkpointer


def get_db(request: Request) -> AsyncIOMotorDatabase:
    db = getattr(request.app.state, "db", None)
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="MongoDB database was not initialized on application state.",
        )
    return db


def get_conversation_manager(request: Request):
    manager = getattr(request.app.state, "conversation_manager", None)
    if manager is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ConversationManager was not initialized on application state.",
        )
    return manager