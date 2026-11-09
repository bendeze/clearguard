"""Tests for session management, transaction scopes, base repository, and error handling."""

import uuid

import pytest
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import engine, get_db_context, transaction_scope
from app.core.exceptions import (
    DatabaseError,
    DuplicateEntityError,
    EntityNotFoundError,
)
from app.models.base import Base, TimestampMixin, UUIDMixin
from app.repositories.base import BaseRepository


class DummyRecord(Base, UUIDMixin, TimestampMixin):
    """Test model for validating repository operations and database constraints."""

    __tablename__ = "test_dummy_records"

    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(String(200), nullable=True)


@pytest.fixture(autouse=True)
async def setup_test_tables():
    """Create test tables before each test and drop them afterwards."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.anyio
async def test_get_db_context_commit_on_success() -> None:
    """Verify get_db_context automatically commits on clean exit."""
    item_id = uuid.uuid4()
    async with get_db_context() as session:
        record = DummyRecord(id=item_id, code="CTX_001", description="Created via context")
        session.add(record)

    # In a separate session, verify data was persisted
    async with get_db_context() as verify_session:
        repo = BaseRepository(DummyRecord, verify_session)
        fetched = await repo.get_by_id(item_id)
        assert fetched is not None
        assert fetched.code == "CTX_001"


@pytest.mark.anyio
async def test_get_db_context_rollback_on_error() -> None:
    """Verify get_db_context rolls back transaction when an exception is raised."""
    item_id = uuid.uuid4()
    with pytest.raises(RuntimeError, match="Intentional failure"):
        async with get_db_context() as session:
            record = DummyRecord(id=item_id, code="ROLLBACK_001")
            session.add(record)
            await session.flush()
            raise RuntimeError("Intentional failure")

    # In a separate session, verify data was rolled back
    async with get_db_context() as verify_session:
        repo = BaseRepository(DummyRecord, verify_session)
        fetched = await repo.get_by_id(item_id)
        assert fetched is None


@pytest.mark.anyio
async def test_transaction_scope_savepoint_rollback() -> None:
    """Verify transaction_scope supports nested savepoints that roll back safely."""
    async with get_db_context() as session:
        repo = BaseRepository(DummyRecord, session)

        # Parent transaction creates item 1
        await repo.create(code="PERSISTED_001")

        # Nested savepoint fails and rolls back
        with pytest.raises(ValueError, match="Nested failure"):
            async with transaction_scope(session):
                await repo.create(code="NESTED_FAILED_001")
                raise ValueError("Nested failure")

        # Parent continues and creates item 2
        await repo.create(code="PERSISTED_002")

    # Verify outer transaction succeeded with only items 1 and 2
    async with get_db_context() as verify_session:
        repo = BaseRepository(DummyRecord, verify_session)
        records = await repo.list()
        codes = [r.code for r in records]
        assert "PERSISTED_001" in codes
        assert "PERSISTED_002" in codes
        assert "NESTED_FAILED_001" not in codes


@pytest.mark.anyio
async def test_base_repository_crud_flow() -> None:
    """Verify complete CRUD lifecycle using BaseRepository."""
    async with get_db_context() as session:
        repo = BaseRepository(DummyRecord, session)

        # 1. Create
        record = await repo.create(code="REPO_001", description="Initial description")
        assert record.id is not None
        assert record.code == "REPO_001"
        assert record.created_at is not None

        # 2. Get by ID
        found = await repo.get_by_id(record.id)
        assert found is not None
        assert found.description == "Initial description"

        # 3. Get by ID or raise
        found_strict = await repo.get_by_id_or_raise(record.id)
        assert found_strict.id == record.id

        # 4. Count
        count = await repo.count()
        assert count == 1

        # 5. List with pagination
        items = await repo.list(offset=0, limit=10)
        assert len(items) == 1
        assert items[0].id == record.id

        # 6. Update
        updated = await repo.update(record, description="Updated description")
        assert updated.description == "Updated description"

        # 7. Delete
        await repo.delete(record)
        assert await repo.get_by_id(record.id) is None
        assert await repo.count() == 0


@pytest.mark.anyio
async def test_base_repository_get_or_raise_not_found() -> None:
    """Verify get_by_id_or_raise raises EntityNotFoundError when record is absent."""
    async with get_db_context() as session:
        repo = BaseRepository(DummyRecord, session)
        missing_id = uuid.uuid4()
        with pytest.raises(EntityNotFoundError) as exc_info:
            await repo.get_by_id_or_raise(missing_id)

        assert exc_info.value.code == "ENTITY_NOT_FOUND"
        assert exc_info.value.status_code == 404
        assert str(missing_id) in exc_info.value.message


@pytest.mark.anyio
async def test_repository_duplicate_entity_error() -> None:
    """Verify unique constraint violations are translated into DuplicateEntityError."""
    async with get_db_context() as session:
        repo = BaseRepository(DummyRecord, session)
        await repo.create(code="UNIQUE_CODE_001")

        with pytest.raises(DuplicateEntityError) as exc_info:
            await repo.create(code="UNIQUE_CODE_001")

        assert exc_info.value.code == "DUPLICATE_ENTITY"
        assert exc_info.value.status_code == 409


@pytest.mark.anyio
async def test_translate_database_errors_constraint_violation() -> None:
    """Verify non-unique integrity errors map to DatabaseConstraintError."""
    from sqlalchemy.exc import IntegrityError

    from app.core.database_errors import translate_database_errors
    from app.core.exceptions import DatabaseConstraintError

    with pytest.raises(DatabaseConstraintError) as exc_info:
        async with translate_database_errors("TestEntity"):
            raise IntegrityError(
                "FOREIGN KEY constraint failed",
                params=None,
                orig=Exception("FOREIGN KEY constraint failed"),
            )

    assert exc_info.value.code == "CONSTRAINT_VIOLATION"
    assert exc_info.value.status_code == 409


@pytest.mark.anyio
async def test_translate_database_errors_no_result_found() -> None:
    """Verify NoResultFound maps to EntityNotFoundError."""
    from sqlalchemy.exc import NoResultFound

    from app.core.database_errors import translate_database_errors

    with pytest.raises(EntityNotFoundError) as exc_info:
        async with translate_database_errors("TestEntity"):
            raise NoResultFound("No row found")

    assert exc_info.value.code == "ENTITY_NOT_FOUND"
    assert exc_info.value.status_code == 404


@pytest.mark.anyio
async def test_translate_database_errors_general_error() -> None:
    """Verify unexpected SQLAlchemyError maps to DatabaseError."""
    from sqlalchemy.exc import SQLAlchemyError

    from app.core.database_errors import translate_database_errors

    with pytest.raises(DatabaseError) as exc_info:
        async with translate_database_errors("TestEntity"):
            raise SQLAlchemyError("Connection reset by peer")

    assert exc_info.value.code == "DATABASE_ERROR"
    assert exc_info.value.status_code == 500
