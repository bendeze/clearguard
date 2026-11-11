"""Comprehensive Milestone B4 Integration and Compatibility Verification Suite.

Validates the full Synchronization and Distribution contract for the ClearGuard Android system.
"""

import hashlib
import time
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
# B4.4.1 — Version Comparison & State Machine Tests
# ==============================================================================


@pytest.mark.anyio
async def test_milestone_b4_version_comparison_and_state_machine(
    async_client: AsyncClient, setup_database
) -> None:
    """Verify end-to-end sync state machine transitions as blocklists evolve and roll back."""
    # 1. Create a blocklist
    res_bl = await async_client.post(
        "/api/v1/blocklists",
        json={"name": "Lifecycle Tracking Blocklist"},
    )
    assert res_bl.status_code == 201
    b_id = res_bl.json()["id"]

    # Ingest 3 domains and publish version 1.0.0
    await async_client.post(
        f"/api/v1/blocklists/{b_id}/ingest",
        json={"content": "site-a.com\nsite-b.com\nsite-c.com\n"},
    )
    pub_v1 = (
        await async_client.post(
            f"/api/v1/blocklists/{b_id}/publish",
            json={"version": "1.0.0", "changelog": "Initial stable seed"},
        )
    ).json()
    hash_v1 = pub_v1["content_hash"]

    # State 1: Fresh client with no cached version -> OUTDATED
    check_fresh = await async_client.post(
        "/api/v1/sync/check",
        json={"blocklist_id": b_id, "client_version": None, "client_content_hash": None},
    )
    assert check_fresh.status_code == 200
    assert check_fresh.json()["status"] == "outdated"
    assert check_fresh.json()["update_required"] is True

    # State 2: Client downloaded 1.0.0 and checks again -> UP_TO_DATE
    check_up_to_date = await async_client.post(
        "/api/v1/sync/check",
        json={"blocklist_id": b_id, "client_version": "1.0.0", "client_content_hash": hash_v1},
    )
    assert check_up_to_date.status_code == 200
    assert check_up_to_date.json()["status"] == "up_to_date"
    assert check_up_to_date.json()["update_required"] is False

    # State 3: Server publishes 1.1.0 with additional domains
    await async_client.post(
        f"/api/v1/blocklists/{b_id}/ingest",
        json={"content": "site-d.com\nsite-e.com\n"},
    )
    pub_v2 = (
        await async_client.post(
            f"/api/v1/blocklists/{b_id}/publish",
            json={"version": "1.1.0", "changelog": "Added 2 new domains"},
        )
    ).json()
    hash_v2 = pub_v2["content_hash"]
    assert hash_v1 != hash_v2

    # Client on 1.0.0 checks server -> UPDATE_AVAILABLE
    check_avail = await async_client.post(
        "/api/v1/sync/check",
        json={"blocklist_id": b_id, "client_version": "1.0.0", "client_content_hash": hash_v1},
    )
    assert check_avail.status_code == 200
    assert check_avail.json()["status"] == "update_available"
    assert check_avail.json()["update_required"] is True
    assert check_avail.json()["latest_version"] == "1.1.0"
    assert check_avail.json()["latest_content_hash"] == hash_v2

    # State 4: Server executes emergency rollback to 1.0.0
    rb = await async_client.post(
        f"/api/v1/blocklists/{b_id}/rollback",
        json={"target_version": "1.0.0", "reason": "Testing rollback state transition"},
    )
    assert rb.status_code == 200

    # Client that had already upgraded to 1.1.0 now checks -> OUTDATED (diverged from active)
    check_reverted = await async_client.post(
        "/api/v1/sync/check",
        json={"blocklist_id": b_id, "client_version": "1.1.0", "client_content_hash": hash_v2},
    )
    assert check_reverted.status_code == 200
    assert check_reverted.json()["status"] == "outdated"
    assert check_reverted.json()["update_required"] is True
    assert check_reverted.json()["latest_version"] == "1.0.0"
    assert check_reverted.json()["latest_content_hash"] == hash_v1


# ==============================================================================
# B4.4.2 — Delivery Formats & Conditional Caching Tests
# ==============================================================================


