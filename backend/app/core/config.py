"""Application configuration using Pydantic Settings."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central application configuration settings."""

    # Application settings
    app_name: str = "ClearGuard API"
    app_version: str = "0.1.0"
    app_env: str = "development"
    debug: bool = True

    # Server settings
    app_host: str = "127.0.0.1"
    app_port: int = 8000

    # API Routing
    api_v1_prefix: str = "/api/v1"

    # Database settings
    database_url: str = "sqlite:///./clearguard.db"

    model_config = SettingsConfigDict(
        env_file=(".env.local", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings instance."""
    return Settings()
