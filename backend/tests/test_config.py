"""Tests for application configuration."""

from app.core.config import Settings, get_settings


def test_default_settings() -> None:
    """Verify default settings values."""
    settings = Settings()
    assert settings.app_name == "ClearGuard API"
    assert settings.app_version == "0.4.0"
    assert settings.api_v1_prefix == "/api/v1"
    assert settings.app_host == "127.0.0.1"
    assert settings.app_port == 8000
    assert "sqlite" in settings.database_url


def test_settings_custom_values() -> None:
    """Verify that settings accept explicit overrides."""
    custom = Settings(
        app_name="Custom API",
        app_env="production",
        debug=False,
        app_port=9000,
    )
    assert custom.app_name == "Custom API"
    assert custom.app_env == "production"
    assert custom.debug is False
    assert custom.app_port == 9000


def test_get_settings_cached() -> None:
    """Verify that get_settings returns a singleton cached instance."""
    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2
