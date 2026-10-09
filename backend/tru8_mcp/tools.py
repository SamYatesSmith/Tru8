"""Tru8 API client for MCP tool implementations.

Wraps the Tru8 REST API. `tru8_check` uses the smart endpoint
(`/agent/check`), asynchronously since 2026-10-09: submit, then poll
`/agent/result/{id}` with short requests.
"""

import asyncio
import json
import logging
import os
from importlib.metadata import PackageNotFoundError, version
from typing import Optional

import hashlib

import httpx

logger = logging.getLogger(__name__)

# Client identifier sent on every request so the backend can attribute usage to
# the MCP package (persisted as Check.client). Format: "mcp/<version>".
try:
    _CLIENT_VERSION = version("tru8-mcp")
except PackageNotFoundError:  # running from source, not installed
    _CLIENT_VERSION = "dev"
CLIENT_HEADER = f"mcp/{_CLIENT_VERSION}"

# Pipeline timeouts (seconds)
PIPELINE_TIMEOUT = 180.0
GET_TIMEOUT = 30.0
POLL_INTERVAL = 3.0
MAX_POLL_DURATION = 300.0

# Tier timeouts — quick is faster, so shorter HTTP timeout
TIER_TIMEOUTS = {
    "lookup": 15.0,
    "consensus": 15.0,
    "quick": 60.0,
    "full": PIPELINE_TIMEOUT + 30.0,
}

# Tier order for fallback
TIER_ORDER = ["lookup", "consensus", "quick", "full"]

# Async submit + poll (2026-10-09). A synchronous call held ONE silent
# connection for the whole pipeline, and Cloudflare closes an origin silent
# for 125 s: a slow check lost its result while the server finished and kept
# the charge. Polling keeps every request short.
#
# /agent/result is limited to 30/minute PER API KEY, so 8 s leaves room for a
# few checks at once. The server sends no Retry-After, hence a fixed backoff.
POLL_INTERVAL_S = 8.0
RATE_LIMIT_BACKOFF_S = 10.0
# How long to poll before answering "still running": the server bounds each
# pipeline phase by the tier's wall time (full 180 s, quick 30 s) and an
# article URL runs two phases, plus a margin for saving.
POLL_DEADLINE_S = {"quick": 2 * 30.0 + 60.0, "full": 2 * 180.0 + 60.0}
_ASYNC_TIERS = ("quick", "full")


def _now() -> float:
    return asyncio.get_running_loop().time()


class Tru8APIError(RuntimeError):
    """A non-success HTTP answer to a submit. Carries the status code so the
    caller decides on the code, never on the message text (a check id can
    contain "404")."""

    def __init__(self, status_code: int, text: str):
        self.status_code = status_code
        super().__init__(f"API error {status_code}: {text}")


class CheckFailedError(Exception):
    """The submitted check failed or cannot be read back. Deliberately NOT a
    RuntimeError: submit_with_fallback's old-server path re-submits under
    different idempotency keys, and must never run because a poll failed."""


# Idempotency (2026-09-02, rebuilt 2026-09-11). Over the hosted transport the
# streamable-HTTP stream dies at ~140 s; the client's next POST is rejected,
# it re-initialises and RE-SENDS the pending tool call, and the server runs it
# again. One tru8_check produced two charged checks (dd2ca726 + c8dd4886).
# The API honours an Idempotency-Key (agent_auth.py: same key + same request
# hash + same payer → the first transaction is returned, no second charge).
#
# ⚠️ The 2026-09-02 key mixed in floor(epoch / 600) — a FIXED clock bucket
# aligned to :00/:10/:20 of every hour, not a window from the first call. A
# retry after gap g straddled a boundary with probability g/600 (57% for the
# 340 s gap seen 2026-09-11: 09:58:40 → 10:04:20, checks a093c7d2 + bebfa026,
# both charged). The key now carries NO time term; the ten-minute window is
# enforced server-side from the first transaction's created_at
# (settings.AGENT_IDEMPOTENCY_TTL_S). It is salted with the caller's API key so
# two hosted users sending the same claim can never share a key — before this,
# the second would have been handed the first's check, uncharged.
IDEMPOTENCY_WINDOW_S = 600.0  # documentary: the server's TTL, not used here


