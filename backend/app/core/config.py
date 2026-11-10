"""Application configuration using Pydantic Settings."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central application configuration settings."""

    # Application settings
    app_name: str = "ClearGuard API"
    app_version: str = "0.6.0"
    app_env: str = "development"
    debug: bool = True

    # Server settings
    app_host: str = "127.0.0.1"
    app_port: int = 8000

    # API Routing
    api_v1_prefix: str = "/api/v1"

    # Database settings
    database_url: str = "sqlite+aiosqlite:///./clearguard.db"
    db_echo: bool = False
    db_pool_size: int = 20
    db_max_overflow: int = 10
    db_pool_timeout: int = 30
    db_pool_recycle: int = 1800

    # Security & Abuse Prevention
    cors_origins: list[str] = ["*"]
    security_headers_enabled: bool = True
    rate_limit_enabled: bool = True
    rate_limit_per_minute: int = 120
    download_rate_limit_per_minute: int = 30

    @property
    def masked_database_url(self) -> str:
        """Return the database URL with any password credentials masked."""
        url = self.database_url
        if "@" in url and "://" in url:
            scheme, rest = url.split("://", 1)
            user_info, host_info = rest.split("@", 1)
            if ":" in user_info:
                username, _ = user_info.split(":", 1)
                return f"{scheme}://{username}:***@{host_info}"
        return url

    @property
    def async_database_url(self) -> str:
        """Return the database URL ensured with an async driver scheme."""
        url = self.database_url
        if url.startswith("sqlite:///") and not url.startswith("sqlite+aiosqlite:///"):
            return url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
        if url.startswith("postgresql://") and not url.startswith("postgresql+asyncpg://"):
            return url.replace("postgresql://", "postgresql+asyncpg://", 1)
        if url.startswith("postgres://") and not url.startswith("postgresql+asyncpg://"):
            return url.replace("postgres://", "postgresql+asyncpg://", 1)
        return url

    model_config = SettingsConfigDict(
        env_file=(".env.local", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings instance."""
    return Settings()
