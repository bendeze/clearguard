"""Tests for ClearGuard Admin Emergency Early Override and Ed25519 Signatures (Phase B6.4)."""

import json

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
from httpx import AsyncClient

from app.core.config import Settings
from app.core.crypto import CryptoManager, get_crypto_manager
from app.core.database import engine
from app.models.base import Base
from app.models.user import User


@pytest.fixture
async def setup_admin_database():
    """Ensure clean schema for admin override tests."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.anyio
async def test_admin_emergency_override_flow_and_ed25519_verification(
    async_client: AsyncClient, setup_admin_database
) -> None:
    """Verify admin approval, asymmetric Ed25519 signature, and offline public key verification."""
    # 1. Register normal user and an admin user
    reg_user = await async_client.post(
        "/api/v1/auth/register",
        json={"username": "helen_user", "password": "UserPassword123!"},
    )
    user_token = reg_user.json()["access_token"]

    reg_admin = await async_client.post(
        "/api/v1/auth/register",
        json={"username": "ian_admin", "password": "AdminPassword123!"},
    )
    admin_token = reg_admin.json()["access_token"]

    # Mark ian_admin as is_admin=True directly in DB
    async with engine.begin() as conn:
        await conn.execute(
            User.__table__.update().where(User.username == "ian_admin").values(is_admin=True)
        )

    # 2. User initiates deactivation
    deact_res = await async_client.post(
        "/api/v1/accountability/request-deactivation",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"partner_email": "partner@example.com"},
    )
    req_id = deact_res.json()["request_id"]

    # 3. Non-admin cannot approve override (RBAC test)
    forbidden_res = await async_client.post(
        "/api/v1/admin/override-requests/approve",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "request_id": req_id,
            "reason": "Unauthorized attempt",
        },
    )
    assert forbidden_res.status_code == 403

    # 4. Admin approves override
    approve_res = await async_client.post(
        "/api/v1/admin/override-requests/approve",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "request_id": req_id,
            "reason": "User sold their phone and requested emergency detachment.",
        },
    )
    assert approve_res.status_code == 201
    approve_data = approve_res.json()
    assert "signed_token" in approve_data

    # Parse signed token
    token_obj = json.loads(approve_data["signed_token"])
    payload = token_obj["payload"]
    signature_b64 = token_obj["signature"]

    # 5. Fetch public key
    pub_res = await async_client.get("/api/v1/admin/public-key")
    assert pub_res.status_code == 200
    assert "BEGIN PUBLIC KEY" in pub_res.json()["public_key_pem"]

    # 6. Verify Ed25519 digital signature
    crypto_mgr = get_crypto_manager()
    payload_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")
    is_valid = crypto_mgr.verify_signature(payload_bytes, signature_b64)
    assert is_valid is True

    # 7. Tampered payload fails verification
    tampered_bytes = json.dumps({**payload, "user_id": "fake_id"}, sort_keys=True).encode("utf-8")
    assert crypto_mgr.verify_signature(tampered_bytes, signature_b64) is False


def test_crypto_manager_loads_escaped_newline_pem() -> None:
    """Verify CryptoManager normalizes escaped \\n PEM private keys from cloud env UIs."""
    key = ed25519.Ed25519PrivateKey.generate()
    raw_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")
    escaped_pem = raw_pem.replace("\n", "\\n")

    mgr = CryptoManager(settings=Settings(admin_override_private_key=escaped_pem))
    sig = mgr.sign_bytes(b"cloud-env-pem-test")
    assert mgr.verify_signature(b"cloud-env-pem-test", sig) is True
    assert "BEGIN PUBLIC KEY" in mgr.get_public_key_pem()
