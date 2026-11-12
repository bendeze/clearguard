"""Pydantic schemas for ClearGuard Admin emergency early deactivation override."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.auth import DeviceResponse
from app.schemas.common import PaginatedResponse


class AdminOverrideCreateRequest(BaseModel):
    """Payload submitted by user or admin to approve emergency early override."""

    request_id: uuid.UUID = Field(..., description="ID of the active deactivation request")
    reason: str = Field(..., min_length=10, max_length=1000, description="Justification")


class AdminOverrideResponse(BaseModel):
    """Details of the issued asymmetric override certificate."""

    override_id: uuid.UUID
    request_id: uuid.UUID
    reason: str
    signed_token: str
    issued_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdminPendingRequestItem(BaseModel):
    """Pending deactivation item displayed on the administrative dashboard."""

    request_id: uuid.UUID
    user_id: uuid.UUID
    username: str
    partner_email: str
    started_at: datetime
    cooloff_days: int
    status: str

    model_config = ConfigDict(from_attributes=True)


class AdminPublicKeyResponse(BaseModel):
    """Public key for offline client-side signature verification."""

    public_key_pem: str
    algorithm: str = "Ed25519"


class AdminClientItem(BaseModel):
    """Client account summary and linked device inventory for admin console."""

    id: uuid.UUID
    username: str
    email: str | None
    is_active: bool
    is_admin: bool
    created_at: datetime
    updated_at: datetime
    device_count: int
    has_vault: bool
    vault_version: int | None = None
    vault_updated_at: datetime | None = None
    latest_deactivation_status: str | None = None
    devices: list[DeviceResponse] = Field(default_factory=list)


class AdminDeviceItem(BaseModel):
    """Registered device record joined with its owning client identity."""

    id: uuid.UUID
    user_id: uuid.UUID
    username: str
    email: str | None
    device_identifier: str
    device_name: str
    client_version: str
    is_active: bool
    last_seen_at: datetime
    created_at: datetime


class AdminClientListResponse(PaginatedResponse[AdminClientItem]):
    """Paginated response of ClearGuard client accounts."""


class AdminDeviceListResponse(PaginatedResponse[AdminDeviceItem]):
    """Paginated response of registered ClearGuard client devices."""
