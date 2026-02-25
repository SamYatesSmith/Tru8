"""H-API-01: Add api_key table for agent/developer authentication

API keys provide a simpler auth path than Clerk JWT for programmatic
access. Keys are hashed (SHA-256) before storage; the raw key is only
returned once at creation time.

Revision ID: h_api_01_api_keys
Revises: f10_archived_url
Create Date: 2026-02-25

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "h_api_01_api_keys"
down_revision: Union[str, None] = "f10_archived_url"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "api_key",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("key_hash", sa.String(), nullable=False),
        sa.Column("key_prefix", sa.String(16), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
        sa.Column("usage_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_api_key_key_hash", "api_key", ["key_hash"])
    op.create_index("ix_api_key_user_id", "api_key", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_api_key_user_id", table_name="api_key")
    op.drop_index("ix_api_key_key_hash", table_name="api_key")
    op.drop_table("api_key")
