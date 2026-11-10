"""Pydantic schemas and enums for blocklist synchronization protocols."""

import datetime
import uuid
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class SyncStatus(StrEnum):
    """Synchronization status indicating client relationship to latest release."""

    UP_TO_DATE = "up_to_date"
    UPDATE_AVAILABLE = "update_available"
    OUTDATED = "outdated"


class SyncCheckItem(BaseModel):
    """Client request checking synchronization state for a single blocklist."""

    model_config = ConfigDict(extra="forbid")

    blocklist_id: uuid.UUID = Field(description="Unique UUID of the blocklist collection to check.")
    client_version: str | None = Field(
        default=None,
        max_length=50,
        description="Version string currently stored on the client (e.g. '1.0.0').",
    )
    client_content_hash: str | None = Field(
        default=None,
        min_length=64,
        max_length=64,
        description="Hex-encoded SHA-256 content hash of the client's current domain list.",
    )


class SyncCheckResponse(BaseModel):
    """Synchronization evaluation response containing update recommendations."""

    model_config = ConfigDict(from_attributes=True)

    blocklist_id: uuid.UUID = Field(description="Unique blocklist UUID.")
    status: SyncStatus = Field(description="Evaluated sync state.")
    update_required: bool = Field(
        description="Whether the client should download a newer rule snapshot."
    )
    latest_version: str = Field(description="Most recent release version string.")
    latest_content_hash: str = Field(
        description="SHA-256 content hash of the latest active domain list."
    )
    domain_count: int = Field(ge=0, description="Total active domain count in the latest release.")
    changelog: str | None = Field(
        default=None, description="Release notes summary for the latest version."
    )
    download_url: str = Field(
        description="Relative endpoint URL to download the domains for this blocklist."
    )


class SyncBatchCheckRequest(BaseModel):
    """Batch request payload to check sync status for multiple blocklists simultaneously."""

    model_config = ConfigDict(extra="forbid")

    items: list[SyncCheckItem] = Field(
        min_length=1,
        max_length=50,
        description="List of blocklist collections to check for updates.",
    )


class SyncBatchCheckResponse(BaseModel):
    """Batch response payload containing sync evaluations for all requested blocklists."""

    items: list[SyncCheckResponse] = Field(
        description="Evaluated sync status for each requested blocklist."
    )


class BlocklistDownloadResponse(BaseModel):
    """Payload representing downloaded blocklist domains and integrity metadata."""

    model_config = ConfigDict(from_attributes=True)

    blocklist_id: uuid.UUID = Field(description="Unique blocklist UUID.")
    name: str = Field(description="Human-readable blocklist name.")
    version: str = Field(description="Snapshot version of the downloaded blocklist.")
    content_hash: str = Field(
        min_length=64,
        max_length=64,
        description="SHA-256 hash of the alphabetically sorted domain collection.",
    )
    domain_count: int = Field(ge=0, description="Total number of domains in this download.")
    published_at: datetime.datetime = Field(
        description="Timestamp when this version was published."
    )
    changelog: str | None = Field(default=None, description="Release notes for this version.")
    domains: list[str] = Field(
        description="Alphabetically sorted list of fully-qualified domain names."
    )


class BlocklistDownloadResponse(BaseModel):
    """Payload representing downloaded blocklist domains and integrity metadata."""

    model_config = ConfigDict(from_attributes=True)

    blocklist_id: uuid.UUID = Field(description="Unique blocklist UUID.")
    name: str = Field(description="Human-readable blocklist name.")
    version: str = Field(description="Snapshot version of the downloaded blocklist.")
    content_hash: str = Field(
        min_length=64,
        max_length=64,
        description="SHA-256 hash of the alphabetically sorted domain collection.",
    )
    domain_count: int = Field(ge=0, description="Total number of domains in this download.")
    published_at: datetime.datetime = Field(
        description="Timestamp when this version was published."
    )
    changelog: str | None = Field(default=None, description="Release notes for this version.")
    domains: list[str] = Field(
        description="Alphabetically sorted list of fully-qualified domain names."
    )

