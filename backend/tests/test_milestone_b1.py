"""Integration tests validating Milestone B1: Database Foundation requirements."""

import uuid
from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import CheckConstraint, String, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import Mapped, mapped_column

from alembic import command
from app.core.config import Settings
from app.core.database_errors import translate_database_errors
from app.core.exceptions import DatabaseConstraintError, DuplicateEntityError
from app.models.base import Base, TimestampMixin, UUIDMixin


class MilestoneItem(Base, UUIDMixin, TimestampMixin):
    """Model used specifically for Milestone B1 verification tests."""

    __tablename__ = "test_milestone_items"
    __table_args__ = (CheckConstraint("length(tag) >= 3", name="check_min_tag_length"),)

    tag: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(String(100), nullable=True)


# --- B1.4.1: SQLite Connectivity & Persistence ---


@pytest.mark.anyio
async def test_sqlite_file_persistence(tmp_path: Path) -> None:
    """B1.4.1: Verify SQLite data persists to disk and can be reloaded across engine sessions."""
    db_file = tmp_path / "persistence_test.db"
    db_url = f"sqlite+aiosqlite:///{db_file}"

    # Session 1: Create table and insert a record
    engine1 = create_async_engine(db_url)
    async with engine1.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    record_id = uuid.uuid4()
    sessionmaker1 = async_sessionmaker(engine1, expire_on_commit=False)
    async with sessionmaker1() as session:
        session.add(MilestoneItem(id=record_id, tag="PERSIST_01", description="Disk test"))
        await session.commit()
    await engine1.dispose()

    # Verify physical file existence and non-zero size
    assert db_file.exists()
    assert db_file.stat().st_size > 0

    # Session 2: Connect with a new engine instance to read from disk
    engine2 = create_async_engine(db_url)
    sessionmaker2 = async_sessionmaker(engine2, expire_on_commit=False)
    async with sessionmaker2() as session:
        result = await session.execute(select(MilestoneItem).where(MilestoneItem.id == record_id))
        loaded = result.scalar_one_or_none()
        assert loaded is not None
        assert loaded.id == record_id
        assert loaded.tag == "PERSIST_01"
        assert loaded.description == "Disk test"
    await engine2.dispose()


# --- B1.4.2: UUID Generation & Persistence ---


@pytest.mark.anyio
async def test_uuid_type_and_roundtrip(tmp_path: Path) -> None:
    """B1.4.2: Verify UUID primary keys are generated and roundtrip properly."""
    db_url = f"sqlite+aiosqlite:///{tmp_path / 'uuid_test.db'}"
    engine = create_async_engine(db_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)

    # 1. Automatic UUID generation on insert
    async with sessionmaker() as session:
        item_auto = MilestoneItem(tag="AUTO_UUID")
        session.add(item_auto)
        await session.commit()
        await session.refresh(item_auto)

        assert isinstance(item_auto.id, uuid.UUID)
        auto_id = item_auto.id

    # 2. Querying loaded object preserves Python uuid.UUID type
    async with sessionmaker() as session:
        result = await session.execute(select(MilestoneItem).where(MilestoneItem.id == auto_id))
        fetched = result.scalar_one()
        assert isinstance(fetched.id, uuid.UUID)
        assert fetched.id == auto_id

    # 3. Explicit UUID assignment preserves exact value
    explicit_id = uuid.uuid4()
    async with sessionmaker() as session:
        item_explicit = MilestoneItem(id=explicit_id, tag="EXPLICIT_UUID")
        session.add(item_explicit)
        await session.commit()

    async with sessionmaker() as session:
        result = await session.execute(select(MilestoneItem).where(MilestoneItem.id == explicit_id))
        fetched_explicit = result.scalar_one()
        assert fetched_explicit.id == explicit_id

    await engine.dispose()


# --- B1.4.3: Model Constraints & Naming Conventions ---


@pytest.mark.anyio
async def test_model_constraints_enforcement(tmp_path: Path) -> None:
    """B1.4.3: Verify check and unique constraints trigger corresponding domain errors."""
    db_url = f"sqlite+aiosqlite:///{tmp_path / 'constraints_test.db'}"
    engine = create_async_engine(db_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)

    # Unique constraint enforcement
    async with sessionmaker() as session:
        session.add(MilestoneItem(tag="UNIQUE_TAG"))
        await session.commit()

    async with sessionmaker() as session:
        with pytest.raises(DuplicateEntityError):
            async with translate_database_errors("MilestoneItem"):
                session.add(MilestoneItem(tag="UNIQUE_TAG"))
                await session.flush()

    # Check constraint enforcement (tag length < 3)
    async with sessionmaker() as session:
        with pytest.raises(DatabaseConstraintError):
            async with translate_database_errors("MilestoneItem"):
                session.add(MilestoneItem(tag="X"))  # Violates length(tag) >= 3
                await session.flush()

    await engine.dispose()


# --- B1.4.4: Migration Operations ---


def test_alembic_migration_commands_execute() -> None:
    """B1.4.4: Verify Alembic migration infrastructure can inspect history and current revisions."""
    backend_dir = Path(__file__).resolve().parent.parent
    alembic_cfg = Config(str(backend_dir / "alembic.ini"))
    # Verify current revision inspection executes cleanly
    command.current(alembic_cfg)
    # Verify history inspection executes cleanly
    command.history(alembic_cfg)


# --- B1.4.5: Environment-Driven Configuration ---


def test_environment_driven_database_url_sqlite(monkeypatch: pytest.MonkeyPatch) -> None:
    """B1.4.5: Verify SQLite database URL can be dynamically driven by environment variables."""
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./env_test.db")
    settings = Settings()
    assert settings.database_url == "sqlite:///./env_test.db"
    assert settings.async_database_url == "sqlite+aiosqlite:///./env_test.db"


def test_environment_driven_database_url_postgresql(monkeypatch: pytest.MonkeyPatch) -> None:
    """B1.4.5: Verify PostgreSQL production URL normalization via environment variables."""
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://clearguard_user:secret_pass@db.internal:5432/clearguard_prod",
    )
    settings = Settings()
    assert (
        settings.async_database_url
        == "postgresql+asyncpg://clearguard_user:secret_pass@db.internal:5432/clearguard_prod"
    )
