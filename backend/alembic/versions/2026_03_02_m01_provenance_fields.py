"""M-01: Add provenance persistence fields to Evidence.

Three fields already computed in the pipeline (llm_relevance_score,
llm_relevance_rationale, classification_method) are now persisted.

Revision ID: m01_provenance_fields
Revises: l05_external_id
Create Date: 2026-03-02
"""

from alembic import op
import sqlalchemy as sa

revision = "m01_provenance_fields"
down_revision = "l05_external_id"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "evidence", sa.Column("llm_relevance_score", sa.Integer(), nullable=True)
    )
    op.add_column(
        "evidence",
        sa.Column("llm_relevance_rationale", sa.String(500), nullable=True),
    )
    op.add_column(
        "evidence",
        sa.Column("classification_method", sa.String(20), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("evidence", "classification_method")
    op.drop_column("evidence", "llm_relevance_rationale")
    op.drop_column("evidence", "llm_relevance_score")