def idempotency_key_for(
    endpoint: str, payload: dict, api_key: Optional[str] = None
) -> str:
    """One key per (endpoint, payload, caller). No time term — see above."""
    raw = json.dumps(
        {
            "e": endpoint,
            "p": payload,
            "k": hashlib.sha256((api_key or "").encode("utf-8")).hexdigest()[:16],
        },
        sort_keys=True,
        default=str,
    )
    return "mcp-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:40]


class Tru8APIClient:
    """HTTP client wrapping the Tru8 Evidence Research API.

    Authenticates via API key (X-API-Key header). Supports both the legacy
    /checks/run endpoint and the agent tier endpoints (/agent/lookup, /quick, /full).
    """

    def __init__(
        self,
        api_url: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        self.base_url = (
            api_url or os.environ.get("TRU8_API_URL", "https://api.trueight.com")
        ).rstrip("/")
        self.api_key = api_key or os.environ.get("TRU8_API_KEY", "")
        if not self.api_key:
            # One class serves both transports, so this message must too. The
            # old wording named only the environment variable, which is the
            # stdio answer — a hosted caller over /mcp has no environment to
            # set and was being told to do something impossible.
            raise ValueError(
                "No Tru8 API key supplied. Over HTTP, send your key as an "
                "'X-API-Key' header (or an 'apiKey' query parameter). Running "
                "the tru8-mcp package locally, set the TRU8_API_KEY "
                "environment variable. Create a key at your Tru8 dashboard "
                "→ Settings → Developer."
            )

    def _headers(self, idempotency_key: Optional[str] = None) -> dict:
        headers = {
            "X-API-Key": self.api_key,
            "Accept": "application/json",
            "X-Tru8-Client": CLIENT_HEADER,
        }
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        return headers

    @staticmethod
    def _detect_input_type(claim: str) -> Optional[str]:
        """Return "url" if claim looks like a URL, else None (server auto-detects)."""
        if claim.strip().startswith(("http://", "https://")):
            return "url"
        return None

    async def submit_tier(
        self,
        claim: str,
        tier: str,
        compact: bool = False,
    ) -> dict:
        """Submit a claim or URL to a specific agent tier endpoint.

        Args:
            claim: The claim text or article URL to analyse.
            tier: "lookup", "quick", or "full".
            compact: If True, strip evidence arrays from response.

        Returns:
            The tier endpoint response dict (includes _meta block).
        """
        timeout = TIER_TIMEOUTS.get(tier, PIPELINE_TIMEOUT)
        payload: dict = {"claim": claim, "compact": compact}
        input_type = self._detect_input_type(claim)
        if input_type:
            payload["input_type"] = input_type

        async with httpx.AsyncClient(
            timeout=httpx.Timeout(timeout, connect=10.0)
        ) as client:
            resp = await client.post(
                f"{self.base_url}/api/v1/agent/{tier}",
                json=payload,
                headers=self._headers(
                    idempotency_key_for(f"agent/{tier}", payload, self.api_key)
                ),
            )
            if resp.status_code == 402:
                raise InsufficientBalanceError(f"Insufficient balance for {tier} tier")
            if resp.status_code not in (200, 201):
                raise Tru8APIError(resp.status_code, resp.text)
            return resp.json()

    async def submit_smart(
        self,
        claim: str,
        max_tier: str = "quick",
        max_age_hours: Optional[int] = None,
        compact: bool = False,
    ) -> dict:
        """Submit via smart endpoint with server-side fallback (M-03).

        Args:
            claim: The claim text or article URL to analyse.
            max_tier: Maximum tier to attempt ("lookup", "quick", or "full").
            max_age_hours: Skip cache hits older than this many hours.
            compact: If True, strip evidence arrays from response.

        Returns:
            The smart endpoint response dict.
        """
        timeout = TIER_TIMEOUTS.get(max_tier, PIPELINE_TIMEOUT)
        payload: dict = {"claim": claim, "max_tier": max_tier, "compact": compact}
        input_type = self._detect_input_type(claim)
        if input_type:
            payload["input_type"] = input_type
        # `is not None`, not truthiness: 0 means "never serve a cached result"
        # and truthiness silently dropped it — the client-side twin of the
        # server bug fixed 2026-08-05 (agent.py), found 2026-08-13 when the
        # TRU-018F-44AA acceptance run was served the stale broken record it
        # existed to invalidate.
        if max_age_hours is not None:
            payload["max_age_hours"] = max_age_hours
        # A query parameter, not part of the payload: the idempotency key and
        # the server's request hash are the same for sync and async calls.
        # The request timeout stays at the tier's, so an older server that
        # ignores the parameter and answers synchronously still works.
        params = {"async": "true"} if max_tier in _ASYNC_TIERS else None

        async with httpx.AsyncClient(
            timeout=httpx.Timeout(timeout, connect=10.0)
        ) as client:
            resp = await client.post(
                f"{self.base_url}/api/v1/agent/check",
                json=payload,
                params=params,
                headers=self._headers(
                    idempotency_key_for("agent/check", payload, self.api_key)
                ),
            )
            if resp.status_code == 402:
                raise InsufficientBalanceError(
                    f"Insufficient balance for {max_tier} tier"
                )
            if resp.status_code == 202:
                accepted = resp.json()
                if not accepted.get("checkId"):
                    raise Tru8APIError(resp.status_code, resp.text)
            elif resp.status_code in (200, 201):
                return resp.json()
            else:
                raise Tru8APIError(resp.status_code, resp.text)
        return await self._await_agent_result(accepted, compact=compact)

    async def _await_agent_result(self, accepted: dict, compact: bool = False) -> dict:
        """Poll /agent/result until the accepted check completes.

        Completed → the result, with ``_meta.chargedPence`` restored from the
        submit (the result endpoint always reports 0). Failed or unreadable →
        CheckFailedError. Rate limits and transient server errors back off and
        continue. Past the deadline → a still-running answer naming the check,
        never an error: an error invites a re-submit, a second charge.
        """
        check_id = accepted["checkId"]
        charged = accepted.get("chargedPence")
        tier = accepted.get("tier") or "full"
        deadline = _now() + POLL_DEADLINE_S.get(tier, POLL_DEADLINE_S["full"])
        params = {"compact": "true"} if compact else None
        status = accepted.get("status") or "processing"

        async with httpx.AsyncClient(
            timeout=httpx.Timeout(GET_TIMEOUT, connect=10.0)
        ) as client:
            while _now() < deadline:
                await asyncio.sleep(POLL_INTERVAL_S)
                try:
                    resp = await client.get(
                        f"{self.base_url}/api/v1/agent/result/{check_id}",
                        params=params,
                        headers=self._headers(),
                    )
                except httpx.HTTPError as e:
                    logger.warning(f"Poll for {check_id} failed, retrying: {e}")
                    continue
                if resp.status_code == 429 or resp.status_code >= 500:
                    await asyncio.sleep(RATE_LIMIT_BACKOFF_S)
                    continue
                if resp.status_code != 200:
                    raise CheckFailedError(
                        f"Could not read check {check_id} "
                        f"(HTTP {resp.status_code}: {resp.text})"
                    )
                try:
                    data = resp.json()
                except ValueError:
                    # An edge error page served as 200; poll again.
                    continue
                status = data.get("status") or status
                if "_meta" in data:
                    if charged is not None:
                        data["_meta"]["chargedPence"] = charged
                    return data
                if status == "failed":
                    raise CheckFailedError(
                        f"Check {check_id} failed. A failed check is not charged: "
                        "credits are refunded, other payment rails are left "
                        "unsettled. Calling tru8_check again starts a new run."
                    )

        return {
            "checkId": check_id,
            "status": status,
            "chargedPence": charged,
            "message": (
                "The check is still running. Call tru8_get_result with this "
                "checkId to fetch it when it completes (free). Do not call "
                "tru8_check again for the same claim: an identical call within "
                "ten minutes returns this same check."
            ),
        }

    async def submit_with_fallback(
        self,
        claim: str,
        max_tier: str = "quick",
        max_age_hours: Optional[int] = None,
        compact: bool = False,
    ) -> dict:
        """Submit a claim with tier fallback: lookup → quick → full (up to max_tier).

        Prefers the smart endpoint (M-03). Falls back to client-side tier
        escalation if the server returns 404 (backward compat with older servers).

        Args:
            claim: The claim text to analyse.
            max_tier: Maximum tier to attempt ("lookup", "quick", or "full").
            max_age_hours: Skip cache hits older than this many hours.
            compact: If True, strip evidence arrays from response.

        Returns:
            The response dict from whichever tier succeeded.
        """
        # Try smart endpoint first (M-03)
        try:
            return await self.submit_smart(
                claim, max_tier=max_tier, max_age_hours=max_age_hours, compact=compact
            )
        except Tru8APIError as e:
            # Decided on the status code of the SUBMIT alone. Matching "404" in
            # the message text also caught check ids that contain "404".
            if e.status_code == 404:
                logger.info(
                    "Smart endpoint not available, falling back to client-side escalation"
                )
            else:
                raise

        # Client-side fallback for older servers
        max_rank = TIER_ORDER.index(max_tier) if max_tier in TIER_ORDER else 1

        # Always try lookup first
        try:
            result = await self.submit_tier(claim, "lookup", compact=compact)
            if result.get("hit"):
                return result
            # Lookup miss — escalate if allowed
        except InsufficientBalanceError:
            raise
        except Exception as e:
            logger.warning(f"Lookup failed: {e}")

        # Escalate to quick if allowed
        if max_rank >= TIER_ORDER.index("quick"):
            try:
                return await self.submit_tier(claim, "quick", compact=compact)
            except InsufficientBalanceError:
                raise
            except Exception as e:
                if max_rank >= TIER_ORDER.index("full"):
                    logger.warning(f"Quick failed, escalating to full: {e}")
                else:
                    raise

        # Escalate to full if allowed
        if max_rank >= TIER_ORDER.index("full"):
            return await self.submit_tier(claim, "full", compact=compact)

        raise RuntimeError(f"No tier up to {max_tier} returned a result")

    async def submit_check_sync(self, text: str) -> dict:
        """Submit content via the synchronous /run endpoint and return the full result.

        Backward-compatible alias. For new code, prefer submit_with_fallback().
        """
        input_type = (
            "url" if text.strip().startswith(("http://", "https://")) else "text"
        )
        payload = {"input_type": input_type}
        if input_type == "url":
            payload["url"] = text.strip()
        else:
            payload["content"] = text.strip()

        async with httpx.AsyncClient(
            timeout=httpx.Timeout(PIPELINE_TIMEOUT + 30.0, connect=10.0)
        ) as client:
            resp = await client.post(
                f"{self.base_url}/api/v1/checks/run",
                json=payload,
                headers=self._headers(),
            )
            if resp.status_code != 200:
                raise RuntimeError(f"API error {resp.status_code}: {resp.text}")
            return resp.json()

    async def submit_check_sse(self, text: str) -> str:
        """Submit content for evidence research and wait for completion.

        Consumes the SSE stream from POST /stream. For URL inputs that pause
        for claim selection, auto-selects all extracted claims (up to 5) and
        polls until Phase 2 completes.

        Returns:
            The completed check ID.
        """
        input_type = (
            "url" if text.strip().startswith(("http://", "https://")) else "text"
        )
        payload = {"input_type": input_type}
        if input_type == "url":
            payload["url"] = text.strip()
        else:
            payload["content"] = text.strip()

        timeout = PIPELINE_TIMEOUT
        check_id = None
        awaiting_selection = False
        claim_positions = []

        async with httpx.AsyncClient(
            timeout=httpx.Timeout(timeout, connect=10.0)
        ) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/api/v1/checks/stream",
                json=payload,
                headers={**self._headers(), "Accept": "text/event-stream"},
            ) as response:
                if response.status_code != 200:
                    body = await response.aread()
                    raise RuntimeError(
                        f"API error {response.status_code}: {body.decode()}"
                    )

                check_id = response.headers.get("x-check-id")

                async for line in response.aiter_lines():
                    line = line.strip()
                    if not line or not line.startswith("data:"):
                        continue
                    try:
                        data = json.loads(line[5:].strip())
                    except json.JSONDecodeError:
                        continue

                    event_type = data.get("type")

                    if event_type == "completed":
                        check_id = check_id or data.get("checkId")
                        return check_id

                    elif event_type == "error":
                        raise RuntimeError(
                            f"Pipeline error: {data.get('error', 'unknown')}"
                        )

                    elif event_type == "timeout":
                        raise RuntimeError("Pipeline timed out")

                    elif event_type == "awaiting_selection":
                        check_id = check_id or data.get("checkId")
                        # Extract claim positions, preferring highest-ranked
                        claims = data.get("claims", [])
                        claims_sorted = sorted(
                            claims,
                            key=lambda c: c.get("significance_rank", 999),
                        )
                        claim_positions = [
                            c.get("position", i) for i, c in enumerate(claims_sorted)
                        ]
                        awaiting_selection = True
                        break

                    elif event_type == "connected":
                        check_id = check_id or data.get("checkId")

        if not check_id:
            raise RuntimeError("No check ID received from pipeline")

        if awaiting_selection:
            await self._select_claims(check_id, claim_positions[:5])
            await self._poll_until_complete(check_id)

        return check_id

    async def _select_claims(self, check_id: str, positions: list[int]) -> None:
        """Select claims for Phase 2 analysis."""
        if not positions:
            positions = [0]

        async with httpx.AsyncClient(timeout=GET_TIMEOUT) as client:
            resp = await client.patch(
                f"{self.base_url}/api/v1/checks/{check_id}/select-claims",
                json={"selected_positions": positions},
                headers={**self._headers(), "Content-Type": "application/json"},
            )
            if resp.status_code not in (200, 202):
                raise RuntimeError(
                    f"Claim selection failed ({resp.status_code}): {resp.text}"
                )

        logger.info(f"Auto-selected {len(positions)} claims for check {check_id}")

    async def _poll_until_complete(self, check_id: str) -> None:
        """Poll check status until completed or failed."""
        elapsed = 0.0
        async with httpx.AsyncClient(timeout=GET_TIMEOUT) as client:
            while elapsed < MAX_POLL_DURATION:
                resp = await client.get(
                    f"{self.base_url}/api/v1/checks/{check_id}",
                    headers=self._headers(),
                )
                if resp.status_code == 200:
                    status = resp.json().get("status")
                    if status == "completed":
                        return
                    elif status == "failed":
                        error = resp.json().get("errorMessage", "Pipeline failed")
                        raise RuntimeError(f"Pipeline failed: {error}")

                await asyncio.sleep(POLL_INTERVAL)
                elapsed += POLL_INTERVAL

        raise RuntimeError(f"Pipeline did not complete within {MAX_POLL_DURATION}s")

    async def get_check(self, check_id: str, computed: bool = False) -> dict:
        """Retrieve a completed check by ID.

        Args:
            check_id: UUID of the check.
            computed: If True, include _computed analytics block.
        """
        params = {"computed": "true"} if computed else {}
        async with httpx.AsyncClient(timeout=GET_TIMEOUT) as client:
            resp = await client.get(
                f"{self.base_url}/api/v1/checks/{check_id}",
                headers=self._headers(),
                params=params,
            )
            if resp.status_code != 200:
                raise RuntimeError(f"API error {resp.status_code}: {resp.text}")
            return resp.json()


class InsufficientBalanceError(RuntimeError):
    """Raised when the agent's credit balance is insufficient for the requested tier."""

    pass
