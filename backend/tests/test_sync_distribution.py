"""Integration tests for Blocklist Distribution Services (Phase B4.2)."""

import hashlib
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


async def seed_test_blocklist(
    async_client: AsyncClient, name: str = "Adult Filter Primary"
) -> tuple[dict, str]:
    """Helper to create a blocklist, associate domains, and publish an initial version."""
    # 1. Create blocklist
    res = await async_client.post(
        "/api/v1/blocklists",
        json={"name": name, "description": "High-confidence adult domain blocklist"},
    )
    assert res.status_code == 201
    blocklist_data = res.json()
    b_id = blocklist_data["id"]

    # 2. Ingest domain feed
    feed_content = "xxx-portal.com\nadult-tube.org\nhardcore-video.net\n"
    feed_res = await async_client.post(
        f"/api/v1/blocklists/{b_id}/ingest",
        json={"content": feed_content, "source": "test_feed", "category": "pornography"},
    )
    assert feed_res.status_code == 200

    # 3. Publish version 1.0.0
    pub_res = await async_client.post(
        f"/api/v1/blocklists/{b_id}/publish",
        json={"version": "1.0.0", "changelog": "Initial baseline seed"},
    )
    assert pub_res.status_code == 201
    version_data = pub_res.json()
    content_hash = version_data["content_hash"]

    return blocklist_data, content_hash


# ==============================================================================
# Single Sync Check Tests
# ==============================================================================


