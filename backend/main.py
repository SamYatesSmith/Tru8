import os

os.environ.setdefault(
    "DEBUG_EVIDENCE_LEDGER", "1"
)  # Enable evidence ledger for V2 frozen replay

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
import sentry_sdk
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware
from prometheus_client import make_asgi_app
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.core.config import settings
from app.core.rate_limit import limiter
from app.core.database import init_db
from app.core.exceptions import register_exception_handlers
from app.core.correlation import CorrelationIdMiddleware
from app.core.tracing import setup_tracing
from app.api.v1 import (
    checks,
    users,
    auth,
    health,
    payments,
    feedback,
    api_keys,
    webhooks,
    agent,
)
from app.core.logging import setup_logging

setup_logging()

import logging
import time

logger = logging.getLogger(__name__)


async def warmup_ml_models():
    """
    Preload ML models to avoid cold-start failures on first claim.

    Cold-start issue: NLI (~400MB) and embedding (~90MB) models are lazy-loaded,
    causing the first claim to timeout (5s limit vs 10-30s load time).

    This warmup runs at app startup, ensuring models are ready before
    the first fact-check request arrives.
    """
    start_time = time.time()
    logger.info("[STARTUP] Starting ML model warmup...")

    # Warmup embedding model (MiniLM for semantic similarity)
    try:
        from app.services.embeddings import get_embedding_service

        embedding_service = await get_embedding_service()
        # Trigger model load by embedding a test string
        await embedding_service.embed_text("warmup test")
        logger.info("[STARTUP] Embedding model loaded successfully")
    except Exception as e:
        logger.error(f"[STARTUP] Embedding model warmup failed: {e}")

    elapsed = time.time() - start_time
    logger.info(f"[STARTUP] ML model warmup complete in {elapsed:.1f}s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()

    # Phase 5: Initialize Government API adapters
    if settings.ENABLE_API_RETRIEVAL:
        from app.services.api_adapters import initialize_adapters

        initialize_adapters()

    # Warmup search providers to prevent cold-start delay on first claim
    from app.services.search import warmup_search_providers

    warmup_search_providers()

    # Warmup ML models (NLI + embeddings) to prevent cold-start failures
    await warmup_ml_models()

    # Agent commerce: stale-pending transaction cleanup (L-01)
    from app.services.agent_maintenance import start_stale_pending_cleanup

    start_stale_pending_cleanup()

    # M-06: Convergence — daily consensus batch job
    from app.services.consensus import start_consensus_loop

    start_consensus_loop()

    yield


API_DESCRIPTION = """
Structured evidence research for AI agents and developers.

Tru8 extracts claims from text or URLs, retrieves evidence from multiple source
types (primary data, news reporting, commentary, academic, official), decomposes
claims into verifiable elements, and maps evidence to elements with relationship
labels (supports / challenges / context).

## Authentication

**API key** (recommended for agents and scripts):
```
X-API-Key: $TRU8_API_KEY
```

**JWT** (dashboard sessions):
```
Authorization: Bearer <clerk_jwt>
```

Manage API keys at `POST /api/v1/api-keys` (requires JWT).

**Security:** Store API keys in environment variables or a secrets manager.
Never hardcode keys in source code, logs, or client-side bundles.
If a key is compromised, revoke it immediately via `DELETE /api/v1/api-keys/{id}`.

## Workflow

### Synchronous (recommended for agents)
`POST /api/v1/checks/run` — blocks until complete, returns full result with analytics.
Set HTTP timeout >= 180s. URLs auto-select claims (up to 5).

### Streaming (for dashboards)
1. **Submit** a URL or text via `POST /api/v1/checks/stream` — returns SSE progress events.
2. **Poll** status via `GET /api/v1/checks/{id}` or stream via `GET /api/v1/checks/{id}/progress`.
3. **Retrieve** the completed check with claims, elements, evidence, and orientation.

For URL/article inputs with multiple claims, the streaming pipeline pauses after extraction
for claim selection (`PATCH /api/v1/checks/{id}/select-claims`), then resumes
with full retrieval and analysis on selected claims.

## Rate Limits

- Default: 60 requests/minute
- Check creation: 10/minute
"""

app = FastAPI(
    title="Tru8 Evidence Research API",
    description=API_DESCRIPTION,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    redirect_slashes=False,
)

# Register global exception handlers for consistent error responses
register_exception_handlers(app)

# Setup OpenTelemetry tracing (instruments FastAPI, HTTPX, SQLAlchemy)
setup_tracing(app)

# Rate limiting setup
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# Middleware configuration
# Development: Allow localhost/127.0.0.1 origins
# Production: Use specific origins from settings.CORS_ORIGINS
dev_origins = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:8081",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
    "http://127.0.0.1:8081",
]

