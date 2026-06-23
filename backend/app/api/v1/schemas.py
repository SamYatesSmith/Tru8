"""OpenAPI response and request schemas for Tru8 API documentation.

These models exist for documentation purposes — they define the shapes
that appear in Swagger UI and ReDoc. Endpoint implementations continue
to return dicts/JSONResponse; FastAPI references these models via the
`responses={}` decorator parameter.

All field descriptions use UK English to match the product voice.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


# ============================================================================
# Enumerations (used across schemas)
# ============================================================================


class InputType(str, Enum):
    """Supported input types for evidence research."""

    url = "url"
    text = "text"
    image = "image"
    video = "video"


class CheckStatus(str, Enum):
    """Pipeline status values."""

    processing = "processing"
    waiting_for_selection = "waiting_for_selection"
    completed = "completed"
    failed = "failed"


class EvidenceTier(str, Enum):
    """Source tier classification — structural role of the source."""

    primary = "primary"
    reporting = "reporting"
    commentary = "commentary"


class EvidenceType(str, Enum):
    """Source type classification — content category."""

    data = "data"
    official = "official"
    news = "news"
    analysis = "analysis"
    opinion = "opinion"
    academic = "academic"


class ClaimTypeEnum(str, Enum):
    """Claim type classification."""

    empirical = "empirical"
    definitional = "definitional"
    causal_interpretive = "causal_interpretive"
    predictive = "predictive"
    normative_flagged = "normative_flagged"


class ElementState(str, Enum):
    """Evidence state for a claim element."""

    supported = "supported"
    disputed = "disputed"
    unresolved = "unresolved"


class EvidenceRelationship(str, Enum):
    """How a piece of evidence relates to an element."""

    supports = "supports"
    challenges = "challenges"
    context = "context"


class ReceiptStatus(str, Enum):
    """Pipeline receipt status — tracks evidence through the pipeline."""

    found = "found"
    extracted = "extracted"
    classified = "classified"
    excluded = "excluded"
    shown = "shown"


class PipelineTier(str, Enum):
    """Agent pipeline tiers — determines depth and cost."""

    lookup = "lookup"
    consensus = "consensus"
    quick = "quick"
    full = "full"


class ContentBasis(str, Enum):
    """How the evidence content was obtained."""

    full = "full"
    snippet = "snippet"
    api = "api"
    pdf = "pdf"


class ClassificationMethod(str, Enum):
    """How the evidence was classified."""

    llm = "llm"
    heuristic = "heuristic"
    api_metadata = "api_metadata"


# ============================================================================
# Evidence schema
# ============================================================================


class EvidenceItem(BaseModel):
    """A single piece of evidence with source metadata and classification."""

    id: str = Field(description="Internal database ID")
    evidenceId: str = Field(description="Stable evidence identifier (URL hash)")
    source: Optional[str] = Field(
        None, description="Human-readable source name (e.g. 'BBC News', 'WHO')"
    )
    url: Optional[str] = Field(None, description="Source URL")
    title: Optional[str] = Field(None, description="Article or document title")
    snippet: Optional[str] = Field(
        None,
        description="Relevant excerpt from the source (up to 1,000 characters)",
    )
    publishedDate: Optional[str] = Field(
        None, description="Publication date in ISO 8601 format"
    )
    relevanceScore: Optional[float] = Field(
        None,
        description="Topical relevance score (1-5 scale). Measures how on-topic the source is, not source authority.",
    )
    tier: Optional[EvidenceTier] = Field(
        None,
        description="Source tier: primary (original data/documents), reporting (news coverage), or commentary (opinion/analysis)",
    )
    evidenceType: Optional[EvidenceType] = Field(
        None,
        description="Content type: data, official, news, analysis, opinion, or academic",
    )
    receiptStatus: Optional[ReceiptStatus] = Field(
        None,
        description="Pipeline receipt: found → extracted → classified → shown (or excluded). Every exclusion has a receipt.",
    )
    corroborationGroupId: Optional[str] = Field(
        None, description="Group ID linking corroborating sources"
    )
    corroboratingEvidenceIds: Optional[List[str]] = Field(
        None, description="IDs of sources that corroborate this evidence"
    )
    isFactcheck: Optional[bool] = Field(
        None, description="Whether this is from a fact-checking organisation"
    )
    externalSourceProvider: Optional[str] = Field(
        None,
        description="API provider that supplied this evidence (e.g. 'semantic_scholar', 'pubmed')",
    )
    sourceType: Optional[str] = Field(
        None, description="Retrieval method: web_search or api"
    )
    archivedUrl: Optional[str] = Field(
        None,
        description="Wayback Machine archived URL (auto-archived for permanence)",
    )
    llmRelevanceScore: Optional[float] = Field(
        None, description="Raw LLM relevance score before normalisation"
    )
    classificationMethod: Optional[ClassificationMethod] = Field(
        None,
        description="How tier/type was assigned: llm, heuristic, or api_metadata",
    )
    contentBasis: Optional[ContentBasis] = Field(
        None,
        description="How the content was obtained: full (page fetch), snippet (search result), api (structured API), pdf",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "ev_abc123",
                "evidenceId": "a1b2c3d4",
                "source": "Office for National Statistics",
                "url": "https://www.ons.gov.uk/economy/data",
                "title": "UK GDP quarterly estimate",
                "snippet": "GDP grew by 0.6% in Q3 2025, following growth of 0.5% in Q2...",
                "publishedDate": "2025-11-15T00:00:00",
                "relevanceScore": 4.2,
                "tier": "primary",
                "evidenceType": "data",
                "receiptStatus": "shown",
                "classificationMethod": "heuristic",
                "contentBasis": "api",
            }
        }
    )


# ============================================================================
# Claim Map schema (nested within claims)
# ============================================================================


class EvidenceRef(BaseModel):
    """Reference linking evidence to a claim element."""

    evidenceId: str = Field(description="ID of the referenced evidence item")
    relationship: EvidenceRelationship = Field(
        description="How this evidence relates to the element: supports, challenges, or context"
    )
    snippet: Optional[str] = Field(
        None, description="Key excerpt used for this mapping"
    )


class ClaimElement(BaseModel):
    """A verifiable sub-question decomposed from the parent claim."""

    elementId: str = Field(description="Unique element identifier")
    description: str = Field(
        description="The verifiable sub-question this element investigates"
    )
    state: ElementState = Field(
        description="Evidence state: supported (evidence agrees), disputed (evidence conflicts), or unresolved (insufficient evidence)"
    )
    evidenceRefs: List[EvidenceRef] = Field(
        description="Evidence items mapped to this element with relationship labels"
    )
    uncertaintyNote: Optional[str] = Field(
        None, description="Note on limitations or ambiguity in the evidence"
    )
    bountyText: Optional[str] = Field(
        None,
        description="User-authored note requesting specific evidence for this element (Seeker feature)",
    )
    basis: Optional[Dict[str, Any]] = Field(
        None,
        description="Metadata breakdown: evidence count, tier/relationship/classification/content_basis distributions",
    )


class ClaimMapSchema(BaseModel):
    """Structured analysis of a single claim — elements, evidence mapping, and orientation."""

    normalisedClaim: str = Field(
        description="The claim restated in neutral, verifiable language"
    )
    claimType: Optional[ClaimTypeEnum] = Field(
        None,
        description="Claim classification: empirical, definitional, causal_interpretive, predictive, or normative_flagged",
    )
    elements: List[ClaimElement] = Field(
        description="1-5 verifiable sub-questions decomposed from the claim"
    )
    orientation: Optional[str] = Field(
        None,
        description="Evidence-centred summary derived mechanically from element states (no LLM). Describes what the evidence landscape shows, not a verdict.",
    )
    orientationBasis: Optional[Dict[str, Any]] = Field(
        None,
        description="Mechanical derivation data: element state counts and the rule that produced the orientation line",
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None, description="Claim map metadata (input hash, model version)"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "normalisedClaim": "UK GDP grew in Q3 2025",
                "claimType": "empirical",
                "elements": [
                    {
                        "elementId": "e1",
                        "description": "Did UK GDP grow in Q3 2025?",
                        "state": "supported",
                        "evidenceRefs": [
                            {
                                "evidenceId": "a1b2c3d4",
                                "relationship": "supports",
                                "snippet": "GDP grew by 0.6% in Q3 2025...",
                            }
                        ],
                    }
                ],
                "orientation": "Evidence broadly supports this claim. 2 of 2 elements are supported by primary and reporting sources.",
                "orientationBasis": {
                    "supported": 2,
                    "disputed": 0,
                    "unresolved": 0,
                    "rule": "all_supported",
                },
            }
        }
    )


# ============================================================================
# Claim schema (used in check responses)
# ============================================================================


class ClaimDetail(BaseModel):
    """A claim extracted from the input, with its evidence landscape."""

    id: str = Field(description="Claim database ID")
    text: str = Field(description="Original claim text as extracted")
    position: int = Field(description="Claim position within the check (0-indexed)")
    claimMap: Optional[ClaimMapSchema] = Field(
        None,
        description="Structured analysis: elements, evidence mapping, orientation. Present only after Phase 2 completes.",
    )
    claimType: Optional[ClaimTypeEnum] = Field(
        None,
        description="Claim classification: empirical, definitional, causal_interpretive, predictive, or normative_flagged",
    )
    isSelected: Optional[bool] = Field(
        None,
        description="Whether this claim was selected for full analysis (article mode)",
    )
    significanceRank: Optional[int] = Field(
        None,
        description="Significance ranking within the article (lower = more significant)",
    )
    subjectContext: Optional[str] = Field(
        None, description="Subject area context for the claim"
    )
    keyEntities: Optional[List[str]] = Field(
        None, description="Key named entities mentioned in the claim"
    )
    sourceTitle: Optional[str] = Field(
        None, description="Title of the source article (URL inputs)"
    )
    sourceUrl: Optional[str] = Field(None, description="URL of the source article")
    sourcesReviewedCount: Optional[int] = Field(
        None,
        description="Number of raw sources reviewed for this claim before filtering",
    )
    evidence: List[EvidenceItem] = Field(
        default_factory=list,
        description="Evidence items organised by the pipeline — classified, mapped, and receipted",
    )


class ClaimSummary(BaseModel):
    """Abbreviated claim data for list views."""

    id: str = Field(description="Claim database ID")
    text: str = Field(description="Original claim text")
    position: int = Field(description="Claim position (0-indexed)")
    claimType: Optional[ClaimTypeEnum] = Field(None, description="Claim classification")
    elementCount: int = Field(
        description="Number of elements decomposed from this claim"
    )
    orientation: Optional[str] = Field(
        None, description="Evidence orientation summary line"
    )


# ============================================================================
# Check response schemas
# ============================================================================


class CheckResponse(BaseModel):
    """Full check response with claims, evidence, and metadata."""

    id: str = Field(description="Check ID (UUID)")
    inputType: InputType = Field(description="Input type: url, text, image, or video")
    inputContent: Optional[Dict[str, Any]] = Field(
        None, description="Original input data"
    )
    inputUrl: Optional[str] = Field(None, description="Source URL (if url input type)")
    status: CheckStatus = Field(
        description="Pipeline status: processing, waiting_for_selection, completed, or failed"
    )
    creditsUsed: int = Field(description="Credits consumed by this check")
    processingTimeMs: Optional[int] = Field(
        None, description="Total pipeline processing time in milliseconds"
    )
    errorMessage: Optional[str] = Field(
        None, description="Error details (only present on failed checks)"
    )
    entryMode: Optional[str] = Field(
        None, description="How the check was initiated: article or direct"
    )
    selectedClaimsCount: Optional[int] = Field(
        None, description="Number of claims selected for analysis"
    )
    articleDomain: Optional[str] = Field(
        None, description="Primary domain classification of the article"
    )
    articleSecondaryDomains: Optional[List[str]] = Field(
        None, description="Secondary domain classifications"
    )
    articleJurisdiction: Optional[str] = Field(
        None,
        description="Detected jurisdiction for adapter routing (UK, US, or global)",
    )
    articleClassificationSource: Optional[str] = Field(
        None, description="How the article domain was classified"
    )
    userQuery: Optional[str] = Field(
        None, description="User's Search Clarity question (if provided)"
    )
    queryResponse: Optional[str] = Field(None, description="Search Clarity answer")
    queryConfidence: Optional[float] = Field(
        None, description="Search Clarity confidence score"
    )
    querySources: Optional[List[Dict[str, Any]]] = Field(
        None, description="Sources used for Search Clarity answer"
    )
    queryRelatedClaims: Optional[List[Dict[str, Any]]] = Field(
        None, description="Claims related to the Search Clarity question"
    )
    claims: List[ClaimDetail] = Field(
        description="Extracted claims with full evidence landscapes"
    )
    createdAt: str = Field(description="Check creation timestamp (ISO 8601)")
    completedAt: Optional[str] = Field(
        None, description="Check completion timestamp (ISO 8601)"
    )
    currentStage: Optional[str] = Field(
        None,
        description="Current pipeline stage (only during processing): ingest, extract, retrieve, classify, map, etc.",
    )
    progress: Optional[float] = Field(
        None, description="Pipeline progress percentage (0-100)"
    )
    progressMessage: Optional[str] = Field(
        None, description="Human-readable progress message"
    )


class CheckListItem(BaseModel):
    """Check summary for list endpoints."""

    id: str = Field(description="Check ID (UUID)")
    inputType: InputType = Field(description="Input type: url, text, image, or video")
    inputUrl: Optional[str] = Field(None, description="Source URL")
    status: CheckStatus = Field(description="Pipeline status")
    creditsUsed: int = Field(description="Credits consumed")
    processingTimeMs: Optional[int] = Field(
        None, description="Processing time in milliseconds"
    )
    createdAt: str = Field(description="Creation timestamp (ISO 8601)")
    completedAt: Optional[str] = Field(
        None, description="Completion timestamp (ISO 8601)"
    )
    claimsCount: int = Field(description="Total number of claims extracted")
    claims: List[ClaimSummary] = Field(description="First claim summary for preview")
    entryMode: Optional[str] = Field(None, description="article or direct")
    selectedClaimsCount: Optional[int] = Field(
        None, description="Claims selected for analysis"
    )
    articleDomain: Optional[str] = Field(
        None, description="Primary domain classification"
    )


class CheckListResponse(BaseModel):
    """Paginated list of the user's checks."""

    checks: List[CheckListItem] = Field(description="Check summaries, newest first")
    total: int = Field(description="Total number of checks returned")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "checks": [
                    {
                        "id": "abc-123",
                        "inputType": "url",
                        "inputUrl": "https://example.com/article",
                        "status": "completed",
                        "creditsUsed": 1,
                        "processingTimeMs": 85000,
                        "createdAt": "2026-03-10T14:30:00Z",
                        "completedAt": "2026-03-10T14:31:25Z",
                        "claimsCount": 3,
                        "claims": [
                            {
                                "id": "claim_1",
                                "text": "UK GDP grew by 0.6% in Q3 2025",
                                "position": 0,
                                "claimType": "empirical",
                                "elementCount": 2,
                                "orientation": "Evidence broadly supports this claim.",
                            }
                        ],
                        "entryMode": "article",
                        "selectedClaimsCount": 3,
                        "articleDomain": "economics",
                    }
                ],
                "total": 1,
            }
        }
    )


