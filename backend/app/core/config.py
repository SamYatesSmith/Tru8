from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = Field(..., env="DATABASE_URL")
    DATABASE_SSL: bool = Field(True, env="DATABASE_SSL")  # Set False for Fly.io internal network
    
    # Redis
    REDIS_URL: str = Field("redis://localhost:6379/0", env="REDIS_URL")
    
    # Qdrant
    QDRANT_URL: str = Field("http://localhost:6333", env="QDRANT_URL")
    QDRANT_API_KEY: str = Field("", env="QDRANT_API_KEY")
    
    # Auth
    CLERK_SECRET_KEY: str = Field(..., env="CLERK_SECRET_KEY")
    CLERK_PUBLISHABLE_KEY: str = Field(..., env="CLERK_PUBLISHABLE_KEY")
    CLERK_JWT_ISSUER: str = Field(..., env="CLERK_JWT_ISSUER")
    
    # APIs
    BRAVE_API_KEY: str = Field("", env="BRAVE_API_KEY")
    SERP_API_KEY: str = Field("", env="SERP_API_KEY")
    OPENAI_API_KEY: str = Field("", env="OPENAI_API_KEY")
    ANTHROPIC_API_KEY: str = Field("", env="ANTHROPIC_API_KEY")  # Deprecated - use GOOGLE_AI_API_KEY as backup
    GOOGLE_AI_API_KEY: str = Field("", env="GOOGLE_AI_API_KEY")  # Google AI Studio (Gemini) - backup LLM provider
    GOOGLE_FACTCHECK_API_KEY: str = Field("", env="GOOGLE_FACTCHECK_API_KEY")
    FOOTBALL_DATA_API_KEY: str = Field("", env="FOOTBALL_DATA_API_KEY")  # Football-Data.org for sports stats
    NOAA_API_KEY: str = Field("", env="NOAA_API_KEY")  # NOAA CDO for climate data
    ALPHA_VANTAGE_API_KEY: str = Field("", env="ALPHA_VANTAGE_API_KEY")  # Alpha Vantage for stocks, forex, crypto
    MARKETAUX_API_KEY: str = Field("", env="MARKETAUX_API_KEY")  # Marketaux for financial news
    FRED_API_KEY: str = Field("", env="FRED_API_KEY")  # FRED for economic data (interest rates, GDP, unemployment)
    WEATHER_API_KEY: str = Field("", env="WEATHER_API_KEY")  # WeatherAPI.com for weather forecasts
    COMPANIES_HOUSE_API_KEY: str = Field("", env="COMPANIES_HOUSE_API_KEY")  # UK company filings, directors
    
    # Storage
    S3_BUCKET: str = Field("tru8-uploads", env="S3_BUCKET")
    S3_ACCESS_KEY: str = Field("", env="S3_ACCESS_KEY")
    S3_SECRET_KEY: str = Field("", env="S3_SECRET_KEY")
    S3_ENDPOINT: str = Field("", env="S3_ENDPOINT")

    # Stripe Payments
    STRIPE_SECRET_KEY: str = Field("", env="STRIPE_SECRET_KEY")
    STRIPE_WEBHOOK_SECRET: str = Field("", env="STRIPE_WEBHOOK_SECRET")
    STRIPE_PRICE_ID_PRO: str = Field("", env="STRIPE_PRICE_ID_PRO")
    FRONTEND_URL: str = Field("http://localhost:3000", env="FRONTEND_URL")

    # Email Notifications (Resend)
    RESEND_API_KEY: str = Field("", env="RESEND_API_KEY")
    EMAIL_FROM_ADDRESS: str = Field("hello@trueight.com", env="EMAIL_FROM_ADDRESS")
    FEEDBACK_EMAIL: Optional[str] = Field(None, env="FEEDBACK_EMAIL")
    EMAIL_FROM_NAME: str = Field("Tru8", env="EMAIL_FROM_NAME")
    ENABLE_EMAIL_NOTIFICATIONS: bool = Field(True, env="ENABLE_EMAIL_NOTIFICATIONS")

    # Monitoring
    SENTRY_DSN: str = Field("", env="SENTRY_DSN")
    POSTHOG_API_KEY: str = Field("", env="POSTHOG_API_KEY")
    OTLP_ENDPOINT: str = Field("", env="OTLP_ENDPOINT")  # OpenTelemetry collector endpoint (e.g., http://localhost:4317)
    
    # App
    ENVIRONMENT: str = Field("development", env="ENVIRONMENT")
    DEBUG: bool = Field(False, env="DEBUG")  # MUST be False in production
    SECRET_KEY: str = Field(..., env="SECRET_KEY")
    # CORS_ORIGINS: Set via env var in production (e.g., '["https://tru8.com","https://app.tru8.com"]')
    # Default is localhost only - MUST override in production
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:3001", "http://localhost:8081", "http://127.0.0.1:3000", "http://127.0.0.1:3001"],
        env="CORS_ORIGINS"
    )

    # Admin emails that bypass credit limits (for testing)
    ADMIN_EMAILS: List[str] = Field(
        default=[],
        env="ADMIN_EMAILS"
    )

    # Rate Limits
    RATE_LIMIT_PER_MINUTE: int = Field(60, env="RATE_LIMIT_PER_MINUTE")
    MAX_CLAIMS_PER_CHECK: int = Field(12, env="MAX_CLAIMS_PER_CHECK")
    
    # Pipeline
    PIPELINE_TIMEOUT_SECONDS: int = Field(180, env="PIPELINE_TIMEOUT_SECONDS")
    CACHE_TTL_SECONDS: int = Field(3600, env="CACHE_TTL_SECONDS")
    
    # NLI & Verification
    NLI_CONFIDENCE_THRESHOLD: float = Field(0.7, env="NLI_CONFIDENCE_THRESHOLD")
    MAX_CONCURRENT_VERIFICATIONS: int = Field(5, env="MAX_CONCURRENT_VERIFICATIONS")
    VERIFICATION_TIMEOUT_SECONDS: int = Field(5, env="VERIFICATION_TIMEOUT_SECONDS")

    # ========== UNIFIED PIPELINE THRESHOLDS ==========
    # These thresholds are ALIGNED across all pipeline stages.
    # Do NOT create separate thresholds in individual files.
    # All stages should reference these values.

    # TIER 1: Lenient - Used for initial retrieval/filtering
    SIMILARITY_TIER1_LENIENT: float = Field(0.25, env="SIMILARITY_TIER1_LENIENT")

    # TIER 2: Standard - Used for display selection
    SIMILARITY_TIER2_STANDARD: float = Field(0.40, env="SIMILARITY_TIER2_STANDARD")

    # TIER 3: Strict - Used for high-confidence operations
    SIMILARITY_TIER3_STRICT: float = Field(0.60, env="SIMILARITY_TIER3_STRICT")

    # Credibility: Unified across pipeline
    CREDIBILITY_MINIMUM: float = Field(0.55, env="CREDIBILITY_MINIMUM")

    # Unknown source default - MUST be >= CREDIBILITY_MINIMUM
    UNKNOWN_SOURCE_CREDIBILITY: float = Field(0.55, env="UNKNOWN_SOURCE_CREDIBILITY")
    
    # Judge LLM
    JUDGE_MAX_TOKENS: int = Field(1000, env="JUDGE_MAX_TOKENS")
    JUDGE_TEMPERATURE: float = Field(0.3, env="JUDGE_TEMPERATURE")
    MAX_CONCURRENT_JUDGMENTS: int = Field(5, env="MAX_CONCURRENT_JUDGMENTS")

    # ========== PIPELINE IMPROVEMENT FEATURE FLAGS ==========
    # Phase 1 - Structural Integrity
    ENABLE_DOMAIN_CAPPING: bool = Field(True, env="ENABLE_DOMAIN_CAPPING")
    ENABLE_DEDUPLICATION: bool = Field(True, env="ENABLE_DEDUPLICATION")
    ENABLE_SOURCE_DIVERSITY: bool = Field(True, env="ENABLE_SOURCE_DIVERSITY")
    ENABLE_CONTEXT_PRESERVATION: bool = Field(True, env="ENABLE_CONTEXT_PRESERVATION")
    ENABLE_SAFETY_CHECKING: bool = Field(False, env="ENABLE_SAFETY_CHECKING")
    ENABLE_CITATION_ARCHIVAL: bool = Field(False, env="ENABLE_CITATION_ARCHIVAL")
    ENABLE_VERDICT_MONITORING: bool = Field(False, env="ENABLE_VERDICT_MONITORING")

    # Search Clarity Feature (MVP)
    ENABLE_SEARCH_CLARITY: bool = Field(default=True, env="ENABLE_SEARCH_CLARITY")
    QUERY_CONFIDENCE_THRESHOLD: float = Field(default=40.0, env="QUERY_CONFIDENCE_THRESHOLD")

    # Phase 1.5 - Semantic Intelligence
    ENABLE_FACTCHECK_API: bool = Field(True, env="ENABLE_FACTCHECK_API")
    ENABLE_TEMPORAL_CONTEXT: bool = Field(True, env="ENABLE_TEMPORAL_CONTEXT")  # Enabled: Extracts temporal markers from claims for date-specific queries

    # Fact-Check Parser (Programmatic parsing of fact-check articles)
    ENABLE_FACTCHECK_PARSING: bool = Field(False, env="ENABLE_FACTCHECK_PARSING")  # Parse fact-check articles for target claim extraction
    FACTCHECK_SIMILARITY_THRESHOLD: float = Field(0.7, env="FACTCHECK_SIMILARITY_THRESHOLD")  # Min similarity to keep fact-check evidence
    FACTCHECK_LOW_RELEVANCE_PENALTY: float = Field(0.1, env="FACTCHECK_LOW_RELEVANCE_PENALTY")  # Penalty for low-similarity fact-checks

    # Phase 2 - User Experience & Trust
    ENABLE_CLAIM_CLASSIFICATION: bool = Field(True, env="ENABLE_CLAIM_CLASSIFICATION")
    ENABLE_ENHANCED_EXPLAINABILITY: bool = Field(True, env="ENABLE_ENHANCED_EXPLAINABILITY")

    # Phase 3 - Critical Credibility Enhancements
    ENABLE_DOMAIN_CREDIBILITY_FRAMEWORK: bool = Field(True, env="ENABLE_DOMAIN_CREDIBILITY_FRAMEWORK")
    ENABLE_ABSTENTION_LOGIC: bool = Field(True, env="ENABLE_ABSTENTION_LOGIC")

    # Phase 3.5 - Source Quality Control (Week 9.5-10)
    ENABLE_SOURCE_VALIDATION: bool = Field(True, env="ENABLE_SOURCE_VALIDATION")
    # Aligned with CREDIBILITY_MINIMUM (unified threshold)
    SOURCE_CREDIBILITY_THRESHOLD: float = Field(0.55, env="SOURCE_CREDIBILITY_THRESHOLD")

    # Phase 6 - Source Diversity Enhancement
    # Boost credibility for evidence corroborated by multiple independent sources
    ENABLE_CORROBORATION_BOOST: bool = Field(True, env="ENABLE_CORROBORATION_BOOST")

    # Phase 4 - Legal Integration
    ENABLE_LEGAL_SEARCH: bool = Field(True, env="ENABLE_LEGAL_SEARCH")
    GOVINFO_API_KEY: Optional[str] = Field(None, env="GOVINFO_API_KEY")
    CONGRESS_API_KEY: Optional[str] = Field(None, env="CONGRESS_API_KEY")
    LEGAL_API_TIMEOUT_SECONDS: int = Field(10, env="LEGAL_API_TIMEOUT_SECONDS")
    LEGAL_CACHE_TTL_DAYS: int = Field(30, env="LEGAL_CACHE_TTL_DAYS")

    # Phase 5 - Government API Integration
    ENABLE_API_RETRIEVAL: bool = Field(True, env="ENABLE_API_RETRIEVAL")

    # Phase 6 - Judge Improvements (Week 12)
    EVIDENCE_SNIPPET_LENGTH: int = Field(400, env="EVIDENCE_SNIPPET_LENGTH")  # Increased from 150 to preserve context
    ENABLE_EVIDENCE_RELEVANCE_FILTER: bool = Field(False, env="ENABLE_EVIDENCE_RELEVANCE_FILTER")  # Filter low-relevance evidence
    RELEVANCE_THRESHOLD: float = Field(0.65, env="RELEVANCE_THRESHOLD")  # Minimum relevance score (0-1)

    # Semantic Similarity Filtering (Retrieve Stage)
    # Filters out irrelevant evidence BEFORE it reaches the judge
    # Prevents generic landing pages (e.g., "how to fact check" guides) from being used as evidence
    ENABLE_SEMANTIC_RELEVANCE_FILTER: bool = Field(True, env="ENABLE_SEMANTIC_RELEVANCE_FILTER")
    # Aligned with SIMILARITY_TIER1_LENIENT (unified threshold)
    SEMANTIC_SIMILARITY_THRESHOLD: float = Field(0.25, env="SEMANTIC_SIMILARITY_THRESHOLD")  # Min semantic similarity (0-1)

    # Domain Capping Configuration
    MAX_EVIDENCE_PER_DOMAIN: int = Field(3, env="MAX_EVIDENCE_PER_DOMAIN")  # Allow 3 results per domain for better evidence coverage
    DOMAIN_DIVERSITY_THRESHOLD: float = Field(0.6, env="DOMAIN_DIVERSITY_THRESHOLD")
    OUTSTANDING_SOURCE_THRESHOLD: float = Field(0.95, env="OUTSTANDING_SOURCE_THRESHOLD")

    # Global Domain Capping (cross-claim diversity enforcement)
    # Tightened from 5/25% to 3/15% to prevent single-source dominance (e.g., NYTimes appearing 5x)
    ENABLE_GLOBAL_DOMAIN_CAPPING: bool = Field(True, env="ENABLE_GLOBAL_DOMAIN_CAPPING")
    GLOBAL_MAX_PER_DOMAIN: int = Field(3, env="GLOBAL_MAX_PER_DOMAIN")  # Max sources from any domain across ALL claims
    GLOBAL_MAX_DOMAIN_RATIO: float = Field(0.15, env="GLOBAL_MAX_DOMAIN_RATIO")  # Max 15% from any single domain

    # Abstention Thresholds (Phase 3)
    # Lowered from 0.70 -> 0.60 and 0.65 -> 0.50 to reduce fence-sitting
    # MIN_SOURCES lowered from 3 to 2: For established scientific facts with
    # high-credibility sources, 2 sources is sufficient to take a position.
    MIN_SOURCES_FOR_VERDICT: int = Field(2, env="MIN_SOURCES_FOR_VERDICT")
    MIN_CREDIBILITY_THRESHOLD: float = Field(0.60, env="MIN_CREDIBILITY_THRESHOLD")
    MIN_CONSENSUS_STRENGTH: float = Field(0.50, env="MIN_CONSENSUS_STRENGTH")

    # NLI Signal Control (Phase 3 - Redundancy Removal)
    # When False: Judge makes verdict decisions without seeing NLI verdict/confidence scores
    # NLI still runs for evidence relevance filtering, but doesn't bias Judge's decision
    PASS_NLI_VERDICT_TO_JUDGE: bool = Field(False, env="PASS_NLI_VERDICT_TO_JUDGE")

    # ========== LLM RELEVANCE SCORER ==========
    # Replaces embedding-based ranking with LLM-based understanding of evidential value
    # Uses GPT-4o-mini to score evidence 1-5 based on how well it helps verify/refute claims
    ENABLE_LLM_RELEVANCE_SCORER: bool = Field(True, env="ENABLE_LLM_RELEVANCE_SCORER")
    LLM_RELEVANCE_MODEL: str = Field("gpt-4o-mini-2024-07-18", env="LLM_RELEVANCE_MODEL")
    LLM_RELEVANCE_MIN_SCORE: int = Field(4, env="LLM_RELEVANCE_MIN_SCORE")  # Keep evidence with score >= 4
    LLM_RELEVANCE_MAX_EVIDENCE: int = Field(50, env="LLM_RELEVANCE_MAX_EVIDENCE")  # Max items to score per call
    LLM_RELEVANCE_CACHE_TTL: int = Field(3600, env="LLM_RELEVANCE_CACHE_TTL")  # Cache TTL in seconds (1 hour)

    # Rollout Controls
    FEATURE_ROLLOUT_PERCENTAGE: int = Field(0, env="FEATURE_ROLLOUT_PERCENTAGE")
    INTERNAL_USER_IDS: List[str] = Field([], env="INTERNAL_USER_IDS")

    # ========== BETA TESTING CONFIGURATION ==========
    # Comma-separated list of email addresses that get unlimited checks during beta
    # Example: BETA_TESTER_EMAILS=["alice@example.com","bob@example.com"]
    BETA_TESTER_EMAILS: List[str] = Field([], env="BETA_TESTER_EMAILS")

    # When False, subscription endpoints return "coming soon" message
    # Set to True when ready to accept paid subscriptions
    SUBSCRIPTIONS_ENABLED: bool = Field(False, env="SUBSCRIPTIONS_ENABLED")

    # ========== PHASE 1: ACCURACY IMPROVEMENTS ==========
    # DeBERTa NLI Model Swap (Phase 1.1)
    ENABLE_DEBERTA_NLI: bool = Field(False, env="ENABLE_DEBERTA_NLI")

    # Judge Few-Shot Prompting (Phase 1.2)
    ENABLE_JUDGE_FEW_SHOT: bool = Field(True, env="ENABLE_JUDGE_FEW_SHOT")  # ENABLED: Provides concrete examples to guide judge reasoning

    # Cross-Encoder Evidence Reranking (Phase 1.3)
    ENABLE_CROSS_ENCODER_RERANK: bool = Field(False, env="ENABLE_CROSS_ENCODER_RERANK")

    # ========== TIER 1 IMPROVEMENTS (2025-01-17) ==========
    # Query Formulation Enhancement
    ENABLE_QUERY_EXPANSION: bool = Field(False, env="ENABLE_QUERY_EXPANSION")
    QUERY_EXPANSION_SYNONYMS: int = Field(2, env="QUERY_EXPANSION_SYNONYMS")
    QUERY_TEMPORAL_BOOST: bool = Field(True, env="QUERY_TEMPORAL_BOOST")

    # Semantic Snippet Extraction
    ENABLE_SEMANTIC_SNIPPET_EXTRACTION: bool = Field(True, env="ENABLE_SEMANTIC_SNIPPET_EXTRACTION")  # ENABLED: Extract claim-relevant sentences using embeddings
    SNIPPET_SEMANTIC_THRESHOLD: float = Field(0.65, env="SNIPPET_SEMANTIC_THRESHOLD")
    SNIPPET_CONTEXT_SENTENCES: int = Field(2, env="SNIPPET_CONTEXT_SENTENCES")

    # Primary Source Prioritization
    ENABLE_PRIMARY_SOURCE_DETECTION: bool = Field(False, env="ENABLE_PRIMARY_SOURCE_DETECTION")
    PRIMARY_SOURCE_BOOST: float = Field(0.25, env="PRIMARY_SOURCE_BOOST")
    SECONDARY_SOURCE_PENALTY: float = Field(0.15, env="SECONDARY_SOURCE_PENALTY")

    # ========== RHETORICAL CONTEXT DETECTION ==========
    # Detect when evidence sources describe rhetorical intent (sarcasm, mockery, satire)
    # More reliable than direct sarcasm detection - trusts journalists' characterization
    ENABLE_RHETORICAL_CONTEXT: bool = Field(True, env="ENABLE_RHETORICAL_CONTEXT")

    # ========== ARTICLE-LEVEL CLASSIFICATION ==========
    # LLM-based article classification (runs once per check, not per claim)
    # Replaces per-claim spaCy NER domain detection with ~95% accuracy
    ENABLE_ARTICLE_CLASSIFICATION: bool = Field(True, env="ENABLE_ARTICLE_CLASSIFICATION")
    ARTICLE_CLASSIFICATION_MODEL: str = Field("gpt-4o-mini-2024-07-18", env="ARTICLE_CLASSIFICATION_MODEL")

    # ========== QUERY PLANNING AGENT ==========
    # LLM-powered batch query planning for semantic claim understanding
    # Generates targeted queries based on claim type (squad, stats, contract, etc.)
    ENABLE_QUERY_PLANNING: bool = Field(True, env="ENABLE_QUERY_PLANNING")
    QUERY_PLANNING_MODEL: str = Field("gpt-4o-mini-2024-07-18", env="QUERY_PLANNING_MODEL")
    QUERY_PLANNING_TIMEOUT: int = Field(30, env="QUERY_PLANNING_TIMEOUT")

    # Fallback policy: When content extraction fails (403/timeout), should we use search snippets?
    # True = Keep snippet as low-quality fallback (marked in metadata for downstream weighting)
    # False = Drop sources entirely if content extraction fails
    ALLOW_SNIPPET_FALLBACK: bool = Field(True, env="ALLOW_SNIPPET_FALLBACK")

    # ========== DOMAIN-AWARE EVIDENCE FRESHNESS ==========
    # Enable claim-type-based freshness filtering for evidence retrieval
    # When enabled, squad_composition claims get fresher evidence (1-2 weeks)
    # vs contract_info claims which can use older evidence (up to 6 months)
    ENABLE_FRESHNESS_BY_CLAIM_TYPE: bool = Field(True, env="ENABLE_FRESHNESS_BY_CLAIM_TYPE")

    @property
    def nli_model_name(self) -> str:
        """Dynamic NLI model selection based on feature flag"""
        if self.ENABLE_DEBERTA_NLI:
            # Using DeBERTa-v3-LARGE for better FEVER-trained fact-checking
            # Trained on MNLI, FEVER, ANLI, LingNLI, WANLI (SNLI excluded for quality)
            # Better at distinguishing "NOT ENOUGH INFO" from "CONTRADICTION"
            return "MoritzLaurer/DeBERTa-v3-large-mnli-fever-anli-ling-wanli"
        return "facebook/bart-large-mnli"

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()