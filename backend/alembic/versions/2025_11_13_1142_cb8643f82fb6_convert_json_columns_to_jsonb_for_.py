"""convert_json_columns_to_jsonb_for_performance

This migration converts all JSON columns to JSONB for:
- Better query performance
- Native JSONB operator support (@>, ->, ->>, etc.)
- GIN indexing capability
- Consistent use of PostgreSQL-specific features

Affected tables:
- check (4 columns)
- claim (4 columns)
- evidence (2 columns)
- unknown_source (1 column)

The conversion is safe and preserves all existing data using USING clause.

Issue #4: Inconsistent JSONB Usage

Revision ID: cb8643f82fb6
Revises: 595bc2ddd5c5
Create Date: 2025-11-13 11:42:28.910435+00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'cb8643f82fb6'
down_revision: Union[str, None] = '595bc2ddd5c5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Convert JSON columns to JSONB for performance.

    Uses USING clause to safely convert existing data.
    This is a non-destructive operation.
    """

    print("Converting JSON columns to JSONB for PostgreSQL optimization...")

    # Check table (4 columns)
    print("  - check.input_content")
    op.execute("""
        ALTER TABLE check
        ALTER COLUMN input_content
        TYPE jsonb
        USING input_content::jsonb
    """)

    print("  - check.decision_trail")
    op.execute("""
        ALTER TABLE check
        ALTER COLUMN decision_trail
        TYPE jsonb
        USING decision_trail::jsonb
    """)

    print("  - check.query_sources")
    op.execute("""
        ALTER TABLE check
        ALTER COLUMN query_sources
        TYPE jsonb
        USING query_sources::jsonb
    """)

    print("  - check.api_sources_used")
    op.execute("""
        ALTER TABLE check
        ALTER COLUMN api_sources_used
        TYPE jsonb
        USING api_sources_used::jsonb
    """)

    # Claim table (4 columns)
    print("  - claim.temporal_markers")
    op.execute("""
        ALTER TABLE claim
        ALTER COLUMN temporal_markers
        TYPE jsonb
        USING temporal_markers::jsonb
    """)

    print("  - claim.legal_metadata")
    op.execute("""
        ALTER TABLE claim
        ALTER COLUMN legal_metadata
        TYPE jsonb
        USING legal_metadata::jsonb
    """)

    print("  - claim.confidence_breakdown")
    op.execute("""
        ALTER TABLE claim
        ALTER COLUMN confidence_breakdown
        TYPE jsonb
        USING confidence_breakdown::jsonb
    """)

    print("  - claim.key_entities")
    op.execute("""
        ALTER TABLE claim
        ALTER COLUMN key_entities
        TYPE jsonb
        USING key_entities::jsonb
    """)

    # Evidence table (2 columns)
    print("  - evidence.risk_flags")
    op.execute("""
        ALTER TABLE evidence
        ALTER COLUMN risk_flags
        TYPE jsonb
        USING risk_flags::jsonb
    """)

    print("  - evidence.api_metadata")
    op.execute("""
        ALTER TABLE evidence
        ALTER COLUMN api_metadata
        TYPE jsonb
        USING api_metadata::jsonb
    """)

    # Unknown_source table (1 column)
    print("  - unknown_source.review_notes")
    op.execute("""
        ALTER TABLE unknown_source
        ALTER COLUMN review_notes
        TYPE jsonb
        USING review_notes::jsonb
    """)

    print("✅ Successfully converted 11 JSON columns to JSONB")
    print("   Performance improvement: JSONB supports GIN indexes and native operators")


def downgrade() -> None:
    """
    Revert JSONB columns to JSON.

    This is provided for rollback capability but should rarely be needed.
    """

    print("Reverting JSONB columns to JSON...")

    # Check table
    op.execute("ALTER TABLE check ALTER COLUMN input_content TYPE json USING input_content::json")
    op.execute("ALTER TABLE check ALTER COLUMN decision_trail TYPE json USING decision_trail::json")
    op.execute("ALTER TABLE check ALTER COLUMN query_sources TYPE json USING query_sources::json")
    op.execute("ALTER TABLE check ALTER COLUMN api_sources_used TYPE json USING api_sources_used::json")

    # Claim table
    op.execute("ALTER TABLE claim ALTER COLUMN temporal_markers TYPE json USING temporal_markers::json")
    op.execute("ALTER TABLE claim ALTER COLUMN legal_metadata TYPE json USING legal_metadata::json")
    op.execute("ALTER TABLE claim ALTER COLUMN confidence_breakdown TYPE json USING confidence_breakdown::json")
    op.execute("ALTER TABLE claim ALTER COLUMN key_entities TYPE json USING key_entities::json")

    # Evidence table
    op.execute("ALTER TABLE evidence ALTER COLUMN risk_flags TYPE json USING risk_flags::json")
    op.execute("ALTER TABLE evidence ALTER COLUMN api_metadata TYPE json USING api_metadata::json")

    # Unknown_source table
    op.execute("ALTER TABLE unknown_source ALTER COLUMN review_notes TYPE json USING review_notes::json")

    print("✅ Reverted 11 JSONB columns to JSON")