# ============================================================================
# Agent endpoint schemas
# ============================================================================


class SourceDiversity(BaseModel):
    """Source diversity breakdown within the evidence landscape."""

    tierSpread: Dict[EvidenceTier, int] = Field(
        description="Count of evidence items per tier (primary, reporting, commentary)"
    )
    uniqueDomains: int = Field(
        description="Number of distinct source domains in the evidence set"
    )
    typeCoverage: int = Field(
        description="Number of distinct source types represented (max 6)"
    )


class Freshness(BaseModel):
    """Evidence freshness metrics."""

    freshestDaysAgo: Optional[int] = Field(
        None, description="Days since the most recent dated evidence item"
    )
    dateSpanDays: Optional[int] = Field(
        None,
        description="Time span in days between oldest and newest dated evidence",
    )
    undatedCount: int = Field(
        description="Number of evidence items without a publication date"
    )


class LandscapeGap(BaseModel):
    """An identified gap in the evidence landscape."""

    elementId: Optional[str] = Field(
        None, description="Element ID (if element-level gap)"
    )
    description: Optional[str] = Field(
        None, description="Element description (if element-level gap)"
    )
    claimPosition: Optional[int] = Field(None, description="Parent claim position")
    reason: str = Field(
        description="Gap type: no_evidence, unresolved, no_primary_sources, or no_academic_sources"
    )
    evidenceCount: Optional[int] = Field(
        None, description="Evidence count for unresolved elements"
    )


