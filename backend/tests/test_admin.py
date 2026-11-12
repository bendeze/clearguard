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


@pytest.mark.anyio
async def test_admin_list_users_and_devices(
    async_client: AsyncClient, setup_admin_database
) -> None:
    """Verify admin-only client directory and device inventory without exposing secrets."""
    reg_client = await async_client.post(
        "/api/v1/auth/register",
        json={
            "username": "alice_client",
            "password": "ClientPassword123!",
            "email": "alice@example.com",
        },
    )
    assert reg_client.status_code == 201
    client_token = reg_client.json()["access_token"]

    # Register a device and upload an encrypted vault for alice_client
    dev_res = await async_client.post(
        "/api/v1/auth/devices/register",
        headers={"Authorization": f"Bearer {client_token}"},
        json={
            "device_identifier": "android-pixel-8-001",
            "device_name": "Pixel 8 Pro",
            "client_version": "0.7.0",
        },
    )
    assert dev_res.status_code == 201

    vault_res = await async_client.put(
        "/api/v1/vault",
        headers={"Authorization": f"Bearer {client_token}"},
        json={
            "ciphertext": "ZW5jcnlwdGVkX3BsZWRnZV9ibG9i",
            "iv": "MTIzNDU2Nzg5MDEy",
            "tag": "dGFnMTIzNDU2Nzg5MDEyMzQ1Ng==",
            "salt": "c2FsdDEyMzQ1Njc4OTAxMjM0NTY=",
            "kdf_iterations": 100000,
        },
    )
    assert vault_res.status_code == 200

    # Register admin user and promote in DB
    reg_admin = await async_client.post(
        "/api/v1/auth/register",
        json={"username": "root_admin", "password": "AdminPassword123!"},
    )
    assert reg_admin.status_code == 201
    admin_token = reg_admin.json()["access_token"]

    async with engine.begin() as conn:
        await conn.execute(
            User.__table__.update().where(User.username == "root_admin").values(is_admin=True)
        )

    # Unauthenticated and non-admin access must be denied
    assert (await async_client.get("/api/v1/admin/users")).status_code == 401
    assert (await async_client.get("/api/v1/admin/devices")).status_code == 401
    assert (
        await async_client.get(
            "/api/v1/admin/users",
            headers={"Authorization": f"Bearer {client_token}"},
        )
    ).status_code == 403
    assert (
        await async_client.get(
            "/api/v1/admin/devices",
            headers={"Authorization": f"Bearer {client_token}"},
        )
    ).status_code == 403

    # Admin lists users with search query
    users_res = await async_client.get(
        "/api/v1/admin/users?query=alice",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert users_res.status_code == 200
    users_payload = users_res.json()
    assert users_payload["total"] == 1
    alice_item = users_payload["items"][0]
    assert alice_item["username"] == "alice_client"
    assert alice_item["email"] == "alice@example.com"
    assert alice_item["device_count"] == 1
    assert alice_item["has_vault"] is True
    assert alice_item["vault_version"] == 1
    assert alice_item["devices"][0]["device_name"] == "Pixel 8 Pro"
    assert "hashed_password" not in alice_item
    assert "ciphertext" not in alice_item

    # Admin lists devices
    devices_res = await async_client.get(
        "/api/v1/admin/devices?query=Pixel",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert devices_res.status_code == 200
    devices_payload = devices_res.json()
    assert devices_payload["total"] == 1
    device_item = devices_payload["items"][0]
    assert device_item["username"] == "alice_client"
    assert device_item["device_identifier"] == "android-pixel-8-001"
    assert device_item["client_version"] == "0.7.0"
    assert device_item["is_active"] is True
