"""Add Evidence.date_basis — provenance of published_date (F2).

Search engines sometimes synthesise a "publication" date from a URL upload
path (e.g. a 2000-era PDF under /uploads/2026/04/ reported as Apr 2026).
This column records where each evidence item's published_date came from so
surfaces can label unconfirmed dates honestly:

    page_metadata | engine | url_inferred_suspect | api_adapter | NULL

Labelling only — no admission/exclusion behaviour reads this column.
NULL for all pre-existing rows and for items with no date at all.
Design: audit/2026-07-03_f1f2_design_review.md (founder-approved 2026-07-03).

Revision ID: date_basis
Revises: cost_telemetry
Create Date: 2026-07-03
"""

from alembic import op
import sqlalchemy as sa

revision = "date_basis"
down_revision = "cost_telemetry"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "evidence",
        sa.Column("date_basis", sa.String(32), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("evidence", "date_basis")
