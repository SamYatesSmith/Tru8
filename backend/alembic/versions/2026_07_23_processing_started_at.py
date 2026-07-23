"""Add processing_started_at to check (hang-proofing boot sweep, W2).

The boot-time stale sweep fails+refunds rows stuck 'processing' longer than
the watchdog ceiling. created_at is the wrong clock for article checks: they
pause at waiting_for_selection (durable) and phase 2 may start hours later —
ageing those from created_at would kill legitimate fresh phase-2 runs. This
column records when the CURRENT processing run started: set on row creation,
refreshed when phase 2 flips status back to 'processing'.

Nullable + additive: pre-migration rows stay NULL and the sweep COALESCEs to
created_at (correct for them — any pre-migration row still 'processing' at
boot is a stranding, e.g. check 46406547 from the 2026-07-23 OOM).

Design: audit/2026-07-23_hang_proofing_design.md.

Revision ID: processing_started_at
Revises: claim_type_hint
Create Date: 2026-07-23
"""

from alembic import op
import sqlalchemy as sa

revision = "processing_started_at"
down_revision = "claim_type_hint"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "check",
        sa.Column("processing_started_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("check", "processing_started_at")
