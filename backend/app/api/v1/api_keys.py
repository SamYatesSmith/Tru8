"""
API key management endpoints.

Keys are created/listed/revoked from the dashboard (Clerk JWT auth only).
The raw key is returned exactly once at creation — it cannot be retrieved later.
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, Field
from datetime import datetime
import secrets
import logging

from app.core.database import get_session
from app.core.auth import get_current_user, _hash_api_key, API_KEY_PREFIX
from app.models.api_key import APIKey
from app.models.user import User
from app.api.v1.users import get_or_create_user

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------


class CreateAPIKeyRequest(BaseModel):
    name: str = Field(
        ..., min_length=1, max_length=100, description="Label for this key"
    )


class APIKeyCreatedResponse(BaseModel):
    """Returned once at creation. The `key` field is never shown again."""

    id: str
    key: str
    key_prefix: str
    name: str
    created_at: datetime


class APIKeyListItem(BaseModel):
    id: str
    key_prefix: str
    name: str
    is_active: bool
    last_used_at: Optional[datetime]
    usage_count: int
    created_at: datetime


class APIKeyListResponse(BaseModel):
    keys: List[APIKeyListItem]


# ---------------------------------------------------------------------------
# Endpoints — all require Clerk JWT (dashboard access)
# ---------------------------------------------------------------------------


@router.post("", response_model=APIKeyCreatedResponse, status_code=201)
async def create_api_key(
    body: CreateAPIKeyRequest,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Create a new API key. The raw key is returned in the response body
    exactly once — store it securely. It cannot be retrieved later.
    """
    user = await get_or_create_user(session, current_user)

    # Cap at 5 active keys per user
    result = await session.execute(
        select(APIKey).where(APIKey.user_id == user.id, APIKey.is_active == True)
    )
    active_keys = result.scalars().all()
    if len(active_keys) >= 5:
        raise HTTPException(
            status_code=400,
            detail="Maximum 5 active API keys per account. Revoke an existing key first.",
        )

    # Generate key: tru8_sk_ + 32 hex chars (128 bits of entropy)
    raw_secret = secrets.token_hex(16)
    raw_key = f"{API_KEY_PREFIX}{raw_secret}"
    key_hash = _hash_api_key(raw_key)
    key_prefix = f"{API_KEY_PREFIX}{raw_secret[:4]}"

    api_key = APIKey(
        user_id=user.id,
        key_hash=key_hash,
        key_prefix=key_prefix,
        name=body.name,
    )
    session.add(api_key)
    await session.commit()
    await session.refresh(api_key)

    logger.info(f"API key created: user={user.id} prefix={key_prefix}")

    return APIKeyCreatedResponse(
        id=api_key.id,
        key=raw_key,
        key_prefix=key_prefix,
        name=api_key.name,
        created_at=api_key.created_at,
    )


@router.get("", response_model=APIKeyListResponse)
async def list_api_keys(
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """List all API keys for the current user. Raw keys are never returned."""
    result = await session.execute(
        select(APIKey)
        .where(APIKey.user_id == current_user["id"])
        .order_by(APIKey.created_at.desc())
    )
    keys = result.scalars().all()

    return APIKeyListResponse(
        keys=[
            APIKeyListItem(
                id=k.id,
                key_prefix=k.key_prefix,
                name=k.name,
                is_active=k.is_active,
                last_used_at=k.last_used_at,
                usage_count=k.usage_count,
                created_at=k.created_at,
            )
            for k in keys
        ]
    )


@router.delete("/{key_id}", status_code=204)
async def revoke_api_key(
    key_id: str,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Revoke an API key. The key immediately stops working."""
    result = await session.execute(
        select(APIKey).where(APIKey.id == key_id, APIKey.user_id == current_user["id"])
    )
    api_key = result.scalar_one_or_none()

    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")

    api_key.is_active = False
    await session.commit()

    logger.info(f"API key revoked: user={current_user['id']} key={key_id}")
