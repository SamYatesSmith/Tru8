"""Retained extraction windows alongside derived evidence text."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "text_provenance"
down_revision = "research_operations"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("evidence", sa.Column("text_provenance", JSONB, nullable=True))


def downgrade():
    op.drop_column("evidence", "text_provenance")