class LandscapeMetrics(BaseModel):
    """Structured summary of the evidence landscape — designed for programmatic consumption."""

    elementCount: int = Field(
        description="Total number of verifiable elements across all claims"
    )
    elementStates: Dict[ElementState, int] = Field(
        description="Count of elements in each state: supported, disputed, unresolved"
    )
    evidenceDensity: int = Field(description="Total evidence items across all claims")
    sourcesConsidered: int = Field(
        description="Total sources reviewed (same as evidenceDensity for organised sources)"
    )
    sourceDiversity: SourceDiversity = Field(
        description="Source diversity breakdown: tier spread, unique domains, type coverage"
    )
    freshness: Freshness = Field(
        description="Evidence freshness: recency, date span, undated count"
    )
    gaps: List[LandscapeGap] = Field(
        description="Identified gaps in the evidence landscape (elements without evidence, missing source types)"
    )
    providerStatus: Optional[Dict[str, Any]] = Field(
        None,
        description="Aggregated provider status: which search/API providers succeeded, failed, or timed out during retrieval",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "elementCount": 5,
                "elementStates": {
                    "supported": 3,
                    "disputed": 1,
                    "unresolved": 1,
                },
                "evidenceDensity": 13,
                "sourcesConsidered": 13,
                "sourceDiversity": {
                    "tierSpread": {
                        "primary": 4,
                        "reporting": 6,
                        "commentary": 3,
                    },
                    "uniqueDomains": 9,
                    "typeCoverage": 4,
                },
                "freshness": {
                    "freshestDaysAgo": 2,
                    "dateSpanDays": 180,
                    "undatedCount": 1,
                },
                "gaps": [
                    {
                        "reason": "unresolved",
                        "elementId": "e3",
                        "description": "Is the trend accelerating?",
                        "claimPosition": 0,
                        "evidenceCount": 2,
                    }
                ],
                "providerStatus": None,
            }
        }
    )


