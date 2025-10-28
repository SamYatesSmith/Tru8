"""add_unknown_source_tracking

Revision ID: 871f08e9f196
Revises: add_claim_context_fields
Create Date: 2025-10-28 13:15:05.626052+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '871f08e9f196'
down_revision: Union[str, None] = 'add_claim_context_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create unknown_source table for progressive curation
    op.create_table('unknown_source',
    sa.Column('id', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('domain', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('full_url', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('claim_topic', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('evidence_title', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('evidence_snippet', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('frequency', sa.Integer(), nullable=False),
    sa.Column('first_seen', sa.DateTime(), nullable=False),
    sa.Column('last_seen', sa.DateTime(), nullable=False),
    sa.Column('reviewed', sa.Boolean(), nullable=False),
    sa.Column('added_to_credibility_list', sa.Boolean(), nullable=False),
    sa.Column('review_notes', sa.JSON(), nullable=True),
    sa.Column('assigned_tier', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('assigned_credibility', sa.Float(), nullable=True),
    sa.Column('has_https', sa.Boolean(), nullable=False),
    sa.Column('has_author_byline', sa.Boolean(), nullable=True),
    sa.Column('has_primary_sources', sa.Boolean(), nullable=True),
    sa.Column('domain_age_years', sa.Integer(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_unknown_source_domain'), 'unknown_source', ['domain'], unique=False)


def downgrade() -> None:
    # Drop unknown_source table
    op.drop_index(op.f('ix_unknown_source_domain'), table_name='unknown_source')
    op.drop_table('unknown_source')