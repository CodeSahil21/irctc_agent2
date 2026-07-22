# app/core/handlers.py
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.exceptions import BaseAPIException
from app.schemas.errors import ErrorDetail, ErrorResponse
from app.telemetry.logging import app_logger


def register_exception_handlers(app: FastAPI) -> None:
    """Registers global exception handlers on the FastAPI application."""

    @app.exception_handler(BaseAPIException)
    async def custom_api_exception_handler(request: Request, exc: BaseAPIException):
        app_logger.warning("API Exception [{code}]: {msg}", code=exc.code, msg=exc.message)
        
        body = ErrorResponse(
            error=ErrorDetail(
                code=exc.code,
                message=exc.message,
                details=exc.details,
            )
        )
        return JSONResponse(status_code=exc.status_code, content=body.model_dump())

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        app_logger.warning("Validation error on path {path}", path=request.url.path)
        
        body = ErrorResponse(
            error=ErrorDetail(
                code="VALIDATION_ERROR",
                message="Invalid request body or query parameters",
                details={"errors": exc.errors()},
            )
        )
        return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=body.model_dump())

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        app_logger.exception("Unhandled error occurred: {error}", error=str(exc))
        
        body = ErrorResponse(
            error=ErrorDetail(
                code="INTERNAL_SERVER_ERROR",
                message="An unexpected server error occurred.",
            )
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=body.model_dump(),
        )