class AgentMeta(BaseModel):
    """Agent response metadata — tier, cost, and landscape summary."""

    executedTier: PipelineTier = Field(
        description="Pipeline tier that was executed: lookup, consensus, quick, or full"
    )
    chargedPence: int = Field(
        description="Amount charged in pence GBP (0 for free retrievals)"
    )
    limitations: List[str] = Field(
        description="Pipeline stages skipped in quick mode (empty for full tier). Values: heuristic_classification, no_factcheck_lookup, no_api_sources, no_llm_relevance_scoring, no_coverage_recovery, no_query_answering",
    )
    landscape: LandscapeMetrics = Field(
        description="Structured evidence landscape metrics for programmatic analysis"
    )
    cachedFrom: Optional[str] = Field(
        None,
        description="ISO 8601 timestamp of the cached result (present only on lookup hits)",
    )


class AgentManifest(BaseModel):
    """HMAC-signed manifest. Verify the signed fields haven't changed since signing via GET /verify/{checkId}."""

    checkId: str = Field(description="Check ID this manifest covers")
    landscapeHash: str = Field(
        description="SHA-256 hash of the canonical evidence landscape"
    )
    signedAt: str = Field(description="Signing timestamp (ISO 8601)")
    signature: str = Field(description="HMAC-SHA256 signature (hex)")
    kid: str = Field(description="Key ID used for signing")
    verifyUrl: str = Field(
        description="Relative URL for public verification: /verify/{checkId}"
    )