@pytest.mark.anyio
async def test_sync_check_up_to_date(async_client: AsyncClient, setup_database) -> None:
    """Verify client with matching hash and version receives UP_TO_DATE status."""
    blocklist_data, content_hash = await seed_test_blocklist(async_client)
    b_id = blocklist_data["id"]

    res = await async_client.post(
        "/api/v1/sync/check",
        json={
            "blocklist_id": b_id,
            "client_version": "1.0.0",
            "client_content_hash": content_hash,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["blocklist_id"] == b_id
    assert data["status"] == "up_to_date"
    assert data["update_required"] is False
    assert data["latest_version"] == "1.0.0"
    assert data["latest_content_hash"] == content_hash
    assert data["domain_count"] == 3
    assert data["download_url"] == f"/api/v1/sync/blocklists/{b_id}/download"


@pytest.mark.anyio
async def test_sync_check_update_available(async_client: AsyncClient, setup_database) -> None:
    """Verify client with older version receives UPDATE_AVAILABLE status."""
    blocklist_data, content_hash = await seed_test_blocklist(async_client)
    b_id = blocklist_data["id"]

    res = await async_client.post(
        "/api/v1/sync/check",
        json={
            "blocklist_id": b_id,
            "client_version": "0.9.0",
            "client_content_hash": "a" * 64,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "update_available"
    assert data["update_required"] is True
    assert data["latest_version"] == "1.0.0"


@pytest.mark.anyio
async def test_sync_check_outdated_missing_cache(async_client: AsyncClient, setup_database) -> None:
    """Verify client without version/hash receives OUTDATED status."""
    blocklist_data, content_hash = await seed_test_blocklist(async_client)
    b_id = blocklist_data["id"]

    res = await async_client.post(
        "/api/v1/sync/check",
        json={
            "blocklist_id": b_id,
            "client_version": None,
            "client_content_hash": None,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "outdated"
    assert data["update_required"] is True


@pytest.mark.anyio
async def test_sync_check_nonexistent_blocklist(async_client: AsyncClient, setup_database) -> None:
    """Verify checking a nonexistent blocklist returns 404."""
    random_id = str(uuid.uuid4())
    res = await async_client.post(
        "/api/v1/sync/check",
        json={
            "blocklist_id": random_id,
            "client_version": "1.0.0",
            "client_content_hash": "a" * 64,
        },
    )
    assert res.status_code == 404
    err = res.json()
    assert "error" in err


# ==============================================================================
# Batch Sync Check Tests
# ==============================================================================


@pytest.mark.anyio
async def test_sync_batch_check_success(async_client: AsyncClient, setup_database) -> None:
    """Verify multi-blocklist batch evaluation in a single request."""
    bl1, hash1 = await seed_test_blocklist(async_client, name="Blocklist One")
    bl2, hash2 = await seed_test_blocklist(async_client, name="Blocklist Two")

    batch_payload = {
        "items": [
            {
                "blocklist_id": bl1["id"],
                "client_version": "1.0.0",
                "client_content_hash": hash1,
            },
            {
                "blocklist_id": bl2["id"],
                "client_version": "0.1.0",
                "client_content_hash": "b" * 64,
            },
        ]
    }

    res = await async_client.post("/api/v1/sync/batch", json=batch_payload)
    assert res.status_code == 200
    data = res.json()
    assert len(data["items"]) == 2

    # First item is up to date
    assert data["items"][0]["blocklist_id"] == bl1["id"]
    assert data["items"][0]["status"] == "up_to_date"
    assert data["items"][0]["update_required"] is False

    # Second item has update available
    assert data["items"][1]["blocklist_id"] == bl2["id"]
    assert data["items"][1]["status"] == "update_available"
    assert data["items"][1]["update_required"] is True


# ==============================================================================
# Latest Metadata Endpoint Tests
# ==============================================================================


@pytest.mark.anyio
async def test_sync_latest_metadata(async_client: AsyncClient, setup_database) -> None:
    """Verify inspecting latest metadata for a published blocklist."""
    blocklist_data, content_hash = await seed_test_blocklist(async_client)
    b_id = blocklist_data["id"]

    res = await async_client.get(f"/api/v1/sync/blocklists/{b_id}/latest")
    assert res.status_code == 200
    data = res.json()
    assert data["blocklist_id"] == b_id
    assert data["latest_version"] == "1.0.0"
    assert data["latest_content_hash"] == content_hash
    assert data["domain_count"] == 3


@pytest.mark.anyio
async def test_sync_latest_metadata_no_versions(async_client: AsyncClient, setup_database) -> None:
    """Verify 404 is returned when a blocklist exists but has no published versions."""
    res = await async_client.post(
        "/api/v1/blocklists",
        json={"name": "Unpublished Collection", "description": "No versions yet"},
    )
    b_id = res.json()["id"]

    latest_res = await async_client.get(f"/api/v1/sync/blocklists/{b_id}/latest")
    assert latest_res.status_code == 404


# ==============================================================================
# Blocklist Download & Conditional Caching Tests
# ==============================================================================


@pytest.mark.anyio
async def test_sync_download_json_format_and_integrity(
    async_client: AsyncClient, setup_database
) -> None:
    """Verify downloading full domain list in JSON format and verifying cryptographic integrity."""
    blocklist_data, content_hash = await seed_test_blocklist(async_client)
    b_id = blocklist_data["id"]

    res = await async_client.get(f"/api/v1/sync/blocklists/{b_id}/download")
    assert res.status_code == 200

    # Verify custom response headers
    assert res.headers["etag"] == f'"{content_hash}"'
    assert res.headers["x-content-hash"] == content_hash
    assert res.headers["x-blocklist-version"] == "1.0.0"
    assert res.headers["x-domain-count"] == "3"
    assert "public, max-age=3600" in res.headers["cache-control"]

    # Verify payload body
    data = res.json()
    assert data["blocklist_id"] == b_id
    assert data["version"] == "1.0.0"
    assert data["content_hash"] == content_hash
    assert data["domain_count"] == 3
    assert data["domains"] == ["adult-tube.org", "hardcore-video.net", "xxx-portal.com"]

    # Validate local client SHA-256 calculation matches server content hash
    joined = "\n".join(data["domains"]).encode("utf-8")
    client_computed_hash = hashlib.sha256(joined).hexdigest()
    assert client_computed_hash == content_hash


@pytest.mark.anyio
async def test_sync_download_raw_format_and_accept_header(
    async_client: AsyncClient, setup_database
) -> None:
    """Verify downloading raw plain text stream via format query parameter and Accept header."""
    blocklist_data, content_hash = await seed_test_blocklist(async_client)
    b_id = blocklist_data["id"]

    # 1. Download with ?format=raw
    res_param = await async_client.get(f"/api/v1/sync/blocklists/{b_id}/download?format=raw")
    assert res_param.status_code == 200
    assert "text/plain" in res_param.headers["content-type"]
    assert res_param.headers["etag"] == f'"{content_hash}"'
    assert res_param.headers["x-domain-count"] == "3"
    assert res_param.text == "adult-tube.org\nhardcore-video.net\nxxx-portal.com"

    # 2. Download with Accept: text/plain header
    res_header = await async_client.get(
        f"/api/v1/sync/blocklists/{b_id}/download",
        headers={"Accept": "text/plain"},
    )
    assert res_header.status_code == 200
    assert "text/plain" in res_header.headers["content-type"]
    assert res_header.text == "adult-tube.org\nhardcore-video.net\nxxx-portal.com"


@pytest.mark.anyio
async def test_sync_download_conditional_caching_etag_304(
    async_client: AsyncClient, setup_database
) -> None:
    """Verify conditional caching: If-None-Match with matching ETag returns 304 Not Modified."""
    blocklist_data, content_hash = await seed_test_blocklist(async_client)
    b_id = blocklist_data["id"]

    # 1. Quoted ETag
    res_quoted = await async_client.get(
        f"/api/v1/sync/blocklists/{b_id}/download",
        headers={"If-None-Match": f'"{content_hash}"'},
    )
    assert res_quoted.status_code == 304
    assert res_quoted.content == b""
    assert res_quoted.headers["etag"] == f'"{content_hash}"'
    assert res_quoted.headers["x-content-hash"] == content_hash
    assert res_quoted.headers["x-blocklist-version"] == "1.0.0"

    # 2. Unquoted hash
    res_unquoted = await async_client.get(
        f"/api/v1/sync/blocklists/{b_id}/download",
        headers={"If-None-Match": content_hash},
    )
    assert res_unquoted.status_code == 304
    assert res_unquoted.content == b""

    # 3. Wildcard ETag
    res_star = await async_client.get(
        f"/api/v1/sync/blocklists/{b_id}/download",
        headers={"If-None-Match": "*"},
    )
    assert res_star.status_code == 304

    # 4. Stale ETag -> returns 200 with full payload
    res_stale = await async_client.get(
        f"/api/v1/sync/blocklists/{b_id}/download",
        headers={"If-None-Match": f'"{("9" * 64)}"'},
    )
    assert res_stale.status_code == 200
    assert len(res_stale.json()["domains"]) == 3


@pytest.mark.anyio
async def test_sync_download_specific_version_and_not_found(
    async_client: AsyncClient, setup_database
) -> None:
    """Verify downloading specific version and 404 for invalid versions."""
    blocklist_data, content_hash = await seed_test_blocklist(async_client)
    b_id = blocklist_data["id"]

    # 1. Request existing version explicitly
    res_v1 = await async_client.get(f"/api/v1/sync/blocklists/{b_id}/download?version=1.0.0")
    assert res_v1.status_code == 200
    assert res_v1.json()["version"] == "1.0.0"

    # 2. Request nonexistent version
    res_invalid = await async_client.get(f"/api/v1/sync/blocklists/{b_id}/download?version=99.0.0")
    assert res_invalid.status_code == 404

    # 3. Request nonexistent blocklist
    random_id = str(uuid.uuid4())
    res_missing = await async_client.get(f"/api/v1/sync/blocklists/{random_id}/download")
    assert res_missing.status_code == 404
