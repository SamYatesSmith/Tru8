"""
Webhook management endpoints.

Register, list, and delete webhook URLs. Webhooks fire on check.completed
and check.failed events with HMAC-signed payloads.
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete as sql_delete
from pydantic import BaseModel, Field, HttpUrl
from datetime import datetime
import secrets
import logging

from app.core.database import get_session
from app.core.auth import get_current_user_or_api_key
from app.core.config import settings
from app.core.url_safety import UnsafeUrlError, assert_public_url
from app.models.webhook import Webhook
from app.services.webhooks import VALID_EVENTS

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------


class CreateWebhookRequest(BaseModel):
    url: str = Field(..., max_length=2048, description="HTTPS URL to receive events")
    events: List[str] = Field(..., min_length=1, description="Events to subscribe to")
    description: Optional[str] = Field(
        None, max_length=200, description="Label for this webhook"
    )


class WebhookCreatedResponse(BaseModel):
    """Returned once at creation. The signing `secret` is shown once — store it to verify payloads."""

    id: str = Field(description="Webhook database ID")
    url: str = Field(description="HTTPS URL that will receive events")
    events: List[str] = Field(
        description="Events this webhook is subscribed to (e.g. check.completed, check.failed)"
    )
    secret: str = Field(
        description="HMAC signing secret (shown once). Use to verify X-Tru8-Signature headers on incoming payloads."
    )
    description: Optional[str] = Field(None, description="Webhook label")
    created_at: datetime = Field(description="Creation timestamp")


class WebhookListItem(BaseModel):
    """Webhook summary (secret is never returned after creation)."""

    id: str = Field(description="Webhook database ID")
    url: str = Field(description="HTTPS URL receiving events")
    events: List[str] = Field(description="Subscribed events")
    is_active: bool = Field(description="Whether the webhook is currently active")
    description: Optional[str] = Field(None, description="Webhook label")
    last_triggered_at: Optional[datetime] = Field(
        None, description="Last time this webhook was triggered"
    )
    failure_count: int = Field(
        description="Consecutive delivery failures (webhook is deactivated after 10)"
    )
    created_at: datetime = Field(description="Creation timestamp")


class WebhookListResponse(BaseModel):
    """All webhooks for the authenticated user."""

    webhooks: List[WebhookListItem] = Field(
        description="Webhooks, newest first. Secrets are never included."
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("", response_model=WebhookCreatedResponse, status_code=201)
async def create_webhook(
    body: CreateWebhookRequest,
    current_user: dict = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_session),
):
    """
    Register a webhook URL. The signing secret is returned once — store it
    to verify `X-Tru8-Signature` headers on incoming payloads.
    """
    # Validate URL scheme
    if not body.url.startswith("https://"):
        raise HTTPException(status_code=400, detail="Webhook URL must use HTTPS")

    # F-SEC-02: refuse webhook URLs that target private/internal addresses.
    # Without this, /webhooks accepts https://qdrant.railway.internal:6333/
    # or https://10.x.x.x/ and turns the webhook delivery pipeline into an
    # exfiltration channel.
    try:
        assert_public_url(body.url)
    except UnsafeUrlError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Webhook URL refused (private/internal address): {e}",
        )

    # Validate events
    invalid = set(body.events) - VALID_EVENTS
    if invalid:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid events: {', '.join(invalid)}. Valid: {', '.join(sorted(VALID_EVENTS))}",
        )

    # Cap at 5 active webhooks per user
    result = await session.execute(
        select(Webhook).where(
            Webhook.user_id == current_user["id"], Webhook.is_active == True
        )
    )
    active = result.scalars().all()
    if len(active) >= 5:
        raise HTTPException(
            status_code=400,
            detail="Maximum 5 active webhooks. Delete an existing webhook first.",
        )

    secret = secrets.token_hex(32)

    webhook = Webhook(
        user_id=current_user["id"],
        url=body.url,
        events=body.events,
        secret=secret,
        description=body.description,
    )
    session.add(webhook)
    await session.commit()
    await session.refresh(webhook)

    logger.info(
        f"Webhook created: user={current_user['id']} url={body.url} events={body.events}"
    )

    return WebhookCreatedResponse(
        id=webhook.id,
        url=webhook.url,
        events=webhook.events,
        secret=secret,
        description=webhook.description,
        created_at=webhook.created_at,
    )


@router.get("", response_model=WebhookListResponse)
async def list_webhooks(
    current_user: dict = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_session),
):
    """List all webhooks. Secrets are never returned after creation."""
    result = await session.execute(
        select(Webhook)
        .where(Webhook.user_id == current_user["id"])
        .order_by(Webhook.created_at.desc())
    )
    webhooks = result.scalars().all()

    return WebhookListResponse(
        webhooks=[
            WebhookListItem(
                id=w.id,
                url=w.url,
                events=w.events,
                is_active=w.is_active,
                description=w.description,
                last_triggered_at=w.last_triggered_at,
                failure_count=w.failure_count,
                created_at=w.created_at,
            )
            for w in webhooks
        ]
    )


@router.delete("/{webhook_id}", status_code=204)
async def delete_webhook(
    webhook_id: str,
    current_user: dict = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_session),
):
    """Delete a webhook. It immediately stops receiving events."""
    result = await session.execute(
        select(Webhook).where(
            Webhook.id == webhook_id, Webhook.user_id == current_user["id"]
        )
    )
    webhook = result.scalar_one_or_none()

    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")

    await session.delete(webhook)
    await session.commit()

    logger.info(f"Webhook deleted: user={current_user['id']} webhook={webhook_id}")


# ---------------------------------------------------------------------------
# F-AUTH-02: Inbound Clerk webhook (user.deleted / user.updated)
# ---------------------------------------------------------------------------


async def _cascade_delete_user(session: AsyncSession, user_id: str) -> int:
    """Delete a user and all owned data. Mirrors DELETE /users/me but is
    safe to invoke from a webhook context where the deleted user can no
    longer authenticate. Returns the number of rows touched across tables
    (for logging only)."""
    from app.models import User, Check, Claim, Evidence, Subscription
    from app.models.webhook import Webhook as OutboundWebhook

    stmt = select(User).where(User.id == user_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        logger.info(f"[CLERK WEBHOOK] user.deleted for unknown user {user_id}")
        return 0

    # Cancel active Stripe subscriptions best-effort before removing rows.
    import stripe

    sub_stmt = select(Subscription).where(
        Subscription.user_id == user_id,
        Subscription.status.in_(["active", "trialing", "past_due"]),
    )
    sub_result = await session.execute(sub_stmt)
    for sub in sub_result.scalars().all():
        if sub.stripe_subscription_id:
            try:
                stripe.Subscription.delete(sub.stripe_subscription_id)
            except Exception as e:
                logger.error(
                    f"[CLERK WEBHOOK] Stripe cancel failed for {sub.stripe_subscription_id}: {e}"
                )

    touched = 0
    check_ids = [
        row[0]
        for row in (
            await session.execute(select(Check.id).where(Check.user_id == user_id))
        ).all()
    ]
    if check_ids:
        claim_ids = [
            row[0]
            for row in (
                await session.execute(
                    select(Claim.id).where(Claim.check_id.in_(check_ids))
                )
            ).all()
        ]
        if claim_ids:
            r = await session.execute(
                sql_delete(Evidence).where(Evidence.claim_id.in_(claim_ids))
            )
            touched += r.rowcount or 0
            r = await session.execute(
                sql_delete(Claim).where(Claim.check_id.in_(check_ids))
            )
            touched += r.rowcount or 0
        r = await session.execute(sql_delete(Check).where(Check.user_id == user_id))
        touched += r.rowcount or 0

    r = await session.execute(
        sql_delete(Subscription).where(Subscription.user_id == user_id)
    )
    touched += r.rowcount or 0

    r = await session.execute(
        sql_delete(OutboundWebhook).where(OutboundWebhook.user_id == user_id)
    )
    touched += r.rowcount or 0

    # API keys are removed via a raw delete to avoid importing the APIKey
    # model into this module's surface area; the column name is canonical.
    try:
        from app.models.api_key import APIKey

        r = await session.execute(sql_delete(APIKey).where(APIKey.user_id == user_id))
        touched += r.rowcount or 0
    except Exception as e:
        logger.warning(f"[CLERK WEBHOOK] API key cascade skipped: {e}")

    # Agent transactions — best-effort cascade.
    try:
        from app.models.agent_transaction import AgentTransaction

        r = await session.execute(
            sql_delete(AgentTransaction).where(AgentTransaction.user_id == user_id)
        )
        touched += r.rowcount or 0
    except Exception as e:
        logger.warning(f"[CLERK WEBHOOK] AgentTransaction cascade skipped: {e}")

    await session.delete(user)
    await session.commit()
    return touched + 1


def _primary_email_from_clerk(data: dict) -> Optional[str]:
    """Extract the primary email address from a Clerk user.* event payload."""
    primary_id = data.get("primary_email_address_id")
    for entry in data.get("email_addresses") or []:
        if entry.get("id") == primary_id and entry.get("email_address"):
            return entry["email_address"]
    # Fallback: first email_addresses entry
    addrs = data.get("email_addresses") or []
    if addrs and addrs[0].get("email_address"):
        return addrs[0]["email_address"]
    return None


@router.post("/clerk", include_in_schema=False)
async def clerk_webhook(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """F-AUTH-02: receive Clerk lifecycle events with Svix verification.

    Handles ``user.deleted`` (cascade delete) and ``user.updated`` (sync
    email/name). Other event types are acknowledged but ignored.

    Set ``CLERK_WEBHOOK_SECRET`` to the Svix signing secret displayed in the
    Clerk dashboard. When the secret is unset every request is rejected so a
    misconfigured deployment cannot fall through to no-verification.
    """
    if not settings.CLERK_WEBHOOK_SECRET:
        raise HTTPException(
            status_code=503,
            detail="Clerk webhook endpoint not configured (CLERK_WEBHOOK_SECRET unset)",
        )

    payload = await request.body()
    headers = {k.lower(): v for k, v in request.headers.items()}

    # Svix requires svix-id, svix-timestamp, svix-signature.
    try:
        from svix.webhooks import Webhook as SvixWebhook
        from svix.webhooks import WebhookVerificationError
    except ImportError as e:
        logger.error(f"[CLERK WEBHOOK] svix not installed: {e}")
        raise HTTPException(
            status_code=500, detail="Server misconfigured: svix missing"
        )

    try:
        wh = SvixWebhook(settings.CLERK_WEBHOOK_SECRET)
        event = wh.verify(payload, headers)
    except WebhookVerificationError as e:
        logger.warning(f"[CLERK WEBHOOK] signature verification failed: {e}")
        raise HTTPException(status_code=403, detail="Invalid Svix signature")
    except Exception as e:
        logger.error(f"[CLERK WEBHOOK] verify error: {e}")
        raise HTTPException(status_code=403, detail="Webhook verification error")

    event_type = event.get("type", "")
    data = event.get("data", {}) or {}
    clerk_user_id = data.get("id")

    if not clerk_user_id and event_type.startswith("user."):
        logger.warning(f"[CLERK WEBHOOK] {event_type} with no user id")
        return {"ok": True, "ignored": "no_user_id"}

    if event_type == "user.deleted":
        touched = await _cascade_delete_user(session, clerk_user_id)
        logger.info(
            f"[CLERK WEBHOOK] user.deleted cascade: user={clerk_user_id} touched={touched}"
        )
        return {"ok": True, "event": event_type, "rows": touched}

    if event_type == "user.updated":
        from app.models import User

        stmt = select(User).where(User.id == clerk_user_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        if not user:
            logger.info(
                f"[CLERK WEBHOOK] user.updated for unknown user {clerk_user_id} — ignoring"
            )
            return {"ok": True, "event": event_type, "ignored": "unknown_user"}

        new_email = _primary_email_from_clerk(data)
        if new_email and new_email != user.email:
            old_email = user.email
            user.email = new_email
            logger.info(
                f"[CLERK WEBHOOK] user.updated email change: {clerk_user_id} {old_email!r} -> {new_email!r}"
            )

        first = data.get("first_name") or ""
        last = data.get("last_name") or ""
        new_name = (f"{first} {last}".strip()) or None
        if new_name and getattr(user, "name", None) != new_name:
            user.name = new_name

        await session.commit()
        return {"ok": True, "event": event_type}

    logger.debug(f"[CLERK WEBHOOK] ignoring event type {event_type}")
    return {"ok": True, "event": event_type, "ignored": "type_not_handled"}
