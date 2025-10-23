"""add_phase3_credibility_framework_and_abstention_logic

Phase 3 - Critical Credibility Enhancements:
- Domain Credibility Framework fields (Evidence table)
- Consensus & Abstention Logic fields (Claim table)

Revision ID: ccb08c180d36
Revises: 06b51a7c2d88
Create Date: 2025-10-21 11:15:51.580755+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'ccb08c180d36'
down_revision: Union[str, None] = '06b51a7c2d88'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ========== CLAIM TABLE UPDATES ==========
    # Consensus & Abstention Logic (Phase 3, Week 8)

    op.add_column('claim', sa.Column('abstention_reason', sa.Text(), nullable=True))
    op.add_column('claim', sa.Column('min_requirements_met', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('claim', sa.Column('consensus_strength', sa.Float(), nullable=True))

    # ========== EVIDENCE TABLE UPDATES ==========
    # Domain Credibility Framework (Phase 3, Week 9)

    op.add_column('evidence', sa.Column('tier', sa.Text(), nullable=True))
    op.add_column('evidence', sa.Column('risk_flags', postgresql.JSON(astext_type=sa.Text()), nullable=True))
    op.add_column('evidence', sa.Column('credibility_reasoning', sa.Text(), nullable=True))
    op.add_column('evidence', sa.Column('risk_level', sa.Text(), nullable=True))
    op.add_column('evidence', sa.Column('risk_warning', sa.Text(), nullable=True))


def downgrade() -> None:
    # Remove Evidence table columns
    op.drop_column('evidence', 'risk_warning')
    op.drop_column('evidence', 'risk_level')
    op.drop_column('evidence', 'credibility_reasoning')
    op.drop_column('evidence', 'risk_flags')
    op.drop_column('evidence', 'tier')

    # Remove Claim table columns
    op.drop_column('claim', 'consensus_strength')
    op.drop_column('claim', 'min_requirements_met')
    op.drop_column('claim', 'abstention_reason')