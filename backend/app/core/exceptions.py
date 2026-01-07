"""
Global exception handlers for consistent error responses.

This module provides centralized exception handling for the FastAPI application,
ensuring all errors are returned in a consistent JSON format with appropriate
logging and Sentry integration.
"""

import logging
import traceback
from typing import Any

from fastapi import Request, status
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.responses import JSONResponse
import sentry_sdk

from app.core.config import settings

logger = logging.getLogger(__name__)


class APIError(Exception):
    """Base exception for API errors with consistent format."""

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code or f"ERR_{status_code}"
        self.details = details or {}
        super().__init__(message)


class InsufficientCreditsError(APIError):
    """Raised when user doesn't have enough credits."""

    def __init__(self, required: int = 1, available: int = 0):
        super().__init__(
            message="Insufficient credits for this operation",
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            error_code="INSUFFICIENT_CREDITS",
            details={"required": required, "available": available},
        )


class PipelineError(APIError):
    """Raised when the fact-checking pipeline fails."""

    def __init__(self, stage: str, message: str):
        super().__init__(
            message=f"Pipeline failed at stage '{stage}': {message}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="PIPELINE_ERROR",
            details={"stage": stage},
        )


class ExternalServiceError(APIError):
    """Raised when an external service (API, database) fails."""

    def __init__(self, service: str, message: str):
        super().__init__(
            message=f"External service '{service}' error: {message}",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error_code="EXTERNAL_SERVICE_ERROR",
            details={"service": service},
        )


def _build_error_response(
    status_code: int,
    message: str,
    error_code: str,
    details: dict[str, Any] | None = None,
    request_id: str | None = None,
) -> dict[str, Any]:
    """Build a consistent error response structure."""
    response = {
        "error": {
            "code": error_code,
            "message": message,
            "status": status_code,
        }
    }

    if details:
        response["error"]["details"] = details

    if request_id:
        response["error"]["request_id"] = request_id

    return response


async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
    """Handle custom API errors."""
    request_id = getattr(request.state, "request_id", None)

    logger.warning(
        "API error: %s (code=%s, status=%d)",
        exc.message,
        exc.error_code,
        exc.status_code,
        extra={
            "error_code": exc.error_code,
            "status_code": exc.status_code,
            "path": request.url.path,
            "request_id": request_id,
        },
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=_build_error_response(
            status_code=exc.status_code,
            message=exc.message,
            error_code=exc.error_code,
            details=exc.details,
            request_id=request_id,
        ),
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle FastAPI HTTPException with consistent format."""
    request_id = getattr(request.state, "request_id", None)

    # Map common status codes to error codes
    error_code_map = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        409: "CONFLICT",
        422: "VALIDATION_ERROR",
        429: "RATE_LIMIT_EXCEEDED",
        500: "INTERNAL_ERROR",
        502: "BAD_GATEWAY",
        503: "SERVICE_UNAVAILABLE",
    }

    error_code = error_code_map.get(exc.status_code, f"HTTP_{exc.status_code}")

    logger.warning(
        "HTTP exception: %s (status=%d, path=%s)",
        exc.detail,
        exc.status_code,
        request.url.path,
        extra={
            "status_code": exc.status_code,
            "path": request.url.path,
            "request_id": request_id,
        },
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=_build_error_response(
            status_code=exc.status_code,
            message=str(exc.detail),
            error_code=error_code,
            request_id=request_id,
        ),
        headers=exc.headers,
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle Pydantic validation errors with detailed field info."""
    request_id = getattr(request.state, "request_id", None)

    # Extract field-level errors
    errors = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"])
        errors.append({
            "field": field,
            "message": error["msg"],
            "type": error["type"],
        })

    logger.warning(
        "Validation error on %s: %d field(s) invalid",
        request.url.path,
        len(errors),
        extra={
            "path": request.url.path,
            "errors": errors,
            "request_id": request_id,
        },
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=_build_error_response(
            status_code=422,
            message="Request validation failed",
            error_code="VALIDATION_ERROR",
            details={"fields": errors},
            request_id=request_id,
        ),
    )


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle all uncaught exceptions with consistent format.

    This is the last-resort handler that catches any unhandled exceptions,
    logs them, reports to Sentry, and returns a safe error response.
    """
    request_id = getattr(request.state, "request_id", None)

    # Log the full traceback
    logger.error(
        "Unhandled exception on %s %s: %s",
        request.method,
        request.url.path,
        str(exc),
        exc_info=True,
        extra={
            "path": request.url.path,
            "method": request.method,
            "request_id": request_id,
        },
    )

    # Report to Sentry if configured
    if settings.SENTRY_DSN:
        with sentry_sdk.push_scope() as scope:
            scope.set_tag("path", request.url.path)
            scope.set_tag("method", request.method)
            if request_id:
                scope.set_tag("request_id", request_id)
            sentry_sdk.capture_exception(exc)

    # In debug mode, include traceback for development
    details = None
    if settings.DEBUG:
        details = {
            "exception_type": type(exc).__name__,
            "traceback": traceback.format_exc().split("\n"),
        }

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=_build_error_response(
            status_code=500,
            message="An internal error occurred. Please try again later.",
            error_code="INTERNAL_ERROR",
            details=details,
            request_id=request_id,
        ),
    )


def register_exception_handlers(app) -> None:
    """Register all exception handlers with the FastAPI app."""
    from fastapi.exceptions import HTTPException, RequestValidationError

    app.add_exception_handler(APIError, api_error_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, global_exception_handler)
