"""
Correlation ID middleware for request tracing.

This module provides a correlation ID that can be used to trace requests
across all log entries, making debugging and monitoring easier.
"""

import uuid
import logging
from contextvars import ContextVar
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Context variable to store correlation ID per request
correlation_id_var: ContextVar[str | None] = ContextVar("correlation_id", default=None)


def get_correlation_id() -> str | None:
    """Get the current correlation ID from context."""
    return correlation_id_var.get()


def set_correlation_id(correlation_id: str) -> None:
    """Set the correlation ID in context."""
    correlation_id_var.set(correlation_id)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """
    Middleware that generates or extracts a correlation ID for each request.

    The correlation ID can be provided via the X-Correlation-ID header,
    or a new one will be generated. The ID is stored in request.state
    and added to response headers.
    """

    HEADER_NAME = "X-Correlation-ID"

    async def dispatch(self, request: Request, call_next) -> Response:
        # Extract from header or generate new ID
        correlation_id = request.headers.get(self.HEADER_NAME) or str(uuid.uuid4())

        # Store in context var for logging access
        set_correlation_id(correlation_id)

        # Store in request.state for exception handlers
        request.state.request_id = correlation_id

        # Process request
        response = await call_next(request)

        # Add to response headers for client tracing
        response.headers[self.HEADER_NAME] = correlation_id

        return response


class CorrelationIdFilter(logging.Filter):
    """
    Logging filter that adds correlation_id to log records.

    This allows the correlation ID to be included in log output
    via the %(correlation_id)s format specifier.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = get_correlation_id() or "-"
        return True
