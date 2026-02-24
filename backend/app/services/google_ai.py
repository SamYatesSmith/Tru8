"""Centralised Google AI (Gemini) client with rate limiting and retry.

Every pipeline module that calls the Gemini API should use `call_google_ai`
instead of building its own httpx request.  This gives us:

- A process-wide asyncio.Semaphore to stay under burst-rate limits.
- Exponential back-off with up to 3 retries on HTTP 429 / 503.
- A single place to change the endpoint, headers, or retry policy.
"""

import asyncio
import json
import logging
from typing import Any, Dict, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

# Process-wide concurrency gate for Gemini requests.
# Free tier: 30 RPM — semaphore of 10 allows burst while backoff handles 429s.
# Paid tier: 2,000 RPM — can raise further.
_semaphore = asyncio.Semaphore(10)

_MAX_RETRIES = 3
_BASE_DELAY = 1.0  # seconds; doubles each retry


async def call_google_ai(
    prompt: str,
    *,
    temperature: float = 0.1,
    max_tokens: int = 1500,
    timeout: float = 30,
    model: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Send a prompt to Google Gemini and return the parsed JSON response.

    Returns ``None`` on any unrecoverable error (caller decides fallback).
    """
    api_key = getattr(settings, "GOOGLE_AI_API_KEY", "")
    if not api_key:
        logger.debug("Google AI API key not configured")
        return None

    model = model or getattr(settings, "GOOGLE_LLM_MODEL", "gemini-2.5-flash-lite")
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={api_key}"
    )
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
            "responseMimeType": "application/json",
        },
    }

    last_status: Optional[int] = None

    for attempt in range(_MAX_RETRIES):
        async with _semaphore:
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.post(
                        url,
                        headers={"Content-Type": "application/json"},
                        json=body,
                    )
            except httpx.TimeoutException:
                logger.warning(
                    "Google AI timeout (attempt %d/%d)", attempt + 1, _MAX_RETRIES
                )
                last_status = None
                # fall through to retry/back-off
            except httpx.HTTPError as exc:
                logger.warning(
                    "Google AI HTTP error (attempt %d/%d): %s",
                    attempt + 1,
                    _MAX_RETRIES,
                    exc,
                )
                last_status = None
            else:
                last_status = response.status_code

                if response.status_code == 200:
                    try:
                        result = response.json()
                        text = result["candidates"][0]["content"]["parts"][0]["text"]
                        return json.loads(text)
                    except (KeyError, IndexError, json.JSONDecodeError) as exc:
                        logger.error("Google AI response parse error: %s", exc)
                        return None

                if response.status_code not in (429, 503):
                    logger.error("Google AI error: %d", response.status_code)
                    return None

                # 429 / 503 → retry with back-off
                logger.warning(
                    "Google AI %d (attempt %d/%d), backing off",
                    response.status_code,
                    attempt + 1,
                    _MAX_RETRIES,
                )

        # Exponential back-off (outside semaphore so we don't hold the slot)
        await asyncio.sleep(_BASE_DELAY * (2**attempt))

    logger.error(
        "Google AI failed after %d retries (last status: %s)",
        _MAX_RETRIES,
        last_status,
    )
    return None
