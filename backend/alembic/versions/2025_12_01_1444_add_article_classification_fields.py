"""add_article_classification_fields

Revision ID: add_article_classification
Revises: c165e729198b
Create Date: 2025-12-01 14:44:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = 'add_article_classification'
down_revision: Union[str, None] = 'c165e729198b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Article Classification fields (LLM-based, runs once per check)
    op.add_column('check', sa.Column('article_domain', sa.String(50), nullable=True))
    op.add_column('check', sa.Column('article_secondary_domains', JSONB, nullable=True))
    op.add_column('check', sa.Column('article_jurisdiction', sa.String(20), nullable=True))
    op.add_column('check', sa.Column('article_classification_confidence', sa.Float(), nullable=True))
    op.add_column('check', sa.Column('article_classification_source', sa.String(30), nullable=True))


def downgrade() -> None:
    op.drop_column('check', 'article_classification_source')
    op.drop_column('check', 'article_classification_confidence')
    op.drop_column('check', 'article_jurisdiction')
    op.drop_column('check', 'article_secondary_domains')
    op.drop_column('check', 'article_domain')
