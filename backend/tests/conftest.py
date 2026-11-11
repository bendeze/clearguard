"""Shared Pytest fixtures for ClearGuard backend tests."""

import asyncio
import os
import shutil
import tempfile
from collections.abc import AsyncGenerator, Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

# Force all tests onto an isolated temporary SQLite database BEFORE importing any `app.*`
# module so module-level `app.core.database.engine` never reads `.env` or touches remote DBs.
_TEST_DB_DIR: Path = Path(tempfile.mkdtemp(prefix="clearguard_pytest_"))
_TEST_DB_PATH: Path = _TEST_DB_DIR / "clearguard_test.db"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_TEST_DB_PATH.as_posix()}"
os.environ["AUTO_MIGRATE_ON_STARTUP"] = "false"
os.environ["APP_HOST"] = "127.0.0.1"
os.environ["APP_PORT"] = "8000"

from app.core.config import Settings, get_settings  # noqa: E402
from app.main import app  # noqa: E402

get_settings.cache_clear()


def pytest_unconfigure(config: pytest.Config) -> None:
    """Dispose cached test engine and remove the temporary SQLite directory."""
    try:
        from app.core.database import engine

        asyncio.run(engine.dispose())
    except Exception:
        pass
    if _TEST_DB_DIR.exists():
        shutil.rmtree(_TEST_DB_DIR, ignore_errors=True)


@pytest.fixture
def test_settings() -> Settings:
    """Return test configuration settings."""
    return Settings(
        app_name="ClearGuard Test API",
        app_version="0.7.0",
        app_env="testing",
        debug=True,
        database_url="sqlite:///:memory:",
        rate_limit_enabled=False,
    )


@pytest.fixture
def client(test_settings: Settings) -> Generator[TestClient, None, None]:
    """Return FastAPI TestClient with test settings override."""
    app.dependency_overrides[get_settings] = lambda: test_settings
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
async def async_client(test_settings: Settings) -> AsyncGenerator[AsyncClient, None]:
    """Return an asynchronous httpx client configured with test settings override."""
    app.dependency_overrides[get_settings] = lambda: test_settings
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
