"""Rename cents columns to pence (USD→GBP currency alignment).

Revision ID: rename_cents_pence
Revises: bf5412c4e2a0
Create Date: 2026-03-24
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "rename_cents_pence"
down_revision: Union[str, None] = "bf5412c4e2a0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "user", "credit_balance_cents", new_column_name="credit_balance_pence"
    )
    op.alter_column("agent_transaction", "amount_cents", new_column_name="amount_pence")


def downgrade() -> None:
    op.alter_column(
        "user", "credit_balance_pence", new_column_name="credit_balance_cents"
    )
    op.alter_column("agent_transaction", "amount_pence", new_column_name="amount_cents")
