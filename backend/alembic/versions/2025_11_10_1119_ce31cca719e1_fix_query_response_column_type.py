"""fix_query_response_column_type

Revision ID: ce31cca719e1
Revises: a1b2c3d4e5f6
Create Date: 2025-11-10 11:19:43.865274+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ce31cca719e1'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Change query_response from TEXT to VARCHAR to match SQLModel schema
    op.alter_column('check', 'query_response',
                    type_=sa.String(),
                    existing_type=sa.Text(),
                    existing_nullable=True)


def downgrade() -> None:
    # Revert query_response back to TEXT
    op.alter_column('check', 'query_response',
                    type_=sa.Text(),
                    existing_type=sa.String(),
                    existing_nullable=True)