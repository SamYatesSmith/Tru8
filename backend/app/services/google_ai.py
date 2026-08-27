"""Centralised Google AI (Gemini) client with rate limiting and retry.

Every pipeline module that calls the Gemini API should use `call_google_ai`
instead of building its own httpx request.  This gives us:

- A process-wide concurrency gate sized for the project's paid API tier.
- Jittered exponential back-off with Retry-After header respect.
- A shared HTTP client for connection pooling.
- A single place to change the endpoint, headers, or retry policy.

Rate limits are determined by the Google Developer Console tier, not by this
code.  The concurrency gate and retry policy should be generous enough to use
the full quota without self-throttling.
"""

import asyncio
import json
import logging
import random
import re
from typing import Any, Dict, Optional, Tuple

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

# Process-wide concurrency gate — caps parallel in-flight requests.
# Actual RPM is governed by the API tier in Google Developer Console.
_CONCURRENCY = 25
_semaphore = asyncio.Semaphore(_CONCURRENCY)

_MAX_RETRIES = 5
_BASE_DELAY = 2.0  # seconds; grows with jittered exponential backoff
_MAX_DELAY = 30.0  # cap per-retry wait

# ---------------------------------------------------------------------------
# Thinking control — the 2.5 → 3.x migration seam (2026-08-25)
# ---------------------------------------------------------------------------
# Gemini 2.5 takes ``thinkingConfig.thinkingBudget`` (an int; 0 = thinking OFF).
# Gemini 3.x takes ``thinkingLevel`` (a string) instead. MEASURED LIVE 2026-08-25
# — and the failure is NOT uniform, which is the point of this table:
#
#   model                  bare thinkingBudget=0        thinkingLevel
#   ---------------------  ---------------------------  ----------------------
#   gemini-3.5-flash-lite  400 "invalid argument"       minimal -> 200, 0 thoughts
#   gemini-3.7-flash       200, SILENTLY IGNORED,       low     -> 200, 70 thoughts
#                          thinking still ran (83)      minimal -> 400
#   gemini-2.5-flash       200, 0 thoughts              low     -> 400
#
# ⚠️ TWO DIFFERENT FAILURES, and the quiet one is worse. On 3.5-flash-lite a bare
# budget is a hard 400 — loud, and since ``call_google_ai_with_usage`` returns
# None on a terminal non-429/503 WITHOUT retry, every mapping caller would fall
# silently to the OpenAI path. On 3.7-flash the same field returns 200 and is
# DISCARDED: thinking runs anyway and bills at the output rate, so a thinking-off
# config becomes a placebo that nothing surfaces. (The 2026-08-01 probe checked
# 3.5-flash-lite only and concluded a silent ignore had been ruled out. It had
# not — it was ruled out on one model of three.)
#
# ⚠️ Thinking cannot be fully DISABLED on any Gemini 3 model, but the floors are
# not equal: 3.5-flash-lite at ``minimal`` really does report 0 thought tokens,
# while 3.7-flash's lowest accepted level still spends ~70. That difference is
# the M1 latency lever, and only one of these models keeps it.
_GEMINI3_THINKING_FLOOR: Dict[str, str] = {
    # live-verified 2026-08-25: 200, thoughtsTokenCount == 0
    "gemini-3.5-flash-lite": "minimal",
    # live-verified 2026-08-25: "minimal" -> 400 "Thinking level MINIMAL is not
    # supported for this model". Listed explicitly rather than left to the
    # default so the measurement is recorded where someone would look for it.
    "gemini-3.7-flash": "low",
}
# "low" is accepted by every 3.x model tested and is the safe default for a model
# we have not probed. Erring high costs latency and thinking tokens; erring low
# costs a 400 — and on some models a SILENT no-op — which is far worse.
_GEMINI3_DEFAULT_FLOOR = "low"
# A budget > 0 means the caller asked for SOME thinking (the rollback path from
# MAPPING_THINKING_BUDGET=0 → =1024). There is no token-budget equivalent on
# 3.x, so it maps to the lowest level that is unambiguously "thinking on".
_GEMINI3_SOME_THINKING = "low"


