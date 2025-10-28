"""Add context preservation fields to claims

Adds context preservation fields to Claim table for improved evidence retrieval:
- subject_context: Main subject/topic of the claim
- key_entities: JSON array of key entities mentioned
- source_title: Title of source article
- source_url: URL of source article

Revision ID: add_claim_context_fields
Revises: 0baaddca9c24
Create Date: 2025-10-27

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON

# revision identifiers, used by Alembic.
revision = 'add_claim_context_fields'
down_revision = '0baaddca9c24'
branch_labels = None
depends_on = None

def upgrade():
    # Add context preservation fields to claim table
    op.add_column('claim', sa.Column('subject_context', sa.String(), nullable=True))
    op.add_column('claim', sa.Column('key_entities', JSON, nullable=True))
    op.add_column('claim', sa.Column('source_title', sa.String(), nullable=True))
    op.add_column('claim', sa.Column('source_url', sa.String(), nullable=True))

def downgrade():
    # Remove context fields
    op.drop_column('claim', 'source_url')
    op.drop_column('claim', 'source_title')
    op.drop_column('claim', 'key_entities')
    op.drop_column('claim', 'subject_context')
