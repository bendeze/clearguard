"""Domain database model representing blocked and monitored domains."""

from sqlalchemy import Enum, Float, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.enums import DomainCategory, DomainStatus


class Domain(Base, UUIDMixin, TimestampMixin):
    """Database entity representing an adult-content or filtered domain."""

    __tablename__ = "domains"

    domain: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )
    category: Mapped[DomainCategory] = mapped_column(
        Enum(DomainCategory, name="domain_category_enum", native_enum=False),
        default=DomainCategory.PORNOGRAPHY,
        index=True,
        nullable=False,
    )
    status: Mapped[DomainStatus] = mapped_column(
        Enum(DomainStatus, name="domain_status_enum", native_enum=False),
        default=DomainStatus.ACTIVE,
        index=True,
        nullable=False,
    )
    source: Mapped[str] = mapped_column(
        String(100),
        default="manual",
        nullable=False,
    )
    confidence_score: Mapped[float] = mapped_column(
        Float,
        default=1.0,
        nullable=False,
    )
    notes: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    __table_args__ = (Index("ix_domains_category_status", "category", "status"),)