# CORS configuration - more restrictive in production
is_dev = settings.ENVIRONMENT == "development"
app.add_middleware(
    CORSMiddleware,
    allow_origins=dev_origins if is_dev else settings.CORS_ORIGINS,
    allow_credentials=True,
    # Explicit methods (not "*") for security
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    # Explicit headers (not "*") for security
    allow_headers=[
        "Authorization",
        "Content-Type",
        "Accept",
        "Origin",
        "X-Requested-With",
        "X-API-Key",
        "Idempotency-Key",
        "skyfire-pay-id",
    ],
    expose_headers=[
        "X-Request-Id",
        "X-RateLimit-Limit",
        "X-RateLimit-Remaining",
        "X-Correlation-ID",
        "X-Check-Id",
        "X-Tru8-Tx-Id",
        "PAYMENT-RESPONSE",
        "PAYMENT-REQUEST",
        "PAYMENT-CHALLENGE",
    ],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

if settings.SENTRY_DSN:
    sentry_sdk.init(dsn=settings.SENTRY_DSN, environment=settings.ENVIRONMENT)
    app.add_middleware(SentryAsgiMiddleware)

# Correlation ID middleware - added LAST so it executes FIRST (LIFO order)
# This ensures all requests have a correlation ID before any other middleware runs
app.add_middleware(CorrelationIdMiddleware)

# Metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# API Routes
app.include_router(health.router, prefix="/api/v1/health", tags=["health"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
app.include_router(checks.router, prefix="/api/v1/checks", tags=["checks"])
app.include_router(payments.router, prefix="/api/v1/payments", tags=["payments"])
app.include_router(feedback.router, prefix="/api/v1", tags=["feedback"])
app.include_router(api_keys.router, prefix="/api/v1/api-keys", tags=["api-keys"])
app.include_router(webhooks.router, prefix="/api/v1/webhooks", tags=["webhooks"])
app.include_router(agent.router, prefix="/api/v1/agent", tags=["agent"])

# M-04: Public manifest verification (unauthenticated, rate-limited)
from app.api.v1 import verify

app.include_router(verify.router, prefix="/api/v1", tags=["verify"])

# x402 USDC payment routes (L-05) — conditional on feature flag
if settings.X402_ENABLED:
    from app.api.v1 import agent_x402

    app.include_router(
        agent_x402.router, prefix="/api/v1/agent/x402", tags=["agent-x402"]
    )

    # x402 audit middleware — pure ASGI, outer layer (LIFO: added last, runs first)
    from app.middleware.x402_audit import X402AuditMiddleware

    app.add_middleware(X402AuditMiddleware)


@app.get("/")
async def root():
    return {"name": "Tru8 API", "version": "1.0.0", "status": "operational"}


# MCP Discovery (SEP-1649 draft) — allows agents to find the MCP server
# by probing the API host at a well-known path.
MCP_SERVER_CARD = {
    "version": "1.0",
    "protocolVersion": "2025-06-18",
    "serverInfo": {
        "name": "io.tru8/mcp-server",
        "title": "Tru8 Evidence Research",
        "version": "1.0.0",
    },
    "description": (
        "Structured evidence research. Ground factual claims in source-traced "
        "evidence organized by tier (primary/reporting/commentary) and type "
        "(data/official/news/analysis/opinion/academic), with element "
        "decomposition and relationship mapping (supports/challenges/context)."
    ),
    "documentationUrl": "https://tru8.app/developers",
    "capabilities": {
        "tools": {"listChanged": False},
    },
    "authentication": {
        "required": True,
        "schemes": ["apiKey"],
    },
    "tools": [
        {
            "name": "tru8_check",
            "description": (
                "Evidence research for any claim or URL. Accepts max_tier "
                "(lookup/quick/full) to control depth and cost. Tier fallback: "
                "lookup → quick → full up to max_tier. Returns structured "
                "evidence landscape with element decomposition, source "
                "classification, and _meta (executedTier, chargedCents)."
            ),
        },
        {
            "name": "tru8_get_result",
            "description": "Retrieve completed check with pre-computed analytics.",
        },
        {
            "name": "tru8_get_result_raw",
            "description": "Retrieve raw check data without computed analytics.",
        },
    ],
}


@app.get("/.well-known/mcp/server-card.json", include_in_schema=False)
async def mcp_server_card():
    """MCP server discovery endpoint (SEP-1649 draft)."""
    return MCP_SERVER_CARD


@app.get("/llms.txt", include_in_schema=False)
async def llms_txt():
    """Machine-readable API description for autonomous agents."""
    llms_path = Path(__file__).parent / "static" / "llms.txt"
    return PlainTextResponse(llms_path.read_text(), media_type="text/plain")
