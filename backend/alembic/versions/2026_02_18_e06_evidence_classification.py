"""E06: Add evidence classification fields, drop NLI columns

Add tier/type classification, receipt tracking, and exclusion reason
fields to Evidence table. Drop unused NLI fields.

Revision ID: e06_evidence_classification
Revises: b07_remove_verdicts
Create Date: 2026-02-18

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e06_evidence_classification"
down_revision: Union[str, None] = "b07_remove_verdicts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ---- Evidence table: add classification + receipt fields ----
    op.add_column(
        "evidence",
        sa.Column("evidence_type", sa.String(30), nullable=True),
    )
    op.add_column(
        "evidence",
        sa.Column("receipt_status", sa.String(20), nullable=True),
    )
    op.add_column(
        "evidence",
        sa.Column("exclusion_reason", sa.String(30), nullable=True),
    )

    # ---- Evidence table: drop unused NLI columns ----
    op.drop_column("evidence", "nli_stance")
    op.drop_column("evidence", "nli_confidence")
    op.drop_column("evidence", "nli_entailment")
    op.drop_column("evidence", "nli_contradiction")


def downgrade() -> None:
    # Re-add NLI columns
    op.add_column("evidence", sa.Column("nli_contradiction", sa.Float(), nullable=True))
    op.add_column("evidence", sa.Column("nli_entailment", sa.Float(), nullable=True))
    op.add_column("evidence", sa.Column("nli_confidence", sa.Float(), nullable=True))
    op.add_column("evidence", sa.Column("nli_stance", sa.String(), nullable=True))

    # Drop new columns
    op.drop_column("evidence", "exclusion_reason")
    op.drop_column("evidence", "receipt_status")
    op.drop_column("evidence", "evidence_type")
