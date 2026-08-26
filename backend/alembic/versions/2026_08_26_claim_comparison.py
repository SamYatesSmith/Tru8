"""COMPARE tab: claim_comparison table.

One row per completed comparison of two evidence items on one claim.
Stores PROSE ONLY (summaries + divergence) — collisions are computed on
read from the live claim_map so they can never go stale. The evidence pair
is stored sorted, and the unique constraint makes A/B and B/A one cache
row; the row count per check is the comparison budget spend.

Design: audit/2026-08-26_compare_tab_design.md.

Revision ID: claim_comparison
Revises: claim_claimant
Create Date: 2026-08-26
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "claim_comparison"
down_revision = "claim_claimant"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "claim_comparison",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("check_id", sa.String(), sa.ForeignKey("check.id"), nullable=False),
        sa.Column("claim_id", sa.String(), sa.ForeignKey("claim.id"), nullable=False),
        sa.Column("evidence_a_id", sa.String(64), nullable=False),
        sa.Column("evidence_b_id", sa.String(64), nullable=False),
        sa.Column("summary_a", sa.String(), nullable=False),
        sa.Column("summary_b", sa.String(), nullable=False),
        sa.Column("divergence", sa.String(), nullable=False),
        sa.Column("basis_a", sa.String(16), nullable=False),
        sa.Column("basis_b", sa.String(16), nullable=False),
        sa.Column("words_a", sa.Integer(), nullable=True),
        sa.Column("words_b", sa.Integer(), nullable=True),
        sa.Column("usage", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint(
            "claim_id",
            "evidence_a_id",
            "evidence_b_id",
            name="uq_claim_comparison_pair",
        ),
    )
    op.create_index("ix_claim_comparison_check_id", "claim_comparison", ["check_id"])
    op.create_index("ix_claim_comparison_claim_id", "claim_comparison", ["claim_id"])


def downgrade() -> None:
    op.drop_index("ix_claim_comparison_claim_id", table_name="claim_comparison")
    op.drop_index("ix_claim_comparison_check_id", table_name="claim_comparison")
    op.drop_table("claim_comparison")
