"""L-01: AgentTransaction table + Check.initiated_via column

Revision ID: l01_agent_transaction
Revises: claim_text_hash
Create Date: 2026-02-27
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "l01_agent_transaction"
down_revision = "claim_text_hash"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # AgentTransaction table
    op.create_table(
        "agent_transaction",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "check_id",
            sa.String(),
            sa.ForeignKey("check.id"),
            nullable=True,
            comment="Null for lookup misses",
        ),
        sa.Column(
            "provider", sa.String(), nullable=False, comment="x402 | skyfire | credit"
        ),
        sa.Column("payer_id", sa.String(), nullable=False),
        sa.Column("tier", sa.String(), nullable=False, comment="lookup | quick | full"),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("transaction_ref", sa.String(), nullable=True),
        sa.Column("idempotency_key", sa.String(), nullable=True),
        sa.Column("request_hash", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("metadata", JSONB, nullable=True),
    )
    op.create_index("ix_agent_transaction_check_id", "agent_transaction", ["check_id"])
    op.create_index("ix_agent_transaction_payer_id", "agent_transaction", ["payer_id"])
    op.create_index(
        "ix_agent_transaction_idempotency_key",
        "agent_transaction",
        ["idempotency_key"],
        unique=True,
    )

    # Check.initiated_via column
    op.add_column(
        "check",
        sa.Column(
            "initiated_via",
            sa.String(20),
            nullable=True,
            comment="dashboard | api_key | agent_x402 | agent_skyfire | agent_credit",
        ),
    )


def downgrade() -> None:
    op.drop_column("check", "initiated_via")
    op.drop_index("ix_agent_transaction_idempotency_key")
    op.drop_index("ix_agent_transaction_payer_id")
    op.drop_index("ix_agent_transaction_check_id")
    op.drop_table("agent_transaction")
