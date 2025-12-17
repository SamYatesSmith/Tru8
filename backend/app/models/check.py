from typing import Optional, List
from datetime import datetime
from sqlmodel import Field, SQLModel, Relationship, JSON
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
import uuid

def generate_uuid() -> str:
    return str(uuid.uuid4())

class Check(SQLModel, table=True):
    id: str = Field(default_factory=generate_uuid, primary_key=True)
    user_id: str = Field(foreign_key="user.id", index=True)
    input_type: str  # 'url', 'text', 'image', 'video'
    input_content: str = Field(sa_column=Column(JSONB))  # Store as JSONB for PostgreSQL optimization
    input_url: Optional[str] = None
    status: str = Field(default="pending")  # 'pending', 'processing', 'completed', 'failed'
    credits_used: int = Field(default=1)
    processing_time_ms: Optional[int] = None
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    # Article context for holistic judgment
    article_excerpt: Optional[str] = Field(
        default=None,
        max_length=5000,
        description="First 5000 characters of article for context-aware fact-checking"
    )

    # Explainability fields (Phase 2, Week 6.5-7.5)
    decision_trail: Optional[str] = Field(default=None, sa_column=Column(JSONB))  # Full decision trail
    transparency_score: Optional[float] = Field(default=None, ge=0, le=1)  # How explainable the verdict is (0-1)

    # Overall Summary fields (for PDF & UI display)
    overall_summary: Optional[str] = Field(default=None, description="LLM-generated executive summary of all claims")
    credibility_score: Optional[int] = Field(default=None, ge=0, le=100, description="Overall credibility score 0-100")
    claims_supported: Optional[int] = Field(default=0, description="Count of supported claims")
    claims_contradicted: Optional[int] = Field(default=0, description="Count of contradicted claims")
    claims_uncertain: Optional[int] = Field(default=0, description="Count of uncertain claims")

    # Search Clarity fields (MVP Feature)
    user_query: Optional[str] = Field(
        default=None,
        max_length=200,
        description="User's specific question about the content"
    )
    query_response: Optional[str] = Field(
        default=None,
        description="Answer to user's query based on evidence"
    )
    query_confidence: Optional[float] = Field(
        default=None,
        ge=0,
        le=100,
        description="Confidence in query answer (0-100)"
    )
    query_sources: Optional[str] = Field(
        default=None,
        sa_column=Column(JSONB),
        description="Evidence sources used for query response (JSON array)"
    )

    # Government API Integration fields (Phase 5)
    api_sources_used: Optional[str] = Field(
        default=None,
        sa_column=Column(JSONB),
        description="List of government APIs queried for this check"
    )
    api_call_count: Optional[int] = Field(
        default=0,
        description="Total number of API calls made"
    )
    api_coverage_percentage: Optional[float] = Field(
        default=None,
        ge=0,
        le=100,
        description="Percentage of evidence from government APIs (0-100)"
    )

    # Article Classification fields (LLM-based, runs once per check)
    article_domain: Optional[str] = Field(
        default=None,
        max_length=50,
        description="Primary domain classification (Sports, Politics, Finance, etc.)"
    )
    article_secondary_domains: Optional[str] = Field(
        default=None,
        sa_column=Column(JSONB),
        description="Secondary domains for cross-domain articles (JSON array)"
    )
    article_jurisdiction: Optional[str] = Field(
        default=None,
        max_length=20,
        description="Geographic jurisdiction (UK, US, EU, Global)"
    )
    article_classification_confidence: Optional[int] = Field(
        default=None,
        ge=0,
        le=100,
        description="Confidence in article classification (0-100)"
    )
    article_classification_source: Optional[str] = Field(
        default=None,
        max_length=30,
        description="Classification source (cache_pattern, cache_url, llm_primary, fallback_general)"
    )

    # Raw Sources List feature (Pro feature - shows all sources reviewed)
    raw_sources_count: Optional[int] = Field(
        default=0,
        description="Total number of sources reviewed before filtering"
    )

    # Relationships
    user: "User" = Relationship(back_populates="checks")
    claims: List["Claim"] = Relationship(back_populates="check")
    raw_evidence: List["RawEvidence"] = Relationship(back_populates="check")

