"""Specialized repository for Domain database operations."""

from collections.abc import Sequence
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database_errors import translate_database_errors
from app.models.domain import Domain
from app.models.enums import DomainCategory, DomainStatus
from app.repositories.base import BaseRepository


class DomainRepository(BaseRepository[Domain]):
    """Repository handling domain queries, existence checks, and bulk operations."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Domain, session)

    async def get_by_domain(self, domain: str) -> Domain | None:
        """Find a domain by its exact normalized name."""
        async with translate_database_errors(self.entity_name):
            result = await self.session.execute(select(Domain).where(Domain.domain == domain))
            return result.scalar_one_or_none()

    async def exists_by_domain(self, domain: str) -> bool:
        """Check whether a normalized domain name exists in the database."""
        async with translate_database_errors(self.entity_name):
            result = await self.session.execute(
                select(func.count(Domain.id)).where(Domain.domain == domain)
            )
            count = result.scalar_one() or 0
            return count > 0

    async def get_by_domains(self, domains: Sequence[str]) -> Sequence[Domain]:
        """Fetch all domains matching any of the provided domain names in a single query."""
        if not domains:
            return []
        async with translate_database_errors(self.entity_name):
            result = await self.session.execute(select(Domain).where(Domain.domain.in_(domains)))
            return result.scalars().all()

    async def search(
        self,
        *,
        query: str | None = None,
        category: DomainCategory | None = None,
        status: DomainStatus | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> tuple[Sequence[Domain], int]:
        """Search domains with optional substring query, category, and status filters."""
        async with translate_database_errors(self.entity_name):
            stmt = select(Domain)
            count_stmt = select(func.count(Domain.id))

            if query:
                pattern = f"%{query.lower()}%"
                stmt = stmt.where(Domain.domain.ilike(pattern))
                count_stmt = count_stmt.where(Domain.domain.ilike(pattern))

            if category:
                stmt = stmt.where(Domain.category == category)
                count_stmt = count_stmt.where(Domain.category == category)

            if status:
                stmt = stmt.where(Domain.status == status)
                count_stmt = count_stmt.where(Domain.status == status)

            # Total matching count
            count_result = await self.session.execute(count_stmt)
            total = count_result.scalar_one() or 0

            # Paginated items ordered by created_at desc
            stmt = stmt.order_by(Domain.created_at.desc()).offset(offset).limit(limit)
            result = await self.session.execute(stmt)
            items = result.scalars().all()

            return items, total

    async def bulk_create(self, domains_data: Sequence[dict[str, Any]]) -> Sequence[Domain]:
        """Insert multiple Domain instances within a savepoint."""
        if not domains_data:
            return []
        async with translate_database_errors(self.entity_name):
            async with self.session.begin_nested():
                instances = [Domain(**data) for data in domains_data]
                self.session.add_all(instances)
                await self.session.flush()
            return instances
