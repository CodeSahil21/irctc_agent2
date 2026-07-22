# app/config/settings.py
from functools import lru_cache
from typing import Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field("ai-service", alias="APP_NAME")
    app_env: str = Field("development", alias="APP_ENV")
    debug: bool = Field(False, alias="DEBUG")
    anthropic_api_key: str = Field(..., alias="ANTHROPIC_API_KEY")
    anthropic_default_model: str = Field("claude-haiku-4-5", alias="ANTHROPIC_DEFAULT_MODEL")
    log_level: str = Field("INFO", alias="LOG_LEVEL")
    langsmith_tracing: bool = Field(True, alias="LANGSMITH_TRACING")
    langsmith_endpoint: str = Field("https://api.smith.langchain.com", alias="LANGSMITH_ENDPOINT")
    langsmith_api_key: Optional[str] = Field(None, alias="LANGSMITH_API_KEY")
    langsmith_project: str = Field("default", alias="LANGSMITH_PROJECT")

    # JWT (shared secret with auth-service for cookie verification)
    jwt_secret: str = Field("change-me", alias="JWT_SECRET")
    jwt_algorithm: str = Field("HS256", alias="JWT_ALGORITHM")

    # MCP Server
    mcp_server_url: str = Field("http://localhost:3000", alias="MCP_SERVER_URL")
    mcp_server_timeout: float = Field(30.0, alias="MCP_SERVER_TIMEOUT")

    # MongoDB
    mongo_url: str = Field("mongodb://localhost:27017", alias="MONGO_URL")
    mongo_db: str = Field("irctc_ai", alias="MONGO_DB")

    @field_validator("anthropic_api_key")
    @classmethod
    def validate_key(cls, v: str) -> str:
        if not v or not v.startswith("sk-ant"):
            raise ValueError("ANTHROPIC_API_KEY must be set and start with 'sk-ant'")
        return v

    @field_validator("jwt_secret")
    @classmethod
    def validate_jwt_secret(cls, v: str) -> str:
        import warnings
        if v == "change-me":
            warnings.warn(
                "JWT_SECRET is set to the insecure default 'change-me'. "
                "Set a strong secret in your .env file before deploying.",
                stacklevel=2,
            )
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()