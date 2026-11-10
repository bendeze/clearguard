"""Comprehensive Milestone B5 Integration and Production Readiness Verification Suite.

Validates the full Security, Deployment, and Android MVP Readiness for ClearGuard Backend.
"""

import hashlib

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
# B5.4.1 & B5.4.2 — Android MVP Flow & Production Blocklist Retrieval
# ==============================================================================


@pytest.mark.anyio
async def test_milestone_b5_end_to_end_android_mvp_flow(
    async_client: AsyncClient, setup_database
) -> None:
    """Verify complete Android MVP synchronization, rule retrieval,
    caching, and integrity verification.
    """
    # 1. Register default adult blocklist collection
    create_res = await async_client.post(
        "/api/v1/blocklists",
        json={
            "name": "ClearGuard Core Adult Filter",
            "description": "Primary high-confidence adult content domain filter",
            "is_default": True,
        },
    )
    assert create_res.status_code == 201
    b_id = create_res.json()["id"]

    # 2. Ingest curated domain feed
    feed_data = "||bad-adult-domain.com^\n0.0.0.0 porn-tube-stream.net\nhardcore-xxx-tracker.org\n"
    ingest_res = await async_client.post(
        f"/api/v1/blocklists/{b_id}/ingest",
        json={"content": feed_data, "source": "curated_mvp_feed"},
    )
    assert ingest_res.status_code == 200
    assert ingest_res.json()["total_blocklist_domains"] == 3

    # 3. Publish baseline version 1.0.0
    pub_res = await async_client.post(
        f"/api/v1/blocklists/{b_id}/publish",
        json={"version": "1.0.0", "changelog": "Initial Android MVP release snapshot"},
    )
    assert pub_res.status_code == 201
    server_hash = pub_res.json()["content_hash"]

    # 4. Android Client queries batch sync for its configured blocklist
    batch_check = await async_client.post(
        "/api/v1/sync/batch",
        json={
            "items": [
                {
                    "blocklist_id": b_id,
                    "client_version": None,
                    "client_content_hash": None,
                }
            ]
        },
    )
    assert batch_check.status_code == 200
    batch_items = batch_check.json()["items"]
    assert len(batch_items) == 1
    assert batch_items[0]["status"] == "outdated"
    assert batch_items[0]["update_required"] is True
    assert batch_items[0]["latest_version"] == "1.0.0"
    assert batch_items[0]["latest_content_hash"] == server_hash

    # 5. Android Client downloads raw rules stream
    download_res = await async_client.get(f"/api/v1/sync/blocklists/{b_id}/download?format=raw")
    assert download_res.status_code == 200
    assert "text/plain" in download_res.headers["content-type"]
    assert download_res.headers["etag"] == f'"{server_hash}"'
    assert download_res.headers["x-content-hash"] == server_hash
    assert download_res.headers["x-blocklist-version"] == "1.0.0"
    assert download_res.headers["x-domain-count"] == "3"

    # 6. Android Client performs cryptographic integrity check
    client_computed_hash = hashlib.sha256(download_res.content).hexdigest()
    assert client_computed_hash == server_hash

    # 7. Subsequent client check returns UP_TO_DATE
    sync_check = await async_client.post(
        "/api/v1/sync/check",
        json={
            "blocklist_id": b_id,
            "client_version": "1.0.0",
            "client_content_hash": server_hash,
        },
    )
    assert sync_check.status_code == 200
    assert sync_check.json()["status"] == "up_to_date"
    assert sync_check.json()["update_required"] is False

    # 8. Conditional download with ETag returns 304 Not Modified (0 bytes body)
    cached_download = await async_client.get(
        f"/api/v1/sync/blocklists/{b_id}/download",
        headers={"If-None-Match": f'"{server_hash}"'},
    )
    assert cached_download.status_code == 304
    assert cached_download.content == b""


# ==============================================================================
# B5.4.3 — Sync Failure & Emergency Rollback Recovery Scenarios
# ==============================================================================


