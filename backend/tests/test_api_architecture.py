"""Unit and architectural tests for API conventions, common schemas, and envelopes."""

import uuid

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.schemas.blocklist import (
    BlocklistAssociateDomainsRequest,
    BlocklistDomainsResponse,
    BlocklistListResponse,
    BlocklistPublishRequest,
    BlocklistRemoveDomainsRequest,
    BlocklistVersionListResponse,
)
from app.schemas.common import (
    ErrorDetail,
    ErrorResponse,
    PaginatedResponse,
    PaginationParams,
)

# ==============================================================================
# PaginationParams Tests
# ==============================================================================


def test_pagination_params_defaults() -> None:
    """Verify default values for PaginationParams."""
    params = PaginationParams()
    assert params.offset == 0
    assert params.limit == 50


def test_pagination_params_custom_bounds() -> None:
    """Verify that custom within-bound pagination values are accepted."""
    params = PaginationParams(offset=100, limit=250)
    assert params.offset == 100
    assert params.limit == 250


def test_pagination_params_rejection_of_invalid_bounds() -> None:
    """Verify that negative offsets and out-of-bound limits are rejected."""
    # Negative offset
    with pytest.raises(ValidationError):
        PaginationParams(offset=-1)

    # Zero limit
    with pytest.raises(ValidationError):
        PaginationParams(limit=0)

    # Limit exceeding 1000
    with pytest.raises(ValidationError):
        PaginationParams(limit=1001)

    # Extra unrecognized parameters forbidden
    with pytest.raises(ValidationError):
        PaginationParams(offset=0, limit=50, extra_param="unsupported")  # type: ignore[call-arg]


# ==============================================================================
# PaginatedResponse Generic Envelope Tests
# ==============================================================================


def test_paginated_response_has_more_computation() -> None:
    """Verify PaginatedResponse.create calculates has_more accurately."""
    # Page 1 of 10 items (3 items on page) -> has_more is True
    page1 = PaginatedResponse.create(items=["a", "b", "c"], total=10, offset=0, limit=3)
    assert page1.items == ["a", "b", "c"]
    assert page1.total == 10
    assert page1.offset == 0
    assert page1.limit == 3
    assert page1.has_more is True

    # Page 2 (offset 3, 3 items) -> has_more is True
    page2 = PaginatedResponse.create(items=["d", "e", "f"], total=10, offset=3, limit=3)
    assert page2.has_more is True

    # Final page (offset 9, 1 item) -> has_more is False
    page4 = PaginatedResponse.create(items=["j"], total=10, offset=9, limit=3)
    assert page4.has_more is False

    # Empty collection -> has_more is False
    empty_page = PaginatedResponse.create(items=[], total=0, offset=0, limit=50)
    assert empty_page.has_more is False


def test_paginated_response_serialization() -> None:
    """Verify JSON dictionary serialization format of PaginatedResponse."""
    envelope = PaginatedResponse(
        items=[{"id": 1, "name": "Item 1"}],
        total=1,
        offset=0,
        limit=50,
        has_more=False,
    )
    dumped = envelope.model_dump()
    assert dumped == {
        "items": [{"id": 1, "name": "Item 1"}],
        "total": 1,
        "offset": 0,
        "limit": 50,
        "has_more": False,
    }


# ==============================================================================
# ErrorResponse Envelope Tests
# ==============================================================================


def test_error_response_structure() -> None:
    """Verify standard error response model serialization."""
    err = ErrorResponse(
        error=ErrorDetail(
            code="ENTITY_NOT_FOUND",
            message="Blocklist was not found",
            details={"entity": "Blocklist", "id": "123"},
        )
    )
    data = err.model_dump()
    assert "error" in data
    assert data["error"]["code"] == "ENTITY_NOT_FOUND"
    assert data["error"]["message"] == "Blocklist was not found"
    assert data["error"]["details"] == {"entity": "Blocklist", "id": "123"}


def test_error_detail_without_optional_details() -> None:
    """Verify ErrorDetail with None details."""
    err = ErrorResponse(
        error=ErrorDetail(
            code="UNAUTHORIZED",
            message="Access denied",
        )
    )
    data = err.model_dump()
    assert data["error"]["details"] is None


# ==============================================================================
# Extended Blocklist REST Schemas Tests
# ==============================================================================


def test_blocklist_publish_request_schema() -> None:
    """Verify BlocklistPublishRequest handles optional version and changelog."""
    # Blank request
    req1 = BlocklistPublishRequest()
    assert req1.version is None
    assert req1.changelog is None

    # Custom version and changelog
    req2 = BlocklistPublishRequest(version="2.0.0", changelog="Major rule updates")
    assert req2.version == "2.0.0"
    assert req2.changelog == "Major rule updates"


def test_blocklist_domain_association_requests() -> None:
    """Verify domain association and removal request schemas."""
    u1 = uuid.uuid4()
    u2 = uuid.uuid4()

    assoc = BlocklistAssociateDomainsRequest(domain_ids=[u1, u2])
    assert len(assoc.domain_ids) == 2
    assert assoc.domain_ids[0] == u1

    rem = BlocklistRemoveDomainsRequest(domain_ids=[u1])
    assert len(rem.domain_ids) == 1

    # Empty domain list should fail validation
    with pytest.raises(ValidationError):
        BlocklistAssociateDomainsRequest(domain_ids=[])


def test_typed_paginated_blocklist_responses() -> None:
    """Verify that typed PaginatedResponse subclasses correctly inherit and serialize."""
    assert issubclass(BlocklistListResponse, PaginatedResponse)
    assert issubclass(BlocklistVersionListResponse, PaginatedResponse)
    assert issubclass(BlocklistDomainsResponse, PaginatedResponse)

    list_resp = BlocklistListResponse(
        items=[],
        total=0,
        offset=0,
        limit=50,
        has_more=False,
    )
    assert list_resp.items == []
    assert list_resp.total == 0


# ==============================================================================
# OpenAPI Schema & API Documentation Tests
# ==============================================================================


def test_openapi_schema_includes_api_v1_health(client: TestClient) -> None:
    """Verify that OpenAPI schema properly reflects API v1 routes and app version."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()

    assert schema["info"]["title"] == "ClearGuard API"
    assert "/api/v1/health" in schema["paths"]
    assert "paths" in schema
    assert "components" in schema
