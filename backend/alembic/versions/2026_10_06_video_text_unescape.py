"""Decode HTML entities in stored YouTube video text (A− S6, 2026-10-06).

The YouTube Data API returns HTML-escaped snippet text ("Europe&#39;s ...");
the adapter stored it raw until 2026-10-06, so the VIDEO lens showed the
entities. The adapter now decodes once at ingest; this decodes every row
stored before that, exactly once. Data only, no schema change.

Revision ID: video_text_unescape
Revises: heard_about
Create Date: 2026-10-06
"""

import html

from alembic import op
import sqlalchemy as sa

revision = "video_text_unescape"
down_revision = "heard_about"
branch_labels = None
depends_on = None

_FIELDS = ("title", "description", "channel_name")
_LIMITS = {"title": 500, "description": 2000, "channel_name": 200}


def upgrade() -> None:
    conn = op.get_bind()
    rows = conn.execute(
        sa.text(
            "SELECT id, title, description, channel_name FROM video_recommendation "
            "WHERE title LIKE '%&%' OR description LIKE '%&%' OR channel_name LIKE '%&%'"
        )
    ).mappings()
    for row in list(rows):
        values = {}
        for field in _FIELDS:
            text = row[field]
            if isinstance(text, str) and "&" in text:
                decoded = html.unescape(text)[: _LIMITS[field]]
                if decoded != text:
                    values[field] = decoded
        if values:
            sets = ", ".join(f"{f} = :{f}" for f in values)
            conn.execute(
                sa.text(f"UPDATE video_recommendation SET {sets} WHERE id = :id"),
                {**values, "id": row["id"]},
            )


def downgrade() -> None:
    # Decoding is not reversible without the raw text; nothing to undo.
    pass
