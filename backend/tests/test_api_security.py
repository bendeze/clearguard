"""Automated security, defensive headers, CORS, and rate-limiting tests (Phase B5.1)."""

import pytest
from httpx import AsyncClient

from app.core.config import Settings
from app.core.security import limiter


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Ensure in-memory rate limiter is clean before and after every test."""
    limiter.clear()
    yield
    limiter.clear()


# ==============================================================================
# Security Headers & CORS Tests
# ==============================================================================


@pytest.mark.anyio
async def test_security_headers_present_on_all_responses(async_client: AsyncClient) -> None:
    """Verify that standard defensive security headers are appended to responses."""
    res = await async_client.get("/")
    assert res.status_code == 200

    headers = res.headers
    assert headers["x-content-type-options"] == "nosniff"
    assert headers["x-frame-options"] == "DENY"
    assert headers["x-xss-protection"] == "1; mode=block"
    assert headers["referrer-policy"] == "strict-origin-when-cross-origin"


@pytest.mark.anyio
async def test_cors_preflight_and_response_headers(async_client: AsyncClient) -> None:
    """Verify CORS preflight OPTIONS request returns appropriate access control headers."""
    headers = {
        "Origin": "https://dashboard.clearguard.com",
        "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "Content-Type",
    }
    res = await async_client.options("/api/v1/health", headers=headers)
    assert res.status_code == 200
    assert "access-control-allow-origin" in res.headers


# ==============================================================================
# Rate Limiting Tests
# ==============================================================================


@pytest.mark.anyio
async def test_rate_limiter_throttles_excessive_requests(async_client: AsyncClient) -> None:
    """Verify that exceeding rate limits returns 429 Too Many Requests with Retry-After."""
    client_ip = "192.168.1.100"

    # Test rate limiter logic directly using lower threshold
    limit = 5
    for i in range(limit):
        allowed, remaining, retry_after = limiter.check_rate_limit(client_ip, limit=limit)
        assert allowed is True
        assert remaining == limit - (i + 1)
        assert retry_after == 0

    # Next attempt should be blocked
    allowed, remaining, retry_after = limiter.check_rate_limit(client_ip, limit=limit)
    assert allowed is False
    assert remaining == 0
    assert retry_after > 0


@pytest.mark.anyio
async def test_rate_limiting_middleware_429_envelope(
    async_client: AsyncClient, test_settings: Settings
) -> None:
    """Verify the middleware formats 429 status and response headers when rate limit trips."""
    test_settings.rate_limit_enabled = True
    fake_ip = "10.0.0.50"
    # Pre-fill limiter to the default limit
    limiter._records[fake_ip] = [9999999999.0] * 150  # Far in future

    res = await async_client.get("/api/v1/health", headers={"X-Forwarded-For": fake_ip})
    assert res.status_code == 429
    assert "retry-after" in res.headers
    assert res.headers["x-ratelimit-remaining"] == "0"

    data = res.json()
    assert "error" in data
    assert data["error"]["code"] == "RATE_LIMIT_EXCEEDED"


# ==============================================================================
# Sensitive Information Masking Tests
# ==============================================================================


def test_sensitive_database_url_password_masked() -> None:
    """Verify that database connection strings with passwords are masked."""
    settings = Settings(
        database_url="postgresql+asyncpg://app_user:super_secret_pw@db.clearguard.net:5432/clearguard_prod"
    )
    masked = settings.masked_database_url

    assert "super_secret_pw" not in masked
    assert masked == "postgresql+asyncpg://app_user:***@db.clearguard.net:5432/clearguard_prod"


def test_sqlite_url_without_password_preserved() -> None:
    """Verify that passwordless database URLs (e.g. SQLite) remain intact."""
    settings = Settings(database_url="sqlite+aiosqlite:///./test.db")
    assert settings.masked_database_url == "sqlite+aiosqlite:///./test.db"
