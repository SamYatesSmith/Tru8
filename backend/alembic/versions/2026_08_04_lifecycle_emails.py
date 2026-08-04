"""Add lifecycle-email preference and exactly-once markers to user.

Funnel work: a welcome email on first arrival, and a "free checks used up"
email when the trial is spent. Both need a marker so they can fire exactly
once, and the class needs its own opt-out.

Why NOT reuse email_marketing: it defaults to False, so gating on it would
ship the feature dark for every user. email_lifecycle defaults True and is
honoured alongside the global email_notifications_enabled switch.

THE BACKFILLS ARE THE POINT OF THIS MIGRATION, not the DDL. Without them
the deploy mails the entire existing user base:

  - welcome_email_sent_at := created_at for every existing row, so nobody
    already using Tru8 is "welcomed" on their next dashboard load.
  - trial_exhausted_email_sent_at := now() for every existing user who is
    already at or over their trial allowance, so the deploy does not blast
    the historical exhausted cohort with an upgrade pitch they never asked
    for. Reactivating that cohort is a separate, deliberate decision.

The exhaustion backfill mirrors usage_ledger.get_usage_snapshot's trial
branch: usage is the lifetime ledger sum, limit is
max(3, credits + total_credits_used). Users with an active subscription are
excluded because they are not on the trial path at all.

Design: audit/2026-08-04_funnel_lifecycle_emails_design.md

Revision ID: lifecycle_emails
Revises: processing_started_at
Create Date: 2026-08-04
"""

from alembic import op
import sqlalchemy as sa

revision = "lifecycle_emails"
down_revision = "processing_started_at"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user",
        sa.Column(
            "email_lifecycle",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )
    op.add_column(
        "user",
        sa.Column("welcome_email_sent_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "user",
        sa.Column("trial_exhausted_email_sent_at", sa.DateTime(), nullable=True),
    )

    # Backfill 1 — every existing user counts as already welcomed.
    op.execute(
        """
        UPDATE "user"
           SET welcome_email_sent_at = created_at
         WHERE welcome_email_sent_at IS NULL
        """
    )

    # Backfill 2 — suppress the exhaustion email for anyone already spent.
    # GREATEST(3, credits + total_credits_used) mirrors the trial limit
    # formula in usage_ledger.get_usage_snapshot.
    op.execute(
        """
        UPDATE "user" u
           SET trial_exhausted_email_sent_at = NOW() AT TIME ZONE 'utc'
         WHERE u.trial_exhausted_email_sent_at IS NULL
           AND NOT EXISTS (
                 SELECT 1 FROM subscription s
                  WHERE s.user_id = u.id
                    AND s.status IN ('active', 'trialing')
               )
           AND COALESCE(
                 (SELECT SUM(ue.credits) FROM usage_events ue
                   WHERE ue.user_id = u.id), 0
               ) >= GREATEST(3, u.credits + u.total_credits_used)
        """
    )


def downgrade() -> None:
    op.drop_column("user", "trial_exhausted_email_sent_at")
    op.drop_column("user", "welcome_email_sent_at")
    op.drop_column("user", "email_lifecycle")
