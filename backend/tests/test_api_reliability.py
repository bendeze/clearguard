"""Tests for API reliability: status codes, validations, missing resources, and performance."""

import time
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import engine
from app.core.exceptions import DatabaseError
from app.main import app
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
# 1. Path Parameter Validation (UUID Formats)
# ==============================================================================


@pytest.mark.anyio
async def test_invalid_path_parameter_format(async_client: AsyncClient, setup_database) -> None:
    """Verify that malformed UUID path parameters return HTTP 422 with REQUEST_VALIDATION_ERROR."""
    invalid_ids = ["not-a-uuid", "12345", "xyz-789-abc", "00000000-0000-0000-0000-00000000000z"]

    for bad_id in invalid_ids:
        # GET blocklist
        res_get = await async_client.get(f"/api/v1/blocklists/{bad_id}")
        assert res_get.status_code == 422
        assert res_get.json()["error"]["code"] == "REQUEST_VALIDATION_ERROR"

        # PUT blocklist
        res_put = await async_client.put(
            f"/api/v1/blocklists/{bad_id}", json={"name": "Valid Name"}
        )
        assert res_put.status_code == 422
        assert res_put.json()["error"]["code"] == "REQUEST_VALIDATION_ERROR"

        # DELETE blocklist
        res_del = await async_client.delete(f"/api/v1/blocklists/{bad_id}")
        assert res_del.status_code == 422

        # Sub-resources
        assert (await async_client.get(f"/api/v1/blocklists/{bad_id}/domains")).status_code == 422
        assert (await async_client.get(f"/api/v1/blocklists/{bad_id}/versions")).status_code == 422
        assert (
            await async_client.get(f"/api/v1/blocklists/{bad_id}/versions/latest")
        ).status_code == 422
        assert (await async_client.post(f"/api/v1/blocklists/{bad_id}/publish")).status_code == 422
        assert (
            await async_client.post(
                f"/api/v1/blocklists/{bad_id}/ingest", json={"content": "a.com"}
            )
        ).status_code == 422


# ==============================================================================
# 2. Query Parameter Boundaries
# ==============================================================================


@pytest.mark.anyio
async def test_invalid_query_parameters(async_client: AsyncClient, setup_database) -> None:
    """Verify that out-of-bounds or invalid-type query parameters return HTTP 422."""
    # Negative offset
    r1 = await async_client.get("/api/v1/blocklists?offset=-5")
    assert r1.status_code == 422
    assert r1.json()["error"]["code"] == "REQUEST_VALIDATION_ERROR"

    # Zero limit
    r2 = await async_client.get("/api/v1/blocklists?limit=0")
    assert r2.status_code == 422

    # Limit exceeding 1000
    r3 = await async_client.get("/api/v1/blocklists?limit=1001")
    assert r3.status_code == 422

    # String where int is expected
    r4 = await async_client.get("/api/v1/blocklists?offset=abc")
    assert r4.status_code == 422

    r5 = await async_client.get("/api/v1/blocklists?limit=xyz")
    assert r5.status_code == 422


# ==============================================================================
# 3. Missing Resource Handling Across All Endpoints
# ==============================================================================


@pytest.mark.anyio
async def test_missing_resource_handling_across_all_routes(
    async_client: AsyncClient, setup_database
) -> None:
    """Verify that non-existent blocklist UUIDs return HTTP 404 with ENTITY_NOT_FOUND."""
    random_id = uuid.uuid4()
    dummy_dom_id = uuid.uuid4()

    routes = [
        ("GET", f"/api/v1/blocklists/{random_id}", None),
        ("PUT", f"/api/v1/blocklists/{random_id}", {"name": "Does Not Matter"}),
        ("DELETE", f"/api/v1/blocklists/{random_id}", None),
        ("GET", f"/api/v1/blocklists/{random_id}/domains", None),
        (
            "POST",
            f"/api/v1/blocklists/{random_id}/domains",
            {"domain_ids": [str(dummy_dom_id)]},
        ),
        (
            "DELETE",
            f"/api/v1/blocklists/{random_id}/domains",
            {"domain_ids": [str(dummy_dom_id)]},
        ),
        ("GET", f"/api/v1/blocklists/{random_id}/versions", None),
        ("GET", f"/api/v1/blocklists/{random_id}/versions/latest", None),
        ("POST", f"/api/v1/blocklists/{random_id}/publish", {}),
        ("POST", f"/api/v1/blocklists/{random_id}/ingest", {"content": "domain.xxx"}),
    ]

    for method, path, payload in routes:
        if method == "GET":
            res = await async_client.get(path)
        elif method == "POST":
            res = await async_client.post(path, json=payload)
        elif method == "PUT":
            res = await async_client.put(path, json=payload)
        elif method == "DELETE":
            res = await async_client.request(method, path, json=payload)

        assert res.status_code == 404, f"Route {method} {path} expected 404, got {res.status_code}"
        data = res.json()
        assert data["error"]["code"] == "ENTITY_NOT_FOUND"
        assert "not found" in data["error"]["message"].lower()


