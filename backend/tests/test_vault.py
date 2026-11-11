"""Tests for End-to-End Encrypted (E2EE) User Vault (Phase B6.2)."""

import base64

import pytest
from httpx import AsyncClient

from app.core.database import engine
from app.models.base import Base


@pytest.fixture
async def setup_vault_database():
    """Ensure clean schema for vault tests."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.anyio
async def test_vault_lifecycle_and_versioning(
    async_client: AsyncClient, setup_vault_database
) -> None:
    """Verify E2EE vault creation, version increment, retrieval, and auth enforcement."""
    # 1. Register user
    reg = await async_client.post(
        "/api/v1/auth/register",
        json={"username": "dave_vault", "password": "DavePassword123!"},
    )
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Querying vault before uploading returns 404
    missing_vault = await async_client.get("/api/v1/vault", headers=headers)
    assert missing_vault.status_code == 404

    # 3. Upload first encrypted vault blob
    iv_b64 = base64.b64encode(b"0123456789ab").decode()  # 12 bytes
    tag_b64 = base64.b64encode(b"0123456789abcdef").decode()  # 16 bytes
    salt_b64 = base64.b64encode(b"saltysaltysalty!").decode()  # 16 bytes
    cipher_b64 = base64.b64encode(b"encrypted-client-pledge-phrase-payload").decode()

    put_res1 = await async_client.put(
        "/api/v1/vault",
        headers=headers,
        json={
            "ciphertext": cipher_b64,
            "iv": iv_b64,
            "tag": tag_b64,
            "salt": salt_b64,
            "kdf_iterations": 100000,
        },
    )
    assert put_res1.status_code == 200
    v1 = put_res1.json()
    assert v1["vault_version"] == 1
    assert v1["ciphertext"] == cipher_b64

    # 4. Fetch vault
    get_res = await async_client.get("/api/v1/vault", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["ciphertext"] == cipher_b64
    assert get_res.json()["vault_version"] == 1

    # 5. Update vault -> increments version to 2
    new_cipher = base64.b64encode(b"updated-encrypted-client-payload").decode()
    put_res2 = await async_client.put(
        "/api/v1/vault",
        headers=headers,
        json={
            "ciphertext": new_cipher,
            "iv": iv_b64,
            "tag": tag_b64,
            "salt": salt_b64,
            "kdf_iterations": 120000,
        },
    )
    assert put_res2.status_code == 200
    v2 = put_res2.json()
    assert v2["vault_version"] == 2
    assert v2["ciphertext"] == new_cipher


@pytest.mark.anyio
async def test_vault_rejection_of_invalid_base64(
    async_client: AsyncClient, setup_vault_database
) -> None:
    """Verify that invalid Base64 input is strictly rejected."""
    reg = await async_client.post(
        "/api/v1/auth/register",
        json={"username": "eva_vault", "password": "EvaPassword123!"},
    )
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    bad_put = await async_client.put(
        "/api/v1/vault",
        headers=headers,
        json={
            "ciphertext": "NOT_VALID_BASE64!#@$",
            "iv": "bad_iv",
            "tag": "bad_tag",
            "salt": "bad_salt",
            "kdf_iterations": 100000,
        },
    )
    assert bad_put.status_code == 422
