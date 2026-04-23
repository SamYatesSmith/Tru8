from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # Database — normalised to async driver on init
    DATABASE_URL: str = Field(..., env="DATABASE_URL")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Railway/Heroku provide postgresql:// or postgres:// URLs.
        # Normalise to postgresql+asyncpg:// for the async engine.
        if self.DATABASE_URL.startswith("postgres://"):
            object.__setattr__(
                self,
                "DATABASE_URL",
                self.DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1),
            )
        elif (
            self.DATABASE_URL.startswith("postgresql://")
            and "+asyncpg" not in self.DATABASE_URL
        ):
            object.__setattr__(
                self,
                "DATABASE_URL",
                self.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1),
            )

    DATABASE_SSL: bool = Field(
        True, env="DATABASE_SSL"
    )  # Set False for Fly.io internal network

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
    SERPER_API_KEY: str = Field("", env="SERPER_API_KEY")
    OPENAI_API_KEY: str = Field("", env="OPENAI_API_KEY")
    ANTHROPIC_API_KEY: str = Field(
        "", env="ANTHROPIC_API_KEY"
    )  # Deprecated - use GOOGLE_AI_API_KEY as backup
    GOOGLE_AI_API_KEY: str = Field(
        "", env="GOOGLE_AI_API_KEY"
    )  # Google AI Studio (Gemini) - primary LLM provider

    # LLM Provider Configuration
    PRIMARY_LLM_PROVIDER: str = Field(
        "google", env="PRIMARY_LLM_PROVIDER"
    )  # "google" or "openai"
    GOOGLE_LLM_MODEL: str = Field(
        "gemini-2.5-flash-lite", env="GOOGLE_LLM_MODEL"
    )  # Gemini model for all LLM calls
    GOOGLE_FACTCHECK_API_KEY: str = Field("", env="GOOGLE_FACTCHECK_API_KEY")
    FOOTBALL_DATA_API_KEY: str = Field(
        "", env="FOOTBALL_DATA_API_KEY"
    )  # Football-Data.org for sports stats
    NOAA_API_KEY: str = Field("", env="NOAA_API_KEY")  # NOAA CDO for climate data
    ALPHA_VANTAGE_API_KEY: str = Field(
        "", env="ALPHA_VANTAGE_API_KEY"
    )  # Alpha Vantage for stocks, forex, crypto
    MARKETAUX_API_KEY: str = Field(
        "", env="MARKETAUX_API_KEY"
    )  # Marketaux for financial news
    FRED_API_KEY: str = Field(
        "", env="FRED_API_KEY"
    )  # FRED for economic data (interest rates, GDP, unemployment)
    WEATHER_API_KEY: str = Field(
        "", env="WEATHER_API_KEY"
    )  # WeatherAPI.com for weather forecasts
    COMPANIES_HOUSE_API_KEY: str = Field(
        "", env="COMPANIES_HOUSE_API_KEY"
    )  # UK company filings, directors
    YOUTUBE_API_KEY: str = Field(
        "", env="YOUTUBE_API_KEY"
    )  # YouTube Data API v3 for video recommendations (E14)
    NCBI_CONTACT_EMAIL: str = Field(
        "hello@trueight.com", env="NCBI_CONTACT_EMAIL"
    )  # NCBI politeness contact — included in PubMed eutils params to avoid silent throttling (A2)

    # Storage
    S3_BUCKET: str = Field("tru8-uploads", env="S3_BUCKET")
    S3_ACCESS_KEY: str = Field("", env="S3_ACCESS_KEY")
    S3_SECRET_KEY: str = Field("", env="S3_SECRET_KEY")
    S3_ENDPOINT: str = Field("", env="S3_ENDPOINT")
    S3_REGION: str = Field("eu-north-1", env="S3_REGION")

    # Stripe Payments
    STRIPE_SECRET_KEY: str = Field("", env="STRIPE_SECRET_KEY")
    STRIPE_WEBHOOK_SECRET: str = Field("", env="STRIPE_WEBHOOK_SECRET")
    STRIPE_PRICE_ID_PRO: str = Field("", env="STRIPE_PRICE_ID_PRO")
    STRIPE_PRICE_ID_DEVELOPER: str = Field("", env="STRIPE_PRICE_ID_DEVELOPER")
    STRIPE_PRICE_ID_CREDIT_PACK_5: str = Field("", env="STRIPE_PRICE_ID_CREDIT_PACK_5")
    STRIPE_PRICE_ID_CREDIT_PACK_20: str = Field(
        "", env="STRIPE_PRICE_ID_CREDIT_PACK_20"
    )
    STRIPE_PRICE_ID_CREDIT_PACK_100: str = Field(
        "", env="STRIPE_PRICE_ID_CREDIT_PACK_100"
    )
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
    OTLP_ENDPOINT: str = Field(
        "", env="OTLP_ENDPOINT"
    )  # OpenTelemetry collector endpoint (e.g., http://localhost:4317)

    # App
    ENVIRONMENT: str = Field("development", env="ENVIRONMENT")
    DEBUG: bool = Field(False, env="DEBUG")  # MUST be False in production
    SECRET_KEY: str = Field(..., env="SECRET_KEY")
    # CORS_ORIGINS: Set via env var in production (e.g., '["https://tru8.com","https://app.tru8.com"]')
    # Default is localhost only - MUST override in production
    CORS_ORIGINS: List[str] = Field(
        default=[
            "http://localhost:3000",
            "http://localhost:3001",
            "http://localhost:8081",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:3001",
        ],
        env="CORS_ORIGINS",
    )

    # Admin emails that bypass credit limits (for testing)
    ADMIN_EMAILS: List[str] = Field(default=[], env="ADMIN_EMAILS")

    # Rate Limits
    RATE_LIMIT_PER_MINUTE: int = Field(60, env="RATE_LIMIT_PER_MINUTE")
    MAX_CLAIMS_PER_CHECK: int = Field(12, env="MAX_CLAIMS_PER_CHECK")

    # Pipeline
    PIPELINE_TIMEOUT_SECONDS: int = Field(180, env="PIPELINE_TIMEOUT_SECONDS")
    CACHE_TTL_SECONDS: int = Field(3600, env="CACHE_TTL_SECONDS")

    # ========== SCORING MODE ==========
    # LLM relevance scorer is advisory-only: annotates scores but never vetoes evidence.

    # ========== UNIFIED PIPELINE THRESHOLDS ==========
    # These thresholds are ALIGNED across all pipeline stages.
    # Do NOT create separate thresholds in individual files.
    # All stages should reference these values.

    # TIER 1: Lenient - Used for initial retrieval/filtering
    SIMILARITY_TIER1_LENIENT: float = Field(0.25, env="SIMILARITY_TIER1_LENIENT")

    # TIER 2: Standard - Used for display selection
    SIMILARITY_TIER2_STANDARD: float = Field(0.40, env="SIMILARITY_TIER2_STANDARD")

    # Unknown source default - lower than known sources to signal unvetted status
    # Sources not in credibility database are treated with skepticism
    UNKNOWN_SOURCE_CREDIBILITY: float = Field(0.40, env="UNKNOWN_SOURCE_CREDIBILITY")

    # ========== PIPELINE IMPROVEMENT FEATURE FLAGS ==========

    # Search Clarity Feature (MVP)
    ENABLE_SEARCH_CLARITY: bool = Field(default=True, env="ENABLE_SEARCH_CLARITY")
    QUERY_CONFIDENCE_THRESHOLD: float = Field(
        default=40.0, env="QUERY_CONFIDENCE_THRESHOLD"
    )

    # Phase 1.5 - Semantic Intelligence
    ENABLE_FACTCHECK_API: bool = Field(True, env="ENABLE_FACTCHECK_API")
    ENABLE_TEMPORAL_CONTEXT: bool = Field(
        True, env="ENABLE_TEMPORAL_CONTEXT"
    )  # Enabled: Extracts temporal markers from claims for date-specific queries

    # Phase 2 - User Experience & Trust
    ENABLE_CLAIM_CLASSIFICATION: bool = Field(True, env="ENABLE_CLAIM_CLASSIFICATION")

    # Source credibility threshold (used for cache skip in workers)
    SOURCE_CREDIBILITY_THRESHOLD: float = Field(
        0.55, env="SOURCE_CREDIBILITY_THRESHOLD"
    )

    # Phase 4 - Legal Integration
    ENABLE_LEGAL_SEARCH: bool = Field(True, env="ENABLE_LEGAL_SEARCH")
    GOVINFO_API_KEY: Optional[str] = Field(None, env="GOVINFO_API_KEY")
    CONGRESS_API_KEY: Optional[str] = Field(None, env="CONGRESS_API_KEY")
    LEGAL_API_TIMEOUT_SECONDS: int = Field(10, env="LEGAL_API_TIMEOUT_SECONDS")
    LEGAL_CACHE_TTL_DAYS: int = Field(30, env="LEGAL_CACHE_TTL_DAYS")

    # Phase 5 - Government API Integration
    ENABLE_API_RETRIEVAL: bool = Field(True, env="ENABLE_API_RETRIEVAL")

    # Evidence snippet length
    EVIDENCE_SNIPPET_LENGTH: int = Field(
        1000, env="EVIDENCE_SNIPPET_LENGTH"
    )  # PQ-01: Increased from 400 to give mapper sufficient context for nuanced relationship determination

    # Evidence distillation
    ENABLE_EVIDENCE_DISTILLATION: bool = Field(True, env="ENABLE_EVIDENCE_DISTILLATION")
    DISTIL_MODEL: str = Field("gemini-2.5-flash-lite", env="DISTIL_MODEL")
    DISTIL_TIMEOUT: float = Field(15.0, env="DISTIL_TIMEOUT")
    DISTIL_MAX_FACTS_PER_ITEM: int = Field(8, env="DISTIL_MAX_FACTS_PER_ITEM")
    DISTIL_MIN_TEXT_LENGTH: int = Field(500, env="DISTIL_MIN_TEXT_LENGTH")

    # Domain Capping Configuration
    MAX_EVIDENCE_PER_DOMAIN: int = Field(
        3, env="MAX_EVIDENCE_PER_DOMAIN"
    )  # Allow 3 results per domain for better evidence coverage

    # Global Domain Capping (cross-claim diversity enforcement)
    # Tightened from 5/25% to 3/15% to prevent single-source dominance (e.g., NYTimes appearing 5x)
    ENABLE_GLOBAL_DOMAIN_CAPPING: bool = Field(True, env="ENABLE_GLOBAL_DOMAIN_CAPPING")
    GLOBAL_MAX_PER_DOMAIN: int = Field(
        3, env="GLOBAL_MAX_PER_DOMAIN"
    )  # Max sources from any domain across ALL claims
    GLOBAL_MAX_DOMAIN_RATIO: float = Field(
        0.20, env="GLOBAL_MAX_DOMAIN_RATIO"
    )  # Max 20% from any single domain

    # Max claims a single URL can appear in during cross-claim dedup (1 = current behavior)
    # Setting to 2 allows a URL to legitimately support 2 related claims
    MAX_CLAIMS_PER_URL: int = Field(2, env="MAX_CLAIMS_PER_URL")

    # Minimum evidence thresholds (used by cache quality gate)
    MIN_SOURCES_FOR_CACHE: int = Field(2, env="MIN_SOURCES_FOR_CACHE")

    # ========== LLM RELEVANCE SCORER ==========
    # Replaces embedding-based ranking with LLM-based understanding of evidential value
    # Uses GPT-4o-mini to score evidence 1-5 based on how well it helps verify/refute claims
    ENABLE_LLM_RELEVANCE_SCORER: bool = Field(True, env="ENABLE_LLM_RELEVANCE_SCORER")
    LLM_RELEVANCE_MODEL: str = Field(
        "gpt-4o-mini-2024-07-18", env="LLM_RELEVANCE_MODEL"
    )
    # LLM_RELEVANCE_MIN_SCORE removed — scorer is advisory-only, no threshold filtering
    LLM_RELEVANCE_MAX_EVIDENCE: int = Field(
        50, env="LLM_RELEVANCE_MAX_EVIDENCE"
    )  # Max items to score per call
    LLM_RELEVANCE_CACHE_TTL: int = Field(
        3600, env="LLM_RELEVANCE_CACHE_TTL"
    )  # Cache TTL in seconds (1 hour)

    # ========== BETA TESTING CONFIGURATION ==========
    # Comma-separated list of email addresses that get unlimited checks during beta
    # Example: BETA_TESTER_EMAILS=["alice@example.com","bob@example.com"]
    BETA_TESTER_EMAILS: List[str] = Field([], env="BETA_TESTER_EMAILS")

    # When False, subscription endpoints return "coming soon" message
    # Set to True when ready to accept paid subscriptions
    SUBSCRIPTIONS_ENABLED: bool = Field(False, env="SUBSCRIPTIONS_ENABLED")

    # ========== TIER 1 IMPROVEMENTS (2025-01-17) ==========
    QUERY_TEMPORAL_BOOST: bool = Field(True, env="QUERY_TEMPORAL_BOOST")

    # Semantic Snippet Extraction
    ENABLE_SEMANTIC_SNIPPET_EXTRACTION: bool = Field(
        True, env="ENABLE_SEMANTIC_SNIPPET_EXTRACTION"
    )  # ENABLED: Extract claim-relevant sentences using embeddings
    SNIPPET_SEMANTIC_THRESHOLD: float = Field(0.65, env="SNIPPET_SEMANTIC_THRESHOLD")
    SNIPPET_CONTEXT_SENTENCES: int = Field(2, env="SNIPPET_CONTEXT_SENTENCES")

    # ========== RHETORICAL CONTEXT DETECTION ==========
    # Detect when evidence sources describe rhetorical intent (sarcasm, mockery, satire)
    # More reliable than direct sarcasm detection - trusts journalists' characterization
    ENABLE_RHETORICAL_CONTEXT: bool = Field(True, env="ENABLE_RHETORICAL_CONTEXT")

    # ========== ARTICLE-LEVEL CLASSIFICATION ==========
    # LLM-based article classification (runs once per check, not per claim)
    # Replaces per-claim spaCy NER domain detection with ~95% accuracy
    ENABLE_ARTICLE_CLASSIFICATION: bool = Field(
        True, env="ENABLE_ARTICLE_CLASSIFICATION"
    )
    ARTICLE_CLASSIFICATION_MODEL: str = Field(
        "gpt-4o-mini-2024-07-18", env="ARTICLE_CLASSIFICATION_MODEL"
    )

    # ========== QUERY PLANNING AGENT ==========
    # LLM-powered batch query planning for semantic claim understanding
    # Generates targeted queries based on claim type (squad, stats, contract, etc.)
    ENABLE_QUERY_PLANNING: bool = Field(True, env="ENABLE_QUERY_PLANNING")
    QUERY_PLANNING_MODEL: str = Field(
        "gpt-4o-mini-2024-07-18", env="QUERY_PLANNING_MODEL"
    )
    QUERY_PLANNING_TIMEOUT: int = Field(30, env="QUERY_PLANNING_TIMEOUT")

    # Fallback policy: When content extraction fails (403/timeout), should we use search snippets?
    # True = Keep snippet as low-quality fallback (marked in metadata for downstream weighting)
    # False = Drop sources entirely if content extraction fails
    ALLOW_SNIPPET_FALLBACK: bool = Field(True, env="ALLOW_SNIPPET_FALLBACK")

    # ========== PIPELINE EVIDENCE QUALITY (Track N Phase 2) ==========
    # Coverage recovery enrichment: fetch full page content for recovery evidence
    ENABLE_RECOVERY_ENRICHMENT: bool = Field(
        True, env="ENABLE_RECOVERY_ENRICHMENT"
    )  # Fetch full page content for coverage recovery evidence
    ENABLE_RECOVERY_QUERY_PLANNING: bool = Field(
        True, env="ENABLE_RECOVERY_QUERY_PLANNING"
    )  # Use LLM query planner for coverage recovery searches
    RECOVERY_PLANNER_TIMEOUT: float = Field(
        10.0, env="RECOVERY_PLANNER_TIMEOUT"
    )  # Timeout for planner LLM call in recovery (seconds)
    RECOVERY_MAX_RESULTS_PER_ELEMENT: int = Field(
        8, env="RECOVERY_MAX_RESULTS_PER_ELEMENT"
    )  # Search results per element in coverage recovery (was 5)
    RECOVERY_MAX_CLAIMS: int = Field(
        3, env="RECOVERY_MAX_CLAIMS"
    )  # Max claims to recover per check
    RECOVERY_MAX_ELEMENTS_PER_CLAIM: int = Field(
        5, env="RECOVERY_MAX_ELEMENTS_PER_CLAIM"
    )  # Max elements to recover per claim
    RECOVERY_TIMEOUT_SECONDS: int = Field(
        20, env="RECOVERY_TIMEOUT_SECONDS"
    )  # Hard time cap for coverage recovery
    MAX_SOURCES_PER_CLAIM: int = Field(
        20, env="MAX_SOURCES_PER_CLAIM"
    )  # Max evidence sources per claim during retrieval
    MAX_CONCURRENT_URL_FETCHES: int = Field(
        25, env="MAX_CONCURRENT_URL_FETCHES"
    )  # Shared pool: max concurrent HTTP fetches across all claims in one check
    URL_FETCH_TIMEOUT: int = Field(
        5, env="URL_FETCH_TIMEOUT"
    )  # Per-URL HTTP timeout in seconds (healthy sites respond in <3s)
    MAX_EVIDENCE_FOR_RANKING: int = Field(
        60, env="MAX_EVIDENCE_FOR_RANKING"
    )  # Cap combined evidence before expensive ranking
    MIN_EVIDENCE_POST_FILTER: int = Field(
        5, env="MIN_EVIDENCE_POST_FILTER"
    )  # Minimum evidence per claim after scoring — triggers post-filter recovery

    # ========== CLAIM MAP SYSTEM (Track B) ==========
    MAX_SELECTED_CLAIMS: int = Field(
        5, env="MAX_SELECTED_CLAIMS"
    )  # Article mode: max claims for full analysis
    MAX_ELEMENTS_PER_CLAIM: int = Field(
        5, env="MAX_ELEMENTS_PER_CLAIM"
    )  # Decomposition cap
    DECOMPOSITION_MODEL: str = Field(
        "gpt-4o", env="DECOMPOSITION_MODEL"
    )  # LLM for claim decomposition
    DECOMPOSITION_TEMPERATURE: float = Field(0.2, env="DECOMPOSITION_TEMPERATURE")
    ANALYZER_MODEL: str = Field(
        "gpt-4o", env="ANALYZER_MODEL"
    )  # LLM for evidence mapping
    ANALYZER_TEMPERATURE: float = Field(0.2, env="ANALYZER_TEMPERATURE")
    ANALYZER_MAX_TOKENS: int = Field(12000, env="ANALYZER_MAX_TOKENS")
    MAX_CONCURRENT_ANALYSES: int = Field(3, env="MAX_CONCURRENT_ANALYSES")
    MAX_CONCURRENT_AGENT_ANALYSES: int = Field(
        5, env="MAX_CONCURRENT_AGENT_ANALYSES"
    )  # Separate pool for agent-initiated pipelines (O-03)
    MAPPING_GOOGLE_MODEL: str = Field(
        "gemini-2.5-flash", env="MAPPING_GOOGLE_MODEL"
    )  # Google model for evidence mapping (highest-stakes call)

    # ========== TRACK M: EVIDENCE INFRASTRUCTURE ==========

    # M-04: Manifest signing
    MANIFEST_SIGNING_ENABLED: bool = Field(
        False, env="MANIFEST_SIGNING_ENABLED"
    )  # Flip after M-04 ships
    MANIFEST_SIGNING_KEY: str = Field(
        "", env="MANIFEST_SIGNING_KEY"
    )  # Base64-encoded 256-bit key (current)
    MANIFEST_KID: str = Field(
        "tru8-2026-03", env="MANIFEST_KID"
    )  # Current key identifier
    MANIFEST_SIGNING_KEYS: str = Field(
        "{}", env="MANIFEST_SIGNING_KEYS"
    )  # JSON: {"kid": "base64_key"} — includes rotated keys

    # M-05: Jurisdiction-aware source routing
    JURISDICTION_ADAPTERS: str = Field(
        '{"uk": ["ONS Economic Statistics", "UK Parliament Hansard", "GOV.UK Content API", "Companies House", "UK Legislation"], "us": ["FRED", "GovInfo.gov", "Library of Congress"], "eu": [], "global": ["Semantic Scholar", "OpenAlex", "Wikipedia", "PubMed", "WHO", "NOAA CDO", "WeatherAPI", "Open-Meteo", "GBIF", "World Bank", "Internet Archive", "Wikidata", "Marketaux", "Transfermarkt", "Football-Data.org"]}',
        env="JURISDICTION_ADAPTERS",
    )  # JSON mapping jurisdiction → adapter names

    # B1 (audit §2.2): Per-domain adapter caps. DEFAULT is used when a domain
    # is unlisted. Higher caps stop the PQ-06 tier sort silently dropping
    # legitimate tier-2 specialists (OpenAlex, Semantic Scholar) from every
    # Health/Science claim.
    ADAPTER_CAPS_PER_DOMAIN: str = Field(
        '{"Science": 5, "History": 5, "Politics": 4, "Health": 4, "Animals": 4, "DEFAULT": 3}',
        env="ADAPTER_CAPS_PER_DOMAIN",
    )  # JSON mapping domain → integer cap

    # ========== SKYFIRE KYAPay (L-06) ==========
    SKYFIRE_ENABLED: bool = Field(False, env="SKYFIRE_ENABLED")
    SKYFIRE_API_KEY: str = Field("", env="SKYFIRE_API_KEY")
    SKYFIRE_SERVICE_ID: str = Field("", env="SKYFIRE_SERVICE_ID")
    SKYFIRE_JWKS_URL: str = Field(
        "https://auth.skyfire.xyz/.well-known/jwks.json", env="SKYFIRE_JWKS_URL"
    )
    SKYFIRE_CHARGE_URL: str = Field(
        "https://api.skyfire.xyz/v1/charges", env="SKYFIRE_CHARGE_URL"
    )
    SKYFIRE_ENVIRONMENT: str = Field("sandbox", env="SKYFIRE_ENVIRONMENT")
    SKYFIRE_JWKS_CACHE_SECONDS: int = Field(300, env="SKYFIRE_JWKS_CACHE_SECONDS")

    # ========== x402 USDC Payment (L-05) ==========
    X402_ENABLED: bool = Field(False, env="X402_ENABLED")
    X402_PAY_TO_ADDRESS: str = Field("", env="X402_PAY_TO_ADDRESS")
    X402_NETWORK: str = Field("eip155:84532", env="X402_NETWORK")
    X402_FACILITATOR_URL: str = Field("", env="X402_FACILITATOR_URL")
    CDP_API_KEY_ID: str = Field("", env="CDP_API_KEY_ID")
    CDP_API_KEY_SECRET: str = Field("", env="CDP_API_KEY_SECRET")

    # ========== SIWE (Sign-In With Ethereum) ==========
    SIWE_DOMAIN: str = Field("app.tru8.com", env="SIWE_DOMAIN")
    SIWE_NONCE_TTL_SECONDS: int = Field(300, env="SIWE_NONCE_TTL_SECONDS")

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


settings = Settings()
