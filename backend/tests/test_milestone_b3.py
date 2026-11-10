"""Milestone B3 integration tests covering REST API endpoints, client synchronization,

empty blocklist handling, pagination limits, and OpenAPI schema verification.
"""

import hashlib

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient

from app.core.database import engine, get_db_context
from app.models.base import Base
from app.models.enums import DomainCategory
from app.schemas.domain import DomainCreate
from app.services.domain_service import DomainService


@pytest.fixture
async def setup_database():
    """Ensure clean database schema before and after each test."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# ==============================================================================
# B3.4.1 & B3.4.4 — End-to-End Client Sync & Pagination Lifecycle
# ==============================================================================


@pytest.mark.anyio
async def test_milestone_b3_end_to_end_client_sync_flow(
    async_client: AsyncClient, setup_database
) -> None:
    """Verify complete lifecycle: creation, feed ingestion, domain association,

    pagination limits, and SHA-256 version releases.
    """
    # 1. Register a new primary adult blocklist
    create_payload = {
        "name": "ClearGuard Core Adult Blocklist",
        "description": "Primary high-confidence pornographic domain filtering list",
        "is_default": True,
        "is_active": True,
    }
    create_res = await async_client.post("/api/v1/blocklists", json=create_payload)
    assert create_res.status_code == 201
    bl = create_res.json()
    bl_id = bl["id"]
    assert bl["name"] == "ClearGuard Core Adult Blocklist"
    assert bl["domain_count"] == 0

    # 2. Ingest multi-format third-party feed (Hosts + plain domains)
    raw_feed = """
    # Popular adult tracking hosts
    0.0.0.0 tracker.adultsite.com
    127.0.0.1 cdn.adultvideos.xxx
    ||bad-ads.eroticnetwork.net^
    127.0.0.1 localhost
    """
    ingest_res = await async_client.post(
        f"/api/v1/blocklists/{bl_id}/ingest",
        json={
            "content": raw_feed,
            "source": "milestone_b3_feed",
            "category": "pornography",
        },
    )
    assert ingest_res.status_code == 200
    ingest_data = ingest_res.json()
    assert ingest_data["parsed_count"] == 3
    assert ingest_data["new_domains_created"] == 3
    assert ingest_data["domains_associated"] == 3

    # 3. Associate additional domains manually from DB
    async with get_db_context() as session:
        dom_service = DomainService(session)
        extra_domain = await dom_service.create_domain(
            DomainCreate(domain="extra-badsite.org", category=DomainCategory.EXPLICIT)
        )

    assoc_res = await async_client.post(
        f"/api/v1/blocklists/{bl_id}/domains",
        json={"domain_ids": [str(extra_domain.id)]},
    )
    assert assoc_res.status_code == 200
    assert assoc_res.json()["associated"] == 1

    # 4. Verify pagination on associated domains
    p1 = (await async_client.get(f"/api/v1/blocklists/{bl_id}/domains?offset=0&limit=2")).json()
    assert len(p1["items"]) == 2
    assert p1["total"] == 4
    assert p1["has_more"] is True

    p2 = (await async_client.get(f"/api/v1/blocklists/{bl_id}/domains?offset=2&limit=2")).json()
    assert len(p2["items"]) == 2
    assert p2["total"] == 4
    assert p2["has_more"] is False

    # 5. Publish initial version 1.0.0
    pub_res = await async_client.post(
        f"/api/v1/blocklists/{bl_id}/publish",
        json={"version": "1.0.0", "changelog": "Initial v1.0.0 release"},
    )
    assert pub_res.status_code == 201
    v1 = pub_res.json()
    assert v1["version"] == "1.0.0"
    assert v1["domain_count"] == 4

    # Verify deterministic SHA-256 calculation
    all_domains = sorted(
        [
            "tracker.adultsite.com",
            "cdn.adultvideos.xxx",
            "bad-ads.eroticnetwork.net",
            "extra-badsite.org",
        ]
    )
    expected_hash = hashlib.sha256("\n".join(all_domains).encode("utf-8")).hexdigest()
    assert v1["content_hash"] == expected_hash

    # 6. Check latest version endpoint
    latest_res = await async_client.get(f"/api/v1/blocklists/{bl_id}/versions/latest")
    assert latest_res.status_code == 200
    assert latest_res.json()["content_hash"] == expected_hash

    # 7. Disassociate a domain and publish patch update (auto-incrementing to 1.0.1)
    del_assoc_res = await async_client.request(
        "DELETE",
        f"/api/v1/blocklists/{bl_id}/domains",
        json={"domain_ids": [str(extra_domain.id)]},
    )
    assert del_assoc_res.status_code == 200
    assert del_assoc_res.json()["removed"] == 1

    pub_v2 = (
        await async_client.post(
            f"/api/v1/blocklists/{bl_id}/publish",
            json={"changelog": "Removed extra-badsite.org"},
        )
    ).json()
    assert pub_v2["version"] == "1.0.1"
    assert pub_v2["domain_count"] == 3
    assert pub_v2["content_hash"] != expected_hash


# ==============================================================================
# B3.4.2 — Test Invalid Requests & Boundary Violations
# ==============================================================================


@pytest.mark.anyio
async def test_milestone_b3_invalid_requests(async_client: AsyncClient, setup_database) -> None:
    """Verify that malformed requests return structured HTTP 422 errors."""
    # Invalid blocklist name lengths
    assert (await async_client.post("/api/v1/blocklists", json={"name": ""})).status_code == 422
    assert (await async_client.post("/api/v1/blocklists", json={"name": "x"})).status_code == 422
    assert (
        await async_client.post("/api/v1/blocklists", json={"name": "z" * 101})
    ).status_code == 422

    # Malformed UUID path parameters
    assert (await async_client.get("/api/v1/blocklists/invalid-uuid-format")).status_code == 422

    # Negative offset and out-of-range limits
    assert (await async_client.get("/api/v1/blocklists?offset=-1")).status_code == 422
    assert (await async_client.get("/api/v1/blocklists?limit=0")).status_code == 422
    assert (await async_client.get("/api/v1/blocklists?limit=1001")).status_code == 422


# ==============================================================================
# B3.4.3 — Test Empty Blocklists
# ==============================================================================


@pytest.mark.anyio
async def test_milestone_b3_empty_blocklist_handling(
    async_client: AsyncClient, setup_database
) -> None:
    """Verify publishing snapshots and retrieving domains on empty blocklists."""
    bl = (
        await async_client.post(
            "/api/v1/blocklists",
            json={"name": "Empty Test Blocklist"},
        )
    ).json()
    bl_id = bl["id"]

    # Retrieve domains for empty blocklist
    dom_res = await async_client.get(f"/api/v1/blocklists/{bl_id}/domains")
    assert dom_res.status_code == 200
    dom_data = dom_res.json()
    assert dom_data["items"] == []
    assert dom_data["total"] == 0
    assert dom_data["has_more"] is False

    # Publish version on empty blocklist
    pub_res = await async_client.post(
        f"/api/v1/blocklists/{bl_id}/publish",
        json={"version": "1.0.0", "changelog": "Empty initial snapshot"},
    )
    assert pub_res.status_code == 201
    pub_data = pub_res.json()
    assert pub_data["version"] == "1.0.0"
    assert pub_data["domain_count"] == 0

    # Content hash of empty domain list: SHA-256 of empty bytes
    empty_hash = hashlib.sha256(b"").hexdigest()
    assert pub_data["content_hash"] == empty_hash


# ==============================================================================
# B3.4.5 — Review OpenAPI Documentation
# ==============================================================================


def test_milestone_b3_openapi_schema_coverage(client: TestClient) -> None:
    """Verify that all blocklist endpoints and schemas are exposed in OpenAPI schema."""
    res = client.get("/openapi.json")
    assert res.status_code == 200
    schema = res.json()

    # Verify registered paths
    paths = schema["paths"]
    assert "/api/v1/blocklists" in paths
    assert "/api/v1/blocklists/{blocklist_id}" in paths
    assert "/api/v1/blocklists/{blocklist_id}/versions" in paths
    assert "/api/v1/blocklists/{blocklist_id}/versions/latest" in paths
    assert "/api/v1/blocklists/{blocklist_id}/publish" in paths
    assert "/api/v1/blocklists/{blocklist_id}/domains" in paths
    assert "/api/v1/blocklists/{blocklist_id}/ingest" in paths

    # Verify registered schemas in components
    components = schema["components"]["schemas"]
    assert "BlocklistResponse" in components
    assert "BlocklistCreate" in components
    assert "BlocklistUpdate" in components
    assert "BlocklistListResponse" in components
    assert "BlocklistVersionResponse" in components
    assert "BlocklistVersionListResponse" in components
    assert "BlocklistDomainsResponse" in components
    assert "FeedIngestRequest" in components
    assert "FeedIngestResponse" in components
