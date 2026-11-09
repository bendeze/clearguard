"""Database connection management and async session provider using SQLAlchemy 2."""

import logging
from collections.abc import AsyncGenerator
from typing import Annotated, Any

from fastapi import Depends
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def create_engine_instance() -> AsyncEngine:
    """Create and configure the async SQLAlchemy engine."""
    settings = get_settings()
    connect_args: dict[str, Any] = {}

    if settings.async_database_url.startswith("sqlite"):
        # SQLite-specific connect args to allow access across async worker tasks
        connect_args["check_same_thread"] = False

    logger.debug("Configuring database engine for: %s", settings.async_database_url)
    return create_async_engine(
        settings.async_database_url,
        echo=settings.debug,
        connect_args=connect_args,
    )


# Application-level engine instance
engine: AsyncEngine = create_engine_instance()

# Session factory for generating AsyncSession instances
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that provides an AsyncSession per request with automatic cleanup."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Reusable dependency annotation for endpoints
DbSession = Annotated[AsyncSession, Depends(get_db_session)]


async def close_db_engine() -> None:
    """Gracefully dispose of all database engine connections."""
    logger.info("Disposing database engine connection pool.")
    await engine.dispose()
