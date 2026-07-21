from typing import Dict, Optional
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(
        default="ok",
        description="Overall application health status",
        examples=["ok"],
    )
    environment: Optional[str] = Field(
        default=None,
        description="Current running environment (e.g., development, production)",
        examples=["development"],
    )
    services: Optional[Dict[str, str]] = Field(
        default=None,
        description="Status of connected external services (e.g., redis, db, llm)",
        examples=[{"database": "healthy", "redis": "healthy"}],
    )