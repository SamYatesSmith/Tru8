"""H-API-06: Webhook registrations table

Revision ID: h_api_06_webhooks
Revises: h_api_01_api_keys
Create Date: 2026-02-25
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "h_api_06_webhooks"
down_revision = "h_api_01_api_keys"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "webhook",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("url", sa.String(2048), nullable=False),
        sa.Column("events", JSONB, nullable=False, server_default="[]"),
        sa.Column("secret", sa.String(64), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("description", sa.String(200), nullable=True),
        sa.Column("last_triggered_at", sa.DateTime(), nullable=True),
        sa.Column("failure_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_webhook_user_id", "webhook", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_webhook_user_id")
    op.drop_table("webhook")
