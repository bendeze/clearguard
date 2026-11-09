"""Pydantic schemas for domain validation and data transfer."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import DomainCategory, DomainStatus
from app.services.domain_validator import normalize_and_validate_domain


class DomainBase(BaseModel):
    """Base schema for domain representations."""

    domain: str = Field(..., description="Canonical fully qualified domain name")
    category: DomainCategory = Field(
        default=DomainCategory.PORNOGRAPHY, description="Classification category"
    )
    status: DomainStatus = Field(
        default=DomainStatus.ACTIVE, description="Filtering status of the domain"
    )
    source: str = Field(default="manual", max_length=100, description="Origin or provider source")
    confidence_score: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Confidence score from 0.0 to 1.0"
    )
    notes: str | None = Field(
        default=None, max_length=500, description="Optional metadata or context"
    )


class DomainCreate(DomainBase):
    """Schema for registering a new domain with normalization validation."""

    @field_validator("domain", mode="before")
    @classmethod
    def normalize_domain_field(cls, value: str) -> str:
        """Automatically normalize and validate the domain format."""
        return normalize_and_validate_domain(value)


class DomainUpdate(BaseModel):
    """Schema for updating domain attributes."""

    category: DomainCategory | None = None
    status: DomainStatus | None = None
    source: str | None = Field(default=None, max_length=100)
    confidence_score: float | None = Field(default=None, ge=0.0, le=1.0)
    notes: str | None = Field(default=None, max_length=500)


class DomainResponse(DomainBase):
    """Schema for returning domain entities from the API."""

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BulkImportError(BaseModel):
    """Details of a domain that failed validation during bulk import."""

    domain: str
    reason: str


class BulkImportRequest(BaseModel):
    """Payload for submitting bulk domains for filtering ingestion."""

    domains: list[str] = Field(
        ..., min_length=1, max_length=10000, description="List of raw domain strings"
    )
    category: DomainCategory = Field(
        default=DomainCategory.PORNOGRAPHY, description="Category applied to new entries"
    )
    status: DomainStatus = Field(
        default=DomainStatus.ACTIVE, description="Status applied to new entries"
    )
    source: str = Field(default="bulk_import", max_length=100, description="Source identifier")


class BulkImportResponse(BaseModel):
    """Summary metrics of a bulk domain import operation."""

    total_submitted: int
    inserted: int
    skipped_duplicates: int
    invalid_count: int
    errors: list[BulkImportError] = Field(default_factory=list)


class DomainSearchParams(BaseModel):
    """Query parameters for searching and filtering domain records."""

    query: str | None = Field(default=None, description="Substring search on domain name")
    category: DomainCategory | None = Field(default=None, description="Filter by category")
    status: DomainStatus | None = Field(default=None, description="Filter by status")
    offset: int = Field(default=0, ge=0, description="Pagination offset")
    limit: int = Field(default=100, ge=1, le=1000, description="Pagination limit")


class DomainListResponse(BaseModel):
    """Paginated response containing domain records."""

    items: list[DomainResponse]
    total: int
    offset: int
    limit: int
