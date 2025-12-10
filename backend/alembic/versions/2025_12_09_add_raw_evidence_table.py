"""Add RawEvidence table and raw_sources_count field for Full Sources List Pro feature

Revision ID: b7c8d9e0f1a2
Revises: 12c6bf45de11
Create Date: 2025-12-09

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = 'b7c8d9e0f1a2'
down_revision = '12c6bf45de11'
branch_labels = None
depends_on = None


def table_exists(table_name):
    """Check if a table exists in the database."""
    bind = op.get_bind()
    inspector = inspect(bind)
    return table_name in inspector.get_table_names()


def column_exists(table_name, column_name):
    """Check if a column exists in a table."""
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def index_exists(table_name, index_name):
    """Check if an index exists on a table."""
    bind = op.get_bind()
    inspector = inspect(bind)
    indexes = [idx['name'] for idx in inspector.get_indexes(table_name)]
    return index_name in indexes


def upgrade():
    # Add raw_sources_count to Check table (if not exists)
    if not column_exists('check', 'raw_sources_count'):
        op.add_column('check', sa.Column('raw_sources_count', sa.Integer(), nullable=True, server_default='0'))

    # Create RawEvidence table (if not exists - may have been auto-created by SQLModel)
    if not table_exists('rawevidence'):
        op.create_table(
            'rawevidence',
            sa.Column('id', sa.String(), nullable=False),
            sa.Column('check_id', sa.String(), nullable=False),
            sa.Column('claim_position', sa.Integer(), nullable=False),
            sa.Column('claim_text', sa.String(length=500), nullable=True),
            sa.Column('source', sa.String(), nullable=False),
            sa.Column('url', sa.String(), nullable=False),
            sa.Column('title', sa.String(), nullable=False),
            sa.Column('snippet', sa.Text(), nullable=False),
            sa.Column('published_date', sa.DateTime(), nullable=True),
            sa.Column('relevance_score', sa.Float(), nullable=False, server_default='0.0'),
            sa.Column('credibility_score', sa.Float(), nullable=False, server_default='0.6'),
            sa.Column('is_included', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('filter_stage', sa.String(), nullable=True),
            sa.Column('filter_reason', sa.String(), nullable=True),
            sa.Column('tier', sa.String(), nullable=True),
            sa.Column('is_factcheck', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('external_source_provider', sa.String(length=200), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['check_id'], ['check.id'], ondelete='CASCADE'),
        )

    # Create index on check_id for fast lookups (if not exists)
    if table_exists('rawevidence') and not index_exists('rawevidence', 'ix_rawevidence_check_id'):
        op.create_index('ix_rawevidence_check_id', 'rawevidence', ['check_id'])


def downgrade():
    # Drop RawEvidence table
    op.drop_index('ix_rawevidence_check_id', table_name='rawevidence')
    op.drop_table('rawevidence')

    # Remove raw_sources_count from Check table
    op.drop_column('check', 'raw_sources_count')
