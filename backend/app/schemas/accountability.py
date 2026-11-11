"""Pydantic schemas for Multi-Factor Accountability, Partner Verification, and 60-Day Delay."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class DeactivationInitiateRequest(BaseModel):
    """Payload to initiate a 60-day deactivation process with partner notification."""

    partner_email: EmailStr = Field(..., description="Email address of the trusted partner")
    device_id: uuid.UUID | None = Field(default=None, description="Optional initiating device ID")


class DeactivationStatusResponse(BaseModel):
    """Live deactivation status and synchronized countdown information."""

    request_id: uuid.UUID
    user_id: uuid.UUID
    partner_email: str
    started_at: datetime
    cooloff_days: int
    days_remaining: int
    seconds_remaining: int
    status: str
    can_cancel: bool
    partner_responded_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class PartnerCosignRequest(BaseModel):
    """Payload from partner confirming or denying deactivation authorization."""

    token: str = Field(..., min_length=16, description="One-time partner verification token")
    decision: Literal["approve", "reject"] = Field(..., description="Partner decision")
    rejection_reason: str | None = Field(default=None, max_length=500)


class PartnerVerifyTokenResponse(BaseModel):
    """Token validation response for the partner web verification UI."""

    valid: bool
    request_id: uuid.UUID | None = None
    started_at: datetime | None = None
    cooloff_days: int | None = None
    status: str | None = None
    message: str
