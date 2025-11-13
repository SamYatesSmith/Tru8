"""Add Government API fields to Evidence and Check tables

⚠️ IMPORTANT: This migration creates Evidence.metadata which conflicts
with SQLAlchemy's reserved 'metadata' attribute. This is fixed in the
next migration (595bc2ddd5c5) which renames it to api_metadata.

Always apply both migrations together using: alembic upgrade head

See: alembic/versions/README_PHASE5_MIGRATIONS.md

Revision ID: 2025012_gov_api
Revises: f53f987eedde
Create Date: 2025-01-12

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '2025012_gov_api'
down_revision = 'f53f987eedde'  # Add legal_metadata field to claims
branch_labels = None
depends_on = None


def upgrade():
    """Add fields for Government API integration"""

    # 1. Add metadata JSONB to Evidence table
    op.add_column('evidence',
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True)
    )

    # 2. Add external_source_provider to Evidence table
    op.add_column('evidence',
        sa.Column('external_source_provider', sa.String(200), nullable=True)
    )

    # 3. Add API tracking fields to Check table
    op.add_column('check',
        sa.Column('api_sources_used', postgresql.JSONB(astext_type=sa.Text()), nullable=True)
    )
    op.add_column('check',
        sa.Column('api_call_count', sa.Integer(), nullable=True, server_default='0')
    )
    op.add_column('check',
        sa.Column('api_coverage_percentage', sa.Numeric(5, 2), nullable=True)
    )


def downgrade():
    """Remove Government API fields"""

    # Remove Check table columns
    op.drop_column('check', 'api_coverage_percentage')
    op.drop_column('check', 'api_call_count')
    op.drop_column('check', 'api_sources_used')

    # Remove Evidence table columns
    op.drop_column('evidence', 'external_source_provider')
    op.drop_column('evidence', 'metadata')
