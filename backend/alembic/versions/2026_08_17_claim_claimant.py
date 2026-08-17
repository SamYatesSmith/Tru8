"""Add Claim.claimant — WHO makes the claim, so the gates can arm on it.

Quality-first Phase C (2026-08-17): the interested-party and recital gates
arm on `claim_map["metadata"]["subjects"]`, derived from key_entities
PERSON/ORG. The NHS outreach record showed the blind spot: "NHS England" was
typed PRODUCT-adjacent, subjects came out ["gp practices"], and both gates
were structurally silent. The extract stage now names the claimant directly
(it reads the full text; entity typing does not decide attribution), and
`attach_claim_subjects` merges it into subjects.

A column because claims round-trip through the DB at the selection pause —
a dict-only field would die between Phase 1 and Phase 2. NULL means
unattributed (reported findings, plain facts): the gates then stay silent,
the safe direction. No backfill: pre-existing claims stay NULL and keep
exactly their current gate behaviour.

Revision ID: claim_claimant
Revises: signup_source
Create Date: 2026-08-17
"""

from alembic import op
import sqlalchemy as sa

revision = "claim_claimant"
down_revision = "signup_source"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "claim",
        sa.Column("claimant", sa.String(256), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("claim", "claimant")
