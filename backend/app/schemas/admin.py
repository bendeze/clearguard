"""Pydantic schemas for ClearGuard Admin emergency early deactivation override."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


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
