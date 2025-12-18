from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
import sentry_sdk
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware
from prometheus_client import make_asgi_app

from app.core.config import settings
from app.core.database import init_db
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
    description="Fact-checking API with dated evidence",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/api/docs" if settings.DEBUG else None,
    redirect_slashes=False,  # Disable automatic trailing slash redirects
)

# Middleware
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
app.add_middleware(
    CORSMiddleware,
    allow_origins=dev_origins if settings.ENVIRONMENT == "development" else settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

if settings.SENTRY_DSN:
    sentry_sdk.init(dsn=settings.SENTRY_DSN, environment=settings.ENVIRONMENT)
    app.add_middleware(SentryAsgiMiddleware)

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