class AgentClaimCompact(BaseModel):
    """Compact claim representation (compact=true mode)."""

    id: str = Field(description="Claim ID")
    text: str = Field(description="Claim text")
    position: int = Field(description="Position in check (0-indexed)")
    claimMap: Optional[ClaimMapSchema] = Field(
        None, description="Claim map with elements and orientation"
    )
    claimType: Optional[ClaimTypeEnum] = Field(
        None, description="Claim type classification"
    )
    isSelected: Optional[bool] = Field(None, description="Whether claim was selected")


class AgentCheckResponse(BaseModel):
    """Full agent response with evidence landscape, metadata, and signed manifest.

    Returned by /agent/check, /agent/quick, /agent/full, and /agent/lookup (on cache hit).

    **Note:** In the actual JSON response, the metadata fields are prefixed with
    underscores: `_meta`, `_manifest`, `_computed`. The schema below shows them
    without the prefix for documentation purposes.
    """

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(description="Check ID (UUID)")
    status: CheckStatus = Field(description="Check status: completed")
    claims: List[ClaimDetail] = Field(
        description="Claims with full evidence, elements, and orientation"
    )
    hit: Optional[bool] = Field(
        None,
        description="Cache hit indicator (true = served from cache, absent = fresh pipeline run)",
    )
    meta: AgentMeta = Field(
        description="(JSON key: `_meta`) Tier executed, cost, limitations, and landscape metrics",
        json_schema_extra={"title": "_meta"},
    )
    manifest: Optional[AgentManifest] = Field(
        None,
        description="(JSON key: `_manifest`) HMAC-signed manifest. Agents can verify the signed fields haven't changed since signing.",
        json_schema_extra={"title": "_manifest"},
    )
    computed: Optional[Dict[str, Any]] = Field(
        None,
        description="(JSON key: `_computed`) Pre-computed analytics: tier/type distributions, corroboration groups, diagnostic values, timeline, element state summaries",
        json_schema_extra={"title": "_computed"},
    )


