"""Tru8 API client for MCP tool implementations.

Wraps the Tru8 REST API with methods for submitting checks via the
synchronous /run endpoint (preferred) or agent tier endpoints (L-08).
"""

import asyncio
import json
import logging
import os
from importlib.metadata import PackageNotFoundError, version
from typing import Optional

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

    def _headers(self) -> dict:
        return {
            "X-API-Key": self.api_key,
            "Accept": "application/json",
            "X-Tru8-Client": CLIENT_HEADER,
        }

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
                headers=self._headers(),
            )
            if resp.status_code == 402:
                raise InsufficientBalanceError(f"Insufficient balance for {tier} tier")
            if resp.status_code not in (200, 201):
                raise RuntimeError(f"API error {resp.status_code}: {resp.text}")
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
        if max_age_hours:
            payload["max_age_hours"] = max_age_hours

        async with httpx.AsyncClient(
            timeout=httpx.Timeout(timeout, connect=10.0)
        ) as client:
            resp = await client.post(
                f"{self.base_url}/api/v1/agent/check",
                json=payload,
                headers=self._headers(),
            )
            if resp.status_code == 402:
                raise InsufficientBalanceError(
                    f"Insufficient balance for {max_tier} tier"
                )
            if resp.status_code not in (200, 201):
                raise RuntimeError(f"API error {resp.status_code}: {resp.text}")
            return resp.json()

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
        except RuntimeError as e:
            if "404" in str(e):
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
