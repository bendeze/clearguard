"""Shared Pytest fixtures for ClearGuard backend tests."""

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.main import app


@pytest.fixture
def test_settings() -> Settings:
    """Return test configuration settings."""
    return Settings(
        app_name="ClearGuard Test API",
        app_version="0.1.0",
        app_env="testing",
        debug=True,
        database_url="sqlite:///:memory:",
    )


@pytest.fixture
def client(test_settings: Settings) -> TestClient:
    """Return FastAPI TestClient with test settings override."""
    app.dependency_overrides[get_settings] = lambda: test_settings
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

