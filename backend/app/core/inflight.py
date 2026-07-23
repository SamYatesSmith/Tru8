"""In-flight pipeline registry + deploy-shutdown guard (2026-07-21).

Pipeline tasks run as asyncio tasks inside uvicorn (no Celery). A deploy
SIGTERMs the process, so in-flight checks died silently: rows stuck
'processing' forever + credits burned with no refund (checks 57e7dcde /
f2f97f6e during the fa35465 rollout, 2026-07-21 — confirmed in Railway logs:
'Started server process' lands mid-retrieval).

Every pipeline task registers its check_id here and unregisters when it
finishes (any outcome — the existing failure handlers already refund).
The lifespan shutdown hook fails + refunds whatever is still registered
before the process exits.

Checks paused at waiting_for_selection are durable (state in DB; phase 2
resumes on a fresh instance) — their tasks end at the pause and are already
unregistered, so the guard never touches them.
"""

import logging
from typing import Set

logger = logging.getLogger(__name__)

_INFLIGHT: Set[str] = set()

SHUTDOWN_ERROR_MSG = (
    "This check was interrupted by a platform update and could not complete. "
    "Your credit has been refunded — please submit it again."
)


def inflight_register(check_id: str) -> None:
    _INFLIGHT.add(check_id)


def inflight_unregister(check_id: str) -> None:
    _INFLIGHT.discard(check_id)


def inflight_count() -> int:
    return len(_INFLIGHT)


async def fail_and_refund_inflight() -> int:
    """Mark every still-registered check failed and refund its debit.

    Runs in the lifespan shutdown window (SIGTERM grace period) — one short
    DB transaction. Idempotent per check via refund_usage's credits_used==0
    guard. Returns the number of checks failed."""
    if not _INFLIGHT:
        return 0

    from sqlmodel import select

    from app.core.database import async_session
    from app.models.check import Check
    from app.services.usage_ledger import refund_usage

    failed = 0
    try:
        async with async_session() as session:
            for check_id in list(_INFLIGHT):
                try:
                    result = await session.execute(
                        select(Check).where(Check.id == check_id)
                    )
                    check = result.scalar_one_or_none()
                    # Only kill genuinely in-flight states; a task that just
                    # completed/paused between registry read and now is left alone.
                    if not check or check.status not in ("processing", "pending"):
                        continue
                    await refund_usage(session, check_id)
                    check.status = "failed"
                    check.error_message = SHUTDOWN_ERROR_MSG
                    session.add(check)
                    failed += 1
                except Exception as e:  # noqa: BLE001 — never abort the sweep
                    logger.error(
                        f"[SHUTDOWN GUARD] Failed to clean check {check_id}: {e}"
                    )
            await session.commit()
    except Exception as e:  # noqa: BLE001 — shutdown must not raise
        logger.error(f"[SHUTDOWN GUARD] Sweep failed: {e}")
        return failed

    if failed:
        logger.warning(
            f"[SHUTDOWN GUARD] Deploy shutdown: failed + refunded {failed} "
            f"in-flight check(s): {sorted(_INFLIGHT)}"
        )
    return failed


STALE_ERROR_MSG = (
    "This check was interrupted and could not complete. "
    "Your credit has been refunded — please submit it again."
)


async def sweep_stale_checks(session=None) -> int:
    """Boot-time stale sweep (hang-proofing W2, 2026-07-23).

    The SIGTERM guard above only covers graceful shutdowns; an OOM/SIGKILL
    strands rows in 'processing' forever (check 46406547, 2026-07-23 outage).
    On startup, fail + refund every check stuck 'processing' or 'pending'
    for longer than the watchdog ceiling + grace.

    Deploy-overlap safe BY CONSTRUCTION: with the task-level watchdog live,
    no legitimate run can be older than the ceiling — any row past
    ceiling+grace is definitionally dead. The old instance's still-running
    checks are younger than the threshold and untouched. 'waiting_for_selection'
    is a durable pause and is never swept.

    Ages 'processing' rows from processing_started_at (COALESCE created_at
    for pre-migration rows) — created_at would mis-age paused-then-resumed
    article checks. 'pending' rows age from created_at. Idempotent via
    refund_usage's credits_used==0 guard. Returns rows swept.
    """
    from datetime import datetime, timedelta, timezone

    from sqlmodel import select

    from app.core.config import settings
    from app.core.database import async_session
    from app.models.check import Check
    from app.services.usage_ledger import refund_usage

    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(
        seconds=settings.PIPELINE_WATCHDOG_SECONDS + 120
    )

    async def _sweep(sess) -> int:
        swept = 0
        result = await sess.execute(
            select(Check).where(Check.status.in_(("processing", "pending")))
        )
        for check in result.scalars().all():
            started = (
                (check.processing_started_at or check.created_at)
                if check.status == "processing"
                else check.created_at
            )
            if started is None or started >= cutoff:
                continue
            try:
                await refund_usage(sess, check.id)
                check.status = "failed"
                check.error_message = STALE_ERROR_MSG
                sess.add(check)
                swept += 1
                logger.warning(
                    f"[BOOT SWEEP] Failed + refunded stale check {check.id} "
                    f"(stuck since {started})"
                )
            except Exception as e:  # noqa: BLE001 — never abort the sweep
                logger.error(f"[BOOT SWEEP] Could not clean check {check.id}: {e}")
        await sess.commit()
        return swept

    try:
        if session is not None:
            return await _sweep(session)
        async with async_session() as sess:
            return await _sweep(sess)
    except Exception as e:  # noqa: BLE001 — startup must not crash on the sweep
        logger.error(f"[BOOT SWEEP] Sweep failed: {e}")
        return 0
