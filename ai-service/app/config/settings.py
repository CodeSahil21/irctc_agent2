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

    @field_validator("anthropic_api_key")
    @classmethod
    def validate_key(cls, v: str) -> str:
        if not v or not v.startswith("sk-ant"):
            raise ValueError("ANTHROPIC_API_KEY must be set and start with 'sk-ant'")
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()