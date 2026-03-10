"""
Webhook delivery service.

Dispatches signed HTTP POST payloads to registered webhook URLs.
Runs as fire-and-forget background tasks — never blocks the pipeline.
"""

import asyncio
import hashlib
import hmac
import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session
from app.models.webhook import Webhook

logger = logging.getLogger(__name__)

WEBHOOK_TIMEOUT = 10  # seconds
MAX_RETRIES = 2
VALID_EVENTS = {"check.completed", "check.failed"}


def _sign_payload(payload_bytes: bytes, secret: str) -> str:
    """HMAC-SHA256 signature for webhook verification."""
    return hmac.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest()


async def dispatch_webhook_event(
    user_id: str,
    event: str,
    data: Dict[str, Any],
) -> None:
    """
    Fire webhooks for a user event. Runs as a background task.

    Args:
        user_id: Owner of the webhooks
        event: Event name (e.g. "check.completed")
        data: Payload to deliver
    """
    if event not in VALID_EVENTS:
        logger.warning(f"[WEBHOOK] Unknown event type: {event}")
        return

    try:
        async with async_session() as session:
            stmt = select(Webhook).where(
                Webhook.user_id == user_id,
                Webhook.is_active == True,
            )
            result = await session.execute(stmt)
            webhooks = result.scalars().all()

        # Filter to webhooks subscribed to this event
        matching = [w for w in webhooks if event in (w.events or [])]
        if not matching:
            return

        logger.info(
            f"[WEBHOOK] Dispatching {event} to {len(matching)} webhook(s) for user {user_id}"
        )

        tasks = [_deliver(w, event, data) for w in matching]
        await asyncio.gather(*tasks, return_exceptions=True)

    except Exception as e:
        logger.error(f"[WEBHOOK] Failed to dispatch {event}: {e}")


async def _deliver(webhook: Webhook, event: str, data: Dict[str, Any]) -> None:
    """Deliver a single webhook with retry and failure tracking."""
    payload = {
        "event": event,
        "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
        "data": data,
    }
    payload_bytes = json.dumps(payload, default=str).encode()
    signature = _sign_payload(payload_bytes, webhook.secret)

    headers = {
        "Content-Type": "application/json",
        "X-Tru8-Event": event,
        "X-Tru8-Signature": signature,
        "User-Agent": "Tru8-Webhooks/1.0",
    }

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            async with httpx.AsyncClient(timeout=WEBHOOK_TIMEOUT) as client:
                response = await client.post(
                    webhook.url,
                    content=payload_bytes,
                    headers=headers,
                )

            if response.status_code < 300:
                logger.info(
                    f"[WEBHOOK] Delivered {event} to {webhook.url} "
                    f"(status={response.status_code}, attempt={attempt})"
                )
                await _update_webhook_status(webhook.id, success=True)
                return
            else:
                logger.warning(
                    f"[WEBHOOK] {webhook.url} returned {response.status_code} "
                    f"(attempt {attempt}/{MAX_RETRIES})"
                )
        except Exception as e:
            logger.warning(
                f"[WEBHOOK] Delivery failed to {webhook.url}: {e} "
                f"(attempt {attempt}/{MAX_RETRIES})"
            )

        if attempt < MAX_RETRIES:
            await asyncio.sleep(2**attempt)  # Exponential backoff

    # All retries exhausted
    await _update_webhook_status(webhook.id, success=False)
    logger.error(f"[WEBHOOK] All retries exhausted for {webhook.url}")


async def _update_webhook_status(webhook_id: str, success: bool) -> None:
    """Update webhook delivery tracking. Best-effort, never raises."""
    try:
        async with async_session() as session:
            stmt = select(Webhook).where(Webhook.id == webhook_id)
            result = await session.execute(stmt)
            webhook = result.scalar_one_or_none()
            if webhook:
                webhook.last_triggered_at = datetime.now(timezone.utc)
                if success:
                    webhook.failure_count = 0
                else:
                    webhook.failure_count += 1
                    # Auto-disable after 10 consecutive failures
                    if webhook.failure_count >= 10:
                        webhook.is_active = False
                        logger.warning(
                            f"[WEBHOOK] Auto-disabled {webhook.url} after "
                            f"{webhook.failure_count} consecutive failures"
                        )
                await session.commit()
    except Exception as e:
        logger.debug(f"[WEBHOOK] Failed to update status: {e}")
