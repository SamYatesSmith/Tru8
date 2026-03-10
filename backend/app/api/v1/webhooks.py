"""
Webhook management endpoints.

Register, list, and delete webhook URLs. Webhooks fire on check.completed
and check.failed events with HMAC-signed payloads.
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, Field, HttpUrl
from datetime import datetime
import secrets
import logging

from app.core.database import get_session
from app.core.auth import get_current_user_or_api_key
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
