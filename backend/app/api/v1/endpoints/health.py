"""Health check monitoring endpoint."""

from datetime import UTC, datetime

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.core.config import get_settings

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response schema."""

    status: str = Field(
        default="healthy", description="Current service operational status"
    )
    version: str = Field(description="Application version")
    environment: str = Field(description="Deployment environment")
    timestamp: datetime = Field(description="Current server timestamp in UTC")


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Service Health Check",
    description="Returns the operational status, version, environment, and current UTC time of the API service.",
    tags=["System"],
)
def get_health() -> HealthResponse:
    """Check the health status of the ClearGuard backend API."""
    settings = get_settings()
    return HealthResponse(
        status="healthy",
        version=settings.app_version,
        environment=settings.app_env,
        timestamp=datetime.now(UTC),
    )
