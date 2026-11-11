"""Database connection management and async session provider using SQLAlchemy 2."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Annotated, Any

from fastapi import Depends
from sqlalchemy.engine import make_url
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
    engine_kwargs: dict[str, Any] = {
        "echo": settings.db_echo,
    }

    if settings.async_database_url.startswith("sqlite"):
        # SQLite-specific connect args to allow access across async worker tasks
        connect_args["check_same_thread"] = False
    else:
        # Production PostgreSQL connection pool configuration
        engine_kwargs["pool_size"] = settings.db_pool_size
        engine_kwargs["max_overflow"] = settings.db_max_overflow
        engine_kwargs["pool_timeout"] = settings.db_pool_timeout
        engine_kwargs["pool_recycle"] = settings.db_pool_recycle
        engine_kwargs["pool_pre_ping"] = True

    redacted_url = make_url(settings.async_database_url).render_as_string(hide_password=True)
    logger.debug("Configuring database engine for: %s", redacted_url)
    return create_async_engine(
        settings.async_database_url,
        connect_args=connect_args,
        **engine_kwargs,
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


# Reusable dependency annotation for endpoints
DbSession = Annotated[AsyncSession, Depends(get_db_session)]


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """Standalone async context manager for non-request database session management."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def transaction_scope(session: AsyncSession) -> AsyncGenerator[AsyncSession, None]:
    """Transactional context manager supporting savepoints for nested atomic operations."""
    if session.in_transaction():
        async with session.begin_nested():
            yield session
    else:
        async with session.begin():
            yield session


async def close_db_engine() -> None:
    """Gracefully dispose of all database engine connections."""
    logger.info("Disposing database engine connection pool.")
    await engine.dispose()
