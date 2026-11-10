"""Pydantic schemas for End-to-End Encrypted (E2EE) User Vault."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.crypto import is_valid_base64


class VaultUploadRequest(BaseModel):
    """Client-side encrypted vault blob submission.

    All sensitive data (pledge phrase, partner email, partner PIN hash) must be
    encrypted client-side with AES-256-GCM before uploading.
    """

    ciphertext: str = Field(..., min_length=16, description="Base64 encoded ciphertext")
    iv: str = Field(..., min_length=12, max_length=64, description="Base64 encoded 12-byte IV")
    tag: str = Field(..., min_length=16, max_length=64, description="Base64 encoded 16-byte tag")
    salt: str = Field(..., min_length=16, max_length=64, description="Base64 encoded KDF salt")
    kdf_iterations: int = Field(
        default=100000,
        ge=10000,
        description="Key derivation iterations",
    )

    @field_validator("ciphertext", "iv", "tag", "salt")
    @classmethod
    def validate_base64_fields(cls, v: str) -> str:
        """Validate that encrypted payloads are valid Base64 strings."""
        if not is_valid_base64(v):
            raise ValueError("Field must be a valid Base64-encoded string")
        return v


class VaultResponse(BaseModel):
    """Retrieved client-side encrypted vault record."""

    user_id: uuid.UUID
    ciphertext: str
    iv: str
    tag: str
    salt: str
    kdf_iterations: int
    vault_version: int
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
