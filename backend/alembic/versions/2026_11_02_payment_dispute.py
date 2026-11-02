"""payment_dispute table — one row per Stripe dispute (2026-11-02).

An account is on payment hold while it has any dispute not resolved in our
favour. Design + review: audit/2026-11-02_payment_hold_design.md. The model
is exported from app/models/__init__.py so a fresh-database bootstrap
(create_all + stamp head) creates it too — the M-06 failure mode.

Revision ID: payment_dispute
Revises: video_text_unescape
Create Date: 2026-11-02
"""

from alembic import op
import sqlalchemy as sa

revision = "payment_dispute"
down_revision = "video_text_unescape"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "payment_dispute",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("charge_id", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("reason", sa.String(64), nullable=True),
        sa.Column("amount", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(8), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_payment_dispute_user_id", "payment_dispute", ["user_id"])
    op.create_index("ix_payment_dispute_charge_id", "payment_dispute", ["charge_id"])


def downgrade() -> None:
    op.drop_index("ix_payment_dispute_charge_id", table_name="payment_dispute")
    op.drop_index("ix_payment_dispute_user_id", table_name="payment_dispute")
    op.drop_table("payment_dispute")
