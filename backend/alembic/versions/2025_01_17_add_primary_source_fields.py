"""add_primary_source_fields

Add fields for primary source detection (Tier 1 Improvement):
- is_primary_source: Boolean flag for original research/gov data/legal docs
- primary_indicators: JSONB array of detected indicators

Revision ID: tier1_primary_source
Revises: cb8643f82fb6
Create Date: 2025-01-17 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = 'tier1_primary_source'
down_revision: Union[str, None] = 'cb8643f82fb6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add primary source detection fields to Evidence table."""

    # Add is_primary_source boolean field
    op.add_column(
        'evidence',
        sa.Column(
            'is_primary_source',
            sa.Boolean(),
            server_default='false',
            nullable=False,
            comment='True if evidence is original research, government data, or official report'
        )
    )

    # Add primary_indicators JSONB field
    op.add_column(
        'evidence',
        sa.Column(
            'primary_indicators',
            JSONB,
            nullable=True,
            comment='JSON array of primary source indicators detected (e.g., ["academic_journal", "peer_reviewed"])'
        )
    )


def downgrade() -> None:
    """Remove primary source detection fields from Evidence table."""

    op.drop_column('evidence', 'primary_indicators')
    op.drop_column('evidence', 'is_primary_source')
