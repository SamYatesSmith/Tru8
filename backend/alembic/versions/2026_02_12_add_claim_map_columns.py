"""Add Claim Map columns to Check, Claim, Evidence

Track B PR-B01: Foundation — purely additive, no existing columns modified.

Revision ID: b01_claim_map_cols
Revises: a280a370fa15
Create Date: 2026-02-12

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b01_claim_map_cols"
down_revision: Union[str, None] = "a280a370fa15"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Check table — entry mode and selection count
    op.add_column("check", sa.Column("entry_mode", sa.String(length=20), nullable=True))
    op.add_column(
        "check", sa.Column("selected_claims_count", sa.Integer(), nullable=True)
    )

    # Claim table — claim map, new taxonomy, article-mode ranking
    op.add_column("claim", sa.Column("claim_map", sa.JSON(), nullable=True))
    op.add_column(
        "claim", sa.Column("new_claim_type", sa.String(length=30), nullable=True)
    )
    op.add_column("claim", sa.Column("significance_rank", sa.Integer(), nullable=True))
    op.add_column("claim", sa.Column("significance_score", sa.Float(), nullable=True))
    op.add_column("claim", sa.Column("is_selected", sa.Boolean(), nullable=True))

    # Evidence table — stable evidence ID
    op.add_column(
        "evidence", sa.Column("evidence_id", sa.String(length=64), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("evidence", "evidence_id")
    op.drop_column("claim", "is_selected")
    op.drop_column("claim", "significance_score")
    op.drop_column("claim", "significance_rank")
    op.drop_column("claim", "new_claim_type")
    op.drop_column("claim", "claim_map")
    op.drop_column("check", "selected_claims_count")
    op.drop_column("check", "entry_mode")
