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
