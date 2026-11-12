"""create_feed_ingestion_jobs_table

Revision ID: a1b2c3d4e5f6
Revises: 2c4cea41026c
Create Date: 2026-11-12 15:45:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | Sequence[str] | None = "2c4cea41026c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "feed_ingestion_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("blocklist_id", sa.Uuid(), nullable=False),
        sa.Column("source_type", sa.String(length=20), nullable=False),
        sa.Column("source_label", sa.String(length=100), nullable=False),
        sa.Column("source_url", sa.String(length=2048), nullable=True),
        sa.Column("filename", sa.String(length=255), nullable=True),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("parsed_count", sa.Integer(), nullable=False),
        sa.Column("processed_count", sa.Integer(), nullable=False),
        sa.Column("new_domains_created", sa.Integer(), nullable=False),
        sa.Column("domains_associated", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.String(length=1000), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["blocklist_id"], ["blocklists.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_feed_ingestion_jobs_blocklist_id"),
        "feed_ingestion_jobs",
        ["blocklist_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_feed_ingestion_jobs_status"),
        "feed_ingestion_jobs",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_feed_ingestion_jobs_status"), table_name="feed_ingestion_jobs")
    op.drop_index(op.f("ix_feed_ingestion_jobs_blocklist_id"), table_name="feed_ingestion_jobs")
    op.drop_table("feed_ingestion_jobs")
