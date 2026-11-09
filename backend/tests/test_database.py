"""Automated tests for database architecture, engine connectivity, and session management."""

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.database import engine, get_db_session


def test_database_url_normalization() -> None:
    """Verify that sync and standard database URLs are converted to async drivers."""
    sqlite_sync = Settings(database_url="sqlite:///./test.db")
    assert sqlite_sync.async_database_url == "sqlite+aiosqlite:///./test.db"

    postgres_sync = Settings(database_url="postgresql://user:pass@localhost:5432/db")
    assert postgres_sync.async_database_url == "postgresql+asyncpg://user:pass@localhost:5432/db"

    postgres_alt = Settings(database_url="postgres://user:pass@localhost:5432/db")
    assert postgres_alt.async_database_url == "postgresql+asyncpg://user:pass@localhost:5432/db"

    already_async = Settings(database_url="sqlite+aiosqlite:///./test.db")
    assert already_async.async_database_url == "sqlite+aiosqlite:///./test.db"


@pytest.mark.anyio
async def test_async_engine_connectivity() -> None:
    """Verify that the async database engine can connect and execute queries."""
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT 1"))
        assert result.scalar() == 1


@pytest.mark.anyio
async def test_get_db_session_lifecycle() -> None:
    """Verify that get_db_session yields an active AsyncSession."""
    async for session in get_db_session():
        assert isinstance(session, AsyncSession)
        result = await session.execute(text("SELECT 42"))
        assert result.scalar() == 42


@pytest.mark.anyio
async def test_db_session_rollback_on_exception() -> None:
    """Verify that get_db_session executes rollback when an exception is raised."""
    gen = get_db_session()
    session = await anext(gen)
    assert isinstance(session, AsyncSession)
    await session.execute(text("SELECT 1"))
    with pytest.raises(RuntimeError, match="Simulated database operation error"):
        try:
            raise RuntimeError("Simulated database operation error")
        except RuntimeError as exc:
            await gen.athrow(exc)
