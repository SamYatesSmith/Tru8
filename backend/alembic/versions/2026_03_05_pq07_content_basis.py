"""PQ-07: Add content_basis column to Evidence.

Records what the pipeline actually obtained for each evidence item:
full (HTML extracted), snippet (search blurb fallback), api (domain API),
or pdf (PDF document).

Revision ID: pq07_content_basis
Revises: m03_executed_tier
Create Date: 2026-03-05
"""

from alembic import op
import sqlalchemy as sa

revision = "pq07_content_basis"
down_revision = "m03_executed_tier"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "evidence",
        sa.Column("content_basis", sa.String(20), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("evidence", "content_basis")
