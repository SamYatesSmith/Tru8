import logging
import logging.handlers
import sys
import os
from pathlib import Path
from app.core.config import settings
from app.core.correlation import CorrelationIdFilter

# Global flag to prevent duplicate setup
_logging_configured = False

# Log file path - in backend directory for easy access
LOG_FILE_PATH = Path(__file__).parent.parent.parent / "logs" / "pipeline.log"



def setup_logging():
    """
    Configure logging for the application.

    Works with both FastAPI (uvicorn) and Celery workers by explicitly
    configuring app loggers rather than relying on basicConfig.

    Includes correlation ID in all log entries for request tracing.

    Uses a global flag to prevent duplicate handler setup.

    LOGS TO FILE: backend/logs/pipeline.log (rotates at 10MB, keeps 3 backups)
    """
    global _logging_configured

    # Only configure once to prevent duplicate handlers
    if _logging_configured:
        return

    log_level = logging.DEBUG if settings.DEBUG else logging.INFO

    # Create formatter with correlation ID
    # Format: timestamp - correlation_id - logger_name - level - message
    formatter = logging.Formatter(
        "%(asctime)s - %(correlation_id)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)
    console_handler.addFilter(CorrelationIdFilter())

    # Create file handler with rotation (10MB max, keep 3 backups)
    try:
        LOG_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)

        # On Windows, RotatingFileHandler.doRollover() calls os.rename() which
        # fails if ANY other handle holds the file open.  Truncate oversized
        # files *before* opening the handler so the very first emit() does not
        # immediately trigger a rotation that races with other processes.
        if LOG_FILE_PATH.exists() and LOG_FILE_PATH.stat().st_size > 10 * 1024 * 1024:
            LOG_FILE_PATH.write_text("", encoding="utf-8")

        file_handler = logging.handlers.RotatingFileHandler(
            LOG_FILE_PATH,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=3,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG)  # Capture everything to file
        file_handler.addFilter(CorrelationIdFilter())

        print(f"\n{'='*60}", flush=True)
        print(f"[LOGGING] Pipeline log file: {LOG_FILE_PATH}", flush=True)
        print(f"[LOGGING] Logging level: {logging.getLevelName(log_level)}", flush=True)
        print(f"{'='*60}\n", flush=True)

    except Exception as e:
        file_handler = None
        print(f"[LOGGING WARNING] Could not setup file logging: {e}")

    # Configure root logger (single handler point)
    root_logger = logging.getLogger()
    # Clear any existing handlers to prevent duplicates
    root_logger.handlers.clear()
    root_logger.addHandler(console_handler)
    if file_handler:
        root_logger.addHandler(file_handler)
    root_logger.setLevel(log_level)

    # Configure app loggers - set level only, let propagation handle output
    app_loggers = [
        "app",
        "app.api",
        "app.api.v1",
        "app.pipeline",
        "app.pipeline.extract",
        "app.pipeline.retrieve",
        "app.pipeline.judge",
        "app.pipeline.runner",
        "app.pipeline.progress",
        "app.services",
        "app.services.search",
        "app.services.evidence",
        "app.utils",
        "app.utils.query_planner",
        "app.workers",
        "app.workers.pipeline",
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
    logging.getLogger("trafilatura").setLevel(logging.WARNING)  # HTML parsing spam
    logging.getLogger("sentence_transformers").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    _logging_configured = True


def clear_log_file():
    """
    Clear the pipeline log file.

    Call this before running a test to get a clean log.
    Can be triggered via API endpoint or called directly.
    """
    try:
        if LOG_FILE_PATH.exists():
            with open(LOG_FILE_PATH, 'w', encoding='utf-8') as f:
                f.write(f"{'='*60}\n")
                f.write(f"[LOG CLEARED] New logging session started\n")
                f.write(f"{'='*60}\n\n")
            return True
    except Exception as e:
        print(f"[LOGGING] Failed to clear log file: {e}")
    return False


def get_log_file_path() -> str:
    """Return the path to the log file for reading."""
    return str(LOG_FILE_PATH)