def _is_gemini_3(model: str) -> bool:
    """True for Gemini 3.x model ids, which take thinkingLevel not thinkingBudget.

    Matches on the ``gemini-3`` prefix so unreleased 3.x point versions are
    handled correctly the moment they exist — the failure mode of guessing wrong
    here is a hard 400 on every call, so it is deliberately inclusive.
    """
    return (model or "").strip().lower().startswith("gemini-3")


def _thinking_config(
    model: str, thinking_budget: Optional[int]
) -> Optional[Dict[str, Any]]:
    """Build the provider-correct ``thinkingConfig`` block, or None to omit it.

    ``None`` budget means "omit entirely" so the API applies its own default and
    the request body stays byte-identical for replay-bench cassettes. That
    byte-identity is why the 2.5 branch below is untouched: every existing
    cassette was recorded against it.
    """
    if thinking_budget is None:
        return None
    if not _is_gemini_3(model):
        # Gemini 2.5 and earlier — unchanged, byte-identical to pre-2026-08-25.
        return {"thinkingBudget": int(thinking_budget)}
    if int(thinking_budget) > 0:
        return {"thinkingLevel": _GEMINI3_SOME_THINKING}
    level = _GEMINI3_THINKING_FLOOR.get(
        (model or "").strip().lower(), _GEMINI3_DEFAULT_FLOOR
    )
    return {"thinkingLevel": level}


# Shared HTTP client — lazily created, reused for connection pooling.
_client: Optional[httpx.AsyncClient] = None
_client_lock = asyncio.Lock()


def _try_parse_json(text: str) -> Optional[Dict[str, Any]]:
    """Attempt to parse JSON from Gemini output, with repair for common issues.

    Gemini's ``responseMimeType: "application/json"`` constraint is not fully
    reliable — especially for large outputs from thinking models.  Observed
    failures include:

    1. Markdown fences wrapping the JSON (```json ... ```)
    2. Trailing commas before } or ]
    3. Truncated output (unterminated strings, unclosed brackets)

    This function tries progressively more aggressive repairs before giving up.
    Returns the parsed dict/list on success, or ``None`` on failure.
    """
    if not text or not text.strip():
        return None

    # --- Step 1: Strip markdown fences ---
    stripped = text.strip()
    fence_match = re.match(r"^```(?:json)?\s*\n?(.*?)\n?\s*```$", stripped, re.DOTALL)
    if fence_match:
        stripped = fence_match.group(1).strip()
        logger.debug("[JSON-REPAIR] Stripped markdown fences")

    # --- Step 2: Try bare parse ---
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass

    # --- Step 3: Remove trailing commas ---
    cleaned = re.sub(r",(\s*[}\]])", r"\1", stripped)
    if cleaned != stripped:
        try:
            parsed = json.loads(cleaned)
            logger.info("[JSON-REPAIR] Fixed trailing commas in Gemini response")
            return parsed
        except json.JSONDecodeError:
            pass
        # Continue with cleaned version for truncation repair
        stripped = cleaned

    # --- Step 4: Truncation repair ---
    # Close unterminated string literal
    repaired = stripped
    in_string = False
    escape = False
    for ch in repaired:
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == '"':
            in_string = not in_string

    if in_string:
        repaired += '"'
        logger.debug("[JSON-REPAIR] Closed unterminated string")

    # Close unclosed brackets/braces in LIFO order
    stack = []
    in_str = False
    esc = False
    for ch in repaired:
        if esc:
            esc = False
            continue
        if ch == "\\":
            esc = True
            continue
        if ch == '"':
            in_str = not in_str
            continue
        if in_str:
            continue
        if ch in ("{", "["):
            stack.append("}" if ch == "{" else "]")
        elif ch in ("}", "]"):
            if stack and stack[-1] == ch:
                stack.pop()

    if stack:
        # Remove any trailing comma before closing
        repaired = repaired.rstrip().rstrip(",")
        repaired += "".join(reversed(stack))
        logger.debug("[JSON-REPAIR] Closed %d unclosed bracket(s)", len(stack))

    if repaired != stripped:
        try:
            parsed = json.loads(repaired)
            logger.info(
                "[JSON-REPAIR] Repaired truncated Gemini response (%d chars)",
                len(text),
            )
            return parsed
        except json.JSONDecodeError as exc:
            logger.warning("[JSON-REPAIR] Repair attempt failed: %s", exc)

    return None


