"""add_overall_summary_fields

Adds overall summary and credibility scoring fields to Check table for:
- LLM-generated executive summary of all claims
- Overall credibility score (0-100)
- Claim verdict counts (supported, contradicted, uncertain)

Revision ID: 0baaddca9c24
Revises: ccb08c180d36
Create Date: 2025-10-25 16:07:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0baaddca9c24'
down_revision: Union[str, None] = 'ccb08c180d36'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ========== CHECK TABLE UPDATES ==========
    # Overall Summary & Credibility Scoring

    op.add_column('check', sa.Column('overall_summary', sa.Text(), nullable=True))
    op.add_column('check', sa.Column('credibility_score', sa.Integer(), nullable=True))
    op.add_column('check', sa.Column('claims_supported', sa.Integer(), server_default='0', nullable=False))
    op.add_column('check', sa.Column('claims_contradicted', sa.Integer(), server_default='0', nullable=False))
    op.add_column('check', sa.Column('claims_uncertain', sa.Integer(), server_default='0', nullable=False))


def downgrade() -> None:
    # Remove Check table columns
    op.drop_column('check', 'claims_uncertain')
    op.drop_column('check', 'claims_contradicted')
    op.drop_column('check', 'claims_supported')
    op.drop_column('check', 'credibility_score')
    op.drop_column('check', 'overall_summary')
