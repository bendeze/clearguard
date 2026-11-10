"""Multi-Factor Accountability, Partner Verification, and Admin Override models."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class DeactivationStatus(enum.StrEnum):
    """Lifecycle statuses for high-friction deactivation requests."""

    PENDING_PARTNER_APPROVAL = "pending_partner_approval"
    PARTNER_APPROVED = "partner_approved"
    PARTNER_REJECTED = "partner_rejected"
    CANCELLED = "cancelled"
    ADMIN_OVERRIDDEN = "admin_overridden"
    COMPLETED = "completed"


class DeactivationRequest(Base, UUIDMixin, TimestampMixin):
    """High-friction deactivation request tracking 60-day delay and partner co-signing."""

    __tablename__ = "deactivation_requests"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    device_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("devices.id", ondelete="SET NULL"),
        nullable=True,
    )
    partner_email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    cooloff_days: Mapped[int] = mapped_column(
        Integer,
        default=60,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default=DeactivationStatus.PENDING_PARTNER_APPROVAL.value,
        nullable=False,
    )
    partner_token_hash: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        index=True,
        nullable=False,
    )
    partner_token_expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    partner_responded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    partner_rejection_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="deactivation_requests")  # noqa: F821
    device: Mapped["Device | None"] = relationship("Device")  # noqa: F821
    admin_override: Mapped["AdminOverride | None"] = relationship(
        "AdminOverride",
        back_populates="deactivation_request",
        uselist=False,
        cascade="all, delete-orphan",
    )


class AdminOverride(Base, UUIDMixin):
    """Cryptographically signed administrative early deactivation override record."""

    __tablename__ = "admin_overrides"

    request_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("deactivation_requests.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    admin_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reason: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    signed_token: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    deactivation_request: Mapped["DeactivationRequest"] = relationship(
        "DeactivationRequest",
        back_populates="admin_override",
    )
    admin_user: Mapped["User | None"] = relationship("User")  # noqa: F821
