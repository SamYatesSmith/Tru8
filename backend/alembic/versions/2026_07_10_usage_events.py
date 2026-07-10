"""Usage ledger — usage_events table + backfill (single source of truth).

Fixes the split-ledger defect where subscriber re-searches/top-ups were
validated against the monthly limit but never counted toward it (deducts
wrote User counters; subscriber usage summed Check rows). From this
revision, every dashboard debit and refund is an append-only event and all
entitlement reads sum this table.

Backfill:
  1. One 'check' debit event per existing Check with credits_used > 0
     (created_at copied) — subscriber period sums are identical before and
     after by construction.
  2. Per-user 'adjustment' event for total_credits_used minus the user's
     backfilled debits — preserves historical re-search debits that only
     ever lived in the User counter, so trial usage numbers do not move.
     Backdated to the user's created_at so it can never land inside an
     active subscriber's current billing period.
  Backfilled events carry drew_trial=false: for a check in flight during
  this deploy that later fails, a trial user's refund restores net headroom
  rather than +1 — a one-deploy transient edge, accepted in the design.

Design: audit/2026-07-10_usage_ledger_design.md (founder-approved 2026-07-10).

Revision ID: usage_events
Revises: date_basis
Create Date: 2026-07-10
"""

import uuid
from datetime import datetime

from alembic import op
import sqlalchemy as sa

revision = "usage_events"
down_revision = "date_basis"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "usage_events",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("check_id", sa.String(), sa.ForeignKey("check.id"), nullable=True),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("credits", sa.Integer(), nullable=False),
        sa.Column(
            "drew_trial",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_usage_events_user_created",
        "usage_events",
        ["user_id", "created_at"],
    )
    # DB-level idempotency: at most one creation debit and one refund per
    # check. Re-search/top-up events are unbounded per check (correct).
    op.create_index(
        "ux_usage_events_check_kind",
        "usage_events",
        ["check_id", "kind"],
        unique=True,
        postgresql_where=sa.text("kind IN ('check', 'refund')"),
        sqlite_where=sa.text("kind IN ('check', 'refund')"),
    )

    bind = op.get_bind()

    # Step 1 — debit event per surviving check debit.
    checks = bind.execute(
        sa.text(
            'SELECT id, user_id, credits_used, created_at FROM "check" '
            "WHERE credits_used > 0"
        )
    ).fetchall()

    insert = sa.text(
        "INSERT INTO usage_events "
        "(id, user_id, check_id, kind, credits, drew_trial, created_at) "
        "VALUES (:id, :user_id, :check_id, :kind, :credits, :drew_trial, "
        ":created_at)"
    )

    debits_per_user: dict = {}
    for row in checks:
        bind.execute(
            insert,
            {
                "id": str(uuid.uuid4()),
                "user_id": row.user_id,
                "check_id": row.id,
                "kind": "check",
                "credits": row.credits_used,
                "drew_trial": False,
                "created_at": row.created_at,
            },
        )
        debits_per_user[row.user_id] = (
            debits_per_user.get(row.user_id, 0) + row.credits_used
        )

    # Step 2 — per-user reconciliation of the legacy lifetime counter.
    # The adjustment is BACKDATED to the user's created_at (verifier defect
    # 2026-07-10): stamped at migration time it would land inside an active
    # subscriber's current billing period and inflate their meter with
    # prior-period activity. created_at precedes any possible period_start,
    # and lifetime (trial) sums are date-independent, so parity holds for
    # both window shapes.
    users = bind.execute(
        sa.text('SELECT id, total_credits_used, created_at FROM "user"')
    ).fetchall()
    fallback = datetime(2000, 1, 1)
    for row in users:
        delta = (row.total_credits_used or 0) - debits_per_user.get(row.id, 0)
        if delta > 0:
            bind.execute(
                insert,
                {
                    "id": str(uuid.uuid4()),
                    "user_id": row.id,
                    "check_id": None,
                    "kind": "adjustment",
                    "credits": delta,
                    "drew_trial": False,
                    "created_at": row.created_at or fallback,
                },
            )


def downgrade() -> None:
    op.drop_index("ux_usage_events_check_kind", table_name="usage_events")
    op.drop_index("ix_usage_events_user_created", table_name="usage_events")
    op.drop_table("usage_events")
