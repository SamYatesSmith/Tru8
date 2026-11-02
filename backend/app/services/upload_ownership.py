"""Bind an uploaded image to the user who uploaded it.

Security sweep 2026-11-02, #5: `POST /checks` accepted any `file_path` for an
image check. Ingest OCR'd it with a bare `open()` for local paths, or fetched it
from our bucket for storage URLs — so a caller could OCR any image on the
server's disk (and learn whether a file exists from the error), or another
user's upload if its key leaked.

Now `/upload` records `upload_owner:<sha256(path)> = <user id>` in Redis for
24 hours, and an image check is created only when the path was issued to the
same caller. No frontend change: the client already echoes back the
`filePath` that `/upload` returned. Fail closed: if Redis is unavailable the
check is refused, never waved through.
"""

import hashlib
import logging
from typing import Optional

import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)

UPLOAD_OWNER_TTL_S = 24 * 3600


def _key(file_path: str) -> str:
    return "upload_owner:" + hashlib.sha256(file_path.encode("utf-8")).hexdigest()


def _redis():
    return aioredis.from_url(settings.REDIS_URL, decode_responses=True)


async def register_upload(file_path: str, user_id: str) -> None:
    """Record who uploaded `file_path`. Raises if Redis is unavailable, so an
    upload nobody could later use is reported rather than silently stored."""
    client = _redis()
    try:
        await client.setex(_key(file_path), UPLOAD_OWNER_TTL_S, user_id)
    finally:
        await client.aclose()


async def upload_owner(file_path: str) -> Optional[str]:
    """The user `file_path` was issued to, or None if unknown or expired."""
    client = _redis()
    try:
        return await client.get(_key(file_path))
    finally:
        await client.aclose()


async def is_owned_by(file_path: Optional[str], user_id: str) -> bool:
    """True only when `file_path` was issued to `user_id`. Any failure — no
    path, unknown path, Redis down — is False (fail closed)."""
    if not file_path or not user_id:
        return False
    try:
        return (await upload_owner(file_path)) == user_id
    except Exception as e:
        logger.warning(f"[UPLOAD OWNER] lookup failed, refusing: {type(e).__name__}")
        return False
