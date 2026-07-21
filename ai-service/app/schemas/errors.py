from datetime import datetime, timezone
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    code: str = Field(..., description="Machine-readable error code (e.g., NOT_FOUND, VALIDATION_ERROR)")
    message: str = Field(..., description="Human-readable description of the error")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Additional context or validation details")


class ErrorResponse(BaseModel):
    success: bool = Field(default=False, description="Always False for error responses")
    error: ErrorDetail
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 UTC timestamp",
    )