"""Integration tests for Domain model, database constraints, and Pydantic schemas."""

import uuid
from datetime import UTC

import pytest
from pydantic import ValidationError as PydanticValidationError

from app.core.database import engine, get_db_context
from app.core.exceptions import DuplicateEntityError, InvalidDomainError
from app.models.base import Base
from app.models.domain import Domain
from app.models.enums import DomainCategory, DomainStatus
from app.repositories.base import BaseRepository
from app.schemas.domain import DomainCreate, DomainResponse, DomainUpdate


@pytest.fixture
async def setup_database_tables():
    """Ensure clean database schema before and after each test."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.anyio
async def test_domain_model_persistence(setup_database_tables) -> None:
    """Verify Domain entity can be created, persisted, and retrieved."""
    async with get_db_context() as session:
        repo = BaseRepository(Domain, session)
        created = await repo.create(
            domain="bad-adult-site.com",
            category=DomainCategory.PORNOGRAPHY,
            status=DomainStatus.ACTIVE,
            source="manual_review",
            confidence_score=0.98,
            notes="Confirmed explicit content",
        )

        assert isinstance(created.id, uuid.UUID)
        assert created.domain == "bad-adult-site.com"
        assert created.category == DomainCategory.PORNOGRAPHY
        assert created.status == DomainStatus.ACTIVE
        assert created.confidence_score == 0.98
        assert created.created_at is not None

        domain_id = created.id

    # Verify retrieval in an independent session
    async with get_db_context() as session:
        repo = BaseRepository(Domain, session)
        fetched = await repo.get_by_id_or_raise(domain_id)
        assert fetched.domain == "bad-adult-site.com"
        assert fetched.notes == "Confirmed explicit content"


@pytest.mark.anyio
async def test_domain_uniqueness_constraint(setup_database_tables) -> None:
    """Verify duplicate domain registration is prevented by unique constraint."""
    async with get_db_context() as session:
        repo = BaseRepository(Domain, session)
        await repo.create(domain="unique-test-domain.xxx")

        with pytest.raises(DuplicateEntityError) as exc_info:
            await repo.create(domain="unique-test-domain.xxx")

        assert exc_info.value.code == "DUPLICATE_ENTITY"
        assert exc_info.value.status_code == 409


@pytest.mark.anyio
async def test_domain_status_and_category_enums(setup_database_tables) -> None:
    """Verify all domain categories and statuses can be assigned and stored correctly."""
    categories = list(DomainCategory)
    statuses = list(DomainStatus)

    async with get_db_context() as session:
        repo = BaseRepository(Domain, session)
        for i, cat in enumerate(categories):
            stat = statuses[i % len(statuses)]
            await repo.create(
                domain=f"category-test-{i}.xxx",
                category=cat,
                status=stat,
            )

    async with get_db_context() as session:
        repo = BaseRepository(Domain, session)
        count = await repo.count()
        assert count == len(categories)


def test_domain_create_schema_normalization() -> None:
    """Verify DomainCreate automatically normalizes domain inputs."""
    data = DomainCreate(
        domain="  HTTPS://WWW.Porn-Site.XXX:8080/feed?id=123  ",
        category=DomainCategory.EXPLICIT,
    )
    assert data.domain == "porn-site.xxx"
    assert data.category == DomainCategory.EXPLICIT
    assert data.status == DomainStatus.ACTIVE
    assert data.confidence_score == 1.0


def test_domain_create_schema_invalid_domain() -> None:
    """Verify DomainCreate rejects invalid domains during schema validation."""
    with pytest.raises(InvalidDomainError):
        DomainCreate(domain="http://192.168.1.100")

    with pytest.raises(InvalidDomainError):
        DomainCreate(domain="not-a-domain")


def test_domain_update_schema() -> None:
    """Verify DomainUpdate accepts partial updates."""
    update_data = DomainUpdate(
        status=DomainStatus.ALLOWLISTED,
        notes="False positive verified",
    )
    dumped = update_data.model_dump(exclude_unset=True)
    assert dumped == {
        "status": DomainStatus.ALLOWLISTED,
        "notes": "False positive verified",
    }


def test_domain_schema_confidence_score_bounds() -> None:
    """Verify confidence_score is bounded between 0.0 and 1.0."""
    with pytest.raises(PydanticValidationError):
        DomainCreate(domain="test-bounds.com", confidence_score=1.5)

    with pytest.raises(PydanticValidationError):
        DomainCreate(domain="test-bounds.com", confidence_score=-0.1)


def test_domain_response_serialization() -> None:
    """Verify DomainResponse schema serializes fields accurately."""
    item_id = uuid.uuid4()
    from datetime import datetime

    now = datetime.now(UTC)

    response = DomainResponse(
        id=item_id,
        domain="verified-adult.com",
        category=DomainCategory.PORNOGRAPHY,
        status=DomainStatus.ACTIVE,
        source="feed_sync",
        confidence_score=0.95,
        notes=None,
        created_at=now,
        updated_at=now,
    )
    data = response.model_dump()
    assert data["id"] == item_id
    assert data["domain"] == "verified-adult.com"
    assert data["category"] == "pornography"
    assert data["status"] == "active"
