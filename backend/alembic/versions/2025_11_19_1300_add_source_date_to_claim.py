"""add_source_date_to_claim

Add source_date field to Claim table for article publication date context.
Part of Article Context Propagation Enhancement (Phase 1.2).

Revision ID: add_source_date_claim
Revises: c78bee2049c5
Create Date: 2025-11-19 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_source_date_claim'
down_revision: Union[str, None] = 'c78bee2049c5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add source_date field to Claim table."""

    op.add_column(
        'claim',
        sa.Column(
            'source_date',
            sa.String(),
            nullable=True,
            comment='Publication date of source article'
        )
    )


def downgrade() -> None:
    """Remove source_date field from Claim table."""

    op.drop_column('claim', 'source_date')
