"""M-06: Cross-user consensus for claims checked ≥3 times independently.

Aggregates element states and evidence metadata across independent Full checks.
Uses description hashing for element canonicalisation (no embeddings — KD5).
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


class ClaimConsensus(SQLModel, table=True):
    """Consensus aggregate for a claim checked by ≥3 distinct users.

    Primary key is claim_text_hash (same normalisation as Claim.claim_text_hash).
    Recomputed daily by batch job. Not user-facing — consumed by smart endpoint.
    """

    __tablename__ = "claim_consensus"

    claim_text_hash: str = Field(
        primary_key=True,
        max_length=64,
        description="SHA256 of normalised claim text (same as Claim.claim_text_hash)",
    )
    independent_checks: int = Field(
        description="Count of distinct user_ids with completed Full checks"
    )
    stability: str = Field(
        max_length=10,
        description="Consensus stability: stable (≥80%) | mixed (60-80%) | shifting (<60%)",
    )
    element_state_distribution: dict = Field(
        sa_column=Column(JSONB),
        description="Per canonical element: {canonical_eid: {state: count}}",
    )
    unique_sources: int = Field(
        description="Distinct evidence URLs across all contributing checks"
    )
    total_evidence: int = Field(
        description="Sum of evidence items across all contributing checks"
    )
    tier_spread: dict = Field(
        sa_column=Column(JSONB),
        description="Aggregate tier counts: {primary: N, reporting: N, commentary: N}",
    )
    last_full_check_at: datetime = Field(
        description="Most recent contributing Full check completion time"
    )
    computed_at: datetime = Field(
        description="When this consensus row was last recomputed"
    )
