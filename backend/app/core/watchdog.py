"""Task-level pipeline watchdog (hang-proofing W1, 2026-07-23).

A check must always reach a terminal state the user can see — completed, or
failed with an honest message and a refund. Before this module, the only
pipeline ceiling lived inside the SSE stream generator
(``progress.py::events(max_duration_seconds=...)``), which dies with the
client connection: navigate away and the watchdog is gone while the task runs
unbounded. Phase 2 and re-search tasks had no ceiling at all
(design: ``audit/2026-07-23_hang_proofing_design.md``).

Principle: exactly ONE owner of a pipeline task's lifetime — the task itself.
Streams only report; they never control.

Two supervisors, matching the two background-task families:

* ``supervise_pipeline_task`` — submission + phase-2 tasks. On ceiling breach,
  routes through the existing, tested ``handle_pipeline_failure`` (marks the
  check failed with a user-friendly message + idempotent refund). The message
  contains "timeout" so ``get_user_friendly_error`` maps it to the honest
  took-too-long copy.
* ``supervise_re_search_task`` — element re-search/top-up tasks. These run on
  COMPLETED checks and report via the Redis research-status channel, so a
  breach must NOT touch check.status (it would fail a completed check); it
  terminates the Redis status instead, which is what the Seeker UI polls.

Agent async paths (``agent.py::_run_pipeline_background``) already carry their
own ``asyncio.wait_for`` ceilings and are not routed through here.
"""

import asyncio
import logging
from typing import Coroutine

from app.core.config import settings

logger = logging.getLogger(__name__)


def supervise_pipeline_task(
    coro: Coroutine, *, check_id: str, user_id: str, label: str
) -> asyncio.Task:
    """Run a pipeline coroutine under the hard wall-clock ceiling.

    Returns the wrapping task (safe to hand to ``events(pipeline_task=...)`` —
    it is done exactly when the underlying work, or its failure handling, is).
    On breach the wrapper RE-RAISES PipelineError after handling, so an
    attached SSE stream reports an error — finishing clean here would make
    ``events()`` announce "completed" for a check that just failed. A
    done-callback retrieves the exception so detached tasks (phase 2) don't
    log "exception was never retrieved" at GC.
    """
    ceiling_s = settings.PIPELINE_WATCHDOG_SECONDS

    async def _supervised() -> None:
        try:
            await asyncio.wait_for(coro, timeout=ceiling_s)
        except asyncio.TimeoutError:
            logger.error(
                f"[WATCHDOG] {label} exceeded {ceiling_s}s ceiling — "
                f"failing check {check_id} honestly"
            )
            # Imported lazily: runner imports broadly and this module must be
            # importable from the API layer without cycles.
            from app.pipeline.runner import PipelineError, handle_pipeline_failure

            error = PipelineError(
                # 'timeout' in the text maps to the honest took-too-long copy
                # via get_user_friendly_error; the refund line is appended by
                # handle_pipeline_failure when the refund succeeds.
                f"pipeline watchdog timeout: the check exceeded {ceiling_s}s "
                f"and was stopped",
                stage="watchdog",
            )
            try:
                await handle_pipeline_failure(check_id, user_id, error)
            except Exception as e:  # noqa: BLE001 — handler failure never masks
                logger.error(
                    f"[WATCHDOG] failure handling itself failed for {check_id}: {e}"
                )
            raise error from None

    task = asyncio.create_task(_supervised())
    # Retrieve the (deliberate) exception when nothing awaits the task.
    task.add_done_callback(lambda t: t.cancelled() or t.exception())
    return task


def supervise_re_search_task(
    coro: Coroutine, *, check_id: str, claim_id: str, element_id: str
) -> asyncio.Task:
    """Run an element re-search coroutine under its own (shorter) ceiling.

    On breach: terminate the Redis research status the UI polls. The parent
    check stays COMPLETED — a re-search timeout is not a check failure.
    """
    ceiling_s = settings.RESEARCH_WATCHDOG_SECONDS

    async def _supervised() -> None:
        try:
            await asyncio.wait_for(coro, timeout=ceiling_s)
        except asyncio.TimeoutError:
            logger.error(
                f"[WATCHDOG] re-search {check_id}/{claim_id}/{element_id} "
                f"exceeded {ceiling_s}s ceiling — terminating status"
            )
            from app.pipeline.re_search import _update_status

            try:
                _update_status(
                    check_id,
                    claim_id,
                    element_id,
                    "error",
                    "This research took too long and was stopped. Please try again.",
                )
            except Exception as e:  # noqa: BLE001 — watchdog must never raise
                logger.error(f"[WATCHDOG] could not terminate re-search status: {e}")

    return asyncio.create_task(_supervised())
