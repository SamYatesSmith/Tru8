"""Add total_search_results to Check

Revision ID: bf5412c4e2a0
Revises: m06_claim_consensus
Create Date: 2026-03-10 12:29:03.898807+00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "bf5412c4e2a0"
down_revision: Union[str, None] = "m06_claim_consensus"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "check", sa.Column("total_search_results", sa.Integer(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("check", "total_search_results")