async def _get_client() -> httpx.AsyncClient:
    """Return (and lazily create) the shared HTTP client.

    Timeout is NOT set on the client — callers pass it per-request
    via ``client.post(..., timeout=X)``.  The generous default here
    only guards against truly hung connections.
    """
    global _client
    if _client is None or _client.is_closed:
        async with _client_lock:
            if _client is None or _client.is_closed:
                _client = httpx.AsyncClient(
                    timeout=httpx.Timeout(120.0, connect=10.0),
                    limits=httpx.Limits(
                        max_connections=_CONCURRENCY,
                        max_keepalive_connections=_CONCURRENCY,
                    ),
                )
    return _client


def _jittered_delay(attempt: int, retry_after: Optional[float] = None) -> float:
    """Compute backoff delay with full jitter.

    If the server sent a Retry-After header, use that as a floor.
    """
    exp_delay = _BASE_DELAY * (2**attempt)
    jittered = random.uniform(0, exp_delay)
    delay = max(jittered, retry_after or 0)
    return min(delay, _MAX_DELAY)


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

    model = model or getattr(settings, "GOOGLE_LLM_MODEL", "gemini-3.5-flash-lite")
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
    client = await _get_client()

    for attempt in range(_MAX_RETRIES):
        retry_after: Optional[float] = None

        async with _semaphore:
            try:
                response = await client.post(
                    url,
                    headers={"Content-Type": "application/json"},
                    json=body,
                    timeout=timeout,
                )
            except httpx.TimeoutException:
                logger.warning(
                    "Google AI timeout (attempt %d/%d)", attempt + 1, _MAX_RETRIES
                )
                # Don't retry timeouts — thinking models need more time, not another attempt
                return None
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
                        parsed = _try_parse_json(text)
                        if parsed is None:
                            logger.error(
                                "Google AI response parse error (after repair)"
                            )
                        return parsed
                    except (KeyError, IndexError) as exc:
                        logger.error("Google AI response structure error: %s", exc)
                        return None

                if response.status_code not in (429, 503):
                    logger.error("Google AI error: %d", response.status_code)
                    return None

                # Respect Retry-After header if present
                ra = response.headers.get("retry-after")
                if ra:
                    try:
                        retry_after = float(ra)
                    except ValueError:
                        pass

                extra = f" (retry-after: {retry_after}s)" if retry_after else ""
                logger.warning(
                    "Google AI %d (attempt %d/%d), backing off%s",
                    response.status_code,
                    attempt + 1,
                    _MAX_RETRIES,
                    extra,
                )

        # Jittered exponential back-off (outside semaphore so we release the slot)
        delay = _jittered_delay(attempt, retry_after)
        await asyncio.sleep(delay)

    # Transient 429/503 after exhausting retries is an upstream availability blip
    # (e.g. Gemini overloaded), not a Tru8 bug — log at warning so it does not
    # raise a Sentry error event. Any other terminal status stays at error.
    _terminal_log = logger.warning if last_status in (429, 503) else logger.error
    _terminal_log(
        "Google AI failed after %d retries (last status: %s)",
        _MAX_RETRIES,
        last_status,
    )
    return None


