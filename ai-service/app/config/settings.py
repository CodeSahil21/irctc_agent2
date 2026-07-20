from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "ai-service"
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    jwt_algorithm: str = "HS256"
    jwt_secret: str = "change-me"
    auth_public_key: str | None = None
    auth_jwks_url: str | None = None
    mcp_base_url: str = "http://localhost:3000"
    log_level: str = "info"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()