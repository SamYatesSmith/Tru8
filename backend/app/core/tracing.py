"""
OpenTelemetry tracing configuration.

This module sets up distributed tracing for the application using OpenTelemetry.
Traces are exported to the configured OTLP endpoint (e.g., Jaeger, Zipkin, or
cloud providers like Datadog, Honeycomb).

All imports are optional - tracing is disabled gracefully if packages are missing.
"""

import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

# Optional imports - tracing is disabled if packages are missing
try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
    from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False
    logger.info("OpenTelemetry packages not installed - tracing disabled")

# Optional instrumentation packages
try:
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
    HTTPX_INSTRUMENTATION_AVAILABLE = True
except ImportError:
    HTTPX_INSTRUMENTATION_AVAILABLE = False

try:
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
    SQLALCHEMY_INSTRUMENTATION_AVAILABLE = True
except ImportError:
    SQLALCHEMY_INSTRUMENTATION_AVAILABLE = False

# Global flag to track initialization
_tracing_configured = False


def setup_tracing(app) -> None:
    """
    Configure OpenTelemetry tracing for the application.

    Sets up:
    - TracerProvider with service metadata
    - FastAPI instrumentation (auto-creates spans for requests)
    - HTTPX instrumentation (traces outgoing HTTP calls)
    - SQLAlchemy instrumentation (traces database queries)
    - Export to OTLP endpoint if configured, otherwise console in debug mode

    Args:
        app: FastAPI application instance
    """
    global _tracing_configured

    if _tracing_configured:
        return

    # Skip if OpenTelemetry is not installed
    if not OTEL_AVAILABLE:
        logger.info("Tracing disabled - OpenTelemetry packages not installed")
        _tracing_configured = True
        return

    # Skip tracing in development unless explicitly enabled
    otlp_endpoint = settings.OTLP_ENDPOINT  # Empty string if not configured
    if not otlp_endpoint and settings.ENVIRONMENT == "development":
        logger.info("Tracing disabled in development (no OTLP_ENDPOINT configured)")
        _tracing_configured = True
        return

    # Create resource with service metadata
    resource = Resource.create({
        SERVICE_NAME: "tru8-api",
        SERVICE_VERSION: "0.1.0",
        "deployment.environment": settings.ENVIRONMENT,
    })

    # Create tracer provider
    provider = TracerProvider(resource=resource)

    # Configure exporter based on environment
    if otlp_endpoint:
        try:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

            otlp_exporter = OTLPSpanExporter(
                endpoint=otlp_endpoint,
                insecure=settings.ENVIRONMENT != "production",
            )
            provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
            logger.info(f"Tracing enabled: exporting to {otlp_endpoint}")
        except ImportError:
            logger.warning("OTLP exporter not available, install opentelemetry-exporter-otlp")
            if settings.DEBUG:
                provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
    elif settings.DEBUG:
        # Console export for development debugging
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
        logger.info("Tracing enabled: console output (debug mode)")

    # Set global tracer provider
    trace.set_tracer_provider(provider)

    # Instrument FastAPI
    FastAPIInstrumentor.instrument_app(
        app,
        excluded_urls="/health,/metrics",  # Skip health checks and metrics
    )

    # Instrument HTTPX (outgoing HTTP calls)
    if HTTPX_INSTRUMENTATION_AVAILABLE:
        try:
            HTTPXClientInstrumentor().instrument()
            logger.debug("HTTPX instrumentation enabled")
        except Exception as e:
            logger.warning(f"Failed to instrument HTTPX: {e}")

    # Note: SQLAlchemy instrumentation requires the engine to be available
    # This will be called separately after database initialization if needed

    _tracing_configured = True


def instrument_database(engine) -> None:
    """
    Instrument SQLAlchemy engine for tracing.

    Should be called after database engine is created.

    Args:
        engine: SQLAlchemy engine instance
    """
    if not _tracing_configured or not OTEL_AVAILABLE:
        return

    if not SQLALCHEMY_INSTRUMENTATION_AVAILABLE:
        return

    try:
        SQLAlchemyInstrumentor().instrument(engine=engine)
        logger.debug("SQLAlchemy instrumentation enabled")
    except Exception as e:
        logger.warning(f"Failed to instrument SQLAlchemy: {e}")


def get_tracer(name: str = __name__):
    """Get a tracer instance for creating custom spans."""
    if not OTEL_AVAILABLE:
        return None
    return trace.get_tracer(name)
