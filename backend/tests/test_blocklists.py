"""Unit and integration tests for Blocklists, FeedParser, and Versioning."""

import hashlib

import pytest

from app.core.database import engine, get_db_context
from app.core.exceptions import DuplicateEntityError, EntityNotFoundError
from app.models.base import Base
from app.models.enums import DomainCategory
from app.repositories.domain_repository import DomainRepository
from app.schemas.blocklist import BlocklistCreate, BlocklistUpdate, FeedIngestRequest
from app.services.blocklist_service import BlocklistService
from app.services.feed_parser import parse_blocklist_feed


@pytest.fixture
async def setup_database():
    """Ensure clean database schema before and after each test."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# --- FeedParser Unit Tests ---


def test_feed_parser_hosts_format() -> None:
    """Verify hosts file format parsing with loopback exclusion and comments."""
    content = """
    # Main blocklist header
    127.0.0.1 localhost
    ::1 localhost.localdomain
    0.0.0.0 adult-badsite.com
    127.0.0.1 www.evil-porn.xxx # inline comment
    0.0.0.0 127.0.0.1
    # End of hosts
    """
    domains = parse_blocklist_feed(content)
    assert domains == ["adult-badsite.com", "evil-porn.xxx"]


def test_feed_parser_adblock_and_plain_format() -> None:
    """Verify Adblock syntax and plain domain list parsing."""
    content = """
    ! Adblock header
    ||adblock-badsite.com^
    ||another-badsite.xxx
    plain-adult.org
    https://WWW.UPPERCASE-SITE.COM/path
    ! Invalid entries
    ||192.168.1.1^
    singlelabel
    """
    domains = parse_blocklist_feed(content)
    assert "adblock-badsite.com" in domains
    assert "another-badsite.xxx" in domains
    assert "plain-adult.org" in domains
    assert "uppercase-site.com" in domains
    assert len(domains) == 4


# --- Blocklist Repository & Service Tests ---


@pytest.mark.anyio
async def test_blocklist_crud_and_default_flag(setup_database) -> None:
    """Verify blocklist CRUD operations and default blocklist singleton enforcement."""
    async with get_db_context() as session:
        service = BlocklistService(session)

        # 1. Create first blocklist (default)
        b1 = await service.create_blocklist(
            BlocklistCreate(name="standard-adult", description="Standard list", is_default=True)
        )
        assert b1.name == "standard-adult"
        assert b1.is_default is True

        # 2. Prevent duplicate blocklist name
        with pytest.raises(DuplicateEntityError):
            await service.create_blocklist(BlocklistCreate(name="standard-adult"))

        # 3. Create second blocklist with is_default=True (should switch default flag)
        b2 = await service.create_blocklist(
            BlocklistCreate(name="strict-adult", description="Strict list", is_default=True)
        )
        assert b2.is_default is True

    # Verify b1 is no longer default and b2 is default
    async with get_db_context() as session:
        service = BlocklistService(session)
        default_bl = await service.repository.get_default()
        assert default_bl is not None
        assert default_bl.name == "strict-adult"

        # Update b1
        updated = await service.update_blocklist(
            b1.id, BlocklistUpdate(description="Updated standard description")
        )
        assert updated.description == "Updated standard description"

        # Delete b2
        await service.delete_blocklist(b2.id)
        with pytest.raises(EntityNotFoundError):
            await service.get_by_id(b2.id)


@pytest.mark.anyio
async def test_blocklist_domain_association_and_counts(setup_database) -> None:
    """Verify associating domains with a blocklist updates domain counts correctly."""
    async with get_db_context() as session:
        bl_service = BlocklistService(session)
        dom_repo = DomainRepository(session)

        blocklist = await bl_service.create_blocklist(BlocklistCreate(name="association-test"))
        d1 = await dom_repo.create(domain="site-alpha.com")
        d2 = await dom_repo.create(domain="site-beta.com")
        d3 = await dom_repo.create(domain="site-gamma.com")

        # Associate d1 and d2
        added = await bl_service.associate_domains(blocklist.id, [d1.id, d2.id])
        assert added == 2

        # Associate d2 again (should be ignored) along with d3
        added_repeat = await bl_service.associate_domains(blocklist.id, [d2.id, d3.id])
        assert added_repeat == 1

        # Check total associated domains
        domains = await bl_service.get_blocklist_domains(blocklist.id)
        assert len(domains) == 3
        domain_names = {d.domain for d in domains}
        assert domain_names == {"site-alpha.com", "site-beta.com", "site-gamma.com"}

        # Disassociate d1
        removed = await bl_service.remove_domains(blocklist.id, [d1.id])
        assert removed == 1

        refreshed_domains = await bl_service.get_blocklist_domains(blocklist.id)
        assert len(refreshed_domains) == 2


@pytest.mark.anyio
async def test_blocklist_version_publication_and_hash(setup_database) -> None:
    """Verify publishing blocklist releases computes correct SHA-256 hash and version bump."""
    async with get_db_context() as session:
        bl_service = BlocklistService(session)
        dom_repo = DomainRepository(session)

        blocklist = await bl_service.create_blocklist(BlocklistCreate(name="release-test"))
        d1 = await dom_repo.create(domain="zebra-adult.com")
        d2 = await dom_repo.create(domain="apple-adult.com")

        await bl_service.associate_domains(blocklist.id, [d1.id, d2.id])

        # Publish initial version
        v1 = await bl_service.publish_version(blocklist.id, changelog="Initial release")
        assert v1.version == "1.0.0"
        assert v1.domain_count == 2

        # Verify hash is computed on alphabetically sorted domains
        expected_content = b"apple-adult.com\nzebra-adult.com"
        expected_hash = hashlib.sha256(expected_content).hexdigest()
        assert v1.content_hash == expected_hash

        # Publish subsequent version without explicit version tag -> auto-bump to 1.0.1
        v2 = await bl_service.publish_version(blocklist.id, changelog="Second release")
        assert v2.version == "1.0.1"
        assert v2.content_hash == expected_hash

        # Verify latest version query
        latest = await bl_service.repository.get_latest_version(blocklist.id)
        assert latest is not None
        assert latest.version == "1.0.1"


@pytest.mark.anyio
async def test_blocklist_feed_ingestion_pipeline(setup_database) -> None:
    """Verify end-to-end feed ingestion parses, persists new domains, and attaches them."""
    feed_data = """
    # Community feed
    0.0.0.0 feed-domain-01.com
    ||feed-domain-02.xxx^
    feed-domain-03.org
    0.0.0.0 feed-domain-01.com # duplicate in feed
    0.0.0.0 localhost
    """
    async with get_db_context() as session:
        bl_service = BlocklistService(session)
        dom_repo = DomainRepository(session)

        # Pre-seed one domain to test linking pre-existing domain
        await dom_repo.create(domain="feed-domain-01.com")

        blocklist = await bl_service.create_blocklist(BlocklistCreate(name="feed-test-list"))

        response = await bl_service.ingest_feed(
            blocklist.id,
            FeedIngestRequest(
                content=feed_data,
                source="community_feed_v1",
                category=DomainCategory.PORNOGRAPHY,
            ),
        )

        assert response.parsed_count == 3  # 01, 02, 03
        assert response.new_domains_created == 2  # 02 and 03
        assert response.domains_associated == 3
        assert response.total_blocklist_domains == 3

        # Verify domains associated with blocklist
        domains = await bl_service.get_blocklist_domains(blocklist.id)
        names = {d.domain for d in domains}
        assert names == {"feed-domain-01.com", "feed-domain-02.xxx", "feed-domain-03.org"}
