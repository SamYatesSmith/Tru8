from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
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
from app.api.v1 import checks, users, auth, health, payments, feedback
from app.core.logging import setup_logging

setup_logging()

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()

    # Phase 5: Initialize Government API adapters
    if settings.ENABLE_API_RETRIEVAL:
        from app.services.api_adapters import initialize_adapters
        initialize_adapters()

    yield

app = FastAPI(
    title="Tru8 API",
    description="AI-powered fact verification with multi-source evidence",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/api/docs" if settings.DEBUG else None,
    redirect_slashes=False,  # Disable automatic trailing slash redirects
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
    ],
    expose_headers=["X-Request-Id", "X-RateLimit-Limit", "X-RateLimit-Remaining", "X-Correlation-ID"],
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

@app.get("/")
async def root():
    return {"name": "Tru8 API", "version": "0.1.0", "status": "operational"}