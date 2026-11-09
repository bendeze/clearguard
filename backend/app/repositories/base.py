"""Base generic repository for asynchronous SQLAlchemy data operations."""

import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database_errors import translate_database_errors
from app.core.exceptions import EntityNotFoundError
from app.models.base import Base


class BaseRepository[ModelType: Base]:
    """Generic async repository providing decoupled CRUD database operations."""

    def __init__(self, model: type[ModelType], session: AsyncSession) -> None:
        self.model = model
        self.session = session

    @property
    def entity_name(self) -> str:
        """Name of the managed entity model."""
        return self.model.__name__

    async def get_by_id(self, entity_id: uuid.UUID) -> ModelType | None:
        """Retrieve an entity by its UUID primary key, or None if not found."""
        async with translate_database_errors(self.entity_name):
            result = await self.session.execute(
                select(self.model).where(self.model.id == entity_id)
            )
            return result.scalar_one_or_none()

    async def get_by_id_or_raise(self, entity_id: uuid.UUID) -> ModelType:
        """Retrieve an entity by its UUID primary key, or raise EntityNotFoundError."""
        entity = await self.get_by_id(entity_id)
        if entity is None:
            raise EntityNotFoundError(self.entity_name, entity_id)
        return entity

    async def list(self, *, offset: int = 0, limit: int = 100) -> Sequence[ModelType]:
        """Retrieve a paginated sequence of entities."""
        async with translate_database_errors(self.entity_name):
            result = await self.session.execute(select(self.model).offset(offset).limit(limit))
            return result.scalars().all()

    async def create(self, **kwargs: Any) -> ModelType:
        """Create, persist, and refresh a new model instance."""
        async with translate_database_errors(self.entity_name):
            async with self.session.begin_nested():
                instance = self.model(**kwargs)
                self.session.add(instance)
                await self.session.flush()
            await self.session.refresh(instance)
            return instance

    async def update(self, entity: ModelType, **kwargs: Any) -> ModelType:
        """Update fields on an existing model instance, flush, and refresh."""
        async with translate_database_errors(self.entity_name):
            async with self.session.begin_nested():
                for key, value in kwargs.items():
                    if hasattr(entity, key):
                        setattr(entity, key, value)
                self.session.add(entity)
                await self.session.flush()
            await self.session.refresh(entity)
            return entity

    async def delete(self, entity: ModelType) -> None:
        """Delete an entity from the database and flush."""
        async with translate_database_errors(self.entity_name):
            async with self.session.begin_nested():
                await self.session.delete(entity)
                await self.session.flush()

    async def count(self) -> int:
        """Return total count of entities."""
        async with translate_database_errors(self.entity_name):
            result = await self.session.execute(select(func.count()).select_from(self.model))
            return result.scalar_one() or 0
