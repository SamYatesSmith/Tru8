"""Add claim_text_hash for cross-check claim fingerprinting

Revision ID: claim_text_hash
Revises: h_api_06_webhooks
Create Date: 2026-02-26
"""

from alembic import op
import sqlalchemy as sa

revision = "claim_text_hash"
down_revision = "h_api_06_webhooks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "claim",
        sa.Column(
            "claim_text_hash",
            sa.String(64),
            nullable=True,
            comment="SHA256 of normalised claim text for cross-check fingerprinting",
        ),
    )
    op.create_index("ix_claim_claim_text_hash", "claim", ["claim_text_hash"])


def downgrade() -> None:
    op.drop_index("ix_claim_claim_text_hash")
    op.drop_column("claim", "claim_text_hash")
