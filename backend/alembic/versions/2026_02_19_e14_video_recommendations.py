"""E14: Create video_recommendation table

Standalone video context — YouTube recommendations per claim.
Not pipeline evidence; a separate async feature.

Revision ID: e14_video_recommendations
Revises: e07_corroboration_fields
Create Date: 2026-02-19

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e14_video_recommendations"
down_revision: Union[str, None] = "e07_corroboration_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "video_recommendation",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "check_id",
            sa.String(),
            sa.ForeignKey("check.id"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "claim_id",
            sa.String(),
            sa.ForeignKey("claim.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("video_id", sa.String(20), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.String(2000), nullable=True),
        sa.Column("channel_name", sa.String(200), nullable=False),
        sa.Column("channel_id", sa.String(50), nullable=True),
        sa.Column("publish_date", sa.DateTime(), nullable=True),
        sa.Column("video_url", sa.String(500), nullable=False),
        sa.Column("thumbnail_url", sa.String(500), nullable=True),
        sa.Column("duration", sa.String(20), nullable=True),
        sa.Column("tier_label", sa.String(20), nullable=True),
        sa.Column("type_label", sa.String(30), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
    )


def downgrade() -> None:
    op.drop_table("video_recommendation")
