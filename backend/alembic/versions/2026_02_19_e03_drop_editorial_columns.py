"""E03: Drop orphaned editorial/credibility columns from all tables

These columns were removed from ORM models but never dropped from the
database.  credibility_score had NOT NULL constraints on both evidence
and rawevidence tables, crashing every INSERT.

Tables affected:
- evidence: credibility_score, risk_flags, credibility_reasoning, risk_level, risk_warning
- rawevidence: credibility_score
- unknown_source: assigned_credibility

Revision ID: e03_drop_editorial_columns
Revises: e14_video_recommendations
Create Date: 2026-02-19

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e03_drop_editorial_columns"
down_revision: Union[str, None] = "e14_video_recommendations"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # evidence table — 5 orphaned columns
    op.drop_column("evidence", "credibility_score")
    op.drop_column("evidence", "risk_flags")
    op.drop_column("evidence", "credibility_reasoning")
    op.drop_column("evidence", "risk_level")
    op.drop_column("evidence", "risk_warning")

    # rawevidence table — 1 orphaned column (NOT NULL, crashes INSERT)
    op.drop_column("rawevidence", "credibility_score")

    # unknown_source table — 1 orphaned column (nullable, harmless but cruft)
    op.drop_column("unknown_source", "assigned_credibility")


def downgrade() -> None:
    # unknown_source
    op.add_column(
        "unknown_source",
        sa.Column("assigned_credibility", sa.Float(), nullable=True),
    )

    # rawevidence
    op.add_column(
        "rawevidence",
        sa.Column("credibility_score", sa.Float(), nullable=False),
    )

    # evidence
    op.add_column("evidence", sa.Column("risk_warning", sa.String(), nullable=True))
    op.add_column("evidence", sa.Column("risk_level", sa.String(), nullable=True))
    op.add_column(
        "evidence",
        sa.Column("credibility_reasoning", sa.String(), nullable=True),
    )
    op.add_column("evidence", sa.Column("risk_flags", sa.String(), nullable=True))
    op.add_column(
        "evidence",
        sa.Column("credibility_score", sa.Float(), nullable=False),
    )