class AgentCacheMiss(BaseModel):
    """Returned when a lookup or consensus check has no cached result available.

    Status 200 — this is not an error. Use nextSuggestedTier to escalate.
    """

    hit: bool = Field(False, description="Always false for cache misses")
    nextSuggestedTier: PipelineTier = Field(
        description="Suggested tier to try next: consensus, quick, or full"
    )
    upgradeCostPence: int = Field(
        description="Cost in GBP pence to run the suggested tier"
    )
    claimTextHash: str = Field(description="SHA-256 hash of the normalised claim text")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "hit": False,
                "nextSuggestedTier": "quick",
                "upgradeCostPence": 7,
                "claimTextHash": "a1b2c3d4e5f6...",
            }
        }
    )


class CreditBalanceResponse(BaseModel):
    """Agent prepaid credit balance."""

    balancePence: int = Field(description="Current credit balance in pence (GBP)")
    balanceGbp: str = Field(
        description="Current credit balance formatted as GBP string (e.g. '5.00')"
    )

    model_config = ConfigDict(
        json_schema_extra={"example": {"balancePence": 500, "balanceGbp": "5.00"}}
    )


class CheckoutSessionResponse(BaseModel):
    """Stripe Checkout session for credit pack purchase."""

    sessionId: str = Field(description="Stripe Checkout session ID")
    url: str = Field(
        description="Redirect URL — send the user here to complete payment"
    )


class TierStats(BaseModel):
    """Usage statistics for a single pipeline tier."""

    count: int = Field(description="Number of completed transactions")
    totalPence: int = Field(description="Total amount charged in pence (GBP)")


class ProviderStats(BaseModel):
    """Usage statistics for a single payment provider."""

    count: int = Field(description="Number of completed transactions")


