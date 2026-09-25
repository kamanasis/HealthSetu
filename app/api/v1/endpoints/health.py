"""Health and readiness probe endpoints."""

from fastapi import APIRouter, Depends, Response, status
from app.schemas.response import HealthResponse, ReadinessResponse
from app.services.health import HealthService

router = APIRouter(tags=["Health & Diagnostics"])


def get_health_service() -> HealthService:
    """Dependency injection provider for HealthService."""
    return HealthService()


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Application liveness probe",
    description="Indicates that the HealthSetu backend application process is alive and responsive.",
)
async def get_health(
    service: HealthService = Depends(get_health_service),
) -> HealthResponse:
    """Return application liveness status."""
    return service.get_health()


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    responses={
        status.HTTP_200_OK: {"model": ReadinessResponse, "description": "Backend is fully ready to serve traffic"},
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "model": ReadinessResponse,
            "description": "Backend is not ready (e.g. database unavailable)",
        },
    },
    summary="Application readiness probe",
    description="Determines whether the backend and its critical dependencies are ready to process traffic.",
)
async def get_ready(
    response: Response,
    service: HealthService = Depends(get_health_service),
) -> ReadinessResponse:
    """Evaluate database connectivity and report readiness."""
    is_ready, readiness_data = await service.get_readiness()
    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return readiness_data
