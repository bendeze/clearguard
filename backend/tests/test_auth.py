"""Tests for user authentication, password hashing, and token management (Phase B6.1)."""

import pytest
from httpx import AsyncClient

from app.core.auth import hash_password, verify_password
from app.core.database import engine
from app.models.base import Base


@pytest.fixture
async def setup_auth_database():
    """Ensure clean schema for auth tests."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


def test_argon2id_password_hashing() -> None:
    """Verify that password hashing uses Argon2id and verifies correctly."""
    pw = "SuperSecurePassword123!"
    hashed = hash_password(pw)
    assert hashed.startswith("$argon2id$")
    assert verify_password(pw, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False


@pytest.mark.anyio
async def test_user_registration_and_duplicate_conflict(
    async_client: AsyncClient, setup_auth_database
) -> None:
    """Verify successful user registration and rejection of duplicate usernames."""
    # 1. Successful registration
    reg_res = await async_client.post(
        "/api/v1/auth/register",
        json={
            "username": "alice_guard",
            "password": "Password12345!",
            "email": "alice@example.com",
        },
    )
    assert reg_res.status_code == 201
    data = reg_res.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] > 0

    # 2. Duplicate registration rejected
    dup_res = await async_client.post(
        "/api/v1/auth/register",
        json={
            "username": "alice_guard",
            "password": "DifferentPassword1!",
        },
    )
    assert dup_res.status_code == 409
    assert "already taken" in dup_res.json()["error"]["message"]


@pytest.mark.anyio
async def test_user_login_and_token_refresh(async_client: AsyncClient, setup_auth_database) -> None:
    """Verify login authentication and sliding refresh token rotation."""
    # Register user
    await async_client.post(
        "/api/v1/auth/register",
        json={"username": "bob_guard", "password": "BobPassword123!"},
    )

    # Login with valid credentials
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={
            "username": "bob_guard",
            "password": "BobPassword123!",
            "device_identifier": "device-uuid-1234",
            "device_name": "Pixel 8 Pro",
        },
    )
    assert login_res.status_code == 200
    tokens = login_res.json()
    access_token = tokens["access_token"]
    refresh_token = tokens["refresh_token"]

    # Verify /me endpoint with access token
    me_res = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["username"] == "bob_guard"
    assert len(me_data["devices"]) == 1
    assert me_data["devices"][0]["device_identifier"] == "device-uuid-1234"

    # Refresh tokens
    refresh_res = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_res.status_code == 200
    new_tokens = refresh_res.json()
    assert new_tokens["access_token"] != access_token
    assert new_tokens["refresh_token"] != refresh_token

    # Re-using old refresh token must be rejected (Token Rotation)
    reuse_res = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert reuse_res.status_code == 401


@pytest.mark.anyio
async def test_login_invalid_credentials(async_client: AsyncClient, setup_auth_database) -> None:
    """Verify login failure with incorrect password."""
    await async_client.post(
        "/api/v1/auth/register",
        json={"username": "carol_guard", "password": "CorrectPassword123!"},
    )

    bad_login = await async_client.post(
        "/api/v1/auth/login",
        json={"username": "carol_guard", "password": "WrongPassword123!"},
    )
    assert bad_login.status_code == 401
    assert "Invalid username or password" in bad_login.json()["error"]["message"]
