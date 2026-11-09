"""Unit and integration tests for DomainRepository and DomainService."""

import pytest

from app.core.database import engine, get_db_context
from app.core.exceptions import DuplicateEntityError, EntityNotFoundError
from app.models.base import Base
from app.models.enums import DomainCategory, DomainStatus
from app.repositories.domain_repository import DomainRepository
from app.schemas.domain import BulkImportRequest, DomainCreate, DomainUpdate
from app.services.domain_service import DomainService


@pytest.fixture
async def setup_database():
    """Ensure clean database schema before and after each test."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# --- DomainRepository Tests ---


@pytest.mark.anyio
async def test_domain_repository_get_and_exists(setup_database) -> None:
    """Verify get_by_domain and exists_by_domain repository methods."""
    async with get_db_context() as session:
        repo = DomainRepository(session)
        assert await repo.exists_by_domain("non-existent.com") is False
        assert await repo.get_by_domain("non-existent.com") is None

        await repo.create(domain="repo-test-site.com", category=DomainCategory.PORNOGRAPHY)

        assert await repo.exists_by_domain("repo-test-site.com") is True
        fetched = await repo.get_by_domain("repo-test-site.com")
        assert fetched is not None
        assert fetched.domain == "repo-test-site.com"


@pytest.mark.anyio
async def test_domain_repository_get_by_domains_batch(setup_database) -> None:
    """Verify batch lookup of multiple domain strings."""
    async with get_db_context() as session:
        repo = DomainRepository(session)
        assert await repo.get_by_domains([]) == []

        await repo.create(domain="batch-alpha.com")
        await repo.create(domain="batch-beta.com")
        await repo.create(domain="batch-gamma.com")

        found = await repo.get_by_domains(["batch-alpha.com", "batch-gamma.com", "batch-delta.com"])
        assert len(found) == 2
        names = {item.domain for item in found}
        assert names == {"batch-alpha.com", "batch-gamma.com"}


@pytest.mark.anyio
async def test_domain_repository_search_and_pagination(setup_database) -> None:
    """Verify search filtering by substring, category, status, and pagination."""
    async with get_db_context() as session:
        repo = DomainRepository(session)
        await repo.create(
            domain="adult-hub-01.com",
            category=DomainCategory.PORNOGRAPHY,
            status=DomainStatus.ACTIVE,
        )
        await repo.create(
            domain="adult-hub-02.com",
            category=DomainCategory.PORNOGRAPHY,
            status=DomainStatus.ACTIVE,
        )
        await repo.create(
            domain="erotica-lounge.com", category=DomainCategory.EROTICA, status=DomainStatus.ACTIVE
        )
        await repo.create(
            domain="malware-vector.com",
            category=DomainCategory.MALWARE,
            status=DomainStatus.INACTIVE,
        )

    async with get_db_context() as session:
        repo = DomainRepository(session)

        # 1. Search by query substring
        items, total = await repo.search(query="hub")
        assert total == 2
        assert len(items) == 2

        # 2. Filter by category
        items, total = await repo.search(category=DomainCategory.EROTICA)
        assert total == 1
        assert items[0].domain == "erotica-lounge.com"

        # 3. Filter by status
        items, total = await repo.search(status=DomainStatus.INACTIVE)
        assert total == 1
        assert items[0].domain == "malware-vector.com"

        # 4. Pagination
        items, total = await repo.search(limit=2, offset=0)
        assert total == 4
        assert len(items) == 2


# --- DomainService CRUD Tests ---


@pytest.mark.anyio
async def test_domain_service_create_and_duplicate_detection(setup_database) -> None:
    """Verify domain creation with normalization and duplicate rejection."""
    async with get_db_context() as session:
        service = DomainService(session)
        created = await service.create_domain(
            DomainCreate(
                domain="https://WWW.Service-Test.XXX/home", category=DomainCategory.EXPLICIT
            )
        )
        assert created.domain == "service-test.xxx"
        assert created.category == DomainCategory.EXPLICIT

        # Attempt to insert identical domain (with different case and www)
        with pytest.raises(DuplicateEntityError) as exc_info:
            await service.create_domain(DomainCreate(domain="http://service-test.xxx"))
        assert exc_info.value.code == "DUPLICATE_ENTITY"


@pytest.mark.anyio
async def test_domain_service_lookup(setup_database) -> None:
    """Verify lookup_domain with raw input normalization and non-existent handling."""
    async with get_db_context() as session:
        service = DomainService(session)
        await service.create_domain(DomainCreate(domain="lookup-target.xxx"))

        # Lookup with messy raw URL
        found = await service.lookup_domain("https://www.lookup-target.xxx:8080/path")
        assert found is not None
        assert found.domain == "lookup-target.xxx"

        # Lookup non-existent domain
        assert await service.lookup_domain("missing-target.xxx") is None

        # Lookup invalid domain string
        assert await service.lookup_domain("not-a-domain") is None


@pytest.mark.anyio
async def test_domain_service_update_and_delete(setup_database) -> None:
    """Verify updating and deleting a domain record."""
    async with get_db_context() as session:
        service = DomainService(session)
        created = await service.create_domain(DomainCreate(domain="lifecycle-site.com"))
        domain_id = created.id

        # Update
        updated = await service.update_domain(
            domain_id, DomainUpdate(status=DomainStatus.ALLOWLISTED, notes="Exemption granted")
        )
        assert updated.status == DomainStatus.ALLOWLISTED
        assert updated.notes == "Exemption granted"

        # Delete
        await service.delete_domain(domain_id)

        # Confirm 404 on subsequent get
        with pytest.raises(EntityNotFoundError):
            await service.get_by_id(domain_id)


# --- DomainService Bulk Import Tests ---


@pytest.mark.anyio
async def test_domain_service_bulk_import(setup_database) -> None:
    """Verify bulk import handles valid entries, deduplication, and invalid formats."""
    # Pre-populate one domain in the database
    async with get_db_context() as session:
        service = DomainService(session)
        await service.create_domain(DomainCreate(domain="already-exists.com"))

    async with get_db_context() as session:
        service = DomainService(session)

        request = BulkImportRequest(
            domains=[
                "new-domain-01.com",
                "https://www.new-domain-02.com:443/feed",
                "new-domain-03.org",
                "new-domain-01.com",  # Duplicate in input
                "HTTPS://NEW-DOMAIN-02.COM",  # Duplicate in input (normalized)
                "already-exists.com",  # Pre-existing in database
                "192.168.1.50",  # Invalid (IP)
                "http://",  # Invalid (empty after strip)
                "singlelabel",  # Invalid (no TLD)
            ],
            category=DomainCategory.PORNOGRAPHY,
            source="test_blocklist_feed",
        )

        result = await service.bulk_import(request)

        assert result.total_submitted == 9
        assert result.inserted == 3  # new-domain-01, new-domain-02, new-domain-03
        assert result.skipped_duplicates == 3  # 2 in-memory duplicates + 1 database duplicate
        assert result.invalid_count == 3
        assert len(result.errors) == 3

    # Verify all 3 new domains exist in database
    async with get_db_context() as session:
        repo = DomainRepository(session)
        records = await repo.get_by_domains(
            ["new-domain-01.com", "new-domain-02.com", "new-domain-03.org"]
        )
        assert len(records) == 3
