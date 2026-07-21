from typing import Any, Dict, Optional
from fastapi import status


class BaseAPIException(Exception):
    """Base class for all application-specific exceptions."""

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_SERVER_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details
        super().__init__(message)


class NotFoundException(BaseAPIException):
    def __init__(self, message: str = "Resource not found", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
            details=details,
        )


class ValidationException(BaseAPIException):
    def __init__(self, message: str = "Invalid request payload", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details,
        )


# =====================================================================
# Claude / Model Provider Exceptions
# =====================================================================

class ModelProviderException(BaseAPIException):
    """Raised when the LLM provider encounters an internal or upstream error."""

    def __init__(self, message: str = "Model provider error occurred", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="MODEL_PROVIDER_ERROR",
            status_code=status.HTTP_502_BAD_GATEWAY,
            details=details,
        )


class RateLimitException(BaseAPIException):
    """Raised when requests exceed provider rate limits or token quotas."""

    def __init__(self, message: str = "Rate limit exceeded. Please try again later.", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="RATE_LIMIT_EXCEEDED",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            details=details,
        )


class ServiceUnavailableException(BaseAPIException):
    """Raised when the provider is unreachable, timing out, or down."""

    def __init__(self, message: str = "LLM provider is currently unreachable", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="SERVICE_UNAVAILABLE",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details=details,
        )


class AuthenticationException(BaseAPIException):
    """Raised when API key or provider authentication fails."""

    def __init__(self, message: str = "Authentication with model provider failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="AUTHENTICATION_ERROR",
            status_code=status.HTTP_401_UNAUTHORIZED,
            details=details,
        )