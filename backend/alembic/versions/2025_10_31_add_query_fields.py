"""add_query_fields

Adds Search Clarity feature fields to Check table

Revision ID: a1b2c3d4e5f6
Revises: 954dd02c2ec1
Create Date: 2025-10-31 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
import sqlmodel

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '954dd02c2ec1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add Search Clarity fields to Check table
    op.add_column('check', sa.Column('user_query', sa.String(200), nullable=True))
    op.add_column('check', sa.Column('query_response', sa.Text(), nullable=True))
    op.add_column('check', sa.Column('query_confidence', sa.Float(), nullable=True))
    op.add_column('check', sa.Column('query_sources', sa.JSON(), nullable=True))  # JSON column


def downgrade() -> None:
    op.drop_column('check', 'query_sources')
    op.drop_column('check', 'query_confidence')
    op.drop_column('check', 'query_response')
    op.drop_column('check', 'user_query')
