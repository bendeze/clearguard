"""Tests for production database configuration, connection pooling, and PostgreSQL readiness.

Phase B5.2: Production Database Readiness.
"""

from unittest.mock import patch

from sqlalchemy.engine import make_url

from app.core.config import Settings
from app.core.database import create_engine_instance


def test_postgresql_url_scheme_normalization() -> None:
    """Verify that standard postgresql URLs are automatically adapted to asyncpg."""
    s1 = Settings(database_url="postgresql://user:pass@db.internal:5432/clearguard")
    assert s1.async_database_url == "postgresql+asyncpg://user:pass@db.internal:5432/clearguard"

    s2 = Settings(database_url="postgres://user:pass@db.internal:5432/clearguard")
    assert s2.async_database_url == "postgresql+asyncpg://user:pass@db.internal:5432/clearguard"


def test_postgresql_connection_pool_options_configured() -> None:
    """Verify that non-SQLite database URLs receive connection pooling parameters."""
    pg_url = "postgresql+asyncpg://test_user:secret@127.0.0.1:5432/test_db"
    test_settings = Settings(
        database_url=pg_url,
        db_pool_size=15,
        db_max_overflow=5,
        db_pool_timeout=25,
        db_pool_recycle=900,
    )

    with patch("app.core.database.get_settings", return_value=test_settings):
        engine = create_engine_instance()
        assert engine.pool.size() == 15
        assert engine.pool._max_overflow == 5
        assert engine.pool._timeout == 25
        assert engine.pool._recycle == 900
        # Clean up
        engine.sync_engine.dispose()


def test_redacted_database_url_hides_credentials() -> None:
    """Verify make_url redacts passwords properly."""
    raw = "postgresql+asyncpg://myuser:super_secret_pw@db.clearguard.net:5432/clearguard_prod"
    redacted = make_url(raw).render_as_string(hide_password=True)
    assert "super_secret_pw" not in redacted
    assert "myuser:***@" in redacted
