"""End-to-End Encrypted (E2EE) User Vault database model."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin


class UserVault(Base, UUIDMixin):
    """Zero-knowledge client-side encrypted vault record.

    Stores client-side encrypted JSON blob containing commitment pledge phrase,
    trusted partner contact information, and protection settings. The backend
    never possesses the client's encryption key and cannot decrypt this data.
    """

    __tablename__ = "user_vaults"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    ciphertext: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    iv: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    tag: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    salt: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    kdf_iterations: Mapped[int] = mapped_column(
        Integer,
        default=100000,
        nullable=False,
    )
    vault_version: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user: Mapped["User"] = relationship("User", back_populates="vault")  # noqa: F821
