"""Integration tests for Blocklist REST API endpoints."""

import uuid

import pytest
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
# Blocklist CRUD Tests
# ==============================================================================


@pytest.mark.anyio
async def test_list_blocklists_empty_and_pagination(
    async_client: AsyncClient, setup_database
) -> None:
    """Verify listing blocklists on empty database and with pagination."""
    # 1. Empty list
    res = await async_client.get("/api/v1/blocklists")
    assert res.status_code == 200
    data = res.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["has_more"] is False

    # 2. Seed 3 blocklists
    for name in ["List Alpha", "List Beta", "List Gamma"]:
        create_res = await async_client.post(
            "/api/v1/blocklists",
            json={"name": name, "description": f"Description for {name}"},
        )
        assert create_res.status_code == 201

    # 3. Page 1 (limit 2) -> has_more is True
    res_p1 = await async_client.get("/api/v1/blocklists?offset=0&limit=2")
    assert res_p1.status_code == 200
    data_p1 = res_p1.json()
    assert len(data_p1["items"]) == 2
    assert data_p1["total"] == 3
    assert data_p1["has_more"] is True

    # 4. Page 2 (offset 2, limit 2) -> has_more is False
    res_p2 = await async_client.get("/api/v1/blocklists?offset=2&limit=2")
    assert res_p2.status_code == 200
    data_p2 = res_p2.json()
    assert len(data_p2["items"]) == 1
    assert data_p2["total"] == 3
    assert data_p2["has_more"] is False


@pytest.mark.anyio
async def test_create_blocklist_success_and_duplicate_conflict(
    async_client: AsyncClient, setup_database
) -> None:
    """Verify blocklist creation, default flag handling, and duplicate name conflict."""
    payload = {
        "name": "Standard Adult Filter",
        "description": "Filters general pornography domains",
        "is_default": True,
        "is_active": True,
    }
    res = await async_client.post("/api/v1/blocklists", json=payload)
    assert res.status_code == 201
    created = res.json()
    assert created["name"] == "Standard Adult Filter"
    assert created["is_default"] is True
    assert created["domain_count"] == 0
    assert created["current_version"] == "1.0.0"
    assert "id" in created

    # Duplicate name should return HTTP 409
    res_dup = await async_client.post("/api/v1/blocklists", json=payload)
    assert res_dup.status_code == 409
    err = res_dup.json()
    assert err["error"]["code"] == "DUPLICATE_ENTITY"

    # Invalid input (name too short) should return HTTP 422
    res_invalid = await async_client.post("/api/v1/blocklists", json={"name": "A"})
    assert res_invalid.status_code == 422


@pytest.mark.anyio
async def test_get_blocklist_by_id_and_not_found(async_client: AsyncClient, setup_database) -> None:
    """Verify retrieving a blocklist by UUID and handling non-existent resources."""
    create_res = await async_client.post(
        "/api/v1/blocklists",
        json={"name": "Specific Target List"},
    )
    assert create_res.status_code == 201
    bl_id = create_res.json()["id"]

    # Valid ID lookup
    get_res = await async_client.get(f"/api/v1/blocklists/{bl_id}")
    assert get_res.status_code == 200
    assert get_res.json()["name"] == "Specific Target List"

    # Random non-existent UUID -> HTTP 404
    missing_id = uuid.uuid4()
    missing_res = await async_client.get(f"/api/v1/blocklists/{missing_id}")
    assert missing_res.status_code == 404
    err = missing_res.json()
    assert err["error"]["code"] == "ENTITY_NOT_FOUND"


@pytest.mark.anyio
async def test_update_blocklist(async_client: AsyncClient, setup_database) -> None:
    """Verify updating blocklist attributes and detecting update name collisions."""
    # Create two lists
    b1 = (
        await async_client.post(
            "/api/v1/blocklists",
            json={"name": "List One"},
        )
    ).json()
    b2 = (
        await async_client.post(
            "/api/v1/blocklists",
            json={"name": "List Two"},
        )
    ).json()

    # Update b1 description and status
    update_res = await async_client.put(
        f"/api/v1/blocklists/{b1['id']}",
        json={"description": "Updated Description", "is_active": False},
    )
    assert update_res.status_code == 200
    updated = update_res.json()
    assert updated["description"] == "Updated Description"
    assert updated["is_active"] is False
    assert updated["name"] == "List One"

    # Attempt renaming b1 to b2's name -> HTTP 409
    conflict_res = await async_client.put(
        f"/api/v1/blocklists/{b1['id']}",
        json={"name": b2["name"]},
    )
    assert conflict_res.status_code == 409


@pytest.mark.anyio
async def test_delete_blocklist(async_client: AsyncClient, setup_database) -> None:
    """Verify deleting a blocklist returns HTTP 204."""
    create_res = await async_client.post(
        "/api/v1/blocklists",
        json={"name": "List To Delete"},
    )
    bl_id = create_res.json()["id"]

    # Delete
    del_res = await async_client.delete(f"/api/v1/blocklists/{bl_id}")
    assert del_res.status_code == 204

    # Confirm deletion
    get_res = await async_client.get(f"/api/v1/blocklists/{bl_id}")
    assert get_res.status_code == 404


# ==============================================================================
# Feed Ingestion & Domain Associations Tests
# ==============================================================================


