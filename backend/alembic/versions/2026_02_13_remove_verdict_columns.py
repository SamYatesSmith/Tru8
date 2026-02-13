"""Remove verdict system columns + rename new_claim_type → claim_type

Track B PR-B07: Verdict deletion — drop dead columns from Check and Claim tables.
Rename judge_input_hash → claim_map_input_hash, new_claim_type → claim_type.

Revision ID: b07_remove_verdicts
Revises: b01_claim_map_cols
Create Date: 2026-02-13

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b07_remove_verdicts"
down_revision: Union[str, None] = "b01_claim_map_cols"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ---- Check table: drop verdict-era columns ----
    op.drop_column("check", "decision_trail")
    op.drop_column("check", "transparency_score")
    op.drop_column("check", "overall_summary")
    op.drop_column("check", "credibility_score")
    op.drop_column("check", "claims_supported")
    op.drop_column("check", "claims_contradicted")
    op.drop_column("check", "claims_uncertain")

    # ---- Claim table: drop verdict-era columns ----
    op.drop_column("claim", "verdict")
    op.drop_column("claim", "confidence")
    op.drop_column("claim", "rationale")
    op.drop_column("claim", "claim_type")  # old 4-way taxonomy
    op.drop_column("claim", "is_verifiable")
    op.drop_column("claim", "verifiability_reason")
    op.drop_column("claim", "uncertainty_explanation")
    op.drop_column("claim", "confidence_breakdown")
    op.drop_column("claim", "abstention_reason")
    op.drop_column("claim", "min_requirements_met")
    op.drop_column("claim", "consensus_strength")

    # ---- Claim table: rename columns ----
    op.alter_column("claim", "judge_input_hash", new_column_name="claim_map_input_hash")
    op.alter_column("claim", "new_claim_type", new_column_name="claim_type")


def downgrade() -> None:
    # Reverse renames
    op.alter_column("claim", "claim_type", new_column_name="new_claim_type")
    op.alter_column("claim", "claim_map_input_hash", new_column_name="judge_input_hash")

    # Re-add claim columns
    op.add_column("claim", sa.Column("consensus_strength", sa.Float(), nullable=True))
    op.add_column(
        "claim",
        sa.Column(
            "min_requirements_met", sa.Boolean(), server_default="false", nullable=False
        ),
    )
    op.add_column("claim", sa.Column("abstention_reason", sa.String(), nullable=True))
    op.add_column("claim", sa.Column("confidence_breakdown", sa.JSON(), nullable=True))
    op.add_column(
        "claim", sa.Column("uncertainty_explanation", sa.String(), nullable=True)
    )
    op.add_column(
        "claim", sa.Column("verifiability_reason", sa.String(), nullable=True)
    )
    op.add_column(
        "claim",
        sa.Column("is_verifiable", sa.Boolean(), server_default="true", nullable=False),
    )
    op.add_column("claim", sa.Column("claim_type", sa.String(), nullable=True))
    op.add_column(
        "claim", sa.Column("rationale", sa.String(), nullable=False, server_default="")
    )
    op.add_column(
        "claim", sa.Column("confidence", sa.Float(), nullable=False, server_default="0")
    )
    op.add_column(
        "claim",
        sa.Column("verdict", sa.String(), nullable=False, server_default="pending"),
    )

    # Re-add check columns
    op.add_column(
        "check",
        sa.Column("claims_uncertain", sa.Integer(), server_default="0", nullable=True),
    )
    op.add_column(
        "check",
        sa.Column(
            "claims_contradicted", sa.Integer(), server_default="0", nullable=True
        ),
    )
    op.add_column(
        "check",
        sa.Column("claims_supported", sa.Integer(), server_default="0", nullable=True),
    )
    op.add_column("check", sa.Column("credibility_score", sa.Integer(), nullable=True))
    op.add_column("check", sa.Column("overall_summary", sa.String(), nullable=True))
    op.add_column("check", sa.Column("transparency_score", sa.Float(), nullable=True))
    op.add_column("check", sa.Column("decision_trail", sa.JSON(), nullable=True))
