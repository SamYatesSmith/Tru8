"""Claim Map data structures — Track B foundation.

Canonical contract: audit/track-b/2026-02-12_claim-map-contract.md
"""

from enum import Enum
from typing import Optional
from typing_extensions import TypedDict


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


class EvidenceRelationship(str, Enum):
    supports = "supports"
    challenges = "challenges"
    context = "context"


class EvidenceRef(TypedDict):
    evidence_id: str
    relationship: EvidenceRelationship


class ClaimElement(TypedDict):
    element_id: str  # "e1".."e5"
    description: str
    evidence_refs: list[EvidenceRef]
    state: Optional[ElementState]
    uncertainty: Optional[str]
    bounty_text: Optional[str]  # G01: User-supplied research brief (max 200 chars)


class ClaimMapMetadata(TypedDict):
    decomposition_model: str
    mapping_model: Optional[str]
    element_count: int
    completed_at: Optional[str]  # ISO 8601


class ClaimMap(TypedDict):
    claim_id: str
    normalised_claim: str
    claim_type: ClaimType
    elements: list[ClaimElement]
    orientation: Optional[str]
    metadata: ClaimMapMetadata
