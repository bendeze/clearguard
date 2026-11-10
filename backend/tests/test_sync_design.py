"""Unit and architectural tests for blocklist synchronization design and version comparison."""

import hashlib
import uuid

import pytest
from pydantic import ValidationError

from app.schemas.sync import (
    SyncBatchCheckRequest,
    SyncBatchCheckResponse,
    SyncCheckItem,
    SyncCheckResponse,
    SyncStatus,
)
from app.services.version_comparator import (
    compare_versions,
    compute_domain_list_hash,
    determine_sync_status,
    parse_semver,
    verify_content_integrity,
)

# ==============================================================================
# Semver Parsing & Comparison Tests
# ==============================================================================


def test_parse_semver_scenarios() -> None:
    """Verify semantic version string parsing across standard and edge-case inputs."""
    assert parse_semver("1.2.3") == (1, 2, 3)
    assert parse_semver("v2.4.0") == (2, 4, 0)
    assert parse_semver("V3.0.1") == (3, 0, 1)
    assert parse_semver("1.0") == (1, 0, 0)
    assert parse_semver("5") == (5, 0, 0)
    assert parse_semver("1.2.3-beta.1") == (1, 2, 3)
    assert parse_semver("2.0.0+build.42") == (2, 0, 0)
    assert parse_semver(None) == (0, 0, 0)
    assert parse_semver("") == (0, 0, 0)
    assert parse_semver("invalid") == (0, 0, 0)


def test_compare_versions_ordering() -> None:
    """Verify comparison logic returns -1, 0, or 1 correctly."""
    # Client older than latest
    assert compare_versions("1.0.0", "1.0.1") == -1
    assert compare_versions("1.0.0", "1.1.0") == -1
    assert compare_versions("1.9.9", "2.0.0") == -1
    assert compare_versions(None, "1.0.0") == -1
    assert compare_versions("", "1.0.0") == -1

    # Equal
    assert compare_versions("1.0.0", "1.0.0") == 0
    assert compare_versions("v1.2.3", "1.2.3") == 0
    assert compare_versions("  2.0.1  ", "2.0.1") == 0

    # Client newer than latest
    assert compare_versions("1.0.1", "1.0.0") == 1
    assert compare_versions("2.0.0", "1.9.9") == 1
    assert compare_versions("1.2.0", "1.1.9") == 1


# ==============================================================================
# Cryptographic Hash & Integrity Tests
# ==============================================================================


def test_compute_domain_list_hash_invariance() -> None:
    """Verify deterministic hash calculation: sorting, casing, and whitespace normalization."""
    # Empty domain list matches known empty SHA-256
    empty_hash = hashlib.sha256(b"").hexdigest()
    assert compute_domain_list_hash([]) == empty_hash

    # Sorting invariance: order of inputs does not affect output hash
    domains_a = ["zebra-badsite.com", "alpha-badsite.org", "mango-badsite.net"]
    domains_b = ["alpha-badsite.org", "mango-badsite.net", "zebra-badsite.com"]
    assert compute_domain_list_hash(domains_a) == compute_domain_list_hash(domains_b)

    # Whitespace and case-folding invariance
    domains_dirty = ["  ZEBRA-badsite.com  ", "alpha-badsite.org\n", "MANGO-BADSITE.NET"]
    assert compute_domain_list_hash(domains_dirty) == compute_domain_list_hash(domains_a)


def test_verify_content_integrity() -> None:
    """Verify constant-time integrity validation against expected SHA-256 digests."""
    domains = ["adultsite.com", "pornsite.xxx", "explicit.net"]
    expected_hash = compute_domain_list_hash(domains)

    # Correct hash matches
    assert verify_content_integrity(domains, expected_hash) is True
    assert verify_content_integrity(domains, expected_hash.upper()) is True

    # Modified content fails
    tampered_domains = domains + ["injected-site.com"]
    assert verify_content_integrity(tampered_domains, expected_hash) is False

    # Empty expected hash fails
    assert verify_content_integrity(domains, "") is False


