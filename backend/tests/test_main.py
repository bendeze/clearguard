"""Tests for application root and documentation endpoints."""

from fastapi.testclient import TestClient


def test_root_endpoint(client: TestClient) -> None:
    """Verify that GET / returns service metadata and navigation links."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "online"
    assert data["version"] == "0.1.0"
    assert "docs" in data
    assert "health" in data


def test_openapi_schema(client: TestClient) -> None:
    """Verify that the OpenAPI schema is available and correctly configured."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()

    assert schema["info"]["title"] == "ClearGuard API"
    assert schema["info"]["version"] == "0.1.0"
    assert "/api/v1/health" in schema["paths"]


def test_swagger_ui_docs(client: TestClient) -> None:
    """Verify that Swagger UI documentation is reachable."""
    response = client.get("/docs")
    assert response.status_code == 200


def test_redoc_docs(client: TestClient) -> None:
    """Verify that ReDoc documentation is reachable."""
    response = client.get("/redoc")
    assert response.status_code == 200