class AgentStatsResponse(BaseModel):
    """Aggregated agent usage statistics."""

    byTier: Dict[str, TierStats] = Field(
        description="Transaction counts and spend broken down by pipeline tier"
    )
    byProvider: Dict[str, ProviderStats] = Field(
        description="Transaction counts broken down by payment provider (credit, skyfire, x402)"
    )
    totalAgentChecks: int = Field(
        description="Total checks initiated via agent endpoints"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "byTier": {
                    "lookup": {"count": 150, "totalPence": 300},
                    "quick": {"count": 45, "totalPence": 315},
                    "full": {"count": 12, "totalPence": 180},
                },
                "byProvider": {
                    "credit": {"count": 200},
                    "skyfire": {"count": 7},
                },
                "totalAgentChecks": 207,
            }
        }
    )


# ============================================================================
# Verify endpoint schemas
# ============================================================================


class VerifySuccessResponse(BaseModel):
    """Successful manifest verification — data integrity confirmed."""

    valid: bool = Field(True, description="Always true on successful verification")
    checkId: str = Field(description="Verified check ID")
    signedAt: str = Field(description="When the manifest was signed (ISO 8601)")
    kid: str = Field(description="Signing key ID")
    executedTier: Optional[PipelineTier] = Field(
        None, description="Pipeline tier used for this check"
    )
    pipelineFingerprint: Optional[str] = Field(
        None,
        description="SHA-256 fingerprint of pipeline model configuration (first 12 chars)",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "valid": True,
                "checkId": "abc-123",
                "signedAt": "2026-03-10T14:31:25Z",
                "kid": "k1",
                "executedTier": "full",
                "pipelineFingerprint": "a1b2c3d4e5f6",
            }
        }
    )


class VerifyFailureResponse(BaseModel):
    """Failed manifest verification."""

    valid: bool = Field(False, description="Always false on verification failure")
    reason: str = Field(
        description="Failure reason: not_found, invalid_signature, data_modified, or signing_disabled"
    )


# ============================================================================
# Video recommendations schema
# ============================================================================


class VideoItem(BaseModel):
    """A video recommendation from YouTube."""

    id: str = Field(description="Database ID")
    claimId: str = Field(description="Parent claim ID")
    videoId: str = Field(description="YouTube video ID")
    title: str = Field(description="Video title")
    description: Optional[str] = Field(None, description="Video description excerpt")
    channelName: Optional[str] = Field(None, description="YouTube channel name")
    channelId: Optional[str] = Field(None, description="YouTube channel ID")
    publishDate: Optional[str] = Field(
        None, description="Video publish date (ISO 8601)"
    )
    videoUrl: str = Field(description="Full YouTube watch URL")
    thumbnailUrl: Optional[str] = Field(None, description="Video thumbnail URL")
    duration: Optional[str] = Field(
        None, description="Video duration in ISO 8601 format"
    )
    tierLabel: Optional[EvidenceTier] = Field(
        None, description="Source tier classification for this video"
    )
    typeLabel: Optional[EvidenceType] = Field(
        None, description="Source type classification for this video"
    )


class VideosResponse(BaseModel):
    """Video recommendations for a check or claim."""

    checkId: str = Field(description="Check ID")
    videos: List[VideoItem] = Field(description="Video recommendations")


# ============================================================================
# Bounty and re-search schemas
# ============================================================================


class BountyUpdateResponse(BaseModel):
    """Response after updating element bounty text."""

    status: str = Field("success", description="Operation status")
    bountyText: Optional[str] = Field(
        None, description="Updated bounty text (null if cleared)"
    )


class ResearchStartResponse(BaseModel):
    """Response after initiating element re-search."""

    status: str = Field(description="Research status: started")
    checkId: str = Field(description="Check ID")
    claimId: str = Field(description="Claim ID")
    elementId: str = Field(description="Element ID being re-searched")


class ResearchStatusResponse(BaseModel):
    """Current status of an element re-search operation."""

    status: str = Field(description="Research status: idle, searching, or completed")
    message: Optional[str] = Field(None, description="Status message")
    newEvidenceCount: Optional[int] = Field(
        None, description="Number of new evidence items found (when completed)"
    )


