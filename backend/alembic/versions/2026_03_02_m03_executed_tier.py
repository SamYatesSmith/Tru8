"""M-03: Add executed_tier column to Check.

Records which pipeline tier (quick/full) produced the result.
Set at check creation time, not at save time.

Revision ID: m03_executed_tier
Revises: m02_provider_status
Create Date: 2026-03-02
"""

from alembic import op
import sqlalchemy as sa

revision = "m03_executed_tier"
down_revision = "m02_provider_status"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "check",
        sa.Column("executed_tier", sa.String(20), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("check", "executed_tier")
