"""Durable strengthening and report revision snapshots.

Revision ID: research_operations
Revises: claim_comparison
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "research_operations"
down_revision = "claim_comparison"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "research_operation",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "check_id",
            sa.String(),
            sa.ForeignKey("check.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "claim_id",
            sa.String(),
            sa.ForeignKey("claim.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("request_key", sa.String(128), nullable=False),
        sa.Column("request_scope", sa.String(), nullable=False),
        sa.Column("element_ids", JSONB, nullable=False),
        sa.Column(
            "debit_id",
            sa.String(),
            sa.ForeignKey("usage_events.id", ondelete="SET NULL"),
        ),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("stage", sa.String(32), nullable=False),
        sa.Column("message", sa.String(), nullable=False),
        sa.Column("new_evidence_count", sa.Integer(), nullable=False),
        sa.Column("baseline", JSONB, nullable=False),
        sa.Column("baseline_hash", sa.String(64), nullable=False),
        sa.Column("result_revision_id", sa.String()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("deadline_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime()),
        sa.UniqueConstraint("check_id", "request_key", name="uq_research_request"),
    )
    op.create_index(
        "ix_research_operation_check_id", "research_operation", ["check_id"]
    )
    op.create_index(
        "ix_research_operation_claim_id", "research_operation", ["claim_id"]
    )
    op.create_index(
        "uq_research_active_check",
        "research_operation",
        ["check_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('pending', 'running')"),
    )
    op.create_table(
        "report_revision",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "check_id",
            sa.String(),
            sa.ForeignKey("check.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "operation_id",
            sa.String(),
            sa.ForeignKey("research_operation.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("phase", sa.String(8), nullable=False),
        sa.Column("snapshot", JSONB, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("operation_id", "phase", name="uq_research_revision_phase"),
    )
    op.create_index("ix_report_revision_check_id", "report_revision", ["check_id"])


def downgrade():
    op.drop_table("report_revision")
    op.drop_table("research_operation")
