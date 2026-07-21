from fastapi import APIRouter, Depends, status
from app.api.dependencies import get_app_settings
from app.config.settings import Settings
from app.schemas.health import HealthResponse
from app.telemetry.logging import app_logger

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    tags=["System"],
    summary="System Health Check",
    description="Basic health endpoint to verify the API server is alive and responding.",
)
async def health_check(
    settings: Settings = Depends(get_app_settings),
) -> HealthResponse:
    """Basic liveness probe endpoint."""
    app_logger.debug("Health probe check received in {env} mode.", env=settings.app_env)
    return HealthResponse(
        status="ok",
        environment=settings.app_env,
    )