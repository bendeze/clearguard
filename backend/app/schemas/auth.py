"""Pydantic schemas for authentication, tokens, and device management."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRegisterRequest(BaseModel):
    """Payload for registering a new user account."""

    username: str = Field(..., min_length=3, max_length=64, description="Unique username")
    password: str = Field(..., min_length=8, max_length=128, description="Account password")
    email: EmailStr | None = Field(default=None, description="Optional recovery email")


class UserLoginRequest(BaseModel):
    """Payload for authenticating and obtaining tokens."""

    username: str = Field(..., min_length=1, description="Username")
    password: str = Field(..., min_length=1, description="Password")
    device_identifier: str | None = Field(
        default=None,
        description="Optional hardware/install device identifier",
    )
    device_name: str | None = Field(default="Android Device", description="Device display name")


class RefreshTokenRequest(BaseModel):
    """Payload for exchanging a refresh token for new access credentials."""

    refresh_token: str = Field(..., min_length=16, description="Refresh token secret")


class AuthTokensResponse(BaseModel):
    """Bearer access token and refresh token credentials."""

    access_token: str = Field(..., description="Signed JWT access token")
    refresh_token: str = Field(..., description="Opaque refresh token secret")
    token_type: str = Field(default="bearer", description="Token authentication type")
    expires_in: int = Field(..., description="Access token lifetime in seconds")


class DeviceRegisterRequest(BaseModel):
    """Payload for linking a client device to an authenticated account."""

    device_identifier: str = Field(..., min_length=8, max_length=128, description="Device UUID")
    device_name: str = Field(default="Android Device", max_length=100)
    client_version: str = Field(default="0.7.0", max_length=32)


class DeviceResponse(BaseModel):
    """Details of a registered client device."""

    id: uuid.UUID
    device_identifier: str
    device_name: str
    client_version: str
    is_active: bool
    last_seen_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserProfileResponse(BaseModel):
    """Authenticated user profile with linked devices."""

    id: uuid.UUID
    username: str
    email: str | None
    is_admin: bool
    created_at: datetime
    devices: list[DeviceResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
