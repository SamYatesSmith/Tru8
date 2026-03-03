"""M-02: Add provider_status JSONB column to Check.

Per-provider retrieval outcomes (ok/timeout/error/0_results with count).

Revision ID: m02_provider_status
Revises: m01_provenance_fields
Create Date: 2026-03-02
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "m02_provider_status"
down_revision = "m01_provenance_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("check", sa.Column("provider_status", JSONB, nullable=True))


def downgrade() -> None:
    op.drop_column("check", "provider_status")
