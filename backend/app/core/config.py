from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = Field(..., env="DATABASE_URL")
    
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
    ANTHROPIC_API_KEY: str = Field("", env="ANTHROPIC_API_KEY")
    GOOGLE_FACTCHECK_API_KEY: str = Field("", env="GOOGLE_FACTCHECK_API_KEY")
    
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

    # Monitoring
    SENTRY_DSN: str = Field("", env="SENTRY_DSN")
    POSTHOG_API_KEY: str = Field("", env="POSTHOG_API_KEY")
    
    # App
    ENVIRONMENT: str = Field("development", env="ENVIRONMENT")
    DEBUG: bool = Field(True, env="DEBUG")
    SECRET_KEY: str = Field(..., env="SECRET_KEY")
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:3001", "http://localhost:8081", "http://127.0.0.1:3000", "http://127.0.0.1:3001"],
        env="CORS_ORIGINS"
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
    
    # Judge LLM
    JUDGE_MAX_TOKENS: int = Field(1000, env="JUDGE_MAX_TOKENS")
    JUDGE_TEMPERATURE: float = Field(0.3, env="JUDGE_TEMPERATURE")
    MAX_CONCURRENT_JUDGMENTS: int = Field(3, env="MAX_CONCURRENT_JUDGMENTS")

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
    ENABLE_TEMPORAL_CONTEXT: bool = Field(True, env="ENABLE_TEMPORAL_CONTEXT")

    # Phase 2 - User Experience & Trust
    ENABLE_CLAIM_CLASSIFICATION: bool = Field(True, env="ENABLE_CLAIM_CLASSIFICATION")
    ENABLE_ENHANCED_EXPLAINABILITY: bool = Field(True, env="ENABLE_ENHANCED_EXPLAINABILITY")

    # Phase 3 - Critical Credibility Enhancements
    ENABLE_DOMAIN_CREDIBILITY_FRAMEWORK: bool = Field(True, env="ENABLE_DOMAIN_CREDIBILITY_FRAMEWORK")
    ENABLE_ABSTENTION_LOGIC: bool = Field(True, env="ENABLE_ABSTENTION_LOGIC")

    # Phase 3.5 - Source Quality Control (Week 9.5-10)
    ENABLE_SOURCE_VALIDATION: bool = Field(True, env="ENABLE_SOURCE_VALIDATION")
    SOURCE_CREDIBILITY_THRESHOLD: float = Field(0.65, env="SOURCE_CREDIBILITY_THRESHOLD")

    # Phase 4 - Legal Integration
    ENABLE_LEGAL_SEARCH: bool = Field(True, env="ENABLE_LEGAL_SEARCH")
    GOVINFO_API_KEY: Optional[str] = Field(None, env="GOVINFO_API_KEY")
    CONGRESS_API_KEY: Optional[str] = Field(None, env="CONGRESS_API_KEY")
    LEGAL_API_TIMEOUT_SECONDS: int = Field(10, env="LEGAL_API_TIMEOUT_SECONDS")
    LEGAL_CACHE_TTL_DAYS: int = Field(30, env="LEGAL_CACHE_TTL_DAYS")

    # Domain Capping Configuration
    MAX_EVIDENCE_PER_DOMAIN: int = Field(3, env="MAX_EVIDENCE_PER_DOMAIN")
    DOMAIN_DIVERSITY_THRESHOLD: float = Field(0.6, env="DOMAIN_DIVERSITY_THRESHOLD")
    OUTSTANDING_SOURCE_THRESHOLD: float = Field(0.95, env="OUTSTANDING_SOURCE_THRESHOLD")

    # Abstention Thresholds (Phase 3)
    # Lowered from 0.70 -> 0.60 and 0.65 -> 0.50 to reduce fence-sitting
    MIN_SOURCES_FOR_VERDICT: int = Field(3, env="MIN_SOURCES_FOR_VERDICT")
    MIN_CREDIBILITY_THRESHOLD: float = Field(0.60, env="MIN_CREDIBILITY_THRESHOLD")
    MIN_CONSENSUS_STRENGTH: float = Field(0.50, env="MIN_CONSENSUS_STRENGTH")

    # Rollout Controls
    FEATURE_ROLLOUT_PERCENTAGE: int = Field(0, env="FEATURE_ROLLOUT_PERCENTAGE")
    INTERNAL_USER_IDS: List[str] = Field([], env="INTERNAL_USER_IDS")

    # ========== PHASE 1: ACCURACY IMPROVEMENTS ==========
    # DeBERTa NLI Model Swap (Phase 1.1)
    ENABLE_DEBERTA_NLI: bool = Field(False, env="ENABLE_DEBERTA_NLI")

    # Judge Few-Shot Prompting (Phase 1.2)
    ENABLE_JUDGE_FEW_SHOT: bool = Field(False, env="ENABLE_JUDGE_FEW_SHOT")

    # Cross-Encoder Evidence Reranking (Phase 1.3)
    ENABLE_CROSS_ENCODER_RERANK: bool = Field(False, env="ENABLE_CROSS_ENCODER_RERANK")

    @property
    def nli_model_name(self) -> str:
        """Dynamic NLI model selection based on feature flag"""
        if self.ENABLE_DEBERTA_NLI:
            return "MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli"
        return "facebook/bart-large-mnli"

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()