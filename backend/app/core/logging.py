import logging
import sys
from app.core.config import settings

# Global flag to prevent duplicate setup
_logging_configured = False

def setup_logging():
    """
    Configure logging for the application.

    Works with both FastAPI (uvicorn) and Celery workers by explicitly
    configuring app loggers rather than relying on basicConfig.

    Uses a global flag to prevent duplicate handler setup.
    """
    global _logging_configured

    # Only configure once to prevent duplicate handlers
    if _logging_configured:
        return

    log_level = logging.DEBUG if settings.DEBUG else logging.INFO

    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Create single handler for root logger only
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    handler.setLevel(log_level)

    # Configure root logger (single handler point)
    root_logger = logging.getLogger()
    # Clear any existing handlers to prevent duplicates
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level)

    # Configure app loggers - set level only, let propagation handle output
    app_loggers = [
        "app",
        "app.pipeline",
        "app.pipeline.extract",
        "app.pipeline.retrieve",
        "app.pipeline.verify",
        "app.pipeline.judge",
        "app.services",
        "app.services.search",
        "app.services.evidence",
        "app.utils",
        "app.utils.query_planner",
        "app.workers",
    ]

    for logger_name in app_loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(log_level)
        # Propagate to root logger (don't add individual handlers)
        logger.propagate = True
        # Clear any handlers that may have been added previously
        logger.handlers.clear()

    # Silence noisy libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)  # HTTP connection spam
    logging.getLogger("celery.worker").setLevel(logging.INFO)  # Timer wake-up spam
    logging.getLogger("celery.utils.functional").setLevel(logging.WARNING)
    logging.getLogger("trafilatura").setLevel(logging.WARNING)  # HTML parsing spam
    logging.getLogger("sentence_transformers").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    _logging_configured = True