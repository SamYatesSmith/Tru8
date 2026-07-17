"""Add type_hint to claim (Phase 1a extraction hint, persisted).

The 1a extraction reframe emits type_hint="normative" on retained
main-predicate opinion claims, but only in memory + SSE. The hinted flow
ALWAYS takes the selection pause (confirm step, D5), and the phase-2 resume
reloads claims from the DB — so without persistence the §20 slice-2 opinion
grounds stage could never trigger (its gate reads claim.type_hint). Also the
root fix for carried NIT-4 (typeHint lost on page refresh).

Nullable + additive: flag off → extract emits no hint → column stays NULL and
nothing reads it. Existing rows NULL.

Revision ID: claim_type_hint
Revises: billing_interval
Create Date: 2026-07-17
"""

from alembic import op
import sqlalchemy as sa

revision = "claim_type_hint"
down_revision = "billing_interval"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "claim",
        sa.Column("type_hint", sa.String(length=16), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("claim", "type_hint")
