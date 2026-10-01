"""Add User.heard_about — the self-reported "How did you hear about us?".

ACE Stage 4 (2026-10-01). Complements signup_source (a ?src= tag), which is
empty for word-of-mouth arrivals. Asked once, optionally, on the dashboard
first run. NULL = not yet asked; "skipped" = dismissed. No backfill.

Revision ID: heard_about
Revises: text_provenance
Create Date: 2026-10-01
"""

from alembic import op
import sqlalchemy as sa

revision = "heard_about"
down_revision = "text_provenance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("user", sa.Column("heard_about", sa.String(32), nullable=True))
    op.add_column(
        "user", sa.Column("heard_about_detail", sa.String(200), nullable=True)
    )
    op.add_column("user", sa.Column("heard_about_at", sa.DateTime(), nullable=True))
    op.create_index("ix_user_heard_about", "user", ["heard_about"])


def downgrade() -> None:
    op.drop_index("ix_user_heard_about", table_name="user")
    op.drop_column("user", "heard_about_at")
    op.drop_column("user", "heard_about_detail")
    op.drop_column("user", "heard_about")
