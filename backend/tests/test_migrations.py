"""Tests for Alembic migration configuration, environment, and startup runner."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from alembic.config import Config
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import create_async_engine

from alembic import command
from app.core.config import Settings
from app.core.migrations import POSTGRES_MIGRATION_LOCK_ID, run_startup_migrations

BACKEND_DIR = Path(__file__).resolve().parent.parent


def test_alembic_config_loads() -> None:
    """Verify that alembic.ini is present and configured."""
    ini_path = BACKEND_DIR / "alembic.ini"
    assert ini_path.exists()

    alembic_cfg = Config(str(ini_path))
    script_loc = alembic_cfg.get_main_option("script_location")
    assert script_loc is not None
    assert "alembic" in script_loc


def test_alembic_env_targets_base_metadata() -> None:
    """Verify that alembic/env.py specifies Base.metadata and SQLite batch mode."""
    env_py_path = BACKEND_DIR / "alembic" / "env.py"
    assert env_py_path.exists()

    content = env_py_path.read_text(encoding="utf-8")
    assert "target_metadata = Base.metadata" in content
    assert "render_as_batch=True" in content
    assert "settings.async_database_url" in content


def test_alembic_current_command() -> None:
    """Verify that alembic current command executes without error."""
    alembic_cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    command.current(alembic_cfg)


@pytest.mark.anyio
async def test_startup_migrations_skipped_when_disabled_or_testing() -> None:
    """Startup migrations must not run when disabled or in test environments."""
    disabled = Settings(app_env="production", auto_migrate_on_startup=False)
    assert await run_startup_migrations(settings=disabled) is False

    testing = Settings(app_env="testing", auto_migrate_on_startup=True)
    assert await run_startup_migrations(settings=testing) is False


@pytest.mark.anyio
async def test_startup_migrations_apply_all_tables_idempotently(tmp_path: Path) -> None:
    """Verify startup migration upgrades a fresh database to head cleanly and idempotently."""
    db_file = tmp_path / "startup_migrate.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_file.as_posix()}")
    prod_settings = Settings(app_env="production", auto_migrate_on_startup=True)

    try:
        assert await run_startup_migrations(target_engine=engine, settings=prod_settings) is True
        # Second startup run should be a safe no-op
        assert await run_startup_migrations(target_engine=engine, settings=prod_settings) is True

        async with engine.connect() as conn:
            tables = await conn.run_sync(
                lambda sync_conn: set(inspect(sync_conn).get_table_names())
            )

        expected_tables = {
            "alembic_version",
            "domains",
            "blocklists",
            "blocklist_domains",
            "blocklist_versions",
            "users",
            "devices",
            "refresh_tokens",
            "user_vaults",
            "deactivation_requests",
            "admin_overrides",
        }
        assert expected_tables.issubset(tables)
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_startup_migrations_use_postgres_advisory_lock() -> None:
    """Verify PostgreSQL startup migrations acquire and always release advisory lock."""
    mock_conn = AsyncMock()
    mock_conn.in_transaction = MagicMock(return_value=False)
    mock_conn.run_sync = AsyncMock(side_effect=RuntimeError("migration boom"))

    mock_connect_ctx = MagicMock()
    mock_connect_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_connect_ctx.__aexit__ = AsyncMock(return_value=False)

    mock_engine = MagicMock()
    mock_engine.dialect.name = "postgresql"
    mock_engine.connect.return_value = mock_connect_ctx

    prod_settings = Settings(app_env="production", auto_migrate_on_startup=True)

    with pytest.raises(RuntimeError, match="migration boom"):
        await run_startup_migrations(target_engine=mock_engine, settings=prod_settings)

    executed_sql = [str(call.args[0]) for call in mock_conn.execute.await_args_list]
    assert any("pg_advisory_lock" in sql for sql in executed_sql)
    assert any("pg_advisory_unlock" in sql for sql in executed_sql)
    executed_params = [call.args[1] for call in mock_conn.execute.await_args_list]
    assert executed_params == [
        {"lock_id": POSTGRES_MIGRATION_LOCK_ID},
        {"lock_id": POSTGRES_MIGRATION_LOCK_ID},
    ]
    assert mock_conn.commit.await_count == 2
