"""Add User.signup_source — WHY the person came, not HOW a check arrived.

Engineering half of the distribution plan (audit/OUTREACH.md): outreach links
carry ?src=<tag>; the frontend stores the first-touch tag and flushes it once
after signup; this column receives it exactly once. Check.client already
records the transport surface (web/mcp) and is deliberately untouched — the
two answer different questions.

NO backfill, on purpose. Every pre-existing row stays NULL, and NULL is
reported as "(unknown)" — never coerced to "direct". At this account count a
fabricated attribution would kill the wrong channel.

Revision ID: signup_source
Revises: claim_consensus_repair
Create Date: 2026-08-11
"""

from alembic import op
import sqlalchemy as sa

revision = "signup_source"
down_revision = "claim_consensus_repair"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user",
        sa.Column("signup_source", sa.String(64), nullable=True),
    )
    op.add_column(
        "user",
        sa.Column("signup_source_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_user_signup_source", "user", ["signup_source"])


def downgrade() -> None:
    op.drop_index("ix_user_signup_source", table_name="user")
    op.drop_column("user", "signup_source_at")
    op.drop_column("user", "signup_source")
