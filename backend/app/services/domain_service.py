"""Domain management service handling domain business logic, validation, and bulk import."""

import logging
import uuid
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DuplicateEntityError, InvalidDomainError
from app.models.domain import Domain
from app.models.enums import DomainCategory, DomainStatus
from app.repositories.domain_repository import DomainRepository
from app.schemas.domain import (
    BulkImportError,
    BulkImportRequest,
    BulkImportResponse,
    DomainCreate,
    DomainUpdate,
)
from app.services.domain_validator import normalize_and_validate_domain

logger = logging.getLogger(__name__)


class DomainService:
    """Service providing adult-domain management operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = DomainRepository(session)

    async def create_domain(self, data: DomainCreate) -> Domain:
        """Create a new domain after validation and duplicate detection."""
        normalized = normalize_and_validate_domain(data.domain)

        # Duplicate detection
        if await self.repository.exists_by_domain(normalized):
            raise DuplicateEntityError(
                message=f"Domain '{normalized}' is already registered in the system.",
                details={"domain": normalized},
            )

        domain_dict = data.model_dump()
        domain_dict["domain"] = normalized
        return await self.repository.create(**domain_dict)

    async def get_by_id(self, domain_id: uuid.UUID) -> Domain:
        """Retrieve a domain by its ID or raise EntityNotFoundError."""
        return await self.repository.get_by_id_or_raise(domain_id)

    async def lookup_domain(self, raw_domain: str) -> Domain | None:
        """Look up a domain using raw, unnormalized domain or URL input."""
        try:
            normalized = normalize_and_validate_domain(raw_domain)
        except InvalidDomainError:
            return None
        return await self.repository.get_by_domain(normalized)

    async def search_domains(
        self,
        *,
        query: str | None = None,
        category: DomainCategory | None = None,
        status: DomainStatus | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> tuple[Sequence[Domain], int]:
        """Search and filter domains with total count."""
        return await self.repository.search(
            query=query,
            category=category,
            status=status,
            offset=offset,
            limit=limit,
        )

    async def update_domain(self, domain_id: uuid.UUID, data: DomainUpdate) -> Domain:
        """Update domain attributes."""
        domain = await self.repository.get_by_id_or_raise(domain_id)
        update_data = data.model_dump(exclude_unset=True)
        return await self.repository.update(domain, **update_data)

    async def delete_domain(self, domain_id: uuid.UUID) -> None:
        """Delete a domain record by its ID."""
        domain = await self.repository.get_by_id_or_raise(domain_id)
        await self.repository.delete(domain)

    async def bulk_import(self, request: BulkImportRequest) -> BulkImportResponse:
        """Process, validate, deduplicate, and persist bulk domain entries."""
        valid_map: dict[str, str] = {}  # normalized -> raw
        errors: list[BulkImportError] = []
        valid_count = 0

        # 1. Validation & normalization pass
        for raw_item in request.domains:
            try:
                normalized = normalize_and_validate_domain(raw_item)
                valid_count += 1
                if normalized not in valid_map:
                    valid_map[normalized] = raw_item
            except InvalidDomainError as exc:
                errors.append(BulkImportError(domain=raw_item, reason=exc.message))

        total_submitted = len(request.domains)
        invalid_count = len(errors)

        if not valid_map:
            return BulkImportResponse(
                total_submitted=total_submitted,
                inserted=0,
                skipped_duplicates=valid_count,
                invalid_count=invalid_count,
                errors=errors,
            )

        # 2. Database duplicate detection in batch
        normalized_candidates = list(valid_map.keys())
        existing_records = await self.repository.get_by_domains(normalized_candidates)
        existing_domain_names = {rec.domain for rec in existing_records}

        new_domains = [d for d in normalized_candidates if d not in existing_domain_names]
        in_memory_duplicates = valid_count - len(normalized_candidates)
        db_duplicates = len(normalized_candidates) - len(new_domains)
        skipped_duplicates = in_memory_duplicates + db_duplicates

        # 3. Batch insert new domains
        domains_to_create = [
            {
                "domain": d,
                "category": request.category,
                "status": request.status,
                "source": request.source,
                "confidence_score": 1.0,
            }
            for d in new_domains
        ]

        if domains_to_create:
            await self.repository.bulk_create(domains_to_create)

        inserted_count = len(domains_to_create)
        logger.info(
            "Bulk import completed: %d submitted, %d inserted, %d skipped duplicates, %d invalid",
            total_submitted,
            inserted_count,
            skipped_duplicates,
            invalid_count,
        )

        return BulkImportResponse(
            total_submitted=total_submitted,
            inserted=inserted_count,
            skipped_duplicates=skipped_duplicates,
            invalid_count=invalid_count,
            errors=errors,
        )
