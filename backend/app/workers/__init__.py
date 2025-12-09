from celery import Celery
from celery.signals import worker_ready, setup_logging as celery_setup_logging
from app.core.config import settings
from app.core.logging import setup_logging
import logging
import asyncio
import time

# Setup logging at module import time
setup_logging()

logger = logging.getLogger(__name__)


@celery_setup_logging.connect
def configure_celery_logging(**kwargs):
    """
    Configure logging after Celery initializes its own logging system.
    This ensures our app loggers are properly configured.
    """
    setup_logging()
    logger.info("[WORKER] Celery logging configured")

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
    # Restart workers after processing 100 tasks to reduce cold-start frequency
    # (Was 10, but frequent restarts caused ML models to reload, causing first-claim failures)
    worker_max_tasks_per_child=100,
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


def warmup_ml_models():
    """
    Preload ML models to avoid cold-start failures on first claim.

    Cold-start issue: NLI (~400MB) and embedding (~90MB) models are lazy-loaded,
    causing the first claim to timeout (5s limit vs 10-30s load time).

    This warmup runs at worker startup, ensuring models are ready before
    the first fact-check request arrives.
    """
    start_time = time.time()
    logger.info("[WORKER] Starting ML model warmup...")

    async def _warmup():
        # Warmup NLI model (DeBERTa for natural language inference)
        try:
            from app.pipeline.verify import get_claim_verifier
            verifier = await get_claim_verifier()
            await verifier.nli_verifier.initialize()
            logger.info("[WORKER] NLI model loaded successfully")
        except Exception as e:
            logger.error(f"[WORKER] NLI model warmup failed: {e}")

        # Warmup embedding model (MiniLM for semantic similarity)
        try:
            from app.services.embeddings import get_embedding_service
            embedding_service = await get_embedding_service()
            # Trigger model load by embedding a test string
            await embedding_service.embed_text("warmup test")
            logger.info("[WORKER] Embedding model loaded successfully")
        except Exception as e:
            logger.error(f"[WORKER] Embedding model warmup failed: {e}")

    try:
        asyncio.run(_warmup())
        elapsed = time.time() - start_time
        logger.info(f"[WORKER] ML model warmup complete in {elapsed:.1f}s")
    except Exception as e:
        logger.error(f"[WORKER] ML model warmup failed: {e}")


@worker_ready.connect
def initialize_worker(**kwargs):
    """
    Initialize API adapters and ML models when Celery worker starts.

    CRITICAL: Celery workers run in separate processes from FastAPI server,
    so adapters and models must be initialized here as well as in main.py.
    """
    logger.info("Celery worker starting - initializing components...")

    # Initialize API adapters
    if settings.ENABLE_API_RETRIEVAL:
        from app.services.api_adapters import initialize_adapters
        initialize_adapters()
        logger.info("[WORKER] API adapters initialized in Celery worker")
    else:
        logger.info("[WORKER] ENABLE_API_RETRIEVAL is False, skipping adapter initialization")

    # Warmup ML models (NLI + embeddings) to prevent cold-start failures
    warmup_ml_models()