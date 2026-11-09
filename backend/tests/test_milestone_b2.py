"""Milestone B2 integration tests covering domain normalization, validation,

duplicate handling, database persistence, and blocklist versioning.
"""

import hashlib

import pytest

from app.core.database import engine, get_db_context
from app.core.exceptions import InvalidDomainError
from app.models.base import Base
from app.models.enums import DomainCategory, DomainStatus
from app.repositories.blocklist_repository import BlocklistRepository
from app.repositories.domain_repository import DomainRepository
from app.schemas.blocklist import BlocklistCreate, FeedIngestRequest
from app.schemas.domain import BulkImportRequest, DomainCreate
from app.services.blocklist_service import BlocklistService
from app.services.domain_service import DomainService
from app.services.domain_validator import normalize_domain, validate_domain
from app.services.feed_parser import parse_blocklist_feed


@pytest.fixture
async def setup_database():
    """Ensure clean database schema before and after each test."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# ==============================================================================
# B2.4.1 — Test Domain Normalization
# ==============================================================================


def test_milestone_b2_domain_normalization_rules() -> None:
    """Verify domain normalization across schemes, ports, paths, subdomains, and IDN."""
    # Scheme, path, port, query, and fragment removal
    assert (
        normalize_domain("https://WWW.Adult-Portal.com:8443/gallery/view.php?id=123#top")
        == "adult-portal.com"
    )
    assert normalize_domain("http://explicit-content.xxx/video/12345") == "explicit-content.xxx"
    assert normalize_domain("ftp://files.xxx-vault.org:21/") == "files.xxx-vault.org"

    # www. stripping preserves subdomains
    assert normalize_domain("www.adultsite.com") == "adultsite.com"
    assert normalize_domain("cdn.media.adultsite.com") == "cdn.media.adultsite.com"
    assert normalize_domain("www.cdn.adultsite.com") == "cdn.adultsite.com"

    # Whitespace and trailing dots
    assert normalize_domain("  \t  raw-domain.net.   \n ") == "raw-domain.net"

    # Internationalized Domain Names (IDN / Punycode)
    assert normalize_domain("münchen-erotik.de") == "xn--mnchen-erotik-wob.de"
    assert normalize_domain("https://www.bücher-adult.com/") == "xn--bcher-adult-thb.com"


# ==============================================================================
# B2.4.2 — Test Domain Validation
# ==============================================================================


def test_milestone_b2_domain_validation_rfc_rules() -> None:
    """Verify RFC 1035 / RFC 1123 validation and rejection criteria."""
    # Valid domains do not raise an exception
    valid_cases = [
        "adult-portal.com",
        "sub.domain.co.uk",
        "deep.nested.sub.domain.adult",
        "xn--mnchen-3ya.com",
    ]
    for d in valid_cases:
        validate_domain(d)

    # IP address rejection (IPv4 and IPv6)
    invalid_ips = ["127.0.0.1", "192.168.1.1", "10.0.0.1", "2001:db8::1", "::1"]
    for ip in invalid_ips:
        with pytest.raises(InvalidDomainError) as exc_info:
            validate_domain(ip)
        assert "IP addresses are not permitted" in str(exc_info.value)

    # Rejection of single-label, numeric TLD, invalid chars, oversized
    with pytest.raises(InvalidDomainError):
        validate_domain("localhost")

    with pytest.raises(InvalidDomainError):
        validate_domain("domain.123")

    with pytest.raises(InvalidDomainError):
        validate_domain("-invalid-start.com")

    with pytest.raises(InvalidDomainError):
        validate_domain("invalid-end-.com")

    with pytest.raises(InvalidDomainError):
        validate_domain("invalid..consecutive.com")

    with pytest.raises(InvalidDomainError):
        validate_domain("a" * 64 + ".com")


# ==============================================================================
# B2.4.3 — Test Duplicate Handling & Bulk Import Conflict Resolution
# ==============================================================================


@pytest.mark.anyio
async def test_milestone_b2_duplicate_handling_and_bulk_import(setup_database) -> None:
    """Verify bulk import handles novel domains, duplicates, and invalid inputs."""
    async with get_db_context() as session:
        domain_service = DomainService(session)

        # Pre-seed existing domains in database
        await domain_service.create_domain(
            DomainCreate(domain="pre-existing-one.com", category=DomainCategory.PORNOGRAPHY)
        )
        await domain_service.create_domain(
            DomainCreate(domain="pre-existing-two.com", category=DomainCategory.EXPLICIT)
        )

        # Build blended bulk request:
        # 3 new unique domains
        # 2 duplicates within input
        # 2 duplicates matching database
        # 2 invalid domains (IP and malformed)
        blended_candidates = [
            # New unique
            "https://www.fresh-adult-1.com/path",
            "fresh-adult-2.com",
            "sub.fresh-adult-3.org",
            # Duplicates of above within input
            "fresh-adult-1.com",
            "www.fresh-adult-2.com",
            # Duplicates matching pre-existing database domains
            "PRE-EXISTING-ONE.com",
            "https://www.pre-existing-two.com",
            # Invalid items
            "192.168.1.100",
            "invalid..bad--domain",
        ]

        result = await domain_service.bulk_import(
            BulkImportRequest(
                domains=blended_candidates,
                category=DomainCategory.PORNOGRAPHY,
                source="test_milestone_b2",
            )
        )

        assert result.total_submitted == 9
        assert result.inserted == 3
        assert result.skipped_duplicates == 4  # 2 within input + 2 matching database
        assert result.invalid_count == 2
        assert len(result.errors) == 2

        # Verify all 5 valid domains are in database
        repo = DomainRepository(session)
        assert await repo.exists_by_domain("fresh-adult-1.com") is True
        assert await repo.exists_by_domain("fresh-adult-2.com") is True
        assert await repo.exists_by_domain("sub.fresh-adult-3.org") is True
        assert await repo.exists_by_domain("pre-existing-one.com") is True
        assert await repo.exists_by_domain("pre-existing-two.com") is True


# ==============================================================================
# B2.4.4 — Test Database Persistence & Model Relationships
# ==============================================================================


@pytest.mark.anyio
async def test_milestone_b2_database_persistence_and_relationships(setup_database) -> None:
    """Verify database persistence of Domain, Blocklist, BlocklistDomain join, and counts."""
    async with get_db_context() as session:
        domain_service = DomainService(session)
        blocklist_service = BlocklistService(session)

        # Create domains
        d1 = await domain_service.create_domain(
            DomainCreate(
                domain="persisted-alpha.com",
                category=DomainCategory.PORNOGRAPHY,
                status=DomainStatus.ACTIVE,
                confidence_score=0.95,
                source="milestone_test",
                notes="High confidence adult domain",
            )
        )
        d2 = await domain_service.create_domain(
            DomainCreate(
                domain="persisted-beta.com",
                category=DomainCategory.EXPLICIT,
                status=DomainStatus.ACTIVE,
                confidence_score=0.88,
            )
        )

        # Create blocklist
        bl = await blocklist_service.create_blocklist(
            BlocklistCreate(
                name="Milestone B2 Primary Blocklist",
                description="Comprehensive adult filter list",
                is_default=True,
            )
        )
        assert bl.domain_count == 0

        # Associate domains
        added = await blocklist_service.associate_domains(bl.id, [d1.id, d2.id])
        assert added == 2

        # Verify domain count refreshed
        refreshed_bl = await blocklist_service.get_by_id(bl.id)
        assert refreshed_bl.domain_count == 2

        # Retrieve blocklist domains
        members = await blocklist_service.get_blocklist_domains(bl.id)
        assert len(members) == 2
        member_domains = {m.domain for m in members}
        assert member_domains == {"persisted-alpha.com", "persisted-beta.com"}


# ==============================================================================
# B2.4.5 — Test Blocklist Versioning & SHA-256 Integrity Verification
# ==============================================================================


@pytest.mark.anyio
async def test_milestone_b2_blocklist_versioning_and_sha256(setup_database) -> None:
    """Verify version publication, deterministic SHA-256 calculation, and semver."""
    async with get_db_context() as session:
        domain_service = DomainService(session)
        blocklist_service = BlocklistService(session)

        # Create blocklist
        bl = await blocklist_service.create_blocklist(
            BlocklistCreate(name="Versioned Adult Feed", description="Feed with automated releases")
        )

        # Ingest feed with 3 domains
        feed_content = """
        0.0.0.0 zebra-porn.com
        0.0.0.0 alpha-adult.org
        0.0.0.0 mango-xxx.net
        """
        await blocklist_service.ingest_feed(
            bl.id,
            FeedIngestRequest(
                content=feed_content,
                source="milestone_feed",
                category=DomainCategory.PORNOGRAPHY,
            ),
        )

        # Publish initial version 1.0.0
        v1 = await blocklist_service.publish_version(
            bl.id, version="1.0.0", changelog="Initial release"
        )
        assert v1.version == "1.0.0"
        assert v1.domain_count == 3

        # Verify deterministic SHA-256: sorted newline-delimited domain names
        expected_names = ["alpha-adult.org", "mango-xxx.net", "zebra-porn.com"]
        expected_hash = hashlib.sha256("\n".join(expected_names).encode("utf-8")).hexdigest()
        assert v1.content_hash == expected_hash

        # Add another domain and publish next version (auto-increment patch)
        extra = await domain_service.create_domain(
            DomainCreate(domain="beta-explicit.com", category=DomainCategory.EXPLICIT)
        )
        await blocklist_service.associate_domains(bl.id, [extra.id])

        v2 = await blocklist_service.publish_version(bl.id, changelog="Added beta-explicit.com")
        assert v2.version == "1.0.1"
        assert v2.domain_count == 4

        # Version history checks
        repo = BlocklistRepository(session)
        versions = await repo.list_versions(bl.id)
        assert len(versions) == 2
        latest = await repo.get_latest_version(bl.id)
        assert latest is not None
        assert latest.version == "1.0.1"
        assert latest.content_hash != v1.content_hash


# ==============================================================================
# B2.4.6 — Test Invalid Input Handling
# ==============================================================================


@pytest.mark.anyio
async def test_milestone_b2_invalid_input_handling(setup_database) -> None:
    """Verify edge cases for feed parser and domain creation exceptions."""
    # Feed parser with empty content, comment-only content, and loopback
    assert parse_blocklist_feed("") == []
    assert parse_blocklist_feed("   \n\n\t  ") == []
    assert parse_blocklist_feed("# Just a header\n! Another comment\n") == []

    # Local loopbacks are excluded
    loopback_content = """
    127.0.0.1 localhost
    ::1 localhost
    0.0.0.0 0.0.0.0
    127.0.0.1 127.0.0.1
    """
    assert parse_blocklist_feed(loopback_content) == []

    # Domain creation with invalid domain formats raises InvalidDomainError
    async with get_db_context() as session:
        service = DomainService(session)

        with pytest.raises(InvalidDomainError) as exc_info:
            await service.create_domain(DomainCreate(domain="127.0.0.1"))
        assert exc_info.value.code == "INVALID_DOMAIN"

        with pytest.raises(InvalidDomainError):
            await service.create_domain(DomainCreate(domain="bad..format.com"))

        with pytest.raises(InvalidDomainError):
            await service.create_domain(DomainCreate(domain="singlelabel"))
