"""Tru8 API client for MCP tool implementations.

Wraps the Tru8 REST API with methods for submitting checks via the
synchronous /run endpoint (preferred) or SSE streaming (fallback).
"""

import asyncio
import json
import logging
import os
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# Pipeline timeouts (seconds)
FULL_PIPELINE_TIMEOUT = 180.0
SNAPSHOT_PIPELINE_TIMEOUT = 60.0
GET_TIMEOUT = 30.0
POLL_INTERVAL = 3.0
MAX_POLL_DURATION = 300.0


class Tru8APIClient:
    """HTTP client wrapping the Tru8 Evidence Research API.

    Authenticates via API key (X-API-Key header). Handles SSE consumption
    for streaming pipeline endpoints and auto-selects claims for URL inputs.
    """

    def __init__(
        self,
        api_url: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        self.base_url = (
            api_url or os.environ.get("TRU8_API_URL", "https://api.tru8.app")
        ).rstrip("/")
        self.api_key = api_key or os.environ.get("TRU8_API_KEY", "")
        if not self.api_key:
            raise ValueError(
                "TRU8_API_KEY environment variable required. "
                "Create one at your Tru8 dashboard → Settings → Developer."
            )

    def _headers(self) -> dict:
        return {"X-API-Key": self.api_key, "Accept": "application/json"}

    async def submit_check_sync(self, text: str, mode: str = "full") -> dict:
        """Submit content via the synchronous /run endpoint and return the full result.

        Single HTTP call — blocks until the pipeline completes and returns the
        check response with claims, evidence, and computed analytics. No SSE,
        no polling, no claim selection handling required.

        Returns:
            The full check response dict (same shape as GET /checks/{id}?computed=true).
        """
        input_type = (
            "url" if text.strip().startswith(("http://", "https://")) else "text"
        )
        payload = {"input_type": input_type, "mode": mode}
        if input_type == "url":
            payload["url"] = text.strip()
        else:
            payload["content"] = text.strip()

        # Pipeline timeout + 30s buffer for network overhead
        timeout = (
            FULL_PIPELINE_TIMEOUT + 30.0
            if mode == "full"
            else SNAPSHOT_PIPELINE_TIMEOUT + 30.0
        )

        async with httpx.AsyncClient(
            timeout=httpx.Timeout(timeout, connect=10.0)
        ) as client:
            resp = await client.post(
                f"{self.base_url}/api/v1/checks/run",
                json=payload,
                headers=self._headers(),
            )
            if resp.status_code != 200:
                raise RuntimeError(f"API error {resp.status_code}: {resp.text}")
            return resp.json()

    async def submit_check_sse(self, text: str, mode: str = "full") -> str:
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
        payload = {"input_type": input_type, "mode": mode}
        if input_type == "url":
            payload["url"] = text.strip()
        else:
            payload["content"] = text.strip()

        timeout = FULL_PIPELINE_TIMEOUT if mode == "full" else SNAPSHOT_PIPELINE_TIMEOUT
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
