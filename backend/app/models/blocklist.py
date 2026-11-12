"""Blocklist models managing filtering collections, associations, and version snapshots."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.domain import Domain


class BlocklistDomain(Base):
    """Many-to-many junction table associating Blocklists with Domains."""

    __tablename__ = "blocklist_domains"

    blocklist_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("blocklists.id", ondelete="CASCADE"),
        primary_key=True,
    )
    domain_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("domains.id", ondelete="CASCADE"),
        primary_key=True,
    )
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class Blocklist(Base, UUIDMixin, TimestampMixin):
    """Collection of filtering rules representing a curated adult domain blocklist."""

    __tablename__ = "blocklists"

    name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    is_default: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    current_version: Mapped[str] = mapped_column(
        String(50),
        default="1.0.0",
        nullable=False,
    )
    domain_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    domains: Mapped[list["Domain"]] = relationship(
        "Domain",
        secondary="blocklist_domains",
        backref="blocklists",
        lazy="selectin",
    )


class BlocklistVersion(Base, UUIDMixin, TimestampMixin):
    """Immutable release snapshot of a blocklist with cryptographic integrity hash."""

    __tablename__ = "blocklist_versions"

    blocklist_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("blocklists.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    content_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="SHA-256 hash of sorted active domains for client integrity checks",
    )
    domain_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    changelog: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    __table_args__ = (
        UniqueConstraint(
            "blocklist_id", "version", name="uq_blocklist_versions_blocklist_id_version"
        ),
    )


class FeedIngestionJob(Base, UUIDMixin, TimestampMixin):
    """Tracks asynchronous background feed ingestion jobs (file uploads and URL imports)."""

    __tablename__ = "feed_ingestion_jobs"

    blocklist_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("blocklists.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    source_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    source_label: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    source_url: Mapped[str | None] = mapped_column(
        String(2048),
        nullable=True,
    )
    filename: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    category: Mapped[str] = mapped_column(
        String(50),
        default="pornography",
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="queued",
        index=True,
        nullable=False,
    )
    parsed_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    processed_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    new_domains_created: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    domains_associated: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    error_message: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
