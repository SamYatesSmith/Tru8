"""M-04: Add manifest JSONB column to Check.

Stores signed manifest (HMAC-SHA256) at pipeline completion.
Application-immutable after creation.

Revision ID: m04_manifest
Revises: pq07_content_basis
Create Date: 2026-03-09
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "m04_manifest"
down_revision = "pq07_content_basis"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "check",
        sa.Column("manifest", JSONB, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("check", "manifest")
