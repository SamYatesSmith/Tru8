"""F10: Add archived_url column to evidence table

Wayback Machine auto-archiving stores a permanent snapshot URL
for every evidence source. Nullable — populated asynchronously
after pipeline completion.

Revision ID: f10_archived_url
Revises: e03_drop_editorial_columns
Create Date: 2026-02-23

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f10_archived_url"
down_revision: Union[str, None] = "e03_drop_editorial_columns"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "evidence",
        sa.Column("archived_url", sa.String(500), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("evidence", "archived_url")
