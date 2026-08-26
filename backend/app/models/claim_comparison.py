"""COMPARE tab: a user-chosen pair of sources, read whole and summarised once.

Design: audit/2026-08-26_compare_tab_design.md. The rules that shape this
table, so nobody "fixes" them away:

- PROSE ONLY. Collisions (which elements the pair opposes/aligns on) are
  computed on READ from the live claim_map, never persisted — a stored
  collision set silently goes stale when re-search or coverage recovery
  re-maps evidence (the same staleness already logged for basis blocks).
- The row count IS the budget spend. No separate counter to drift.
- (evidence_a_id, evidence_b_id) is stored SORTED so A/B and B/A are one
  cache row, enforced by the unique constraint below.
- This table writes NOTHING back to Evidence or claim_map: per-evidence
  content_basis is inside the signed manifest payload, and mutating it
  would make /verify/{id} return data_modified for the check forever.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Column, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

from app.models.check import generate_uuid, _utcnow_naive


class ClaimComparison(SQLModel, table=True):
    """One completed comparison of two evidence items on one claim."""

    __tablename__ = "claim_comparison"
    __table_args__ = (
        UniqueConstraint(
            "claim_id",
            "evidence_a_id",
            "evidence_b_id",
            name="uq_claim_comparison_pair",
        ),
    )

    id: str = Field(default_factory=generate_uuid, primary_key=True)
    check_id: str = Field(foreign_key="check.id", index=True)
    claim_id: str = Field(foreign_key="claim.id", index=True)

    # Sorted lexicographically before insert — the unique constraint assumes it.
    evidence_a_id: str = Field(max_length=64)
    evidence_b_id: str = Field(max_length=64)

    summary_a: str
    summary_b: str
    divergence: str

    # What the model actually read, per side: full | stored | failed.
    # 'stored' = the pipeline's distilled/snippet/api text (fetch blocked or
    # unusable); 'failed' never persists — a comparison with no usable text on
    # a side is not stored (and not charged).
    basis_a: str = Field(max_length=16)
    basis_b: str = Field(max_length=16)
    # Word counts of what was read (receipt rendering: "full article (1,240
    # words)"). Null when basis is 'stored' and the stored text has no
    # meaningful word identity of its own.
    words_a: Optional[int] = Field(default=None)
    words_b: Optional[int] = Field(default=None)

    # Cost telemetry for the single model call.
    usage: Optional[dict] = Field(
        default=None,
        sa_column=Column(JSONB),
        description="{input_tokens, output_tokens, model}",
    )

    created_at: datetime = Field(default_factory=_utcnow_naive)
