"""Startup Alembic migration runner with PostgreSQL advisory lock coordination."""

import logging
from pathlib import Path

from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncEngine

from alembic import command
from app.core.config import Settings, get_settings
from app.core.database import engine as default_engine

logger = logging.getLogger("clearguard.migrations")

# Deterministic 64-bit PostgreSQL advisory lock key for ClearGuard schema migrations
POSTGRES_MIGRATION_LOCK_ID = 746_192_837_465

_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
_DEFAULT_ALEMBIC_INI = _BACKEND_DIR / "alembic.ini"


def _run_upgrade_sync(sync_conn: Connection, alembic_ini_path: Path) -> None:
    """Execute Alembic `upgrade head` against an existing synchronous connection."""
    cfg = Config(str(alembic_ini_path))
    cfg.attributes["connection"] = sync_conn
    command.upgrade(cfg, "head")


async def run_startup_migrations(
    target_engine: AsyncEngine | None = None,
    settings: Settings | None = None,
    alembic_ini_path: Path = _DEFAULT_ALEMBIC_INI,
) -> bool:
    """Run pending Alembic migrations at startup when enabled.

    On PostgreSQL, acquires a session-level advisory lock so concurrent cloud
    replicas serialize schema upgrades cleanly before serving traffic.

    Returns:
        True if migrations were executed, False if skipped by configuration.
    """
    active_settings = settings or get_settings()
    if not active_settings.auto_migrate_on_startup or active_settings.app_env.lower() in {
        "test",
        "testing",
    }:
        logger.debug(
            "Skipping startup migrations (auto_migrate=%s, env=%s).",
            active_settings.auto_migrate_on_startup,
            active_settings.app_env,
        )
        return False

    active_engine = target_engine or default_engine
    is_postgres = active_engine.dialect.name == "postgresql"
    lock_acquired = False

    logger.info("Running startup database migrations (dialect=%s)...", active_engine.dialect.name)
    async with active_engine.connect() as conn:
        try:
            if is_postgres:
                await conn.execute(
                    text("SELECT pg_advisory_lock(:lock_id)"),
                    {"lock_id": POSTGRES_MIGRATION_LOCK_ID},
                )
                await conn.commit()
                lock_acquired = True

            await conn.run_sync(_run_upgrade_sync, alembic_ini_path)
            logger.info("Database schema is up to date.")
            return True
        finally:
            if is_postgres and lock_acquired:
                try:
                    if conn.in_transaction():
                        await conn.rollback()
                    await conn.execute(
                        text("SELECT pg_advisory_unlock(:lock_id)"),
                        {"lock_id": POSTGRES_MIGRATION_LOCK_ID},
                    )
                    await conn.commit()
                except Exception:
                    logger.exception(
                        "Failed to unlock PostgreSQL advisory lock; invalidating connection."
                    )
                    await conn.invalidate()
