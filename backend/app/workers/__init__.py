from celery import Celery
from app.core.config import settings

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
)