@pytest.mark.anyio
async def test_feed_ingestion_endpoint(async_client: AsyncClient, setup_database) -> None:
    """Verify feed ingestion endpoint parses content and associates domains."""
    bl = (
        await async_client.post(
            "/api/v1/blocklists",
            json={"name": "Feed Ingestion Blocklist"},
        )
    ).json()

    feed_payload = {
        "content": """
        # Comments should be ignored
        0.0.0.0 adult-feed-1.com
        127.0.0.1 www.adult-feed-2.org
        ||adult-feed-3.net^
        127.0.0.1 localhost
        """,
        "source": "automated_test_feed",
        "category": "pornography",
    }

    ingest_res = await async_client.post(
        f"/api/v1/blocklists/{bl['id']}/ingest",
        json=feed_payload,
    )
    assert ingest_res.status_code == 200
    report = ingest_res.json()
    assert report["parsed_count"] == 3
    assert report["new_domains_created"] == 3
    assert report["domains_associated"] == 3
    assert report["total_blocklist_domains"] == 3

    # Check updated blocklist details
    bl_refreshed = (await async_client.get(f"/api/v1/blocklists/{bl['id']}")).json()
    assert bl_refreshed["domain_count"] == 3


@pytest.mark.anyio
async def test_get_blocklist_domains_paginated(async_client: AsyncClient, setup_database) -> None:
    """Verify querying domains associated with a blocklist."""
    bl = (
        await async_client.post(
            "/api/v1/blocklists",
            json={"name": "Domains Query Blocklist"},
        )
    ).json()

    feed_payload = {
        "content": "d1.com\nd2.com\nd3.com",
        "source": "test",
    }
    await async_client.post(f"/api/v1/blocklists/{bl['id']}/ingest", json=feed_payload)

    # Get page 1 (limit 2)
    res_p1 = await async_client.get(f"/api/v1/blocklists/{bl['id']}/domains?offset=0&limit=2")
    assert res_p1.status_code == 200
    data_p1 = res_p1.json()
    assert len(data_p1["items"]) == 2
    assert data_p1["total"] == 3
    assert data_p1["has_more"] is True

    # Get page 2 (offset 2, limit 2)
    res_p2 = await async_client.get(f"/api/v1/blocklists/{bl['id']}/domains?offset=2&limit=2")
    assert res_p2.status_code == 200
    data_p2 = res_p2.json()
    assert len(data_p2["items"]) == 1
    assert data_p2["total"] == 3
    assert data_p2["has_more"] is False


@pytest.mark.anyio
async def test_domain_associations_and_removals(async_client: AsyncClient, setup_database) -> None:
    """Verify manual domain association and removal endpoints."""
    bl = (
        await async_client.post(
            "/api/v1/blocklists",
            json={"name": "Association Test List"},
        )
    ).json()

    # Pre-create domains in database
    async with get_db_context() as session:
        dom_service = DomainService(session)
        d1 = await dom_service.create_domain(
            DomainCreate(domain="manual-assoc-1.com", category=DomainCategory.PORNOGRAPHY)
        )
        d2 = await dom_service.create_domain(
            DomainCreate(domain="manual-assoc-2.com", category=DomainCategory.PORNOGRAPHY)
        )

    # Associate d1 and d2
    assoc_res = await async_client.post(
        f"/api/v1/blocklists/{bl['id']}/domains",
        json={"domain_ids": [str(d1.id), str(d2.id)]},
    )
    assert assoc_res.status_code == 200
    assert assoc_res.json()["associated"] == 2

    # Remove d1
    rem_res = await async_client.request(
        "DELETE",
        f"/api/v1/blocklists/{bl['id']}/domains",
        json={"domain_ids": [str(d1.id)]},
    )
    assert rem_res.status_code == 200
    assert rem_res.json()["removed"] == 1

    # Remaining domain should only be d2
    domains_res = await async_client.get(f"/api/v1/blocklists/{bl['id']}/domains")
    assert domains_res.json()["total"] == 1
    assert domains_res.json()["items"][0]["domain"] == "manual-assoc-2.com"


# ==============================================================================
# Version Publication & Latest Version Tests
# ==============================================================================


@pytest.mark.anyio
async def test_version_publication_and_latest(async_client: AsyncClient, setup_database) -> None:
    """Verify publishing version releases, auto-incrementing, and retrieving /latest."""
    bl = (
        await async_client.post(
            "/api/v1/blocklists",
            json={"name": "Versioning Release List"},
        )
    ).json()

    # Before publishing, /versions/latest should return 404
    latest_none = await async_client.get(f"/api/v1/blocklists/{bl['id']}/versions/latest")
    assert latest_none.status_code == 404

    # Ingest domains
    await async_client.post(
        f"/api/v1/blocklists/{bl['id']}/ingest",
        json={"content": "alpha.xxx\nbeta.xxx"},
    )

    # Publish version 1.0.0
    v1_res = await async_client.post(
        f"/api/v1/blocklists/{bl['id']}/publish",
        json={"version": "1.0.0", "changelog": "Initial release"},
    )
    assert v1_res.status_code == 201
    v1 = v1_res.json()
    assert v1["version"] == "1.0.0"
    assert v1["domain_count"] == 2
    assert len(v1["content_hash"]) == 64

    # Latest should now return 1.0.0
    latest_v1 = await async_client.get(f"/api/v1/blocklists/{bl['id']}/versions/latest")
    assert latest_v1.status_code == 200
    assert latest_v1.json()["version"] == "1.0.0"

    # Publish without version -> auto-increments to 1.0.1
    v2_res = await async_client.post(
        f"/api/v1/blocklists/{bl['id']}/publish",
        json={"changelog": "Patch update"},
    )
    assert v2_res.status_code == 201
    v2 = v2_res.json()
    assert v2["version"] == "1.0.1"

    # List versions
    versions_res = await async_client.get(f"/api/v1/blocklists/{bl['id']}/versions")
    assert versions_res.status_code == 200
    versions_data = versions_res.json()
    assert versions_data["total"] == 2
    assert len(versions_data["items"]) == 2