@pytest.mark.anyio
async def test_milestone_b4_delivery_formats_and_etag_caching(
    async_client: AsyncClient, setup_database
) -> None:
    """Verify JSON and raw delivery formats with ETag 304 conditional caching."""
    # Seed blocklist with 3 domains
    res = await async_client.post(
        "/api/v1/blocklists",
        json={"name": "Delivery Format Test List"},
    )
    b_id = res.json()["id"]
    await async_client.post(
        f"/api/v1/blocklists/{b_id}/ingest",
        json={"content": "alpha.org\nbeta.net\ngamma.com\n"},
    )
    pub = (
        await async_client.post(
            f"/api/v1/blocklists/{b_id}/publish",
            json={"version": "1.0.0"},
        )
    ).json()
    content_hash = pub["content_hash"]

    # 1. Download via JSON (default)
    res_json = await async_client.get(f"/api/v1/sync/blocklists/{b_id}/download")
    assert res_json.status_code == 200
    assert "application/json" in res_json.headers["content-type"]
    assert res_json.headers["etag"] == f'"{content_hash}"'
    assert res_json.headers["x-content-hash"] == content_hash
    assert res_json.headers["x-blocklist-version"] == "1.0.0"
    assert res_json.headers["x-domain-count"] == "3"
    assert "public, max-age=3600" in res_json.headers["cache-control"]

    data_json = res_json.json()
    assert data_json["domains"] == ["alpha.org", "beta.net", "gamma.com"]

    # 2. Download via raw plain text (format=raw query param)
    res_raw = await async_client.get(f"/api/v1/sync/blocklists/{b_id}/download?format=raw")
    assert res_raw.status_code == 200
    assert "text/plain" in res_raw.headers["content-type"]
    assert res_raw.headers["etag"] == f'"{content_hash}"'
    assert res_raw.text == "alpha.org\nbeta.net\ngamma.com"

    # 3. Download via Accept header (Accept: text/plain)
    res_accept = await async_client.get(
        f"/api/v1/sync/blocklists/{b_id}/download",
        headers={"Accept": "text/plain"},
    )
    assert res_accept.status_code == 200
    assert "text/plain" in res_accept.headers["content-type"]
    assert res_accept.text == "alpha.org\nbeta.net\ngamma.com"

    # 4. Conditional caching: If-None-Match matching current ETag -> 304 Not Modified
    res_cached = await async_client.get(
        f"/api/v1/sync/blocklists/{b_id}/download",
        headers={"If-None-Match": f'"{content_hash}"'},
    )
    assert res_cached.status_code == 304
    assert res_cached.content == b""
    assert res_cached.headers["etag"] == f'"{content_hash}"'
    assert res_cached.headers["x-content-hash"] == content_hash


# ==============================================================================
# B4.4.3 — Cryptographic Integrity Verification Tests
# ==============================================================================


@pytest.mark.anyio
async def test_milestone_b4_integrity_metadata_verification(
    async_client: AsyncClient, setup_database
) -> None:
    """Verify that Android client SHA-256 calculation matches server hash identically."""
    res = await async_client.post(
        "/api/v1/blocklists",
        json={"name": "Integrity Test Blocklist"},
    )
    b_id = res.json()["id"]
    domain_list = ["zebra.com", "apple.net", "banana.org", "cherry.io"]
    await async_client.post(
        f"/api/v1/blocklists/{b_id}/ingest",
        json={"content": "\n".join(domain_list) + "\n"},
    )
    pub = (
        await async_client.post(
            f"/api/v1/blocklists/{b_id}/publish",
            json={"version": "1.0.0"},
        )
    ).json()
    server_hash = pub["content_hash"]

    # Client downloads raw payload
    download = await async_client.get(f"/api/v1/sync/blocklists/{b_id}/download?format=raw")
    assert download.status_code == 200

    # Client computes SHA-256 over raw downloaded bytes
    client_hash = hashlib.sha256(download.content).hexdigest()
    assert client_hash == server_hash
    assert client_hash == download.headers["x-content-hash"]


# ==============================================================================
# B4.4.4 — Invalid Versions & Resiliency Tests
# ==============================================================================


@pytest.mark.anyio
async def test_milestone_b4_invalid_inputs_and_edge_cases(
    async_client: AsyncClient, setup_database
) -> None:
    """Verify robust error handling across all sync routes."""
    # 1. Non-UUID blocklist ID on sync check
    res_bad_id = await async_client.post(
        "/api/v1/sync/check",
        json={"blocklist_id": "not-a-valid-uuid"},
    )
    assert res_bad_id.status_code == 422

    # 2. Nonexistent blocklist ID on sync check -> 404
    missing_id = str(uuid.uuid4())
    res_missing = await async_client.post(
        "/api/v1/sync/check",
        json={"blocklist_id": missing_id},
    )
    assert res_missing.status_code == 404

    # 3. Empty items array in batch check -> 422
    res_empty_batch = await async_client.post(
        "/api/v1/sync/batch",
        json={"items": []},
    )
    assert res_empty_batch.status_code == 422

    # 4. Nonexistent version on download -> 404
    bl = (
        await async_client.post(
            "/api/v1/blocklists",
            json={"name": "Valid Blocklist"},
        )
    ).json()
    await async_client.post(
        f"/api/v1/blocklists/{bl['id']}/ingest",
        json={"content": "testsite.com\n"},
    )
    await async_client.post(
        f"/api/v1/blocklists/{bl['id']}/publish",
        json={"version": "1.0.0"},
    )

    res_missing_ver = await async_client.get(
        f"/api/v1/sync/blocklists/{bl['id']}/download?version=99.9.9"
    )
    assert res_missing_ver.status_code == 404


