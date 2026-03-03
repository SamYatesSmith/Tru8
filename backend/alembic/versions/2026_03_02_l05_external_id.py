"""L-05: Add external_id to User for wallet / Skyfire identity mapping.

Revision ID: l05_external_id
Revises: l07_credit_balance
Create Date: 2026-03-02
"""

from alembic import op
import sqlalchemy as sa

revision = "l05_external_id"
down_revision = "l07_credit_balance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("user", sa.Column("external_id", sa.String(100), nullable=True))
    op.create_unique_constraint("uq_user_external_id", "user", ["external_id"])
    op.create_index("ix_user_external_id", "user", ["external_id"])


def downgrade() -> None:
    op.drop_index("ix_user_external_id", table_name="user")
    op.drop_constraint("uq_user_external_id", "user", type_="unique")
    op.drop_column("user", "external_id")