async def call_google_ai_with_usage(
    prompt: str,
    *,
    temperature: float = 0.1,
    max_tokens: int = 1500,
    timeout: float = 30,
    model: Optional[str] = None,
    response_schema: Optional[Dict[str, Any]] = None,
    thinking_budget: Optional[int] = None,
) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, int]]]:
    """Send a prompt to Google Gemini and return parsed JSON + token usage.

    Returns ``(parsed_content, usage_dict)`` where usage_dict contains
    ``input_tokens`` and ``output_tokens``.  On error returns ``(None, None)``.

    When ``response_schema`` is provided, Gemini constrains the model's
    output to match the schema (OpenAPI-3.0-subset). Used by the mapper
    to enforce structural validity at the API level.

    This is a companion to ``call_google_ai`` — the original function is
    unchanged so existing callers (20+) are unaffected.
    """
    api_key = getattr(settings, "GOOGLE_AI_API_KEY", "")
    if not api_key:
        logger.debug("Google AI API key not configured")
        return None, None

    model = model or getattr(settings, "GOOGLE_LLM_MODEL", "gemini-3.5-flash-lite")
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={api_key}"
    )
    generation_config: Dict[str, Any] = {
        "temperature": temperature,
        "maxOutputTokens": max_tokens,
        "responseMimeType": "application/json",
    }
    if response_schema is not None:
        generation_config["responseSchema"] = response_schema
    # `is not None` deliberately: 0 is a real value (thinking OFF), None means
    # omit the field so the API applies its default (dynamic thinking) and the
    # request body stays byte-identical for replay-bench cassettes.
    # The 2.5 vs 3.x field split lives in `_thinking_config` — see its note.
    _thinking = _thinking_config(model, thinking_budget)
    if _thinking is not None:
        generation_config["thinkingConfig"] = _thinking
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": generation_config,
    }

    last_status: Optional[int] = None
    client = await _get_client()

    for attempt in range(_MAX_RETRIES):
        retry_after: Optional[float] = None

        async with _semaphore:
            try:
                response = await client.post(
                    url,
                    headers={"Content-Type": "application/json"},
                    json=body,
                    timeout=timeout,
                )
            except httpx.TimeoutException:
                logger.warning(
                    "Google AI timeout (attempt %d/%d)", attempt + 1, _MAX_RETRIES
                )
                # Don't retry timeouts — thinking models need more time, not another attempt
                return None, None
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
                        parsed = _try_parse_json(text)
                        if parsed is None:
                            logger.error(
                                "Google AI response parse error (after repair)"
                            )
                            return None, None

                        # Extract token usage from response envelope
                        usage_meta = result.get("usageMetadata", {})
                        usage = {
                            "input_tokens": usage_meta.get("promptTokenCount", 0),
                            "output_tokens": usage_meta.get("candidatesTokenCount", 0),
                        }
                        # Thinking models (e.g. gemini-2.5-flash on mapping)
                        # report thought tokens separately from candidate
                        # tokens. Include only when present so the usage
                        # shape is unchanged for non-thinking models.
                        thoughts = usage_meta.get("thoughtsTokenCount", 0)
                        if thoughts:
                            usage["thinking_tokens"] = thoughts
                        return parsed, usage
                    except (KeyError, IndexError) as exc:
                        logger.error("Google AI response structure error: %s", exc)
                        return None, None

                if response.status_code not in (429, 503):
                    logger.error("Google AI error: %d", response.status_code)
                    return None, None

                ra = response.headers.get("retry-after")
                if ra:
                    try:
                        retry_after = float(ra)
                    except ValueError:
                        pass

                extra = f" (retry-after: {retry_after}s)" if retry_after else ""
                logger.warning(
                    "Google AI %d (attempt %d/%d), backing off%s",
                    response.status_code,
                    attempt + 1,
                    _MAX_RETRIES,
                    extra,
                )

        delay = _jittered_delay(attempt, retry_after)
        await asyncio.sleep(delay)

    # Transient 429/503 after exhausting retries is an upstream availability blip
    # (e.g. Gemini overloaded), not a Tru8 bug — log at warning so it does not
    # raise a Sentry error event. Any other terminal status stays at error.
    _terminal_log = logger.warning if last_status in (429, 503) else logger.error
    _terminal_log(
        "Google AI failed after %d retries (last status: %s)",
        _MAX_RETRIES,
        last_status,
    )
    return None, None