# ==============================================================================
# B4.4.5 — Large Blocklist Stress & Determinism Tests
# ==============================================================================


@pytest.mark.anyio
async def test_milestone_b4_large_blocklist_stress_and_determinism(
    async_client: AsyncClient, setup_database
) -> None:
    """Verify performance and deterministic sorting/hashing on 1,000 domains."""
    res = await async_client.post(
        "/api/v1/blocklists",
        json={"name": "Large Scale Blocklist"},
    )
    b_id = res.json()["id"]

    # Generate 1,000 unique domains in reverse order
    domains_1000 = [f"domain-{i:04d}.adult-test.com" for i in reversed(range(1000))]
    feed_body = "\n".join(domains_1000) + "\n"

    # Ingest feed
    ingest_res = await async_client.post(
        f"/api/v1/blocklists/{b_id}/ingest",
        json={"content": feed_body},
    )
    assert ingest_res.status_code == 200

    # Publish version 1.0.0
    pub_res = await async_client.post(
        f"/api/v1/blocklists/{b_id}/publish",
        json={"version": "1.0.0"},
    )
    assert pub_res.status_code == 201
    content_hash = pub_res.json()["content_hash"]

    # Benchmark download latency
    start_time = time.perf_counter()
    dl_res = await async_client.get(f"/api/v1/sync/blocklists/{b_id}/download?format=raw")
    duration = time.perf_counter() - start_time

    assert dl_res.status_code == 200
    assert duration < 0.500  # Sub-500ms even with SQLite in test environment
    assert dl_res.headers["x-domain-count"] == "1000"

    # Verify domains are sorted alphabetically (domain-0000 -> domain-0999)
    lines = dl_res.text.strip().split("\n")
    assert len(lines) == 1000
    assert lines[0] == "domain-0000.adult-test.com"
    assert lines[-1] == "domain-0999.adult-test.com"
    assert lines == sorted(lines)

    # Verify SHA-256 matches
    assert hashlib.sha256(dl_res.content).hexdigest() == content_hash


# ==============================================================================
# B4.4.6 — Android Contract Compatibility Tests
# ==============================================================================


@pytest.mark.anyio
async def test_milestone_b4_android_contract_compatibility(
    async_client: AsyncClient, setup_database
) -> None:
    """Verify payload structures and field naming adhere to Android integration DTOs."""
    res = await async_client.post(
        "/api/v1/blocklists",
        json={"name": "Android Contract Compliance List"},
    )
    b_id = res.json()["id"]
    await async_client.post(
        f"/api/v1/blocklists/{b_id}/ingest",
        json={"content": "compliance-domain.com\n"},
    )
    await async_client.post(
        f"/api/v1/blocklists/{b_id}/publish",
        json={"version": "1.0.0", "changelog": "Contract verification"},
    )

    # 1. SyncCheckResponse contract
    sync_res = await async_client.post(
        "/api/v1/sync/check",
        json={"blocklist_id": b_id},
    )
    assert sync_res.status_code == 200
    data = sync_res.json()

    expected_keys = {
        "blocklist_id",
        "status",
        "update_required",
        "latest_version",
        "latest_content_hash",
        "domain_count",
        "changelog",
        "download_url",
    }
    assert expected_keys.issubset(data.keys())
    assert isinstance(data["update_required"], bool)
    assert isinstance(data["domain_count"], int)
    assert isinstance(data["latest_version"], str)
    assert len(data["latest_content_hash"]) == 64

    # 2. BlocklistDownloadResponse contract
    dl_res = await async_client.get(f"/api/v1/sync/blocklists/{b_id}/download")
    assert dl_res.status_code == 200
    dl_data = dl_res.json()

    expected_dl_keys = {
        "blocklist_id",
        "name",
        "version",
        "content_hash",
        "domain_count",
        "published_at",
        "changelog",
        "domains",
    }
    assert expected_dl_keys.issubset(dl_data.keys())
    assert isinstance(dl_data["domains"], list)
    assert len(dl_data["domains"]) == 1
    assert dl_data["domains"][0] == "compliance-domain.com"
