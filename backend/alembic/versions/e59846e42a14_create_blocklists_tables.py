"""create_blocklists_tables

Revision ID: e59846e42a14
Revises: 6431ba7ba9a6
Create Date: 2026-11-09 19:05:11.056143

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e59846e42a14"
down_revision: str | Sequence[str] | None = "6431ba7ba9a6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "blocklists",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("current_version", sa.String(length=50), nullable=False),
        sa.Column("domain_count", sa.Integer(), nullable=False),
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_blocklists")),
    )
    with op.batch_alter_table("blocklists", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_blocklists_name"), ["name"], unique=True)

    op.create_table(
        "blocklist_domains",
        sa.Column("blocklist_id", sa.Uuid(), nullable=False),
        sa.Column("domain_id", sa.Uuid(), nullable=False),
        sa.Column(
            "added_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["blocklist_id"],
            ["blocklists.id"],
            name=op.f("fk_blocklist_domains_blocklist_id_blocklists"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["domain_id"],
            ["domains.id"],
            name=op.f("fk_blocklist_domains_domain_id_domains"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("blocklist_id", "domain_id", name=op.f("pk_blocklist_domains")),
    )

    op.create_table(
        "blocklist_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("blocklist_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.String(length=50), nullable=False),
        sa.Column(
            "content_hash",
            sa.String(length=64),
            nullable=False,
            comment="SHA-256 hash of sorted active domains for client integrity checks",
        ),
        sa.Column("domain_count", sa.Integer(), nullable=False),
        sa.Column("changelog", sa.String(length=500), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["blocklist_id"],
            ["blocklists.id"],
            name=op.f("fk_blocklist_versions_blocklist_id_blocklists"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_blocklist_versions")),
        sa.UniqueConstraint(
            "blocklist_id", "version", name="uq_blocklist_versions_blocklist_id_version"
        ),
    )
    with op.batch_alter_table("blocklist_versions", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_blocklist_versions_blocklist_id"), ["blocklist_id"], unique=False
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("blocklist_versions", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_blocklist_versions_blocklist_id"))

    op.drop_table("blocklist_versions")
    op.drop_table("blocklist_domains")
    with op.batch_alter_table("blocklists", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_blocklists_name"))

    op.drop_table("blocklists")
