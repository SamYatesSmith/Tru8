from typing import ClassVar, List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
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

        self._refuse_live_stripe_outside_deployment()

    # -- Safety: a developer machine must be incapable of charging anyone ------
    #
    # Found 2026-08-03: backend/.env carried ENVIRONMENT=development alongside a
    # live STRIPE_SECRET_KEY (sk_live_) and a live webhook secret. Nothing was
    # leaked — the file has never been committed — but every local run of the
    # payments path was pointed at REAL customers and REAL money. Clerk was
    # correctly on a test key; Stripe was not.
    #
    # The fix is not "remember to use test keys". A convention decays the next
    # time someone copies a .env to debug a payment; an assertion does not. So
    # the key is REFUSED rather than trusted: outside a deployed environment a
    # live key is discarded, and Stripe calls then fail loudly on auth instead
    # of quietly succeeding against production.
    #
    # Discarding rather than raising is deliberate — raising would brick the
    # test suite and local boot on a machine that merely has a stale .env, which
    # punishes the person doing the right thing. The CRITICAL log is the signal.
    _DEPLOYED_ENVIRONMENTS: ClassVar[set] = {"production", "staging"}

    def _refuse_live_stripe_outside_deployment(self) -> None:
        if self.ENVIRONMENT.lower() in self._DEPLOYED_ENVIRONMENTS:
            return
        if self.ALLOW_LIVE_STRIPE_IN_DEV:
            return

        # Only the SECRET KEY is guarded, because it is the only one whose mode
        # is legible: sk_live_ vs sk_test_. Stripe webhook secrets are `whsec_`
        # in BOTH modes, so there is no prefix to test and no way to catch a live
        # one here — swapping that value stays a manual step. It is also the far
        # smaller risk: a webhook secret only verifies inbound signatures, it
        # cannot move money.
        if not self.STRIPE_SECRET_KEY.startswith("sk_live_"):
            return

        object.__setattr__(self, "STRIPE_SECRET_KEY", "")
        # print to stderr, not logger: this runs at import, before logging config.
        print(
            "CRITICAL [config] STRIPE_SECRET_KEY held a LIVE key (sk_live_) while "
            f"ENVIRONMENT={self.ENVIRONMENT!r}. It has been DISCARDED so this "
            "process cannot reach live Stripe. Put a test-mode key in "
            "backend/.env — the live value belongs on Railway only. Remember the "
            "webhook secret too: it is `whsec_` in both modes, so it cannot be "
            "checked here. Override with ALLOW_LIVE_STRIPE_IN_DEV=true if you "
            "really mean to bill real customers from this machine.",
            file=__import__("sys").stderr,
        )

    DATABASE_SSL: bool = Field(
        True, env="DATABASE_SSL"
    )  # Set False for Fly.io internal network

    # Redis
    REDIS_URL: str = Field("redis://localhost:6379/0", env="REDIS_URL")

    # Auth
    CLERK_SECRET_KEY: str = Field(..., env="CLERK_SECRET_KEY")
    CLERK_PUBLISHABLE_KEY: str = Field(..., env="CLERK_PUBLISHABLE_KEY")
    CLERK_JWT_ISSUER: str = Field(..., env="CLERK_JWT_ISSUER")
    # F-AUTH-03: when set, JWTs are validated against this audience. Leave empty
    # to keep backward-compatible behaviour (no aud check); set in production to
    # tighten defence against cross-application token reuse on the same Clerk
    # instance. Must match the `aud` claim configured in the Clerk JWT template.
    CLERK_JWT_AUDIENCE: str = Field("", env="CLERK_JWT_AUDIENCE")
    # F-AUTH-02: Svix signing secret for the Clerk webhook endpoint
    # (POST /api/v1/webhooks/clerk). When empty the endpoint refuses every
    # request — set in production to wire up user.deleted / user.updated
    # propagation from Clerk to the local DB.
    CLERK_WEBHOOK_SECRET: str = Field("", env="CLERK_WEBHOOK_SECRET")

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
        "gemini-3.5-flash-lite", env="GOOGLE_LLM_MODEL"
    )  # Gemini model for all LLM calls EXCEPT mapping (see MAPPING_GOOGLE_MODEL).
    # Migrated off gemini-2.5-flash-lite 2026-08-25: the whole 2.5 family retires
    # 16 October 2026. NOT gemini-3.1-flash-lite despite it being Google's named
    # replacement — it already carries a 7 May 2027 shutdown, i.e. migrating twice.
    # ⚠️ Google deleted the price point: 2.5-flash-lite was $0.10/$0.40, this is
    # $0.30/$2.50. There is no cheap Gemini 3 tier; cost rises on every path.
    # Thinking control changes shape with the family — google_ai._thinking_config
    # sends thinkingLevel here and thinkingBudget on 2.5. A 3.x model with a bare
    # thinkingBudget is a hard 400. Rollback to "gemini-2.5-flash-lite" works
    # until the retirement date and needs no code change.
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
    SEMANTIC_SCHOLAR_API_KEY: str = Field(
        "", env="SEMANTIC_SCHOLAR_API_KEY"
    )  # Semantic Scholar Academic Graph — sent as x-api-key header; lifts the keyless 100-req/5min limit that 429s under bench/pipeline load

    # Storage
    S3_BUCKET: str = Field("tru8-uploads", env="S3_BUCKET")
    S3_ACCESS_KEY: str = Field("", env="S3_ACCESS_KEY")
    S3_SECRET_KEY: str = Field("", env="S3_SECRET_KEY")
    S3_ENDPOINT: str = Field("", env="S3_ENDPOINT")
    S3_REGION: str = Field("eu-north-1", env="S3_REGION")

    # Stripe Payments
    # Escape hatch for _refuse_live_stripe_outside_deployment(). Leave False.
    ALLOW_LIVE_STRIPE_IN_DEV: bool = Field(False, env="ALLOW_LIVE_STRIPE_IN_DEV")
    STRIPE_SECRET_KEY: str = Field("", env="STRIPE_SECRET_KEY")
    STRIPE_WEBHOOK_SECRET: str = Field("", env="STRIPE_WEBHOOK_SECRET")
    STRIPE_PRICE_ID_PRO: str = Field("", env="STRIPE_PRICE_ID_PRO")
    STRIPE_PRICE_ID_DEVELOPER: str = Field("", env="STRIPE_PRICE_ID_DEVELOPER")
    # Console tier (2026-07 pricing): £20/mo + £200/yr, 200 checks/month hard cap.
    # _PRO/_DEVELOPER above are RETIRED from sale — kept for existing subscribers.
    STRIPE_PRICE_ID_CONSOLE: str = Field("", env="STRIPE_PRICE_ID_CONSOLE")
    STRIPE_PRICE_ID_CONSOLE_ANNUAL: str = Field(
        "", env="STRIPE_PRICE_ID_CONSOLE_ANNUAL"
    )
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

    # ── Hang-proofing watchdogs (2026-07-23, audit/2026-07-23_hang_proofing_design.md)
    # Hard wall-clock ceiling on background pipeline tasks (submission +
    # phase 2). On breach the check is failed HONESTLY (user-friendly message
    # + idempotent refund) via handle_pipeline_failure — never left hanging.
    # Slowest honest check observed: 123.9s (TRU-1795-FFC5). Rollback: raise
    # the env var.
    PIPELINE_WATCHDOG_SECONDS: int = Field(300, env="PIPELINE_WATCHDOG_SECONDS")
    # Ceiling for single-element re-search/top-up tasks. On breach the Redis
    # research status is terminated ("error"); the completed check is untouched.
    RESEARCH_WATCHDOG_SECONDS: int = Field(150, env="RESEARCH_WATCHDOG_SECONDS")
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
    DISTIL_MODEL: str = Field("gemini-3.5-flash-lite", env="DISTIL_MODEL")
    # Migrated 2026-08-27. The 2026-08-25 migration moved GOOGLE_LLM_MODEL and
    # MAPPING_GOOGLE_MODEL and recorded "the whole pipeline is off the retiring
    # Gemini 2.5 family" - but this third model setting lives 180 lines away in
    # the distillation block and was missed. A replay-bench recording caught it:
    # 10 calls on 3.5/3.7, one on 2.5-flash-lite. The distiller is ~60% of input
    # tokens and has NO OpenAI fallback, so it would have failed outright on
    # 16 Oct 2026. If a deployment pins DISTIL_MODEL as an env var, changing this
    # default does nothing - check the environment too.
    DISTIL_TIMEOUT: float = Field(15.0, env="DISTIL_TIMEOUT")
    DISTIL_MAX_FACTS_PER_ITEM: int = Field(8, env="DISTIL_MAX_FACTS_PER_ITEM")
    DISTIL_MIN_TEXT_LENGTH: int = Field(500, env="DISTIL_MIN_TEXT_LENGTH")
    DISTIL_BATCH_SIZE: int = Field(
        5, env="DISTIL_BATCH_SIZE"
    )  # Articles per distil LLM call; batches run CONCURRENTLY (D1 latency
    # fix). 15-article batches measured ~15.6s — exactly ON the 15s timeout
    # (silent flaky failure) and at the 4,000 output-token cap. ~1s/article.

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

    # ========== OPINION DECOUPLING (Phase 1a, 2026-07-16) ==========
    # Extraction KEEPS main-predicate evaluative claims (reframed affirmative,
    # type_hint="normative") instead of dropping them under Rule 6; the grounds
    # stage then rebuilds their elements as neutral empirical questions.
    # The gating precondition — Phase 1b's neutral decompose + grounds-aware
    # mapping — went live in slices 1-3 (1e27f32/6f1c9fc/71e441d), so the flag
    # defaults ON from 2026-07-23 (founder sign-off).
    # ROLLBACK without a redeploy: set ENABLE_OPINION_REFRAME=False on Railway.
    ENABLE_OPINION_REFRAME: bool = Field(True, env="ENABLE_OPINION_REFRAME")

    # F-VERDICT / P13 (2026-07-26): the "normative" hint above is an LLM
    # judgement and under-fires on two witnessed shapes — an IDEA/PROPOSITION as
    # subject ("The learning-styles theory is indefensible" → returned +SUPPORTED
    # by 11 sources, a verdict on a value judgement) and extraposition ("It is
    # indefensible for X to Y", where Rule 6's cleaning licence DELETES the
    # judgement). A mechanical evaluative-head detector runs as a SECOND signal,
    # OR-ed with the LLM hint, never unsetting it.
    # ROLLBACK without a redeploy: ENABLE_EVALUATIVE_HEAD_SIGNAL=False on Railway
    # kills the detector alone; ENABLE_OPINION_REFRAME=False kills the chain.
    ENABLE_EVALUATIVE_HEAD_SIGNAL: bool = Field(
        True, env="ENABLE_EVALUATIVE_HEAD_SIGNAL"
    )

    # ========== QUERY PLANNING AGENT ==========
    # LLM-powered batch query planning for semantic claim understanding
    # Generates targeted queries based on claim type (squad, stats, contract, etc.)
    ENABLE_QUERY_PLANNING: bool = Field(True, env="ENABLE_QUERY_PLANNING")
    QUERY_PLANNING_MODEL: str = Field(
        "gpt-4o-mini-2024-07-18", env="QUERY_PLANNING_MODEL"
    )
    QUERY_PLANNING_TIMEOUT: int = Field(30, env="QUERY_PLANNING_TIMEOUT")

    # Phase 2 (2026-07-27): element-level retrieval. The query planner has
    # always been written for elements, but the key it reads
    # (claim["elements"]) was never written by anything — decompose writes
    # claim["claim_map"]["elements"] — so every check planned queries from a
    # single synthetic element made of the raw claim text. Design:
    # audit/2026-07-27_phase2_element_retrieval_build_design.md.
    # False restores that behaviour byte-for-byte (rollback without a deploy).
    ENABLE_ELEMENT_RETRIEVAL: bool = Field(True, env="ENABLE_ELEMENT_RETRIEVAL")

    # Phase 3a (2026-07-29): element atomicity. 21.2% of grounds elements ask
    # two questions at once and 13.8% ask two that take DIFFERENT grading
    # rules — so the trivially-satisfiable half badges the whole element
    # `supported` while the half bearing on the claim is never graded. Repairs
    # compounds at decompose; a mechanical mapper tag backstops any survivor.
    # Design: audit/2026-07-29_element_atomicity_design.md.
    # False restores today's behaviour byte-for-byte (rollback, no deploy).
    ENABLE_ELEMENT_ATOMICITY: bool = Field(True, env="ENABLE_ELEMENT_ATOMICITY")

    # 2026-08-25: recover headlines the search provider handed us pre-cut.
    # Serper truncates at ~54 chars (43% of results); the page's own og:title
    # normally fixes it, but a blocked fetch leaves the stub on screen looking
    # like a complete headline. For those, a Wayback snapshot yields a usable
    # title 47% of the time. Only lengthens, only on visibly-truncated titles,
    # always with a receipt. False disables the extra archive calls entirely.
    ENABLE_TITLE_RECOVERY: bool = Field(True, env="ENABLE_TITLE_RECOVERY")
    TITLE_RECOVERY_MAX_PER_CLAIM: int = Field(12, env="TITLE_RECOVERY_MAX_PER_CLAIM")

    # F1 (2026-08-05): scope evidence about a DIFFERENT period out of the state
    # count. Production check 618efbc4 returned "UK CPI below 2% in September
    # 2024" — a true, ONS-sourced claim — as `disputed`, on figures from June,
    # May and the 2024 annual average. The mapping prompt already forbade that;
    # the evidence payload carried no dates, so it could not comply.
    # Symmetric: scopes `supports` as readily as `challenges`.
    # ROLLBACK without a redeploy: set ENABLE_TEMPORAL_SCOPE_GATE=False.
    ENABLE_TEMPORAL_SCOPE_GATE: bool = Field(True, env="ENABLE_TEMPORAL_SCOPE_GATE")

    # F1 extension (2026-08-06): resolve a bare month ("in September") against
    # the item's published_date, so an undated-year source is placed in time.
    # This is the INFERRING half of the gate — the source never stated the year —
    # so it carries its own switch. The lexical half (two-digit years such as
    # "September-25") is not affected by this flag and stays on with the gate.
    # Only `date_basis` in TRUSTED_PUBLICATION_BASES is used; url_inferred_suspect
    # is refused. See app/utils/temporal_scope for the over-fire guards.
    # ROLLBACK without a redeploy: ENABLE_TEMPORAL_PUBLICATION_RESOLUTION=False.
    ENABLE_TEMPORAL_PUBLICATION_RESOLUTION: bool = Field(
        True, env="ENABLE_TEMPORAL_PUBLICATION_RESOLUTION"
    )

    # Jurisdiction gate (2026-08-06): the mechanical analogue of F1. Production
    # check 757f02c2 returned a true, ONS-verbatim UK CPI claim as `disputed`, its
    # sole challenge being the IRISH CSO — whose snippet never says "Ireland", so
    # only the domain reveals the mismatch and no prompt could have caught it.
    # Fires only for country-level claims (UK/US), only on foreign NATIONAL
    # OFFICIAL domains (never foreign press, never supranational bodies), and never
    # when the item's own text names the claim's jurisdiction.
    # Symmetric: scopes `supports` as readily as `challenges`.
    # ROLLBACK without a redeploy: ENABLE_JURISDICTION_SCOPE_GATE=False.
    ENABLE_JURISDICTION_SCOPE_GATE: bool = Field(
        True, env="ENABLE_JURISDICTION_SCOPE_GATE"
    )

    # Measure gate (2026-08-06): the third mismatch in check 757f02c2. A rate of
    # change is identified by the interval's END, not by the months it mentions —
    # "between September 2024 and September 2025" measures a DIFFERENT twelve
    # months from "the twelve months to September 2024", yet names ours, so the
    # temporal gate correctly declines to act. Runs LAST of the three, so it can
    # only claim references the others left alone and cannot alter their receipts.
    # ROLLBACK without a redeploy: ENABLE_MEASURE_SCOPE_GATE=False.
    ENABLE_MEASURE_SCOPE_GATE: bool = Field(True, env="ENABLE_MEASURE_SCOPE_GATE")

    # Interested-party gate (2026-08-13): check TRU-018F-44AA badged "Donald
    # Trump stopped 6 wars" supported-all-4, with whitehouse.gov's own "I've
    # solved six wars" weighing primary-3 against PolitiFact at commentary-1. A
    # source CONTROLLED BY the claim's subject cannot be directional on that
    # claim — re-labelled context with a receipt; tier untouched. Arms only when
    # the claim names PERSON/ORG subjects. Symmetric: scopes a subject's
    # self-serving denial out of `challenges` exactly as self-praise out of
    # `supports`. ROLLBACK without a redeploy: ENABLE_INTERESTED_PARTY_GATE=False.
    ENABLE_INTERESTED_PARTY_GATE: bool = Field(True, env="ENABLE_INTERESTED_PARTY_GATE")

    # Recital gate (2026-08-13): the same check's load-bearing failure —
    # "states Trump claimed to have 'settled six wars'" was mapped `supports`.
    # Evidence that a claim WAS MADE is evidence of the making, not the content;
    # a reference resting on subject-anchored attribution (or distancing adverbs
    # like "purportedly") with no verification framing is re-labelled context
    # with a receipt. Reads the mapper's own reasoning first (authoritative in
    # both directions), evidence text as fallback. Never arms for elements that
    # themselves assert a saying. Symmetric, like every gate.
    # ROLLBACK without a redeploy: ENABLE_RECITAL_SCOPE_GATE=False.
    ENABLE_RECITAL_SCOPE_GATE: bool = Field(True, env="ENABLE_RECITAL_SCOPE_GATE")

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
    # 20→35 (2026-07-22): the §4d starvation trigger routes intact single-claim
    # checks into recovery, where retrieval+enrichment alone can eat ~15s — the
    # E323-8862 run's mapping call was killed 5.4s in with the work complete.
    # Ceiling, not a sleep: typical recovery latency is unchanged.
    RECOVERY_TIMEOUT_SECONDS: int = Field(
        35, env="RECOVERY_TIMEOUT_SECONDS"
    )  # Floor for coverage recovery wait; preserves 1-2 candidate behaviour
    # Phase-split (2026-07-22, 11F0-F1AE): RECOVERY_TIMEOUT_SECONDS budgets
    # Phase A (retrieve+score+classify) only. Mapping runs under its own
    # grace and is never cancelled by the Phase A budget once inputs are
    # paid for. MAX_SCORED_ITEMS bounds the scoring/mapping payload
    # (42 unbounded items cost 12.6s of scoring), round-robin per element.
    RECOVERY_MAX_SCORED_ITEMS: int = Field(24, env="RECOVERY_MAX_SCORED_ITEMS")
    RECOVERY_MAPPING_GRACE_SECONDS: int = Field(
        25, env="RECOVERY_MAPPING_GRACE_SECONDS"
    )
    RECOVERY_TIMEOUT_SECONDS_PER_CLAIM: int = Field(
        7, env="RECOVERY_TIMEOUT_SECONDS_PER_CLAIM"
    )  # Per-candidate seconds; total = max(floor, n_candidates * this) (Bug B)
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
    )  # Article mode: max claims for full analysis. Single source of truth —
    # referenced by SelectClaimsRequest validator (checks.py) and the agent
    # auto-select cap (agent.py). Changing this one value adjusts both paths.
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
        "gemini-3.7-flash", env="MAPPING_GOOGLE_MODEL"
    )  # Google model for evidence mapping (highest-stakes call).
    #
    # ⛔ DO NOT MOVE THIS TO gemini-3.5-flash-lite. Measured 2026-08-25,
    # scripts/recital_repeat_probe.py, frozen pool, 5 repeats per model:
    #
    #     model                  recital of the claim labelled as
    #     gemini-2.5-flash       context   10/10
    #     gemini-3.5-flash-lite  SUPPORTS  10/10   <-- invariant #7 breach
    #     gemini-3.7-flash       context    5/5
    #
    # The evidence item is Matt Ridley's tweet, which IS the claim being checked.
    # 3.5-flash-lite counts it as SUPPORT for the claim, every time, on identical
    # input. That is the TRU-018F-44AA failure: "X claimed Y" is never evidence
    # of Y. It is 100% reproducible, not a bad roll.
    #
    # ⚠️ Why the premise-adoption probe cleared 3.5-flash-lite earlier the same
    # day: that probe counts `supported` ELEMENT STATES, and this failure hides
    # below state. Here 12 challenges swamp the 1 bogus support, so the element
    # still reads disputed and the probe sees nothing. It only surfaces when the
    # support side is thin — which is exactly when it does the most damage.
    # A clean premise-adoption score is NOT evidence a model handles recitals.
    # Migrated off gemini-2.5-flash 2026-08-25 (2.5 retires 16 October 2026).
    #
    # WHY A LITE-TIER MODEL ON THE HIGHEST-STAKES CALL — this was NOT the
    # default choice, and it is not a cost decision. Mapping is the only stage
    # that puts the user's claim in the prompt, so it is where invariant #7 is
    # won or lost, and PARROT reports a 3x within-vendor tier gap on exactly that
    # failure (2.5-Flash-Lite 50.7% follow rate vs 2.5-Flash 17.2%). On that
    # basis this shipped as gemini-3.7-flash — tier-preserving, erring safe.
    #
    # Then we MEASURED it instead of reasoning about it.
    # scripts/model_premise_probe.py, 2026-08-25, 3 frozen pools x 3 repeats x
    # {claim shown, claim withheld}: premise adoption came out at +0.11 elements
    # for 3.5-flash-lite against a 2.5-flash baseline of -0.44 and that
    # baseline's own run-to-run noise of 1.00. A PARROT-sized effect would have
    # shown as adopt approaching +1 on ~3 elements. It did not appear.
    # 3.5-flash-lite was also the MOST self-consistent arm (spread 0.33 vs 0.67
    # vs 1.00), which matters for the replay corpus.
    #
    # So the Lite tier is here on evidence, and the saving is a consequence
    # rather than the reason: 1.84x instead of 2.40x, ~4.6s per mapping call
    # instead of ~10.3s (and faster than 2.5-flash is in production today), and
    # thinkingLevel="minimal" measures 0 thought tokens — so MAPPING_THINKING_BUDGET=0
    # keeps working and the M1 latency lever survives the migration intact.
    # 3.7-flash could not have done that: its floor is "low", it 400s on
    # "minimal", and it still spends ~70 thought tokens billed at output rate.
    #
    # ⚠️ The probe rules out a LARGE adoption effect at n=3 pools, not a small
    # one. If mapping quality is ever suspected, re-run the probe with more pools
    # BEFORE blaming anything else — and gemini-3.7-flash is the rollback, as an
    # env var, no code change.
    MAPPING_THINKING_BUDGET: Optional[int] = Field(
        None, env="MAPPING_THINKING_BUDGET"
    )  # Thinking-token cap for mapping calls only. None = omit thinkingConfig
    # entirely (API default: dynamic thinking — current behaviour, and keeps
    # the request body byte-identical for replay-bench cassettes); 0 = thinking
    # off; >0 = cap. Latency lever — see audit/2026-07-02_pipeline_latency_options.md (M1).
    GROUNDS_MIN_WEIGHTED_SUPPORT: int = Field(
        3, env="GROUNDS_MIN_WEIGHTED_SUPPORT"
    )  # Phase 1 mechanical honesty (2026-07-27). Tier-weighted floor a
    # QUESTION-shaped (grounds) element must clear before it can read
    # "supported". Weights are the existing _STATE_TIER_WEIGHTS
    # (primary=3, reporting=2, commentary=1), so 3 = one primary source, two
    # reporting, or three commentary. Rationale: `all_supports` (>=1 support,
    # 0 challenges) is a sound bar for an ASSERTION but near-zero for "did we
    # find out?" — TRU-4B9D-65EA marked two questions supported off one source
    # each. GROUNDS-ONLY: factual claims read FACTUAL_MIN_WEIGHTED_SUPPORT.
    # Set 0 to disable the floor without a deploy (rollback lever).
    # Design: audit/2026-07-27_phase1_mechanical_honesty_design.md

    FACTUAL_MIN_WEIGHTED_SUPPORT: int = Field(
        3, env="FACTUAL_MIN_WEIGHTED_SUPPORT"
    )  # Quality-first Phase B (2026-08-17). Tier-weighted floor a FACTUAL
    # element must clear before `supported`: check 83120010 left an element
    # supported off a single BBC reporting ref. 3 = one primary alone still
    # suffices (a single primary IS the record for many true claims); a lone
    # reporting (2) or commentary (1) ref no longer does. Downgrade target is
    # `unresolved`, receipt rule "support_floor". The design review's §5
    # nominal "floor 2" contradicted its own approved description — the
    # described behaviour is what this value encodes.
    # Set 0 to disable the floor without a deploy (rollback lever).
    # Design: audit/2026-08-14_quality_first_design_review.md §1.4

    # Echo scope gate (2026-08-17, quality-first Phase B). A directional ref
    # whose evidence is a DERIVATIVE (corroboration derivation chain) of an
    # original ALREADY COUNTED on the same side of the same element is
    # re-labelled `context` with a receipt naming the original — five wire
    # copies of one story stop counting as five supports (the NHS outreach
    # record's failure). Symmetric; the first derivative stays directional
    # when its original is not counted. ROLLBACK: ENABLE_ECHO_SCOPE_GATE=False.
    ENABLE_ECHO_SCOPE_GATE: bool = Field(True, env="ENABLE_ECHO_SCOPE_GATE")

    # Item 7 stage 1 (2026-08-28): the factcheck signal. When ON, the evidence
    # classifier (1) asks the LLM for a conservative `factcheck` boolean (a
    # genre judgement — content property, never an outlet roster), (2) marks
    # the four known factcheck domains mechanically on the search path, and
    # (3) promotes a flagged commentary/ANALYSIS item to reporting
    # (`factcheck_promotion` receipt) — the tier the heuristic has always
    # assigned flagged factchecks. DEFAULT OFF: the prompt variant re-keys
    # every classifier cassette in the replay bench, so the flip is a decision
    # that carries a bench re-record; measure firing rates first with
    # scripts/measure_factcheck_signal.py. ROLLBACK: ENABLE_FACTCHECK_SIGNAL=False.
    # Design: audit/2026-08-28_rigour_and_refutation_design_review.md §3, Option 7-A.
    ENABLE_FACTCHECK_SIGNAL: bool = Field(False, env="ENABLE_FACTCHECK_SIGNAL")

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
        '{"uk": ["ONS Economic Statistics", "UK Parliament Hansard", "GOV.UK Content API", "Companies House", "UK Legislation", "UK Parliament Bills"], "us": ["FRED", "GovInfo.gov", "Library of Congress"], "eu": [], "global": ["Semantic Scholar", "OpenAlex", "Wikipedia", "PubMed", "WHO", "NOAA CDO", "WeatherAPI", "Open-Meteo", "GBIF", "World Bank", "Internet Archive", "Wikidata", "Marketaux", "Transfermarkt", "Football-Data.org", "ONS Economic Statistics"]}',
        env="JURISDICTION_ADAPTERS",
    )  # ONS is in both UK and global because its own is_relevant_for_domain accepts UK+Global (Finance/Demographics) — when classifier drifts to Finance/Global on UK economic claims, ONS still routes correctly. Other UK specialists (Hansard, Companies House, GOV.UK, Bills) are deliberately UK-only at adapter level.

    # B1 (audit §2.2): Per-domain adapter caps. DEFAULT is used when a domain
    # is unlisted. Higher caps stop the PQ-06 tier sort silently dropping
    # legitimate tier-2 specialists (OpenAlex, Semantic Scholar) from every
    # Health/Science claim.
    ADAPTER_CAPS_PER_DOMAIN: str = Field(
        '{"Science": 5, "History": 5, "Politics": 4, "Health": 4, "Animals": 4, "Climate": 4, "Finance": 4, "Law": 4, "DEFAULT": 3}',
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

    # Modern pydantic-settings form. The old inner `class Config` is deprecated
    # in pydantic-settings 2.x; the behaviour here is identical, but the class
    # form emits warnings on the >=2.6.1 required by mcp>=1.2.
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
