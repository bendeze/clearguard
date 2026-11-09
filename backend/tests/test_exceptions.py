"""Tests for global exception handling and structured error responses."""

from fastapi import APIRouter
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.core.exceptions import ClearGuardException, NotFoundError, ValidationError
from app.main import app

# Test router to trigger custom exceptions
mock_error_router = APIRouter(prefix="/test-errors")


class SampleBody(BaseModel):
    name: str
    count: int


@mock_error_router.get("/not-found")
def raise_not_found() -> None:
    raise NotFoundError("Test entity was not found")


@mock_error_router.get("/validation-error")
def raise_validation_error() -> None:
    raise ValidationError("Test validation failed", details={"field": "test"})


@mock_error_router.get("/custom-error")
def raise_custom_error() -> None:
    raise ClearGuardException("Something went wrong", code="CUSTOM_CODE", status_code=400)


@mock_error_router.post("/body-validation")
def check_body(body: SampleBody) -> dict[str, str]:
    return {"message": "ok"}


app.include_router(mock_error_router)


def test_404_not_found_structured_response(client: TestClient) -> None:
    """Verify that unknown routes return structured JSON error."""
    response = client.get("/api/v1/nonexistent-route-xyz")
    assert response.status_code == 404
    data = response.json()

    assert "error" in data
    assert data["error"]["code"] == "HTTP_404"
    assert "Not Found" in data["error"]["message"]


def test_custom_not_found_error_handler(client: TestClient) -> None:
    """Verify that NotFoundError returns HTTP 404 and structured JSON."""
    response = client.get("/test-errors/not-found")
    assert response.status_code == 404
    data = response.json()

    assert "error" in data
    assert data["error"]["code"] == "NOT_FOUND"
    assert data["error"]["message"] == "Test entity was not found"


def test_custom_validation_error_handler(client: TestClient) -> None:
    """Verify that ValidationError returns HTTP 422 and structured JSON."""
    response = client.get("/test-errors/validation-error")
    assert response.status_code == 422
    data = response.json()

    assert "error" in data
    assert data["error"]["code"] == "VALIDATION_ERROR"
    assert data["error"]["message"] == "Test validation failed"
    assert data["error"]["details"] == {"field": "test"}


def test_custom_clearguard_error_handler(client: TestClient) -> None:
    """Verify that ClearGuardException returns specified status and code."""
    response = client.get("/test-errors/custom-error")
    assert response.status_code == 400
    data = response.json()

    assert "error" in data
    assert data["error"]["code"] == "CUSTOM_CODE"
    assert data["error"]["message"] == "Something went wrong"


def test_request_validation_error_handler(client: TestClient) -> None:
    """Verify that invalid request payloads return structured 422 error."""
    response = client.post("/test-errors/body-validation", json={"name": 123})
    assert response.status_code == 422
    data = response.json()

    assert "error" in data
    assert data["error"]["code"] == "REQUEST_VALIDATION_ERROR"
    assert isinstance(data["error"]["details"], list)
