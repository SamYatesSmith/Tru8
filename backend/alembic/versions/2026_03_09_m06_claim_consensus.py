"""M-06: Add claim_consensus table for convergence layer.

Stores cross-user consensus aggregates for claims checked ≥3 times
independently. Recomputed daily by batch job.

Revision ID: m06_claim_consensus
Revises: m04_manifest
Create Date: 2026-03-09
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "m06_claim_consensus"
down_revision = "m04_manifest"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "claim_consensus",
        sa.Column("claim_text_hash", sa.String(64), primary_key=True),
        sa.Column("independent_checks", sa.Integer, nullable=False),
        sa.Column("stability", sa.String(10), nullable=False),
        sa.Column("element_state_distribution", JSONB, nullable=False),
        sa.Column("unique_sources", sa.Integer, nullable=False),
        sa.Column("total_evidence", sa.Integer, nullable=False),
        sa.Column("tier_spread", JSONB, nullable=False),
        sa.Column("last_full_check_at", sa.DateTime, nullable=False),
        sa.Column("computed_at", sa.DateTime, nullable=False),
    )


def downgrade() -> None:
    op.drop_table("claim_consensus")