# ============================================================================
# SSE token schema
# ============================================================================


class SSETokenResponse(BaseModel):
    """Short-lived token for SSE progress streaming."""

    token: str = Field(
        description="Check-scoped token (valid 5 minutes). Pass as ?token= in the EventSource URL."
    )
    expiresIn: int = Field(description="Token lifetime in seconds")
    streamUrl: str = Field(description="Full SSE endpoint URL with token appended")


# ============================================================================
# Select claims schema
# ============================================================================


class SelectClaimsResponse(BaseModel):
    """Response after claim selection — pipeline resumes with Phase 2."""

    status: str = Field(description="Operation result: selection_accepted")
    selectedCount: int = Field(description="Number of claims selected")
    checkId: str = Field(description="Check ID")
    message: str = Field(description="Confirmation message")


# ============================================================================
# Public check schemas
# ============================================================================


class PublicCheckMinimal(BaseModel):
    """Minimal public check data for OG card generation (no auth required)."""

    id: str = Field(description="Check ID")
    title: Optional[str] = Field(None, description="Derived title for display")
    sourceUrl: Optional[str] = Field(None, description="Source URL")
    sourceDomain: Optional[str] = Field(None, description="Source domain name")
    claimsCount: int = Field(description="Number of claims")
    sourcesCount: int = Field(description="Number of organised sources")
    totalSearchResults: int = Field(description="Total search results reviewed")
    evidenceCount: int = Field(description="Total evidence items")
    entryMode: Optional[str] = Field(None, description="article or direct")
    selectedClaimsCount: Optional[int] = Field(
        None, description="Number of selected claims"
    )
    topSources: List[str] = Field(description="Up to 5 prominent source names")


# ============================================================================
# Sources export schemas
# ============================================================================


class SourcesClaimSources(BaseModel):
    """Sources for a single claim with filter stage breakdown."""

    claimPosition: int = Field(description="Claim position (0-indexed)")
    claimText: str = Field(description="Claim text")
    included: List[Dict[str, Any]] = Field(
        description="Sources included in the final evidence set"
    )
    filtered: List[Dict[str, Any]] = Field(
        description="Sources excluded with filter stage and reason"
    )


class SourcesResponse(BaseModel):
    """All sources reviewed during evidence research, including filtered items."""

    checkId: str = Field(description="Check ID")
    totalSources: int = Field(description="Total raw sources reviewed")
    includedCount: int = Field(description="Sources included in final evidence set")
    filteredCount: int = Field(description="Sources filtered out")
    legacyCheck: bool = Field(
        description="Whether this is a pre-receipt-system check with limited data"
    )
    message: Optional[str] = Field(None, description="Status or info message")
    claims: Optional[List[SourcesClaimSources]] = Field(
        None, description="Per-claim source breakdown"
    )
    filterBreakdown: Optional[Dict[str, int]] = Field(
        None,
        description="Count of sources excluded at each pipeline stage",
    )


# ============================================================================
# Error response schemas
# ============================================================================


class ErrorResponse(BaseModel):
    """Standard error response body."""

    detail: str = Field(description="Human-readable error message")

    model_config = ConfigDict(
        json_schema_extra={"example": {"detail": "Check not found"}}
    )


class CreditLimitError(BaseModel):
    """Credit limit exceeded error (402)."""

    detail: str = Field(description="Error message with usage count and limit")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "detail": "Monthly limit reached (10/10 checks used). Please upgrade your plan for more checks."
            }
        }
    )


class PipelineErrorResponse(BaseModel):
    """Pipeline failure error (502)."""

    detail: str = Field(description="Pipeline error description")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"detail": "Pipeline error: content extraction failed"}
        }
    )


class TimeoutErrorResponse(BaseModel):
    """Pipeline timeout error (504)."""

    detail: str = Field(description="Timeout message")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"detail": "Pipeline timed out. Credits have been refunded."}
        }
    )
