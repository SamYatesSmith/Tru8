"""Add billing_interval to subscription (monthly vs annual).

Console annual (£200/yr) and monthly (£20/mo) both map to plan 'console' with
200 credits/month; nothing recorded the billing cadence, so the dashboard
showed "£20/month" to annual subscribers. This column lets the API state the
cadence ('month' | 'year') so the frontend can render the correct price. The
annual allowance itself now refreshes monthly via a computed window in
usage_ledger.get_usage_snapshot (no data change needed here).

Existing rows (all monthly today; annual is test-mode only, no live rows)
default to 'month' via server_default.

Revision ID: billing_interval
Revises: usage_events
Create Date: 2026-07-13
"""

from alembic import op
import sqlalchemy as sa

revision = "billing_interval"
down_revision = "usage_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "subscription",
        sa.Column(
            "billing_interval",
            sa.String(length=16),
            nullable=False,
            server_default="month",
        ),
    )


def downgrade() -> None:
    op.drop_column("subscription", "billing_interval")
