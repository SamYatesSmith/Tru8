"""
Progress reporting for inline SSE pipeline execution.

Uses Redis to store progress so both POST /stream and GET /progress endpoints
can access the same data.
"""

import asyncio
import json
import logging
import redis
from datetime import datetime, timezone
from typing import AsyncGenerator, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

# Redis client for progress storage
_redis_client = None


def _get_redis() -> redis.Redis:
    """Get or create Redis client."""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis_client


class ProgressReporter:
    """
    Progress reporter that yields SSE events for streaming responses.

    Replaces Celery's self.update_state() pattern with async queue-based
    event generation that can be consumed by StreamingResponse.
    """

    # Stage progress mappings (must match existing SSE format for client compatibility)
    STAGE_PROGRESS = {
        "starting": 0,
        "ingest": 10,
        "extract": 20,
        "factcheck": 25,
        "select": 30,
        "decompose": 40,
        "retrieve": 55,
        "analyze": 80,
        "query": 85,
        "complete": 100,
    }

    STAGE_MESSAGES = {
        "starting": "Initialising analysis...",
        "ingest": "Processing input content...",
        "extract": "Identifying claims...",
        "factcheck": "Searching fact-check databases...",
        "select": "Ranking claims by significance...",
        "decompose": "Decomposing claims into required elements...",
        "retrieve": "Gathering evidence for each element...",
        "analyze": "Mapping evidence to elements...",
        "query": "Answering your question...",
        "complete": "Analysis complete.",
    }

    def __init__(self, check_id: str):
        self.check_id = check_id
        self._queue: asyncio.Queue = asyncio.Queue()
        self._completed = False
        self._error: Optional[str] = None
        self._redis_key = f"inline-progress:{check_id}"
        # Initialize Redis progress
        self._write_to_redis(
            {
                "status": "processing",
                "stage": "starting",
                "progress": 0,
                "message": "Initialising fact-check...",
                "timeEstimate": "within 2 minutes",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

    def _write_to_redis(self, data: dict) -> None:
        """Write progress data to Redis for GET /progress endpoint."""
        try:
            r = _get_redis()
            r.setex(self._redis_key, 600, json.dumps(data))  # 10 min TTL
        except Exception as e:
            logger.warning(f"[PROGRESS] Failed to write to Redis: {e}")

    def _get_time_estimate(self, progress: int) -> str:
        """Get conservative time estimate based on progress."""
        if progress < 25:
            return "within 2 minutes"
        elif progress < 50:
            return "within 90 seconds"
        elif progress < 70:
            return "within 1 minute"
        elif progress < 90:
            return "within 30 seconds"
        else:
            return "momentarily"

    async def report_progress(
        self, stage: str, progress: Optional[int] = None, message: Optional[str] = None
    ) -> None:
        """
        Report pipeline progress.

        Args:
            stage: Pipeline stage name (ingest, extract, factcheck, select, decompose, retrieve, analyze, query, complete)
            progress: Progress percentage (0-100). If None, uses STAGE_PROGRESS mapping.
            message: Progress message. If None, uses STAGE_MESSAGES mapping.
        """
        if self._completed:
            return

        # Use defaults from mappings if not provided
        if progress is None:
            progress = self.STAGE_PROGRESS.get(stage, 0)
        if message is None:
            message = self.STAGE_MESSAGES.get(stage, f"Processing {stage}...")

        time_estimate = self._get_time_estimate(progress)
        event = {
            "type": "progress",
            "checkId": self.check_id,
            "stage": stage,
            "progress": progress,
            "message": message,
            "timeEstimate": time_estimate,
        }

        # Write to Redis so GET /progress can read it
        self._write_to_redis(
            {
                "status": "processing",
                "stage": stage,
                "progress": progress,
                "message": message,
                "timeEstimate": time_estimate,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

        await self._queue.put(event)
        logger.debug(f"[PROGRESS] {stage}: {progress}% - {message}")

    async def report_completed(self) -> None:
        """Report pipeline completion."""
        if self._completed:
            return

        self._completed = True
        event = {
            "type": "completed",
            "checkId": self.check_id,
            "status": "completed",
            "progress": 100,
            "message": "Fact-check completed successfully",
        }

        # Write to Redis
        self._write_to_redis(
            {
                "status": "completed",
                "stage": "completed",
                "progress": 100,
                "message": "Fact-check completed successfully",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

        await self._queue.put(event)
        await self._queue.put(None)  # Signal end of stream
        logger.info(f"[PROGRESS] Check {self.check_id} completed")

    async def report_error(self, error: str) -> None:
        """Report pipeline error."""
        if self._completed:
            return

        self._completed = True
        self._error = error
        event = {
            "type": "error",
            "checkId": self.check_id,
            "status": "failed",
            "error": error,
        }

        # Write to Redis
        self._write_to_redis(
            {
                "status": "failed",
                "stage": "failed",
                "progress": 0,
                "message": error,
                "error": error,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

        await self._queue.put(event)
        await self._queue.put(None)  # Signal end of stream
        logger.error(f"[PROGRESS] Check {self.check_id} failed: {error}")

    async def send_heartbeat(self) -> None:
        """Send heartbeat to keep connection alive."""
        if self._completed:
            return

        event = {
            "type": "heartbeat",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        await self._queue.put(event)

    async def events(
        self,
        pipeline_task: Optional[asyncio.Task] = None,
        max_duration_seconds: int = 180,  # 3 minute overall timeout
    ) -> AsyncGenerator[str, None]:
        """
        Async generator that yields SSE-formatted events.

        Args:
            pipeline_task: Optional task running the pipeline. If provided,
                          will check for task exceptions and report them.
            max_duration_seconds: Maximum time to run before forcing termination.

        Use this with StreamingResponse:
            return StreamingResponse(reporter.events(task), media_type="text/event-stream")
        """
        import time

        start_time = time.time()

        # Send initial connection event
        connect_event = {
            "type": "connected",
            "checkId": self.check_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        event_str = f"data: {json.dumps(connect_event)}\n\n"
        logger.info(
            f"[SSE] Sending connected event for check {self.check_id}: {event_str[:100]}"
        )
        yield event_str

        # Yield events from queue until completion
        while True:
            try:
                # Check overall timeout - force termination if exceeded
                elapsed = time.time() - start_time
                if elapsed > max_duration_seconds:
                    logger.error(
                        f"Pipeline exceeded max duration ({max_duration_seconds}s), forcing termination"
                    )
                    if pipeline_task and not pipeline_task.done():
                        pipeline_task.cancel()
                    error_event = {
                        "type": "error",
                        "checkId": self.check_id,
                        "status": "failed",
                        "error": "Pipeline timed out. Your credit has been returned.",
                    }
                    yield f"data: {json.dumps(error_event)}\n\n"
                    break

                # Check if pipeline task completed (success or failure)
                if pipeline_task and pipeline_task.done():
                    exc = pipeline_task.exception()
                    if exc:
                        # Pipeline raised an exception - report it
                        logger.error(f"Pipeline task exception: {exc}")
                        error_event = {
                            "type": "error",
                            "checkId": self.check_id,
                            "status": "failed",
                            "error": str(exc),
                        }
                        yield f"data: {json.dumps(error_event)}\n\n"
                        break
                    else:
                        # Pipeline completed successfully - send completion event
                        logger.info(
                            f"Pipeline task completed successfully for {self.check_id}"
                        )
                        complete_event = {
                            "type": "completed",
                            "checkId": self.check_id,
                            "status": "completed",
                            "progress": 100,
                            "message": "Fact-check completed successfully",
                        }
                        yield f"data: {json.dumps(complete_event)}\n\n"
                        self._completed = True
                        break

                # Wait for next event with timeout for heartbeats
                event = await asyncio.wait_for(self._queue.get(), timeout=10.0)

                if event is None:
                    # End of stream
                    break

                yield f"data: {json.dumps(event)}\n\n"

            except asyncio.TimeoutError:
                # Check if pipeline task completed during heartbeat timeout
                if pipeline_task and pipeline_task.done():
                    exc = pipeline_task.exception()
                    if exc:
                        logger.error(f"Pipeline task exception during heartbeat: {exc}")
                        error_event = {
                            "type": "error",
                            "checkId": self.check_id,
                            "status": "failed",
                            "error": str(exc),
                        }
                        yield f"data: {json.dumps(error_event)}\n\n"
                        break
                    else:
                        # Pipeline completed successfully - send completion event
                        logger.info(
                            f"Pipeline task completed during heartbeat for {self.check_id}"
                        )
                        complete_event = {
                            "type": "completed",
                            "checkId": self.check_id,
                            "status": "completed",
                            "progress": 100,
                            "message": "Fact-check completed successfully",
                        }
                        yield f"data: {json.dumps(complete_event)}\n\n"
                        self._completed = True
                        break

                # Send heartbeat on timeout
                heartbeat = {
                    "type": "heartbeat",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                yield f"data: {json.dumps(heartbeat)}\n\n"