# ==============================================================================
# 4. Request Payload Boundary Validation
# ==============================================================================


@pytest.mark.anyio
async def test_request_payload_boundary_validation(
    async_client: AsyncClient, setup_database
) -> None:
    """Verify Pydantic schema validation rejects malformed payloads with HTTP 422."""
    # Empty body for creation
    r1 = await async_client.post("/api/v1/blocklists", json={})
    assert r1.status_code == 422

    # Name too short (< 2 chars)
    r2 = await async_client.post("/api/v1/blocklists", json={"name": "A"})
    assert r2.status_code == 422

    # Name too long (> 100 chars)
    r3 = await async_client.post("/api/v1/blocklists", json={"name": "A" * 101})
    assert r3.status_code == 422

    # Description too long (> 500 chars)
    r4 = await async_client.post(
        "/api/v1/blocklists", json={"name": "Valid Name", "description": "D" * 501}
    )
    assert r4.status_code == 422

    # Create a valid blocklist for sub-resource payload tests
    bl = (await async_client.post("/api/v1/blocklists", json={"name": "Boundary Test List"})).json()

    # Empty domain list for association
    r5 = await async_client.post(
        f"/api/v1/blocklists/{bl['id']}/domains",
        json={"domain_ids": []},
    )
    assert r5.status_code == 422

    # Invalid UUID in domain list
    r6 = await async_client.post(
        f"/api/v1/blocklists/{bl['id']}/domains",
        json={"domain_ids": ["not-a-valid-uuid"]},
    )
    assert r6.status_code == 422

    # Empty feed content for ingestion
    r7 = await async_client.post(
        f"/api/v1/blocklists/{bl['id']}/ingest",
        json={"content": ""},
    )
    assert r7.status_code == 422

    # Invalid category for feed ingestion
    r8 = await async_client.post(
        f"/api/v1/blocklists/{bl['id']}/ingest",
        json={"content": "valid-site.com", "category": "non_existent_category"},
    )
    assert r8.status_code == 422


# ==============================================================================
# 5. Database & Unhandled Error Sanitization
# ==============================================================================


@pytest.mark.anyio
async def test_database_error_sanitization(
    async_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify that DatabaseError returns HTTP 500 with sanitized code and message."""
    from app.services.blocklist_service import BlocklistService

    async def _failing_list(*args, **kwargs):
        raise DatabaseError("Database operation failed due to internal query execution error.")

    monkeypatch.setattr(BlocklistService, "list_blocklists", _failing_list)

    res = await async_client.get("/api/v1/blocklists")
    assert res.status_code == 500
    data = res.json()
    assert data["error"]["code"] == "DATABASE_ERROR"
    assert (
        data["error"]["message"]
        == "Database operation failed due to internal query execution error."
    )
    assert "details" in data["error"]


@pytest.mark.anyio
async def test_unhandled_server_exception_sanitization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify unhandled exceptions return sanitized HTTP 500 without leaking sensitive messages."""
    from app.services.blocklist_service import BlocklistService

    async def _failing_list(*args, **kwargs):
        raise RuntimeError(
            "Sensitive DB Connection String: postgresql://admin:secret@10.0.0.1:5432/db"
        )

    monkeypatch.setattr(BlocklistService, "list_blocklists", _failing_list)

    # Use transport without re-raising server exceptions to verify client response
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/blocklists")
        assert res.status_code == 500
        data = res.json()
        assert data["error"]["code"] == "INTERNAL_SERVER_ERROR"
        assert data["error"]["message"] == "An unexpected internal server error occurred."
        assert "secret" not in str(data)
        assert "postgresql://" not in str(data)


# ==============================================================================
# 6. API Response Latency Benchmark
# ==============================================================================


@pytest.mark.anyio
async def test_api_response_latency_benchmark(async_client: AsyncClient, setup_database) -> None:
    """Benchmark API response time to ensure average latency is well under 100ms."""
    # Seed 5 blocklists
    for i in range(5):
        await async_client.post(
            "/api/v1/blocklists",
            json={"name": f"Benchmark List {i}"},
        )

    # Execute 30 sequential GET requests
    start_time = time.perf_counter()
    iterations = 30
    for _ in range(iterations):
        res = await async_client.get("/api/v1/blocklists")
        assert res.status_code == 200

    elapsed = time.perf_counter() - start_time
    avg_latency_ms = (elapsed / iterations) * 1000

    # Ensure average latency is under 50ms per request on local engine
    assert avg_latency_ms < 50.0, f"Average latency too high: {avg_latency_ms:.2f}ms"
