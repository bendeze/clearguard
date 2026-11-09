"""Tests for Alembic migration configuration and environment."""

from pathlib import Path

from alembic.config import Config

from alembic import command

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
