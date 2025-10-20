from typing import List
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
        ["http://localhost:3000", "http://localhost:8081"],
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
    ENABLE_DOMAIN_CAPPING: bool = Field(False, env="ENABLE_DOMAIN_CAPPING")
    ENABLE_DEDUPLICATION: bool = Field(False, env="ENABLE_DEDUPLICATION")
    ENABLE_SOURCE_DIVERSITY: bool = Field(False, env="ENABLE_SOURCE_DIVERSITY")
    ENABLE_CONTEXT_PRESERVATION: bool = Field(False, env="ENABLE_CONTEXT_PRESERVATION")
    ENABLE_SAFETY_CHECKING: bool = Field(False, env="ENABLE_SAFETY_CHECKING")
    ENABLE_CITATION_ARCHIVAL: bool = Field(False, env="ENABLE_CITATION_ARCHIVAL")
    ENABLE_VERDICT_MONITORING: bool = Field(False, env="ENABLE_VERDICT_MONITORING")

    # Phase 1.5 - Semantic Intelligence
    ENABLE_FACTCHECK_API: bool = Field(False, env="ENABLE_FACTCHECK_API")
    ENABLE_TEMPORAL_CONTEXT: bool = Field(False, env="ENABLE_TEMPORAL_CONTEXT")

    # Phase 2 - User Experience & Trust
    ENABLE_CLAIM_CLASSIFICATION: bool = Field(False, env="ENABLE_CLAIM_CLASSIFICATION")
    ENABLE_ENHANCED_EXPLAINABILITY: bool = Field(False, env="ENABLE_ENHANCED_EXPLAINABILITY")

    # Domain Capping Configuration
    MAX_EVIDENCE_PER_DOMAIN: int = Field(3, env="MAX_EVIDENCE_PER_DOMAIN")
    DOMAIN_DIVERSITY_THRESHOLD: float = Field(0.6, env="DOMAIN_DIVERSITY_THRESHOLD")

    # Rollout Controls
    FEATURE_ROLLOUT_PERCENTAGE: int = Field(0, env="FEATURE_ROLLOUT_PERCENTAGE")
    INTERNAL_USER_IDS: List[str] = Field([], env="INTERNAL_USER_IDS")

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()