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
