"""Integration tests for containerization readiness, health probes, and deployment artifacts.

Phase B5.3: Containerization & Deployment Readiness.
"""

from pathlib import Path

import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_health_live_probe(async_client: AsyncClient) -> None:
    """Verify that /api/v1/health/live returns HTTP 200 and alive status for container liveness."""
    res = await async_client.get("/api/v1/health/live")
    assert res.status_code == 200
    assert res.json() == {"status": "alive"}


@pytest.mark.anyio
async def test_health_ready_probe(async_client: AsyncClient) -> None:
    """Verify that /api/v1/health/ready tests database connectivity and returns ready status."""
    res = await async_client.get("/api/v1/health/ready")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ready"
    assert data["database"] == "connected"
    assert "timestamp" in data
    assert "version" in data


def test_deployment_artifacts_present_and_configured() -> None:
    """Verify that Dockerfile, docker-compose.yml, and .dockerignore exist and are configured."""
    base_dir = Path(__file__).resolve().parent.parent

    dockerfile = base_dir / "Dockerfile"
    docker_compose = base_dir / "docker-compose.yml"
    dockerignore = base_dir / ".dockerignore"

    assert dockerfile.exists(), "Dockerfile must be present"
    assert docker_compose.exists(), "docker-compose.yml must be present"
    assert dockerignore.exists(), ".dockerignore must be present"

    # Verify Dockerfile contains security non-root user and uvicorn CMD
    dockerfile_content = dockerfile.read_text(encoding="utf-8")
    assert "appuser" in dockerfile_content
    assert "uvicorn" in dockerfile_content
    assert "HEALTHCHECK" in dockerfile_content

    # Verify .dockerignore excludes sensitive secrets
    dockerignore_content = dockerignore.read_text(encoding="utf-8")
    assert ".env.production" in dockerignore_content
    assert ".env.local" in dockerignore_content

    # Verify docker-compose specifies postgres and api
    compose_content = docker_compose.read_text(encoding="utf-8")
    assert "postgres" in compose_content
    assert "clearguard-api" in compose_content
