import os
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

    # Hang-proofing W2 (2026-07-23): the SIGTERM guard below can't catch
    # kills (OOM/SIGKILL strand rows 'processing' forever — check 46406547).
    # On every boot, fail + refund anything stuck past the watchdog ceiling.
    from app.core.inflight import sweep_stale_checks

    swept = await sweep_stale_checks()
    if swept:
        logger.warning(f"[BOOT SWEEP] Healed {swept} stranded check(s) at startup")

    yield

    # Deploy-shutdown guard (2026-07-21): pipeline tasks die with the process
    # (no Celery). Fail + refund whatever is still in flight so no check is
    # ever left stuck 'processing' with a burned credit after a deploy.
    from app.core.inflight import fail_and_refund_inflight

    await fail_and_refund_inflight()


API_DESCRIPTION = """
Structured evidence research for AI agents and developers.

Tru8 extracts claims from text or URLs, retrieves evidence from 30+ source
providers (government data, academic databases, news, official records),
decomposes claims into verifiable elements, and maps evidence to elements
with relationship labels (**supports** / **challenges** / **context**).

Every source is classified by **tier** (primary, reporting, commentary) and
**type** (data, official, news, analysis, opinion, academic). No hidden
curation — every exclusion has a receipt.

## Authentication

**API key** (recommended for agents and scripts):
```
X-API-Key: tru8_sk_your_key_here
```

**JWT** (dashboard sessions):
```
Authorization: Bearer <clerk_jwt>
```

Create and manage API keys at `POST /api/v1/api-keys` (requires JWT auth).

**Security:** Store API keys in environment variables or a secrets manager.
Never hardcode keys in source code, logs, or client-side bundles.
If a key is compromised, revoke it immediately via `DELETE /api/v1/api-keys/{id}`.

## Workflows

### Synchronous — recommended for agents
```
POST /api/v1/checks/run
```
Single HTTP call. Blocks until complete (60-120s). Returns the full evidence
landscape with claims, elements, evidence, and analytics.
Set your HTTP client timeout to **at least 180 seconds**.
URL inputs auto-select claims (top-ranked, up to 5).

### Streaming — for dashboards
1. **Submit** via `POST /api/v1/checks/stream` — returns SSE progress events
2. **Monitor** via `GET /api/v1/checks/{id}/progress` (SSE) or poll `GET /api/v1/checks/{id}`
3. **Select claims** (article mode): `PATCH /api/v1/checks/{id}/select-claims`

### Agent Commerce — tiered access
For cost-sensitive agent workflows, use the `/agent/` endpoints:

| Tier | Endpoint | Time | Cost | Description |
|------|----------|------|------|-------------|
| Lookup | `POST /agent/lookup` | Instant | £0.02 | Cached result lookup |
| Consensus | via `/agent/check` | Instant | £0.03 | Cross-user consensus (k≥3) |
| Quick | `POST /agent/quick` | ~15s | £0.07 | Reduced pipeline, heuristic classification |
| Full | `POST /agent/full` | ~90s | £0.15 | Complete pipeline, 30+ sources |
| Smart | `POST /agent/check` | Varies | Varies | Automatic fallback: lookup → consensus → quick → full |

Payment via prepaid credits, Skyfire JWT, or x402 (USDC/SIWE).

## Response Structure

Every completed check returns:
- **claims[]** — extracted claims with type and position
- **claims[].claimMap** — elements, evidence refs, orientation line
- **claims[].evidence[]** — sources with URL, snippet, tier, type, relevance
- **_meta** (agent endpoints) — tier executed, cost, landscape metrics
- **_manifest** (agent endpoints) — HMAC-signed manifest; verify the signed fields haven't changed since signing via `GET /verify/{id}`

## Rate Limits

| Endpoint | Limit |
|----------|-------|
| Default | 60 requests/minute |
| Check creation | 10/minute |
| Lookup | 30/minute |
| Credits balance | 60/minute |
"""

app = FastAPI(
    title="Tru8 Evidence Research API",
    description=API_DESCRIPTION,
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None,  # Overridden below with pinned CDN versions
    redoc_url=None,  # Overridden below with pinned CDN versions
    openapi_url="/api/openapi.json",
    redirect_slashes=False,
)


# --- Custom docs routes with pinned CDN versions ---
# FastAPI's defaults use @next (unstable) tags that can serve blank pages.
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html


@app.get("/api/docs", include_in_schema=False)
async def custom_swagger_ui():
    return get_swagger_ui_html(
        openapi_url="/api/openapi.json",
        title="Tru8 API — Swagger",
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.18.2/swagger-ui-bundle.js",
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.18.2/swagger-ui.css",
    )


