"""Tests for the v1 health check endpoint."""

from datetime import datetime

from fastapi.testclient import TestClient

from app.core.config import get_settings


def test_health_endpoint_returns_200(client: TestClient) -> None:
    """Verify that GET /api/v1/health returns HTTP 200."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200


def test_health_endpoint_payload(client: TestClient) -> None:
    """Verify the health check response payload fields."""
    response = client.get("/api/v1/health")
    data = response.json()

    assert data["status"] == "healthy"
    assert data["version"] == get_settings().app_version
    assert data["environment"] == "testing"
    assert "timestamp" in data

    # Validate timestamp is valid ISO format
    parsed_time = datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))
    assert parsed_time is not None
