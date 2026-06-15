"""Add Check.cost_telemetry — per-check COGS telemetry (P1).

Stores raw LLM token counts (by captured stage), web-search / API-adapter RESULT
counts (not query counts), timing, and a PARTIAL derived estimated_cost_usd. The
raw counts are the ground truth for the P5 pricing decision; the cost estimate is
recomputable from them. See app/core/cost_constants.py for the two known
coverage limitations.

NULL for all pre-existing rows. No index — not queried by value yet; add a GIN
index later if aggregation needs it.

Revision ID: cost_telemetry
Revises: client_origin
Create Date: 2026-06-15
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "cost_telemetry"
down_revision = "client_origin"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "check",
        sa.Column("cost_telemetry", postgresql.JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("check", "cost_telemetry")
