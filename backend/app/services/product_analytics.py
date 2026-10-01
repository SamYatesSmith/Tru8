"""Server-side product analytics: the funnel events the browser cannot see.

Design: ACE Stage 4 (2026-10-01). The web app already sends visit, signup and
check_submitted to PostHog (`web/lib/analytics.ts`, cookieless-first). Two
funnel steps happen on the server and were invisible:

* ``check_completed`` (activation, with ``first``) — from the pipeline's
  completion hook.
* ``subscription_started`` / ``credits_purchased`` (paid) — from the Stripe
  webhook, after the fulfilment commit.

Properties of this module:

1. **Cookieless.** Server-to-server; nothing is stored on any device. The
   distinct id is the Clerk user id, the same id the browser identifies with,
   so PostHog joins both halves of the funnel.
2. **Off without a key.** No ``POSTHOG_API_KEY`` → every call is a no-op.
3. **Never breaks its caller, never blocks it.** Sends are detached tasks
   with a short timeout; every failure is logged and swallowed.
4. **Retry-safe.** Each event carries a deterministic ``uuid`` built from its
   natural key (check id, Stripe checkout session id), so a webhook retry or a
   double hook is ingested once.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Set

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_TIMEOUT_S = 3.0
_NAMESPACE = uuid.UUID("6f1c0a52-7d55-4a0e-9b2b-3b8a3e0d7f18")

# asyncio holds only a weak reference to tasks; keep them alive until done.
_background_tasks: Set[asyncio.Task] = set()


def _enabled() -> bool:
    return bool(getattr(settings, "POSTHOG_API_KEY", ""))


def event_uuid(event: str, key: str) -> str:
    """Deterministic event id: the same (event, key) always maps to one uuid."""
    return str(uuid.uuid5(_NAMESPACE, f"{event}:{key}"))


def build_payload(
    event: str,
    distinct_id: str,
    properties: Optional[Dict[str, Any]] = None,
    dedup_key: Optional[str] = None,
) -> Dict[str, Any]:
    props = {"source": "server", **(properties or {})}
    payload: Dict[str, Any] = {
        "api_key": settings.POSTHOG_API_KEY,
        "event": event,
        "distinct_id": distinct_id,
        "properties": props,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if dedup_key:
        payload["uuid"] = event_uuid(event, dedup_key)
    return payload


async def send_event(
    event: str,
    distinct_id: str,
    properties: Optional[Dict[str, Any]] = None,
    dedup_key: Optional[str] = None,
) -> bool:
    """POST one event to PostHog. Returns True on a 2xx, False otherwise."""
    if not _enabled() or not distinct_id:
        return False
    url = settings.POSTHOG_HOST.rstrip("/") + "/i/v0/e/"
    payload = build_payload(event, distinct_id, properties, dedup_key)
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT_S) as client:
            resp = await client.post(url, json=payload)
        if resp.status_code >= 300:
            logger.warning(f"[ANALYTICS] {event} rejected: HTTP {resp.status_code}")
            return False
        return True
    except Exception as e:
        logger.warning(f"[ANALYTICS] {event} failed: {e}")
        return False


def schedule_event(
    event: str,
    distinct_id: str,
    properties: Optional[Dict[str, Any]] = None,
    dedup_key: Optional[str] = None,
) -> Optional[asyncio.Task]:
    """Send detached; the caller never waits and never sees an error."""
    if not _enabled() or not distinct_id:
        return None
    try:
        task = asyncio.create_task(
            send_event(event, distinct_id, properties, dedup_key)
        )
    except RuntimeError:
        return None  # no running loop: analytics is never worth raising for
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return task


async def _completed_check_count(user_id: str) -> int:
    from sqlalchemy import func, select

    from app.core.database import async_session
    from app.models import Check

    async with async_session() as session:
        result = await session.execute(
            select(func.count(Check.id)).where(
                Check.user_id == user_id, Check.status == "completed"
            )
        )
        return int(result.scalar() or 0)


async def send_check_completed(user_id: str, check_id: str) -> bool:
    """Activation: ``first`` is true when this is the user's only completed
    check. Counted in its own session, after the result has been saved."""
    if not _enabled() or not user_id:
        return False
    try:
        completed = await _completed_check_count(user_id)
    except Exception as e:
        logger.warning(f"[ANALYTICS] check_completed count failed: {e}")
        return False
    return await send_event(
        "check_completed",
        user_id,
        {"check_id": check_id, "first": completed == 1, "completed_checks": completed},
        dedup_key=check_id,
    )


def schedule_check_completed(user_id: str, check_id: str) -> Optional[asyncio.Task]:
    if not _enabled() or not user_id:
        return None
    try:
        task = asyncio.create_task(send_check_completed(user_id, check_id))
    except RuntimeError:
        return None
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return task