@pytest.mark.anyio
async def test_milestone_b5_sync_failure_and_rollback_recovery(
    async_client: AsyncClient, setup_database
) -> None:
    """Verify system resilience during client cache corruption and emergency server rollback."""
    # 1. Create blocklist and publish version 1.0.0
    bl = (
        await async_client.post(
            "/api/v1/blocklists",
            json={"name": "Fault Recovery Blocklist"},
        )
    ).json()
    b_id = bl["id"]

    await async_client.post(
        f"/api/v1/blocklists/{b_id}/ingest",
        json={"content": "safe-adult-1.com\nsafe-adult-2.com\n"},
    )
    v1 = (
        await async_client.post(
            f"/api/v1/blocklists/{b_id}/publish",
            json={"version": "1.0.0"},
        )
    ).json()
    hash_v1 = v1["content_hash"]

    # 2. Corrupted client state: valid version string but altered hash
    corrupt_check = await async_client.post(
        "/api/v1/sync/check",
        json={
            "blocklist_id": b_id,
            "client_version": "1.0.0",
            "client_content_hash": "f" * 64,
        },
    )
    assert corrupt_check.status_code == 200
    # Server detects hash divergence and flags client as outdated
    assert corrupt_check.json()["status"] == "outdated"
    assert corrupt_check.json()["update_required"] is True

    # 3. Publish faulty version 1.1.0
    await async_client.post(
        f"/api/v1/blocklists/{b_id}/ingest",
        json={"content": "accidental-false-positive.com\n"},
    )
    v2 = (
        await async_client.post(
            f"/api/v1/blocklists/{b_id}/publish",
            json={"version": "1.1.0"},
        )
    ).json()
    hash_v2 = v2["content_hash"]

    # 4. Perform emergency administrative rollback to 1.0.0
    rollback_res = await async_client.post(
        f"/api/v1/blocklists/{b_id}/rollback",
        json={
            "target_version": "1.0.0",
            "reason": "False positive in 1.1.0, rolling back to 1.0.0",
        },
    )
    assert rollback_res.status_code == 200

    # 5. Client on 1.1.0 queries server and is properly redirected to download 1.0.0
    recovery_check = await async_client.post(
        "/api/v1/sync/check",
        json={
            "blocklist_id": b_id,
            "client_version": "1.1.0",
            "client_content_hash": hash_v2,
        },
    )
    assert recovery_check.status_code == 200
    rec_data = recovery_check.json()
    assert rec_data["status"] == "outdated"
    assert rec_data["update_required"] is True
    assert rec_data["latest_version"] == "1.0.0"
    assert rec_data["latest_content_hash"] == hash_v1


# ==============================================================================
# B5.4.4 — Comprehensive API Regression Testing
# ==============================================================================


@pytest.mark.anyio
async def test_milestone_b5_complete_api_regression(
    async_client: AsyncClient, setup_database
) -> None:
    """End-to-end regression test validating health, blocklists, versions, sync,
    and security headers.
    """
    # 1. Health and readiness
    health = await async_client.get("/api/v1/health")
    assert health.status_code == 200
    assert health.headers["x-content-type-options"] == "nosniff"

    ready = await async_client.get("/api/v1/health/ready")
    assert ready.status_code == 200
    assert ready.json()["database"] == "connected"

    live = await async_client.get("/api/v1/health/live")
    assert live.status_code == 200
    assert live.json()["status"] == "alive"

    # 2. Blocklist CRUD
    bl = (
        await async_client.post(
            "/api/v1/blocklists",
            json={"name": "Regression Test Blocklist"},
        )
    ).json()
    b_id = bl["id"]

    # 3. Associate domains
    await async_client.post(
        f"/api/v1/blocklists/{b_id}/ingest",
        json={"content": "site1.com\nsite2.com\n"},
    )

    # 4. Publish version
    pub = (
        await async_client.post(
            f"/api/v1/blocklists/{b_id}/publish",
            json={"version": "1.0.0"},
        )
    ).json()

    # 5. Sync metadata
    meta = await async_client.get(f"/api/v1/sync/blocklists/{b_id}/latest")
    assert meta.status_code == 200
    assert meta.json()["latest_content_hash"] == pub["content_hash"]

    # 6. JSON and raw download
    json_dl = await async_client.get(f"/api/v1/sync/blocklists/{b_id}/download")
    assert json_dl.status_code == 200
    assert len(json_dl.json()["domains"]) == 2

    raw_dl = await async_client.get(f"/api/v1/sync/blocklists/{b_id}/download?format=raw")
    assert raw_dl.status_code == 200
    assert raw_dl.text == "site1.com\nsite2.com"
