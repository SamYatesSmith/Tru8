"""L-07: Add credit_balance_cents to User model.

Revision ID: l07_credit_balance
Revises: l01_agent_transaction
Create Date: 2026-02-27
"""

from alembic import op
import sqlalchemy as sa

revision = "l07_credit_balance"
down_revision = "l01_agent_transaction"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user",
        sa.Column(
            "credit_balance_cents",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    op.drop_column("user", "credit_balance_cents")
