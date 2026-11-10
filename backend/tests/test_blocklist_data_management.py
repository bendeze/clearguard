"""Integration tests for Blocklist Data Management & Safety Operations (Phase B4.3)."""

import uuid

import pytest
from httpx import AsyncClient

from app.core.database import engine
from app.models.base import Base


@pytest.fixture
async def setup_database():
    """Ensure clean database schema before and after each test."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# ==============================================================================
# Pre-Publication Safety Guardrail Tests
# ==============================================================================


@pytest.mark.anyio
async def test_publish_safety_guardrail_anomalous_zero_drop(
    async_client: AsyncClient, setup_database
) -> None:
    """Verify publishing 0 domains on a previously populated blocklist is blocked unless forced."""
    # 1. Create blocklist
    res = await async_client.post(
        "/api/v1/blocklists",
        json={"name": "Safety Guardrail List"},
    )
    assert res.status_code == 201
    b_id = res.json()["id"]

    # 2. Ingest 4 domains
    feed = "site1.com\nsite2.com\nsite3.com\nsite4.com\n"
    await async_client.post(
        f"/api/v1/blocklists/{b_id}/ingest",
        json={"content": feed, "source": "feed1"},
    )

    # 3. Publish initial 1.0.0
    pub1 = await async_client.post(
        f"/api/v1/blocklists/{b_id}/publish",
        json={"version": "1.0.0"},
    )
    assert pub1.status_code == 201
    assert pub1.json()["domain_count"] == 4

    # 4. Remove all domains
    dom_res = await async_client.get(f"/api/v1/blocklists/{b_id}/domains")
    dom_ids = [d["id"] for d in dom_res.json()["items"]]
    rem_res = await async_client.request(
        "DELETE",
        f"/api/v1/blocklists/{b_id}/domains",
        json={"domain_ids": dom_ids},
    )
    assert rem_res.status_code == 200

    # 5. Attempt publication with 0 domains (should fail 422)
    pub2_fail = await async_client.post(
        f"/api/v1/blocklists/{b_id}/publish",
        json={"version": "1.1.0", "force": False},
    )
    assert pub2_fail.status_code == 422
    err_data = pub2_fail.json()
    assert "error" in err_data
    assert "Anomalous domain drop" in err_data["error"]["message"]

    # 6. Publish with force=True (should succeed)
    pub2_force = await async_client.post(
        f"/api/v1/blocklists/{b_id}/publish",
        json={"version": "1.1.0", "force": True},
    )
    assert pub2_force.status_code == 201
    assert pub2_force.json()["domain_count"] == 0


@pytest.mark.anyio
async def test_publish_safety_guardrail_50_percent_drop(
    async_client: AsyncClient, setup_database
) -> None:
    """Verify publication is rejected when domains drop by more than 50% without force."""
    res = await async_client.post(
        "/api/v1/blocklists",
        json={"name": "Drop Guardrail List"},
    )
    b_id = res.json()["id"]

    # Ingest 10 domains
    feed = "\n".join([f"domain-{i}.com" for i in range(10)]) + "\n"
    await async_client.post(
        f"/api/v1/blocklists/{b_id}/ingest",
        json={"content": feed},
    )

    # Publish 1.0.0 (10 domains)
    pub1 = await async_client.post(
        f"/api/v1/blocklists/{b_id}/publish",
        json={"version": "1.0.0"},
    )
    assert pub1.status_code == 201
    assert pub1.json()["domain_count"] == 10

    # Remove 6 domains (leaving 4, which is > 50% drop)
    doms = (await async_client.get(f"/api/v1/blocklists/{b_id}/domains")).json()["items"]
    to_remove = [d["id"] for d in doms[:6]]
    await async_client.request(
        "DELETE",
        f"/api/v1/blocklists/{b_id}/domains",
        json={"domain_ids": to_remove},
    )

    # Attempt to publish without force -> rejected 422
    pub_blocked = await async_client.post(
        f"/api/v1/blocklists/{b_id}/publish",
        json={"version": "1.1.0", "force": False},
    )
    assert pub_blocked.status_code == 422
    assert "reduction detected" in pub_blocked.json()["error"]["message"]

    # Publish with force -> accepted 201
    pub_ok = await async_client.post(
        f"/api/v1/blocklists/{b_id}/publish",
        json={"version": "1.1.0", "force": True},
    )
    assert pub_ok.status_code == 201
    assert pub_ok.json()["domain_count"] == 4


# ==============================================================================
# Rollback Endpoint & Recovery Tests
# ==============================================================================


@pytest.mark.anyio
async def test_blocklist_rollback_workflow_and_sync_recovery(
    async_client: AsyncClient, setup_database
) -> None:
    """Verify rolling back to prior version and subsequent client sync detection."""
    # 1. Create blocklist
    res = await async_client.post(
        "/api/v1/blocklists",
        json={"name": "Production Blocklist Rollback Target"},
    )
    b_id = res.json()["id"]

    # 2. Ingest 3 domains and publish 1.0.0
    await async_client.post(
        f"/api/v1/blocklists/{b_id}/ingest",
        json={"content": "alpha.com\nbeta.com\ngamma.com\n"},
    )
    pub_v1 = (
        await async_client.post(
            f"/api/v1/blocklists/{b_id}/publish",
            json={"version": "1.0.0", "changelog": "Known good baseline"},
        )
    ).json()
    hash_v1 = pub_v1["content_hash"]

    # 3. Ingest 2 extra domains and publish 1.1.0
    await async_client.post(
        f"/api/v1/blocklists/{b_id}/ingest",
        json={"content": "bad-feed-1.com\nbad-feed-2.com\n"},
    )
    pub_v2 = (
        await async_client.post(
            f"/api/v1/blocklists/{b_id}/publish",
            json={"version": "1.1.0", "changelog": "Buggy release"},
        )
    ).json()
    hash_v2 = pub_v2["content_hash"]
    assert hash_v1 != hash_v2

    # Verify latest metadata reports 1.1.0
    meta_before = (await async_client.get(f"/api/v1/sync/blocklists/{b_id}/latest")).json()
    assert meta_before["latest_version"] == "1.1.0"

    # 4. Rollback to version 1.0.0
    rollback_res = await async_client.post(
        f"/api/v1/blocklists/{b_id}/rollback",
        json={
            "target_version": "1.0.0",
            "reason": "Emergency rollback: bad-feed domains caused false positives",
        },
    )
    assert rollback_res.status_code == 200
    rb_data = rollback_res.json()
    assert rb_data["version"] == "1.0.0"
    assert rb_data["content_hash"] == hash_v1

    # 5. Verify blocklist current_version is updated
    bl_after = (await async_client.get(f"/api/v1/blocklists/{b_id}")).json()
    assert bl_after["current_version"] == "1.0.0"

    # 6. Verify sync latest endpoint now returns 1.0.0
    meta_after = (await async_client.get(f"/api/v1/sync/blocklists/{b_id}/latest")).json()
    assert meta_after["latest_version"] == "1.0.0"
    assert meta_after["latest_content_hash"] == hash_v1

    # 7. Verify client on 1.1.0 checking updates is notified of outdated state
    sync_check = await async_client.post(
        "/api/v1/sync/check",
        json={
            "blocklist_id": b_id,
            "client_version": "1.1.0",
            "client_content_hash": hash_v2,
        },
    )
    assert sync_check.status_code == 200
    check_data = sync_check.json()
    assert check_data["status"] == "outdated"
    assert check_data["update_required"] is True
    assert check_data["latest_version"] == "1.0.0"
    assert check_data["latest_content_hash"] == hash_v1


@pytest.mark.anyio
async def test_blocklist_rollback_error_handling(async_client: AsyncClient, setup_database) -> None:
    """Verify rollback rejects invalid versions and missing blocklists with 404."""
    # 1. Nonexistent blocklist
    random_id = str(uuid.uuid4())
    res_no_blocklist = await async_client.post(
        f"/api/v1/blocklists/{random_id}/rollback",
        json={"target_version": "1.0.0"},
    )
    assert res_no_blocklist.status_code == 404

    # 2. Existing blocklist but nonexistent version
    bl = (
        await async_client.post(
            "/api/v1/blocklists",
            json={"name": "Rollback Error Target"},
        )
    ).json()
    b_id = bl["id"]

    res_no_version = await async_client.post(
        f"/api/v1/blocklists/{b_id}/rollback",
        json={"target_version": "9.9.9"},
    )
    assert res_no_version.status_code == 404
    assert "error" in res_no_version.json()
