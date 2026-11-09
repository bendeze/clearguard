"""Blocklist management business service handling collections, feed ingestion, and releases."""

import hashlib
import logging
import uuid
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DuplicateEntityError
from app.models.blocklist import Blocklist, BlocklistVersion
from app.models.domain import Domain
from app.repositories.blocklist_repository import BlocklistRepository
from app.repositories.domain_repository import DomainRepository
from app.schemas.blocklist import (
    BlocklistCreate,
    BlocklistUpdate,
    FeedIngestRequest,
    FeedIngestResponse,
)
from app.services.feed_parser import parse_blocklist_feed

logger = logging.getLogger(__name__)


class BlocklistService:
    """Service managing blocklists, domain associations, version releases, and feed ingestion."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = BlocklistRepository(session)
        self.domain_repository = DomainRepository(session)

    async def create_blocklist(self, data: BlocklistCreate) -> Blocklist:
        """Create a new blocklist collection with unique name validation."""
        existing = await self.repository.get_by_name(data.name)
        if existing:
            raise DuplicateEntityError(
                message=f"Blocklist with name '{data.name}' already exists.",
                details={"name": data.name},
            )

        # If marked default, unset any existing default
        if data.is_default:
            current_default = await self.repository.get_default()
            if current_default:
                current_default.is_default = False
                self.session.add(current_default)

        return await self.repository.create(**data.model_dump())

    async def get_by_id(self, blocklist_id: uuid.UUID) -> Blocklist:
        """Retrieve blocklist by ID or raise EntityNotFoundError."""
        return await self.repository.get_by_id_or_raise(blocklist_id)

    async def get_by_name(self, name: str) -> Blocklist | None:
        """Find blocklist by its name."""
        return await self.repository.get_by_name(name)

    async def list_blocklists(self, *, offset: int = 0, limit: int = 100) -> Sequence[Blocklist]:
        """List all blocklists with pagination."""
        return await self.repository.list(offset=offset, limit=limit)

    async def update_blocklist(self, blocklist_id: uuid.UUID, data: BlocklistUpdate) -> Blocklist:
        """Update blocklist properties."""
        blocklist = await self.repository.get_by_id_or_raise(blocklist_id)
        update_dict = data.model_dump(exclude_unset=True)

        if "name" in update_dict and update_dict["name"] != blocklist.name:
            existing = await self.repository.get_by_name(update_dict["name"])
            if existing:
                raise DuplicateEntityError(
                    message=f"Blocklist with name '{update_dict['name']}' already exists.",
                    details={"name": update_dict["name"]},
                )

        if update_dict.get("is_default"):
            current_default = await self.repository.get_default()
            if current_default and current_default.id != blocklist.id:
                current_default.is_default = False
                self.session.add(current_default)

        return await self.repository.update(blocklist, **update_dict)

    async def delete_blocklist(self, blocklist_id: uuid.UUID) -> None:
        """Delete a blocklist and its versions."""
        blocklist = await self.repository.get_by_id_or_raise(blocklist_id)
        await self.repository.delete(blocklist)

    async def get_blocklist_domains(
        self, blocklist_id: uuid.UUID, *, offset: int = 0, limit: int = 1000
    ) -> Sequence[Domain]:
        """Retrieve domains associated with a blocklist."""
        await self.repository.get_by_id_or_raise(blocklist_id)
        return await self.repository.get_domains(blocklist_id, offset=offset, limit=limit)

    async def associate_domains(
        self, blocklist_id: uuid.UUID, domain_ids: Sequence[uuid.UUID]
    ) -> int:
        """Associate existing domain IDs with a blocklist."""
        await self.repository.get_by_id_or_raise(blocklist_id)
        return await self.repository.add_domains(blocklist_id, domain_ids)

    async def remove_domains(self, blocklist_id: uuid.UUID, domain_ids: Sequence[uuid.UUID]) -> int:
        """Disassociate domains from a blocklist."""
        await self.repository.get_by_id_or_raise(blocklist_id)
        return await self.repository.remove_domains(blocklist_id, domain_ids)

    async def ingest_feed(
        self, blocklist_id: uuid.UUID, request: FeedIngestRequest
    ) -> FeedIngestResponse:
        """Parse feed content, register discovered domains, and associate them."""
        blocklist = await self.repository.get_by_id_or_raise(blocklist_id)
        parsed_domains = parse_blocklist_feed(request.content)
        parsed_count = len(parsed_domains)

        if not parsed_domains:
            return FeedIngestResponse(
                blocklist_id=blocklist_id,
                parsed_count=0,
                new_domains_created=0,
                domains_associated=0,
                total_blocklist_domains=blocklist.domain_count,
            )

        # 1. Fetch already existing domains in database
        existing_records = await self.domain_repository.get_by_domains(parsed_domains)
        existing_map = {rec.domain: rec for rec in existing_records}

        # 2. Insert any brand new domains
        new_names = [d for d in parsed_domains if d not in existing_map]
        if new_names:
            domains_to_create = [
                {
                    "domain": d,
                    "category": request.category,
                    "status": "active",
                    "source": request.source,
                    "confidence_score": 1.0,
                }
                for d in new_names
            ]
            new_records = await self.domain_repository.bulk_create(domains_to_create)
            for rec in new_records:
                existing_map[rec.domain] = rec

        # 3. Associate all domains with the blocklist
        all_domain_ids = [existing_map[d].id for d in parsed_domains if d in existing_map]
        associated_count = await self.repository.add_domains(blocklist_id, all_domain_ids)

        await self.session.refresh(blocklist)
        return FeedIngestResponse(
            blocklist_id=blocklist_id,
            parsed_count=parsed_count,
            new_domains_created=len(new_names),
            domains_associated=associated_count,
            total_blocklist_domains=blocklist.domain_count,
        )

    async def publish_version(
        self,
        blocklist_id: uuid.UUID,
        *,
        version: str | None = None,
        changelog: str | None = None,
    ) -> BlocklistVersion:
        """Compile active domains, compute SHA-256 hash, and release a new version."""
        await self.repository.get_by_id_or_raise(blocklist_id)

        # Retrieve all associated domains
        domains = await self.repository.get_domains(blocklist_id, limit=1_000_000)
        domain_names = sorted([d.domain for d in domains if d.status == "active"])
        domain_count = len(domain_names)

        # Compute deterministic SHA-256 hash of sorted newline-delimited domains
        content = "\n".join(domain_names).encode("utf-8")
        content_hash = hashlib.sha256(content).hexdigest()

        # Compute next version if not explicitly supplied
        if not version:
            latest = await self.repository.get_latest_version(blocklist_id)
            if latest and "." in latest.version:
                parts = latest.version.split(".")
                try:
                    parts[-1] = str(int(parts[-1]) + 1)
                    version = ".".join(parts)
                except ValueError:
                    version = f"{latest.version}.1"
            else:
                version = "1.0.0"

        snapshot = await self.repository.create_version(
            blocklist_id=blocklist_id,
            version=version,
            content_hash=content_hash,
            domain_count=domain_count,
            changelog=changelog,
        )
        return snapshot
