"""Add Check.client — first-party client attribution (MCP usage tracking).

Records which first-party client submitted a check, derived from the
``X-Tru8-Client`` request header (e.g. ``mcp/1.0.1`` -> ``mcp``). Kept
separate from ``initiated_via`` because services/consensus.py filters
``initiated_via`` with an exact-match IN-list; a suffix there would have
silently dropped MCP checks from consensus computation.

NULL for all pre-existing rows and for ordinary dashboard / raw-API traffic.
Indexed for cheap "usage by client" aggregation.

Revision ID: client_origin
Revises: classification_method_64
Create Date: 2026-06-10
"""

from alembic import op
import sqlalchemy as sa

revision = "client_origin"
down_revision = "classification_method_64"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "check",
        sa.Column("client", sa.String(32), nullable=True),
    )
    op.create_index("ix_check_client", "check", ["client"])


def downgrade() -> None:
    op.drop_index("ix_check_client", table_name="check")
    op.drop_column("check", "client")
