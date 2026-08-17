import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.middleware.mcp_cors import MCPCorsMiddleware
import sentry_sdk
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware
from prometheus_client import make_asgi_app
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.core.config import settings
from app.core.observability import sentry_integrations
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

    # Remote MCP transport (2026-08-04). The MCP ASGI app is MOUNTED below, and
    # a mounted sub-app's own lifespan is NOT run by the parent — a Starlette
    # behaviour that would leave the session manager unstarted and every /mcp
    # request failing at runtime with nothing obviously wrong at boot. So its
    # lifespan is driven from here, explicitly.
    from tru8_mcp.server import mcp as tru8_mcp_server

    async with tru8_mcp_server.session_manager.run():
        logger.info("[STARTUP] MCP streamable-HTTP transport ready at /mcp")

        yield

    # Deploy-shutdown guard (2026-07-21): pipeline tasks die with the process
    # (no Celery). Fail + refund whatever is still in flight so no check is
    # ever left stuck 'processing' with a burned credit after a deploy.
    from app.core.inflight import fail_and_refund_inflight

    await fail_and_refund_inflight()


API_DESCRIPTION = """
Structured evidence research for AI agents and developers.

Tru8 extracts claims from text or URLs, retrieves evidence from web search and specialist
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
| Full | `POST /agent/full` | ~90s | £0.15 | Complete pipeline, web + specialist APIs |
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

# CORS for /mcp only (2026-08-05). The policy above is right for the dashboard
# API and wrong for a public protocol endpoint: it rejected `mcp-session-id` as
# a request header and never exposed it as a response header, so NO browser MCP
# client could hold a session with us — from any origin, including our own.
#
# Registered AFTER the block above on purpose. Starlette answers a preflight and
# returns without calling downstream, and the last middleware added is the
# outermost, so this must be added later to see OPTIONS at all. Moving it above
# the CORSMiddleware call silently disables it.
#
# Everything outside /mcp passes straight through, so the authenticated API's
# CORS posture is unchanged. Reasoning in app/middleware/mcp_cors.py.
app.add_middleware(MCPCorsMiddleware, path_prefix="/mcp")

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
        # Sentry carries EXCEPTIONS; logs go to the log stream. Omitting this
        # argument left the SDK's default LoggingIntegration on at ERROR, so all
        # ~280 logger.error() sites became issues and emails — see
        # app/core/observability.py for the full reasoning before changing it.
        integrations=sentry_integrations(),
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

# Remote MCP server (2026-08-04) — the same tools the published `tru8-mcp`
# package serves over stdio, exposed over streamable HTTP at /mcp so clients
# can connect without installing anything.
#
# One codebase, two transports: this mounts the SAME FastMCP instance from
# tru8_mcp.server, so the tools cannot drift between local and hosted.
#
# Mounted rather than run as a second service: it is a thin adapter over
# /agent/* endpoints this process already serves, so a separate deployment
# would add infrastructure and cost for nothing.
#
# ⚠️ Two things this depends on, both easy to break silently:
#   1. The session manager's lifespan is driven from `lifespan()` above.
#      Mounting alone does NOT start it.
#   2. Credentials are resolved PER REQUEST in tru8_mcp.server._get_client().
#      A cached client here would serve one caller's key to everyone —
#      see tests/unit/test_mcp_request_auth.py.
from mcp.server.transport_security import TransportSecuritySettings

from tru8_mcp.server import mcp as _tru8_mcp_server

# FastMCP's own app serves at settings.streamable_http_path, which defaults to
# "/mcp". Mounting THAT at "/mcp" would put the endpoint at "/mcp/mcp" — and
# the wrong path 404s while everything looks healthy at boot. Set the inner
# path to root so the mount point alone decides the URL.
#
# Set here rather than in tru8_mcp/server.py so the published stdio package
# keeps its stock settings.
_tru8_mcp_server.settings.streamable_http_path = "/"

# Stateless transport (2026-08-05). The SDK keeps an initialisation state per
# session: a session only becomes usable once the client sends the
# `notifications/initialized` notification, and until then EVERY other request
# is rejected with `-32602 Invalid request parameters` before it reaches method
# dispatch. That is spec-correct — clients are required to send it — but it is
# not what real clients all do. Smithery's capability scanner goes straight
# from `initialize` to listing, so it saw:
#
#   Failed to list tools / resources / prompts / triggers:
#   MCP error -32602: Invalid request parameters
#
# and published us as a server with no tools at all. Diagnosed by A/B against
# the deployed endpoint and against mcp 1.12.4 locally: the SAME `tools/list`
# call fails with -32602 without the notification and returns all three tools
# with it. One variable, one outcome.
#
# Stateless mode starts each session already initialised, so a first-request
# `tools/list` is answered normally and a compliant handshake still works. What
# it gives up is session continuity: no `mcp-session-id` is issued, and
# server-initiated messages, resumable streams, progress notifications and
# sampling become impossible. We use none of them — the tools are plain
# request/response — and per-request credential resolution is unaffected
# because it reads the live request, not the session.
#
# It also removes an assumption we would otherwise be making silently: a
# stateful session lives in ONE process, so it breaks the moment this service
# runs more than one replica.
#
# Guard: tests/unit/test_mcp_stateless.py
_tru8_mcp_server.settings.stateless_http = True

# Transport security, stated rather than inherited (2026-08-05). The SDK ships
# DNS rebinding protection that validates the Host and Origin headers, and
# FastMCP AUTO-ENABLES it — with a localhost-only allowlist — whenever the
# server's `host` setting is the default 127.0.0.1, which ours is. That default
# is right for a laptop and fatal for a public endpoint.
#
# It does not fire on the deployed image only because that image resolved
# mcp 1.12.4, which predates the auto-enable. requirements.txt pins a RANGE
# (`mcp[cli]>=1.2,<2`), pip resolves 1.29.0 today, and measured on 1.29.0:
#
#   Host: api.trueight.com      -> 421 Misdirected Request
#   Origin: https://smithery.ai -> 403 Forbidden
#
# i.e. the next rebuild would have taken /mcp down and re-broken every browser
# client, with no code change and nothing in the diff to explain it — the same
# shape as the `mcp>=1.0.0` resolution that killed the PyPI package.
#
# Disabled rather than allowlisted because an allowlist has to be right about
# every hostname that will ever reach us (public domain, Railway health checks,
# any future domain) and is silent when it is wrong. The protection guards
# browser-reachable localhost servers that carry ambient authority; this one is
# public, behind Cloudflare, and authenticates every call with an explicit API
# key, so there is no ambient authority to steal. This restores exactly the
# behaviour production has been verified against, on every version in the range.
#
# Guard: tests/unit/test_mcp_stateless.py
_tru8_mcp_server.settings.transport_security = TransportSecuritySettings(
    enable_dns_rebinding_protection=False
)

app.mount("/mcp", _tru8_mcp_server.streamable_http_app())


# A mount whose inner route is "/" only answers "/mcp/", and this app sets
# redirect_slashes=False, so the bare "/mcp" 404s. Developers will paste the
# bare URL — it is what we document — so send it on explicitly.
#
# 307 rather than 302: it preserves the method and body, which matters because
# every MCP call is a POST carrying JSON-RPC.
@app.api_route(
    "/mcp",
    methods=["GET", "POST", "DELETE"],
    include_in_schema=False,
)
async def _mcp_trailing_slash(request: Request):
    from fastapi.responses import RedirectResponse

    target = "/mcp/"
    if request.url.query:
        target = f"{target}?{request.url.query}"
    return RedirectResponse(url=target, status_code=307)


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
# by probing the API host at a well-known path. Smithery also falls back to
# this card when its automatic scan of the endpoint fails, so it is a public
# statement of identity and must agree with the other two places we declare it.
#
# ⚠️ `name` MUST match the official MCP registry namespace and the PyPI
# ownership marker in the package README (`io.github.SamYatesSmith/tru8`).
# It read `io.tru8/mcp-server` until 2026-08-05 — a namespace asserting
# ownership of `tru8.io`, a domain that does not exist. That exact invention
# already cost us one failed registry publish; served publicly it also
# contradicts the registry entry anyone cross-checks us against.
MCP_SERVER_CARD = {
    "version": "1.0",
    "protocolVersion": "2025-06-18",
    "serverInfo": {
        "name": "io.github.SamYatesSmith/tru8",
        "title": "Tru8 Evidence Research",
        # Must track the published tru8-mcp package version — the 1.0.5
        # release (3c8d3ff) missed this line and the drift guard caught it
        # 2026-08-17. server.json (the registry manifest) is bumped only on a
        # founder-gated re-publish; this card is what OUR API serves and has
        # no such gate.
        "version": "1.0.5",
    },
    # Where the hosted transport actually is. Without this a scanner reading
    # the card has our identity but no endpoint to connect to.
    "remotes": [
        {
            "type": "streamable-http",
            "url": "https://api.trueight.com/mcp",
        }
    ],
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
    # Precise on purpose: connecting and listing tools needs NO credential —
    # that is what lets Smithery and other registries scan us automatically.
    # A key is required only to INVOKE a tool. Saying just "required: true"
    # invites a scanner to assume an OAuth handshake we do not implement.
    "authentication": {
        "required": True,
        "schemes": ["apiKey"],
        "appliesTo": "toolInvocation",
        "discoveryRequiresAuth": False,
        "apiKey": {
            "header": "X-API-Key",
            "queryParameter": "apiKey",
            "obtainAt": "https://www.trueight.com/dashboard/settings",
        },
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
