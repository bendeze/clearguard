"""Health check monitoring endpoint."""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import text

from app.core.config import Settings, get_settings
from app.core.database import DbSession

router = APIRouter()

SettingsDep = Annotated[Settings, Depends(get_settings)]


class HealthResponse(BaseModel):
    """Health check response schema."""

    status: str = Field(default="healthy", description="Current service operational status")
    version: str = Field(description="Application version")
    environment: str = Field(description="Deployment environment")
    timestamp: datetime = Field(description="Current server timestamp in UTC")


class ReadinessResponse(BaseModel):
    """Readiness probe response including database subsystem state."""

    status: str = Field(description="Subsystem readiness state: 'ready' or 'unhealthy'")
    database: str = Field(description="Database connectivity status: 'connected' or 'disconnected'")
    version: str = Field(description="Application version")
    timestamp: datetime = Field(description="Current server timestamp in UTC")


@router.get(
    "/health",
    summary="Service Health Check",
    description="Returns operational status, version, environment, and UTC timestamp.",
    tags=["System"],
)
def get_health(settings: SettingsDep) -> HealthResponse:
    """Check the health status of the ClearGuard backend API."""
    return HealthResponse(
        status="healthy",
        version=settings.app_version,
        environment=settings.app_env,
        timestamp=datetime.now(UTC),
    )


@router.get(
    "/health/live",
    summary="Liveness Probe",
    description="Kubernetes / Docker liveness check confirming the process is alive.",
    tags=["System"],
)
def get_liveness() -> dict[str, str]:
    """Lightweight process liveness check."""
    return {"status": "alive"}


@router.get(
    "/health/ready",
    summary="Readiness Probe",
    description="Kubernetes / Docker readiness probe verifying database connectivity.",
    tags=["System"],
)
async def get_readiness(session: DbSession, settings: SettingsDep) -> ReadinessResponse:
    """Verify application readiness and database connectivity."""
    try:
        await session.execute(text("SELECT 1"))
        db_status = "connected"
        overall = "ready"
    except Exception as exc:
        db_status = f"disconnected: {exc}"
        overall = "unhealthy"

    return ReadinessResponse(
        status=overall,
        database=db_status,
        version=settings.app_version,
        timestamp=datetime.now(UTC),
    )
