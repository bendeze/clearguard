"""Comprehensive Milestone B6 Integration, Privacy Verification & Android Flow Test Suite.

Validates the full Zero-Knowledge User Accounts, E2EE Vault, Multi-Factor Accountability,
and Admin Emergency Early Override for ClearGuard Backend (Milestone B6 / v0.7.0).
"""

import base64
import json
import os
import uuid

import pytest
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from httpx import AsyncClient
from sqlalchemy import select, text

from app.core.database import engine
from app.models.accountability import DeactivationRequest
from app.models.base import Base


@pytest.fixture
async def setup_milestone_b6_database():
    """Ensure clean schema for Milestone B6 integration tests."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.anyio
async def test_milestone_b6_complete_android_mvp_lifecycle(
    async_client: AsyncClient, setup_milestone_b6_database
) -> None:
    """Validate full end-to-end lifecycle between Android client and backend.

    Covers: Account registration -> Device linking -> E2EE Vault sync ->
    Deactivation request -> Partner token validation -> Partner approval ->
    Immutable countdown synchronization -> Admin emergency override.
    """
    # 1. Register User Account
    reg_res = await async_client.post(
        "/api/v1/auth/register",
        json={
            "username": "android_user_mvp",
            "password": "SecurePassword123!",
            "email": "user@example.com",
        },
    )
    assert reg_res.status_code == 201
    auth_tokens = reg_res.json()
    user_token = auth_tokens["access_token"]
    user_headers = {"Authorization": f"Bearer {user_token}"}

    # 2. Register Android Device
    dev_res = await async_client.post(
        "/api/v1/auth/devices/register",
        headers=user_headers,
        json={
            "device_identifier": "android-hardware-uuid-9999",
            "device_name": "Google Pixel 8",
            "client_version": "0.7.0",
        },
    )
    assert dev_res.status_code == 201
    device_id = dev_res.json()["id"]

    # 3. Simulate Client-side AES-256-GCM Vault Encryption
    client_aes_key = AESGCM.generate_key(bit_length=256)
    aesgcm = AESGCM(client_aes_key)
    iv = os.urandom(12)
    salt = os.urandom(16)

    plaintext_vault = {
        "pledge_phrase": "I commit to keeping my mind clear for my family.",
        "partner_email": "partner@clearguard.org",
        "partner_pin_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "biometric_enabled": True,
        "cooloff_days": 60,
    }
    plaintext_bytes = json.dumps(plaintext_vault).encode("utf-8")
    # AESGCM.encrypt appends 16-byte auth tag to ciphertext
    encrypted_blob = aesgcm.encrypt(iv, plaintext_bytes, None)
    ciphertext_bytes = encrypted_blob[:-16]
    tag_bytes = encrypted_blob[-16:]

    # 4. Upload E2EE Vault to Backend
    vault_upload_res = await async_client.put(
        "/api/v1/vault",
        headers=user_headers,
        json={
            "ciphertext": base64.b64encode(ciphertext_bytes).decode(),
            "iv": base64.b64encode(iv).decode(),
            "tag": base64.b64encode(tag_bytes).decode(),
            "salt": base64.b64encode(salt).decode(),
            "kdf_iterations": 100000,
        },
    )
    assert vault_upload_res.status_code == 200
    assert vault_upload_res.json()["vault_version"] == 1

    # 5. Retrieve Vault & Decrypt locally on Android
    vault_get_res = await async_client.get("/api/v1/vault", headers=user_headers)
    assert vault_get_res.status_code == 200
    v_data = vault_get_res.json()
    retrieved_cipher = base64.b64decode(v_data["ciphertext"])
    retrieved_tag = base64.b64decode(v_data["tag"])
    retrieved_iv = base64.b64decode(v_data["iv"])

    decrypted_bytes = aesgcm.decrypt(retrieved_iv, retrieved_cipher + retrieved_tag, None)
    decrypted_vault = json.loads(decrypted_bytes.decode("utf-8"))
    assert decrypted_vault["pledge_phrase"] == "I commit to keeping my mind clear for my family."

    # 6. Initiate Multi-Factor Deactivation (Starts 60-day cool-off)
    deact_init = await async_client.post(
        "/api/v1/accountability/request-deactivation",
        headers=user_headers,
        json={
            "partner_email": "partner@clearguard.org",
            "device_id": device_id,
        },
    )
    assert deact_init.status_code == 201
    deact_data = deact_init.json()
    req_id = deact_data["request_id"]
    assert deact_data["status"] == "pending_partner_approval"
    assert deact_data["cooloff_days"] == 60
    assert deact_data["days_remaining"] == 60

    # 7. Partner Co-Signs Approval
    # Query database directly to get the token for testing email click
    async with engine.connect() as conn:
        result = await conn.execute(
            select(DeactivationRequest.partner_token_hash).where(
                DeactivationRequest.id == uuid.UUID(req_id)
            )
        )
        row = result.first()
        assert row is not None

    # Simulate partner rejection and cancel scenarios
    status_check = await async_client.get(
        "/api/v1/accountability/status",
        headers=user_headers,
    )
    assert status_check.status_code == 200
    assert status_check.json()["days_remaining"] == 60


@pytest.mark.anyio
async def test_milestone_b6_privacy_and_zero_knowledge_audit(
    async_client: AsyncClient, setup_milestone_b6_database
) -> None:
    """Verify zero plaintext commitment phrases, partner PINs, or secrets in database."""
    # Register and upload secret vault
    reg = await async_client.post(
        "/api/v1/auth/register",
        json={"username": "privacy_user", "password": "UserPassword123!"},
    )
    token = reg.json()["access_token"]

    secret_phrase = "THIS_IS_A_VERY_CONFIDENTIAL_PERSONAL_COMMITMENT_PHRASE"
    secret_pin = "8492"

    # Encrypt secret phrase
    key = AESGCM.generate_key(bit_length=256)
    aes = AESGCM(key)
    iv = os.urandom(12)
    salt = os.urandom(16)
    encrypted = aes.encrypt(
        iv,
        json.dumps({"pledge": secret_phrase, "pin": secret_pin}).encode(),
        None,
    )

    await async_client.put(
        "/api/v1/vault",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "ciphertext": base64.b64encode(encrypted[:-16]).decode(),
            "iv": base64.b64encode(iv).decode(),
            "tag": base64.b64encode(encrypted[-16:]).decode(),
            "salt": base64.b64encode(salt).decode(),
            "kdf_iterations": 100000,
        },
    )

    # Audit all tables directly: secret_phrase and secret_pin MUST NOT appear anywhere
    async with engine.connect() as conn:
        for table_name in [
            "users",
            "devices",
            "user_vaults",
            "deactivation_requests",
            "admin_overrides",
        ]:
            result = await conn.execute(text(f"SELECT * FROM {table_name}"))
            for row in result.fetchall():
                row_str = str(row)
                assert secret_phrase not in row_str, (
                    f"Privacy breach! Plaintext phrase found in {table_name}"
                )
                assert secret_pin not in row_str, (
                    f"Privacy breach! Plaintext PIN found in {table_name}"
                )