class Claim(SQLModel, table=True):
    id: str = Field(default_factory=generate_uuid, primary_key=True)
    check_id: str = Field(foreign_key="check.id", index=True)
    text: str
    verdict: str  # 'supported', 'contradicted', 'uncertain', 'insufficient_evidence', 'conflicting_expert_opinion', 'needs_primary_source', 'outdated_claim', 'lacks_context'
    confidence: float = Field(ge=0, le=100)  # 0-100
    rationale: str
    position: int  # Order in the check
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Temporal context fields (Phase 1.5, Week 4.5-5.5)
    temporal_markers: Optional[str] = Field(default=None, sa_column=Column(JSONB))  # Detected time markers
    time_reference: Optional[str] = None  # 'present', 'recent_past', 'specific_year', 'historical', 'future'
    is_time_sensitive: bool = Field(default=False)  # True if claim requires temporal context

    # Classification fields (Phase 2, Week 5.5-6.5)
    claim_type: Optional[str] = None  # 'factual', 'opinion', 'prediction', 'personal_experience', 'legal'
    is_verifiable: bool = Field(default=True)  # False for opinions, predictions, personal experiences
    verifiability_reason: Optional[str] = None  # Explanation of why claim is/isn't verifiable
    legal_metadata: Optional[str] = Field(default=None, sa_column=Column(JSONB))  # Legal citations, jurisdiction, etc. for legal claims

    # Explainability fields (Phase 2, Week 6.5-7.5)
    uncertainty_explanation: Optional[str] = None  # Explanation for uncertain verdicts
    confidence_breakdown: Optional[str] = Field(default=None, sa_column=Column(JSONB))  # Detailed confidence factors

    # Consensus & Abstention fields (Phase 3, Week 8)
    abstention_reason: Optional[str] = None  # Why we abstained from making a verdict
    min_requirements_met: bool = Field(default=False)  # Did evidence meet minimum quality requirements
    consensus_strength: Optional[float] = Field(default=None, ge=0, le=1)  # Credibility-weighted agreement (0-1)

    # Context Preservation (Context Improvement)
    subject_context: Optional[str] = Field(default=None, description="Main subject/topic the claim is about")
    key_entities: Optional[str] = Field(default=None, sa_column=Column(JSONB), description="Key entities mentioned in claim")
    source_title: Optional[str] = Field(default=None, description="Title of source article")
    source_url: Optional[str] = Field(default=None, description="URL of source article")
    source_date: Optional[str] = Field(default=None, description="Publication date of source article")

    # Temporal Drift Comparison fields (API current data vs claimed values)
    current_verified_data: Optional[str] = Field(
        default=None,
        sa_column=Column(JSONB),
        description="Current authoritative data from APIs for temporal comparison with claimed values"
    )

    # Rhetorical Context Detection fields (sarcasm, mockery, satire detection via source analysis)
    rhetorical_context: Optional[str] = Field(
        default=None,
        sa_column=Column(JSONB),
        description="Rhetorical context detected from evidence sources (sarcasm, mockery, satire markers)"
    )
    has_rhetorical_context: bool = Field(
        default=False,
        description="True if evidence sources describe rhetorical intent (sarcasm, mockery, etc.)"
    )
    rhetorical_style: Optional[str] = Field(
        default=None,
        max_length=30,
        description="Primary rhetorical style detected (sarcasm, mockery, satire, joking, inflammatory, hyperbole)"
    )

    # Relationships
    check: Check = Relationship(back_populates="claims")
    evidence: List["Evidence"] = Relationship(back_populates="claim")

