from functools import lru_cache
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field("ai-service", alias="APP_NAME")
    app_env: str = Field("development", alias="APP_ENV")
    debug: bool = Field(False, alias="DEBUG")
    anthropic_api_key: str = Field(..., alias="ANTHROPIC_API_KEY")
    log_level: str = Field("info", alias="LOG_LEVEL")

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