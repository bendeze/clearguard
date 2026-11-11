"""Tests for declarative model base, UUID conventions, and model mixins."""

import uuid

import pytest
from sqlalchemy import MetaData, String, Uuid, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.core.database import engine
from app.models.base import NAMING_CONVENTION, Base, TimestampMixin, UUIDMixin


class _TestBase(DeclarativeBase):
    """Isolated declarative base so test-only tables never pollute Base.metadata."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class SampleItem(_TestBase, UUIDMixin, TimestampMixin):
    """Sample test entity to verify Base, UUIDMixin, and TimestampMixin."""

    __tablename__ = "test_sample_items"

    name: Mapped[str] = mapped_column(String(100), nullable=False)


def test_naming_convention_present() -> None:
    """Verify that naming convention dictionary is defined and attached to Base.metadata."""
    assert "fk" in NAMING_CONVENTION
    assert "pk" in NAMING_CONVENTION
    assert "uq" in NAMING_CONVENTION
    assert Base.metadata.naming_convention == NAMING_CONVENTION


def test_uuid_mixin_column_configuration() -> None:
    """Verify that UUIDMixin defines a UUID primary key with default generator."""
    id_col = SampleItem.__table__.c.id
    assert id_col.primary_key is True
    assert isinstance(id_col.type, Uuid)
    assert id_col.default is not None
    assert id_col.default.is_callable is True
    assert id_col.default.arg.__name__ == "uuid4"


def test_model_explicit_uuid_assignment() -> None:
    """Verify that models accept explicit UUID assignment."""
    custom_id = uuid.uuid4()
    item = SampleItem(id=custom_id, name="Custom ID Item")
    assert item.id == custom_id


@pytest.mark.anyio
async def test_sample_entity_lifecycle_in_database() -> None:
    """Verify creating, persisting, and querying an entity using model mixins."""
    async with engine.begin() as conn:
        await conn.run_sync(_TestBase.metadata.create_all)

    try:
        async with engine.connect() as conn:
            item_id = str(uuid.uuid4())
            await conn.execute(
                text(
                    "INSERT INTO test_sample_items (id, name, created_at, updated_at) "
                    "VALUES (:id, :name, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
                ),
                {"id": item_id, "name": "Persisted Item"},
            )
            await conn.commit()

            result = await conn.execute(
                text("SELECT id, name FROM test_sample_items WHERE id = :id"),
                {"id": item_id},
            )
            row = result.mappings().one()
            assert row["name"] == "Persisted Item"
            assert row["id"] == item_id
    finally:
        # Clean up test table
        async with engine.begin() as conn:
            await conn.run_sync(_TestBase.metadata.drop_all)
