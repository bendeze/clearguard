"""Specialized repository for Blocklist and BlocklistVersion database operations."""

import uuid
from collections.abc import Sequence

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database_errors import translate_database_errors
from app.models.blocklist import Blocklist, BlocklistDomain, BlocklistVersion
from app.models.domain import Domain
from app.repositories.base import BaseRepository


class BlocklistRepository(BaseRepository[Blocklist]):
    """Repository managing blocklists, domain associations, and release versions."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Blocklist, session)

    async def get_by_name(self, name: str) -> Blocklist | None:
        """Find a blocklist collection by its exact name."""
        async with translate_database_errors(self.entity_name):
            result = await self.session.execute(select(Blocklist).where(Blocklist.name == name))
            return result.scalar_one_or_none()

    async def get_default(self) -> Blocklist | None:
        """Retrieve the primary default blocklist."""
        async with translate_database_errors(self.entity_name):
            result = await self.session.execute(
                select(Blocklist).where(Blocklist.is_default.is_(True))
            )
            return result.scalar_one_or_none()

    async def get_domains(
        self, blocklist_id: uuid.UUID, *, offset: int = 0, limit: int = 1000
    ) -> Sequence[Domain]:
        """Fetch domains associated with a blocklist."""
        async with translate_database_errors("BlocklistDomain"):
            stmt = (
                select(Domain)
                .join(BlocklistDomain, Domain.id == BlocklistDomain.domain_id)
                .where(BlocklistDomain.blocklist_id == blocklist_id)
                .order_by(Domain.domain.asc())
                .offset(offset)
                .limit(limit)
            )
            result = await self.session.execute(stmt)
            return result.scalars().all()

    async def add_domains(self, blocklist_id: uuid.UUID, domain_ids: Sequence[uuid.UUID]) -> int:
        """Associate a set of domain IDs with a blocklist, ignoring duplicates."""
        if not domain_ids:
            return 0

        async with translate_database_errors("BlocklistDomain"):
            async with self.session.begin_nested():
                # Filter out domain IDs already associated with this blocklist
                existing_stmt = select(BlocklistDomain.domain_id).where(
                    BlocklistDomain.blocklist_id == blocklist_id,
                    BlocklistDomain.domain_id.in_(domain_ids),
                )
                existing_result = await self.session.execute(existing_stmt)
                existing_ids = set(existing_result.scalars().all())

                new_ids = [did for did in domain_ids if did not in existing_ids]
                if new_ids:
                    records = [
                        BlocklistDomain(blocklist_id=blocklist_id, domain_id=did) for did in new_ids
                    ]
                    self.session.add_all(records)
                    await self.session.flush()

                # Update blocklist domain_count
                count_stmt = select(func.count(BlocklistDomain.domain_id)).where(
                    BlocklistDomain.blocklist_id == blocklist_id
                )
                total_count = (await self.session.execute(count_stmt)).scalar_one() or 0

                blocklist = await self.get_by_id(blocklist_id)
                if blocklist:
                    blocklist.domain_count = total_count
                    self.session.add(blocklist)
                    await self.session.flush()

                return len(new_ids)

    async def remove_domains(self, blocklist_id: uuid.UUID, domain_ids: Sequence[uuid.UUID]) -> int:
        """Remove domain associations from a blocklist."""
        if not domain_ids:
            return 0

        async with translate_database_errors("BlocklistDomain"):
            async with self.session.begin_nested():
                stmt = delete(BlocklistDomain).where(
                    BlocklistDomain.blocklist_id == blocklist_id,
                    BlocklistDomain.domain_id.in_(domain_ids),
                )
                result = await self.session.execute(stmt)
                removed_count = result.rowcount

                # Update domain_count
                count_stmt = select(func.count(BlocklistDomain.domain_id)).where(
                    BlocklistDomain.blocklist_id == blocklist_id
                )
                total_count = (await self.session.execute(count_stmt)).scalar_one() or 0

                blocklist = await self.get_by_id(blocklist_id)
                if blocklist:
                    blocklist.domain_count = total_count
                    self.session.add(blocklist)
                    await self.session.flush()

                return removed_count

    async def create_version(
        self,
        *,
        blocklist_id: uuid.UUID,
        version: str,
        content_hash: str,
        domain_count: int,
        changelog: str | None = None,
    ) -> BlocklistVersion:
        """Publish a new BlocklistVersion snapshot."""
        async with translate_database_errors("BlocklistVersion"):
            async with self.session.begin_nested():
                snapshot = BlocklistVersion(
                    blocklist_id=blocklist_id,
                    version=version,
                    content_hash=content_hash,
                    domain_count=domain_count,
                    changelog=changelog,
                )
                self.session.add(snapshot)

                # Update current_version on the parent blocklist
                blocklist = await self.get_by_id(blocklist_id)
                if blocklist:
                    blocklist.current_version = version
                    blocklist.domain_count = domain_count
                    self.session.add(blocklist)

                await self.session.flush()
                await self.session.refresh(snapshot)
                return snapshot

    async def get_latest_version(self, blocklist_id: uuid.UUID) -> BlocklistVersion | None:
        """Retrieve the most recently published version of a blocklist."""
        async with translate_database_errors("BlocklistVersion"):
            stmt = (
                select(BlocklistVersion)
                .where(BlocklistVersion.blocklist_id == blocklist_id)
                .order_by(
                    BlocklistVersion.created_at.desc(),
                    BlocklistVersion.version.desc(),
                )
                .limit(1)
            )
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()

    async def list_versions(
        self, blocklist_id: uuid.UUID, *, offset: int = 0, limit: int = 100
    ) -> Sequence[BlocklistVersion]:
        """List published versions for a blocklist with pagination."""
        async with translate_database_errors("BlocklistVersion"):
            stmt = (
                select(BlocklistVersion)
                .where(BlocklistVersion.blocklist_id == blocklist_id)
                .order_by(
                    BlocklistVersion.created_at.desc(),
                    BlocklistVersion.version.desc(),
                )
                .offset(offset)
                .limit(limit)
            )
            result = await self.session.execute(stmt)
            return result.scalars().all()

    async def count_versions(self, blocklist_id: uuid.UUID) -> int:
        """Count total versions published for a blocklist."""
        async with translate_database_errors("BlocklistVersion"):
            stmt = select(func.count(BlocklistVersion.id)).where(
                BlocklistVersion.blocklist_id == blocklist_id
            )
            result = await self.session.execute(stmt)
            return result.scalar_one() or 0

    async def count_domains(self, blocklist_id: uuid.UUID) -> int:
        """Count total domains associated with a blocklist."""
        async with translate_database_errors("BlocklistDomain"):
            stmt = select(func.count(BlocklistDomain.domain_id)).where(
                BlocklistDomain.blocklist_id == blocklist_id
            )
            result = await self.session.execute(stmt)
            return result.scalar_one() or 0
