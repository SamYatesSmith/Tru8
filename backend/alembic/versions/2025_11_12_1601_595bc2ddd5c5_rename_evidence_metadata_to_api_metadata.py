"""Rename Evidence.metadata to Evidence.api_metadata

Fixes SQLAlchemy reserved name conflict from previous migration.

The column 'metadata' conflicts with SQLAlchemy's table metadata attribute,
causing runtime errors. This migration renames it to 'api_metadata'.

This is a corrective migration for Phase 5 API integration.

See: alembic/versions/README_PHASE5_MIGRATIONS.md

Revision ID: 595bc2ddd5c5
Revises: 2025012_gov_api
Create Date: 2025-11-12 16:01:21.163833+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '595bc2ddd5c5'
down_revision: Union[str, None] = '2025012_gov_api'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Rename Evidence.metadata to Evidence.api_metadata to avoid SQLAlchemy reserved name conflict"""
    op.alter_column('evidence', 'metadata', new_column_name='api_metadata')


def downgrade() -> None:
    """Revert Evidence.api_metadata back to Evidence.metadata"""
    op.alter_column('evidence', 'api_metadata', new_column_name='metadata')