class Evidence(SQLModel, table=True):
    id: str = Field(default_factory=generate_uuid, primary_key=True)
    claim_id: str = Field(foreign_key="claim.id", index=True)
    source: str  # Publisher name
    url: str
    title: str
    snippet: str
    published_date: Optional[datetime] = None
    relevance_score: float = Field(ge=0, le=1)  # 0-1
    credibility_score: float = Field(default=0.6, ge=0, le=1)  # 0-1 (source trustworthiness)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Deduplication fields (Phase 1, Week 2)
    content_hash: Optional[str] = None  # MD5 hash of normalized content
    is_syndicated: bool = Field(default=False)  # True if content duplicated elsewhere
    original_source_url: Optional[str] = None  # URL of original source if syndicated

    # Source independence fields (Phase 1, Week 3)
    parent_company: Optional[str] = None  # Media company owner (e.g., "News Corp")
    independence_flag: Optional[str] = None  # 'independent', 'corporate', 'state-funded', 'unknown'
    domain_cluster_id: Optional[int] = None  # Unique ID for ownership group

    # Fact-check fields (Phase 1.5, Week 4)
    is_factcheck: bool = Field(default=False)  # True if from fact-checking organization
    factcheck_publisher: Optional[str] = None  # "Snopes", "Full Fact", etc.
    factcheck_rating: Optional[str] = None  # Original rating text
    factcheck_date: Optional[datetime] = None  # When fact-check was published
    source_type: Optional[str] = None  # 'factcheck', 'news', 'academic', 'government', 'general'

    # Fact-check Parsing fields (Programmatic parser)
    factcheck_target_claim: Optional[str] = None  # The claim the fact-checker is checking (not our claim)
    factcheck_claim_similarity: Optional[float] = Field(default=None, ge=0, le=1)  # Similarity between our claim and their target claim
    factcheck_parse_success: bool = Field(default=False)  # True if parsing succeeded
    factcheck_low_relevance: bool = Field(default=False)  # True if similarity < threshold

    # Temporal context fields (Phase 1.5, Week 4.5-5.5)
    temporal_relevance_score: Optional[float] = Field(default=None, ge=0, le=1)  # How temporally relevant (0-1)
    extracted_date: Optional[str] = None  # Date extracted from content
    is_time_sensitive: bool = Field(default=False)  # True if evidence relates to time-sensitive claim
    temporal_window: Optional[str] = None  # 'last_30_days', 'last_90_days', 'year_YYYY', 'timeless'

    # Domain Credibility Framework fields (Phase 3, Week 9)
    tier: Optional[str] = None  # 'tier1', 'tier2', 'tier3', 'general', 'blacklist', 'flagged', 'excluded'
    risk_flags: Optional[str] = Field(default=None, sa_column=Column(JSONB))  # List of risk indicators
    credibility_reasoning: Optional[str] = None  # Explanation of credibility score
    risk_level: Optional[str] = None  # 'none', 'low', 'medium', 'high'
    risk_warning: Optional[str] = None  # User-facing warning message

    # Citation Precision & NLI Context (Phase 2, Week 10)
    page_number: Optional[int] = Field(default=None, description="Page number in PDF/document")
    context_before: Optional[str] = Field(default=None, description="Text before snippet")
    context_after: Optional[str] = Field(default=None, description="Text after snippet")
    nli_stance: Optional[str] = Field(default=None, description="'supporting'|'contradicting'|'neutral'")
    nli_confidence: Optional[float] = Field(default=None, ge=0, le=1, description="NLI confidence score 0-1")
    nli_entailment: Optional[float] = Field(default=None, ge=0, le=1, description="Entailment probability")
    nli_contradiction: Optional[float] = Field(default=None, ge=0, le=1, description="Contradiction probability")

    # Government API Integration fields (Phase 5)
    api_metadata: Optional[str] = Field(
        default=None,
        sa_column=Column(JSONB),
        description="API-specific response metadata"
    )
    external_source_provider: Optional[str] = Field(
        default=None,
        max_length=200,
        description="API name (e.g., 'ONS Economic Statistics', 'PubMed')"
    )

    # Primary Source Detection fields (Tier 1 Improvement, 2025-01-17)
    is_primary_source: bool = Field(
        default=False,
        description="True if evidence is original research, government data, or official report"
    )
    primary_indicators: Optional[str] = Field(
        default=None,
        sa_column=Column(JSONB),
        description="JSON array of primary source indicators detected (e.g., ['academic_journal', 'peer_reviewed'])"
    )

    # Relationships
    claim: Claim = Relationship(back_populates="evidence")


class RawEvidence(SQLModel, table=True):
    """All sources reviewed during evidence retrieval, including filtered ones.

    This table stores every source that was considered during fact-checking,
    not just the final filtered evidence. Used for the Pro "Sources" feature
    that shows users all sources reviewed with filtering reasons.
    """
    id: str = Field(default_factory=generate_uuid, primary_key=True)
    check_id: str = Field(foreign_key="check.id", index=True)
    claim_position: int = Field(description="Which claim this evidence was retrieved for (0-indexed)")
    claim_text: Optional[str] = Field(default=None, max_length=500, description="Text of the claim for display")

    # Core evidence fields
    source: str = Field(description="Publisher/source name")
    url: str = Field(description="Source URL")
    title: str = Field(description="Article/page title")
    snippet: str = Field(description="Relevant text excerpt")
    published_date: Optional[datetime] = None
    relevance_score: float = Field(default=0.0, ge=0, le=1, description="Semantic relevance to claim (0-1)")
    credibility_score: float = Field(default=0.6, ge=0, le=1, description="Source credibility (0-1)")

    # Filtering metadata - the key feature
    is_included: bool = Field(default=False, description="True if this source made it to final evidence")
    filter_stage: Optional[str] = Field(
        default=None,
        description="Which filter stage excluded this source: credibility|temporal|dedup|diversity|domain_cap|validation|extraction_failed"
    )
    filter_reason: Optional[str] = Field(
        default=None,
        description="Human-readable explanation of why source was filtered"
    )

    # Display metadata
    tier: Optional[str] = Field(default=None, description="Source tier: tier1|tier2|tier3|general|blacklist")
    is_factcheck: bool = Field(default=False, description="True if from fact-checking organization")
    external_source_provider: Optional[str] = Field(
        default=None,
        max_length=200,
        description="API source if from government/authoritative API (e.g., 'ONS', 'PubMed')"
    )

    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    check: Check = Relationship(back_populates="raw_evidence")