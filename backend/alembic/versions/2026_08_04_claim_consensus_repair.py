"""Create claim_consensus if it is missing (repair for stamped-past databases).

The table has a migration already — m06_claim_consensus (2026-03-09) — and that
migration is correct. It simply never ran on databases that were bootstrapped
rather than migrated.

HOW A CORRECT MIGRATION GETS SKIPPED FOREVER
--------------------------------------------
entrypoint.sh bootstraps a fresh database like this:

    from app.models import *                 # only what __init__.py exports
    SQLModel.metadata.create_all             # so: only the exported models
    alembic stamp head                       # "everything is applied"

ClaimConsensus was never exported from app/models/__init__.py, so create_all
did not build it — and the stamp then told Alembic that m06_claim_consensus had
already been applied. The table could not be created by either route again.

WHAT IT COST
------------
Every /agent request at quick or full tier calls session.get(ClaimConsensus,...).
That raised UndefinedTableError, which api/v1/agent.py swallowed at DEBUG
WITHOUT rolling back, leaving the session aborted. The next statement — the
credit debit — then failed with InFailedSQLTransactionError, so the 500 surfaced
in Sentry pointing at billing code that was entirely innocent. Found 2026-08-04
while smoke-testing the new remote MCP endpoint, which uses exactly that path.

The export is fixed in app/models/__init__.py, but that only helps databases
built from scratch afterwards. This migration repairs the ones already running.

IDEMPOTENT BY DESIGN: databases that DID migrate normally already have the
table, so this must be a no-op there rather than an error. Checked against the
live inspector rather than assumed.

Revision ID: claim_consensus_repair
Revises: lifecycle_emails
Create Date: 2026-08-04
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "claim_consensus_repair"
down_revision = "lifecycle_emails"
branch_labels = None
depends_on = None

TABLE = "claim_consensus"


def upgrade() -> None:
    bind = op.get_bind()
    if TABLE in sa.inspect(bind).get_table_names():
        # Already present — a normally-migrated database. Nothing to do.
        return

    # Column-for-column identical to m06_claim_consensus. Copied from that file
    # rather than written from the model: a migration must express the schema as
    # it was defined, not as the model happens to look today.
    op.create_table(
        TABLE,
        sa.Column("claim_text_hash", sa.String(64), primary_key=True),
        sa.Column("independent_checks", sa.Integer, nullable=False),
        sa.Column("stability", sa.String(10), nullable=False),
        sa.Column("element_state_distribution", JSONB, nullable=False),
        sa.Column("unique_sources", sa.Integer, nullable=False),
        sa.Column("total_evidence", sa.Integer, nullable=False),
        sa.Column("tier_spread", JSONB, nullable=False),
        sa.Column("last_full_check_at", sa.DateTime, nullable=False),
        sa.Column("computed_at", sa.DateTime, nullable=False),
    )


def downgrade() -> None:
    # Deliberately NOT dropping. This migration only ever creates a table that
    # should already have existed; dropping it here could destroy data that
    # m06_claim_consensus legitimately owns on a normally-migrated database.
    pass
