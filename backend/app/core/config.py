"""Application configuration using Pydantic Settings."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url


class Settings(BaseSettings):
    """Central application configuration settings."""

    # Application settings
    app_name: str = "ClearGuard API"
    app_version: str = "0.7.0"
    app_env: str = "development"
    debug: bool = True

    # Server settings
    app_host: str = "127.0.0.1"
    app_port: int = 8000

    # API Routing
    api_v1_prefix: str = "/api/v1"

    # Database settings
    database_url: str = "sqlite+aiosqlite:///./clearguard.db"
    auto_migrate_on_startup: bool = True
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

    # Authentication & JWT Settings (Milestone B6)
    jwt_secret_key: str = "clearguard-super-secret-jwt-key-change-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 30

    # Admin Emergency Override Keys (Milestone B6)
    admin_override_private_key: str = ""
    admin_override_public_key: str = ""

    # Notification & Transactional Email Settings (Milestone B6)
    public_base_url: str = ""
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from_email: str = "no-reply@clearguard.app"

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
        """Return the database URL ensured with an async driver and compatible params."""
        url = self.database_url
        if url.startswith("sqlite:///") and not url.startswith("sqlite+aiosqlite:///"):
            return url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
        if url.startswith("postgresql://") and not url.startswith("postgresql+asyncpg://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgres://") and not url.startswith("postgresql+asyncpg://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)

        if url.startswith("postgresql+asyncpg://") and "?" in url:
            parsed = make_url(url)
            query = dict(parsed.query)
            changed = False

            if "sslmode" in query:
                sslmode = query.pop("sslmode")
                query.setdefault("ssl", sslmode)
                changed = True

            for unsupported in ("channel_binding", "gssencmode"):
                if unsupported in query:
                    query.pop(unsupported)
                    changed = True

            if changed:
                return parsed.set(query=query).render_as_string(hide_password=False)

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
