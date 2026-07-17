"""Claim Map data structures — Track B foundation.

Canonical contract: audit/track-b/2026-02-12_claim-map-contract.md
"""

from enum import Enum
from typing import Optional
from typing_extensions import NotRequired, TypedDict


class ClaimType(str, Enum):
    empirical = "empirical"
    definitional = "definitional"
    causal_interpretive = "causal_interpretive"
    predictive = "predictive"
    normative_flagged = "normative_flagged"


class ElementState(str, Enum):
    supported = "supported"
    disputed = "disputed"
    unresolved = "unresolved"
    # contextual (2026-05-12) — element has only context-tier evidence
    # (no supports, no challenges). Distinguishes "we have related
    # evidence but nothing directly substantiating" from "we have
    # nothing at all". Pre-fix, both rendered as unresolved/gap which
    # misrepresented the pool to users.
    contextual = "contextual"


class EvidenceRelationship(str, Enum):
    supports = "supports"
    challenges = "challenges"
    context = "context"


class EvidenceRef(TypedDict):
    evidence_id: str
    relationship: EvidenceRelationship
    reasoning: Optional[str]  # One-sentence explanation of the relationship


class ClaimElement(TypedDict):
    element_id: str  # "e1".."e5"
    description: str
    evidence_refs: list[EvidenceRef]
    state: Optional[ElementState]
    uncertainty: Optional[str]
    bounty_text: Optional[str]  # G01: User-supplied research brief (max 200 chars)
    basis: Optional[dict]  # PQ-03: Evidence basis metadata for state transparency
    scope_flags: Optional[
        dict
    ]  # F3: {geographic, universal} scope-sensitive wording (set at decompose; absent = not scope-sensitive)


class ClaimMapMetadata(TypedDict):
    decomposition_model: str
    mapping_model: Optional[str]
    element_count: int
    completed_at: Optional[str]  # ISO 8601
    # F-R2e (2026-07-09, additive — audit/2026-07-09_retrieval_quality_plan.md):
    # the retrieval query plan that ran for this claim, INCLUDING zero-yield
    # queries. {queries: [str], element_ids: [str], freshness: [str]},
    # parallel arrays. Diagnostic provenance only — absent on pre-R2e rows
    # and when query planning fell back.
    query_plan: NotRequired[dict]
    # §20 slice 2 (2026-07-17, additive — audit/2026-07-15_decoupling_build_plan.md
    # §20.6): opinion grounds stage disclosure. {applied: bool, converged: bool,
    # element_count: int}. Present ONLY on normative-hinted claims processed
    # with ENABLE_OPINION_REFRAME on; applied=false = stage failed or degenerate
    # input, baseline kept untouched. Feeds the 1c receipt.
    grounds: NotRequired[dict]


class ClaimMap(TypedDict):
    claim_id: str
    normalised_claim: str
    claim_type: ClaimType
    elements: list[ClaimElement]
    orientation: Optional[str]
    orientation_basis: Optional[dict]  # PQ-05: Structured orientation breakdown
    metadata: ClaimMapMetadata
