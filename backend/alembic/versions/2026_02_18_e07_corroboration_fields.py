"""E07: Add corroboration metadata fields to Evidence

Add corroboration_group_id and corroborating_evidence_ids columns
for structural corroboration tracking (Cartographer convergence zones).

Revision ID: e07_corroboration_fields
Revises: e06_evidence_classification
Create Date: 2026-02-18

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e07_corroboration_fields"
down_revision: Union[str, None] = "e06_evidence_classification"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "evidence",
        sa.Column("corroboration_group_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "evidence",
        sa.Column("corroborating_evidence_ids", sa.String(500), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("evidence", "corroborating_evidence_ids")
    op.drop_column("evidence", "corroboration_group_id")
