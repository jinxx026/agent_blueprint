"""Service health endpoint."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import get_request_settings
from app.core.config import Settings
from app.schemas.health import HealthResponse, HealthStatus

router = APIRouter()


@router.get("/health", response_model=HealthResponse, summary="Check API health")
def get_health(
    settings: Annotated[Settings, Depends(get_request_settings)],
) -> HealthResponse:
    """Confirm that the API process is alive and expose non-secret metadata."""

    return HealthResponse(
        status=HealthStatus.OK,
        service=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
    )