@app.get("/api/redoc", include_in_schema=False)
async def custom_redoc():
    return get_redoc_html(
        openapi_url="/api/openapi.json",
        title="Tru8 API — ReDoc",
        redoc_js_url="https://cdn.jsdelivr.net/npm/redoc@2.1.5/bundles/redoc.standalone.js",
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

# A8a (pipeline remediation 2026-04-22): filter pipeline-instrumentation
# noise so real errors aren't buried.
#
# A8b retirement note (2026-04-27): the four `_SENTRY_NOISE_MARKERS` have
# been removed because A8b demoted the underlying logger.critical/error
# calls to logger.info at source — they no longer reach Sentry's error
# pipeline, so filtering them here is dead code. The breadcrumb filter
# remains: Redis embedding cache writes still flood the 100-crumb buffer
# and push actionable context out before real exceptions fire.


def _filter_breadcrumb(crumb, hint):
    """Drop high-volume, low-signal breadcrumbs. Redis embedding cache writes
    produce 60+ breadcrumbs per check and push actionable context out of the
    100-crumb buffer before real exceptions fire."""
    if crumb.get("category") == "redis":
        msg = crumb.get("message", "") or ""
        if "'embedding:" in msg:
            return None
    return crumb


# F-SEC-07: keys that may carry user-submitted content or PII; redacted before
# any event leaves the process.
_PII_REDACT_KEYS = {
    "content",
    "url",
    "claim",
    "input_content",
    "input_url",
    "user_query",
    "email",
    "password",
    "api_key",
    "x-api-key",
    "authorization",
    "skyfire-pay-id",
    "x-payer-address",
}


def _redact_pii(obj):
    """Recursively redact known PII-carrying keys from an arbitrary structure."""
    if isinstance(obj, dict):
        return {
            k: ("[REDACTED]" if k.lower() in _PII_REDACT_KEYS else _redact_pii(v))
            for k, v in obj.items()
        }
    if isinstance(obj, list):
        return [_redact_pii(item) for item in obj]
    return obj


def _scrub_event_pii(event, hint):
    """F-SEC-07: drop PII from Sentry events before they leave the process.
    Strips user email/IP, request body fields carrying claim text or URLs,
    and sensitive headers (API keys, auth tokens, wallet addresses)."""
    if not isinstance(event, dict):
        return event

    # Drop the user.email + user.ip_address that send_default_pii would carry.
    user = event.get("user")
    if isinstance(user, dict):
        for key in ("email", "ip_address", "username"):
            user.pop(key, None)

    request = event.get("request")
    if isinstance(request, dict):
        if "data" in request:
            request["data"] = _redact_pii(request["data"])
        headers = request.get("headers")
        if isinstance(headers, dict):
            request["headers"] = {
                k: ("[REDACTED]" if k.lower() in _PII_REDACT_KEYS else v)
                for k, v in headers.items()
            }
        query = request.get("query_string")
        if query and isinstance(query, str) and "token=" in query.lower():
            request["query_string"] = "[REDACTED]"

    extra = event.get("extra")
    if isinstance(extra, dict):
        event["extra"] = _redact_pii(extra)

    return event


# Initialise Sentry only when running in a deployed environment.
# Local dev (ENVIRONMENT=development) was previously polluting the
# production Sentry project — every uvicorn run with a SENTRY_DSN in
# .env produced 127.0.0.1:5433 connection errors against the prod
# project. Gate on ENVIRONMENT so dev runs are silent regardless of
# DSN presence.
_SENTRY_ENABLED_ENVIRONMENTS = {"production", "staging"}
if settings.SENTRY_DSN and settings.ENVIRONMENT.lower() in _SENTRY_ENABLED_ENVIRONMENTS:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,
        before_breadcrumb=_filter_breadcrumb,
        before_send=_scrub_event_pii,
        send_default_pii=False,
        max_breadcrumbs=100,
    )
    app.add_middleware(SentryAsgiMiddleware)
elif settings.SENTRY_DSN:
    logger.info(
        "Sentry DSN set but ENVIRONMENT=%s — skipping Sentry init "
        "(only enabled for %s)",
        settings.ENVIRONMENT,
        sorted(_SENTRY_ENABLED_ENVIRONMENTS),
    )

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

# M-04: Public manifest verification (unauthenticated, rate-limited).
# Mounted at root (not /api/v1) — the verify endpoint is intentionally
# outside the auth-bearing API namespace. The verifyUrl returned in
# _manifest is "/verify/{check_id}", and the developer page documents
# the same path. Keep the mount path aligned with both.
from app.api.v1 import verify

app.include_router(verify.router, tags=["verify"])

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
    "documentationUrl": "https://www.trueight.com/developers",
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
                "classification, and _meta (executedTier, chargedPence)."
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