# ==============================================================================
# Sync State Evaluator Tests
# ==============================================================================


def test_determine_sync_status_scenarios() -> None:
    """Verify sync state evaluation across up-to-date, update-available, and outdated conditions."""
    h_v1 = "1111111111111111111111111111111111111111111111111111111111111111"
    h_v2 = "2222222222222222222222222222222222222222222222222222222222222222"

    # 1. Hashes match -> UP_TO_DATE (update not required)
    status, req = determine_sync_status(
        client_version="1.0.0", client_hash=h_v2, latest_version="1.0.0", latest_hash=h_v2
    )
    assert status == SyncStatus.UP_TO_DATE
    assert req is False

    # 2. Hashes match even if version string differs -> UP_TO_DATE
    status, req = determine_sync_status(
        client_version="0.9.0", client_hash=h_v2, latest_version="1.0.0", latest_hash=h_v2
    )
    assert status == SyncStatus.UP_TO_DATE
    assert req is False

    # 3. Client version is older and hashes differ -> UPDATE_AVAILABLE
    status, req = determine_sync_status(
        client_version="1.0.0", client_hash=h_v1, latest_version="1.0.1", latest_hash=h_v2
    )
    assert status == SyncStatus.UPDATE_AVAILABLE
    assert req is True

    # 4. Same version string but divergent hash -> OUTDATED (corrupted/dirty local state)
    status, req = determine_sync_status(
        client_version="1.0.0", client_hash=h_v1, latest_version="1.0.0", latest_hash=h_v2
    )
    assert status == SyncStatus.OUTDATED
    assert req is True

    # 5. Missing client version or hash -> OUTDATED
    status, req = determine_sync_status(
        client_version=None, client_hash=None, latest_version="1.0.0", latest_hash=h_v2
    )
    assert status == SyncStatus.OUTDATED
    assert req is True


# ==============================================================================
# Pydantic Sync Schemas Validation Tests
# ==============================================================================


def test_sync_check_item_schema_validation() -> None:
    """Verify validation boundaries on SyncCheckItem."""
    b_id = uuid.uuid4()
    valid_hash = "a" * 64

    # Valid schema
    item = SyncCheckItem(blocklist_id=b_id, client_version="1.0.0", client_content_hash=valid_hash)
    assert item.blocklist_id == b_id
    assert item.client_version == "1.0.0"

    # Hash must be exactly 64 characters if provided
    with pytest.raises(ValidationError):
        SyncCheckItem(blocklist_id=b_id, client_content_hash="too_short")

    # Extra fields forbidden
    with pytest.raises(ValidationError):
        SyncCheckItem(blocklist_id=b_id, unexpected_field="bad")  # type: ignore[call-arg]


def test_sync_batch_check_schemas() -> None:
    """Verify batch request and response schema models."""
    b1 = uuid.uuid4()
    b2 = uuid.uuid4()

    # Valid batch request
    req = SyncBatchCheckRequest(
        items=[
            SyncCheckItem(blocklist_id=b1, client_version="1.0.0"),
            SyncCheckItem(blocklist_id=b2, client_version="2.0.0"),
        ]
    )
    assert len(req.items) == 2

    # Empty batch rejected (min_length=1)
    with pytest.raises(ValidationError):
        SyncBatchCheckRequest(items=[])

    # Valid batch response
    resp = SyncBatchCheckResponse(
        items=[
            SyncCheckResponse(
                blocklist_id=b1,
                status=SyncStatus.UPDATE_AVAILABLE,
                update_required=True,
                latest_version="1.0.1",
                latest_content_hash="b" * 64,
                domain_count=1500,
                changelog="Patch 1",
                download_url=f"/api/v1/blocklists/{b1}/domains",
            )
        ]
    )
    assert len(resp.items) == 1
    assert resp.items[0].status == SyncStatus.UPDATE_AVAILABLE
    assert resp.items[0].domain_count == 1500
