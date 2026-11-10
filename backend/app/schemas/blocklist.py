"""Pydantic schemas for Blocklists, versions, and feed ingestion."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import DomainCategory
from app.schemas.common import PaginatedResponse
from app.schemas.domain import DomainResponse


class BlocklistBase(BaseModel):
    """Base attributes for a blocklist."""

    name: str = Field(
        ..., min_length=2, max_length=100, description="Unique blocklist identifier name"
    )
    description: str | None = Field(
        default=None, max_length=500, description="Blocklist description"
    )
    is_default: bool = Field(
        default=False, description="Whether this is the default protection list"
    )
    is_active: bool = Field(default=True, description="Whether this blocklist is actively applied")


class BlocklistCreate(BlocklistBase):
    """Schema for registering a new blocklist collection."""


class BlocklistUpdate(BaseModel):
    """Schema for updating blocklist attributes."""

    name: str | None = Field(default=None, min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    is_default: bool | None = None
    is_active: bool | None = None


class BlocklistResponse(BlocklistBase):
    """Schema for returning blocklist entities."""

    id: uuid.UUID
    current_version: str
    domain_count: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BlocklistVersionResponse(BaseModel):
    """Schema for returning release snapshots with content integrity hashes."""

    id: uuid.UUID
    blocklist_id: uuid.UUID
    version: str
    content_hash: str
    domain_count: int
    changelog: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FeedIngestRequest(BaseModel):
    """Request payload for ingesting a raw blocklist feed."""

    content: str = Field(
        ...,
        min_length=1,
        description="Raw blocklist text in Hosts, plain domain, or Adblock syntax",
    )
    source: str = Field(default="feed_ingest", max_length=100, description="Feed origin identifier")
    category: DomainCategory = Field(
        default=DomainCategory.PORNOGRAPHY,
        description="Category applied to newly discovered domains",
    )


class FeedIngestResponse(BaseModel):
    """Response reporting feed parsing and blocklist association metrics."""

    blocklist_id: uuid.UUID
    parsed_count: int
    new_domains_created: int
    domains_associated: int
    total_blocklist_domains: int


class BlocklistPublishRequest(BaseModel):
    """Request payload for publishing a new blocklist version snapshot."""

    version: str | None = Field(
        default=None,
        max_length=50,
        description="Optional semantic version string (e.g. '1.1.0'). If omitted, auto-increments.",
    )
    changelog: str | None = Field(
        default=None,
        max_length=500,
        description="Optional release notes or changelog summary.",
    )
    force: bool = Field(
        default=False,
        description="Force publication even if validation warnings occur (e.g., zero domains).",
    )


class BlocklistRollbackRequest(BaseModel):
    """Request payload to revert a blocklist's active pointer to a historical snapshot."""

    model_config = ConfigDict(extra="forbid")

    target_version: str = Field(
        min_length=1,
        max_length=50,
        description="Historical version string to roll back to (e.g. '1.0.0').",
    )
    reason: str | None = Field(
        default=None,
        max_length=500,
        description="Operational justification for the rollback.",
    )


class BlocklistAssociateDomainsRequest(BaseModel):
    """Request payload for associating domains with a blocklist."""

    domain_ids: list[uuid.UUID] = Field(
        min_length=1,
        max_length=10000,
        description="List of domain IDs to associate with this blocklist.",
    )


class BlocklistRemoveDomainsRequest(BaseModel):
    """Request payload for removing domain associations from a blocklist."""

    domain_ids: list[uuid.UUID] = Field(
        min_length=1,
        max_length=10000,
        description="List of domain IDs to remove from this blocklist.",
    )


class BlocklistListResponse(PaginatedResponse[BlocklistResponse]):
    """Paginated response collection of blocklists."""


class BlocklistVersionListResponse(PaginatedResponse[BlocklistVersionResponse]):
    """Paginated response collection of blocklist release versions."""


class BlocklistDomainsResponse(PaginatedResponse[DomainResponse]):
    """Paginated response collection of domains associated with a blocklist."""
