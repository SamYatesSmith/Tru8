from celery import Celery
from celery.signals import worker_ready
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

celery_app = Celery(
    "tru8",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.workers.pipeline"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=settings.PIPELINE_TIMEOUT_SECONDS,
    task_soft_time_limit=settings.PIPELINE_TIMEOUT_SECONDS - 2,
    # CRITICAL: Limit worker concurrency to prevent memory exhaustion
    # Default would be CPU count (32 on your system) which causes crashes
    worker_concurrency=2,
    # Use solo pool for Windows compatibility (prefork has permission issues on Windows)
    worker_pool="solo",
    # Restart workers after processing 10 tasks to prevent memory leaks
    worker_max_tasks_per_child=10,
    # Don't prefetch too many tasks
    worker_prefetch_multiplier=1,
    # CRITICAL: Set visibility timeout to match task timeout
    # Without this, tasks remain invisible for 1 hour (default) if not acked
    broker_transport_options={
        'visibility_timeout': settings.PIPELINE_TIMEOUT_SECONDS + 10,  # Task timeout + buffer
        'fanout_prefix': True,
        'fanout_patterns': True
    },
    # Ensure tasks are acknowledged immediately when received
    task_acks_late=False,
    task_reject_on_worker_lost=True,
)


@worker_ready.connect
def initialize_worker(**kwargs):
    """
    Initialize API adapters when Celery worker starts.

    CRITICAL: Celery workers run in separate processes from FastAPI server,
    so adapters must be initialized here as well as in main.py.
    """
    logger.info("Celery worker starting - initializing API adapters...")

    if settings.ENABLE_API_RETRIEVAL:
        from app.services.api_adapters import initialize_adapters
        initialize_adapters()
        logger.info("✅ API adapters initialized in Celery worker")
    else:
        logger.info("⚠️  ENABLE_API_RETRIEVAL is False, skipping adapter initialization")