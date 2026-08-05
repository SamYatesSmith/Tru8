"""Tru8 MCP server — structured evidence research tools for AI agents.

Run standalone:
    python -m tru8_mcp

Configure for Claude Desktop (claude_desktop_config.json):
    {
        "mcpServers": {
            "tru8": {
                "command": "python",
                "args": ["-m", "tru8_mcp"],
                "env": {"TRU8_API_KEY": "tru8_sk_..."}
            }
        }
    }

Environment variables:
    TRU8_API_KEY  — Required. Create at dashboard → Settings → Developer.
                    Store in env vars or a secrets manager — never hardcode in source.
    TRU8_API_URL  — Optional. Default: https://api.trueight.com
"""

import json
from typing import Optional

from mcp.server.fastmcp import FastMCP

from .tools import Tru8APIClient

mcp = FastMCP(
    "tru8",
    instructions=(
        "Structured evidence research. Submit a factual claim or article URL. "
        "Evidence is organised by source tier (primary/reporting/commentary) "
        "and type (data/official/news/analysis/opinion/academic), with element "
        "decomposition and relationship mapping (supports/challenges/context)."
    ),
)


def _request_api_key() -> Optional[str]:
    """The calling user's API key for THIS request, or None.

    Only meaningful over an HTTP transport, where one process serves many
    users. Reads the same header the Tru8 API itself uses (``X-API-Key``),
    accepts ``Authorization: Bearer`` as a courtesy, and finally a query
    parameter — which is how Smithery-style gateways pass session config.

    Returns None under stdio, where there is no HTTP request and the key
    belongs in the environment instead.
    """
    try:
        request = mcp.get_context().request_context.request
    except Exception:
        return None
    if request is None or not hasattr(request, "headers"):
        return None

    key = request.headers.get("x-api-key")
    if key:
        return key.strip()

    auth = request.headers.get("authorization") or ""
    if auth.lower().startswith("bearer "):
        return auth[7:].strip() or None

    params = getattr(request, "query_params", None)
    if params:
        for name in ("apiKey", "api_key", "TRU8_API_KEY"):
            if params.get(name):
                return params[name].strip()
    return None


def _get_client() -> Tru8APIClient:
    """Build the API client for the current request.

    DELIBERATELY NOT CACHED. This was a module-level singleton built once
    from the environment, which is correct for stdio (one process, one user)
    and a credential-crossing bug the moment the same process serves more
    than one caller over HTTP: whichever key initialised the singleton would
    then have served everyone else's requests.

    The client is a stateless holder of a base URL and a key — it opens its
    own connection per call — so constructing one per request costs an object
    allocation and removes the entire class of bug. Do not reintroduce a
    cache here without keying it on the resolved credential.

    Under stdio ``_request_api_key()`` returns None and Tru8APIClient falls
    back to TRU8_API_KEY, so local behaviour is unchanged.
    """
    return Tru8APIClient(api_key=_request_api_key())


def _format(data: dict) -> str:
    """Serialize API response as indented JSON for agent consumption."""
    return json.dumps(data, indent=2, default=str)


@mcp.tool()
async def tru8_check(
    claim: str,
    max_tier: str = "full",
    max_age_hours: int | None = None,
    compact: bool = False,
) -> str:
    """Evidence research for a factual claim or article URL.

    Submit a claim as text or paste an article URL. URLs are auto-detected
    and trigger article mode: the pipeline extracts claims from the page
    and auto-selects up to 5 for evidence research.

    Tiers (in fallback order):
    - lookup    (~£0.02, instant) — cached prior analysis
    - consensus (~£0.03, instant) — cross-user aggregate landscape (k≥3 checks)
    - quick     (~£0.07, ~15s) — web search + heuristic classification
    - full      (~£0.15, ~60-90s) — web + specialist APIs, LLM classification, coverage recovery

    Charges based on tier actually executed, not tier requested.
    Set max_tier to control maximum spend per call.

    Output structure:
    - claims[].claimMap.elements[] — verifiable sub-claims with state
      (supported/disputed/unresolved)
    - claims[].claimMap.elements[].evidenceRefs[] — evidence mapped to elements
      with relationship (supports/challenges/context) and reasoning
    - claims[].evidence[] — sources classified by tier (primary/reporting/
      commentary) and type (data/official/news/analysis/opinion/academic)
    - claims[].claimMap.orientation — mechanical summary from element states
    - _meta — execution metadata: executedTier, chargedPence, limitations

    Args:
        claim: A factual claim ("The Earth's average temperature rose 1.1°C
               since 1880") or an article URL (https://example.com/article).
               URLs are auto-detected and the pipeline extracts claims from
               the page content.
        max_tier: Maximum tier to attempt — "lookup", "consensus", "quick", or
                  "full" (default). This is a CEILING, not a floor: cached and
                  consensus hits still return instantly at their own lower
                  price, so the default costs ~£0.15 only for claims that have
                  never been researched. Set "quick" to cap spend at ~£0.07,
                  accepting web-search-only sourcing and heuristic
                  classification (see the limitations list in _meta).
        max_age_hours: Skip cache hits older than this many hours. If set,
                       lookup hits that are stale will be discarded and the
                       pipeline re-runs at the next tier up to max_tier.
        compact: If True, strip full evidence arrays from response (smaller payload).
    """
    client = _get_client()
    result = await client.submit_with_fallback(
        claim,
        max_tier=max_tier,
        max_age_hours=max_age_hours,
        compact=compact,
    )
    return _format(result)


@mcp.tool()
async def tru8_get_result(check_id: str) -> str:
    """Retrieve a previously submitted check with pre-computed analytics.

    Returns the full result including a _computed block with tier/type
    distributions, corroboration groups, diagnostic values, timeline
    analysis, element state summaries, and per-claim dispositions.

    Use this over tru8_get_result_raw when you want structured analytics
    ready for summarisation or comparison without post-processing.

    Args:
        check_id: UUID returned by tru8_check.
    """
    client = _get_client()
    result = await client.get_check(check_id, computed=True)
    return _format(result)


@mcp.tool()
async def tru8_get_result_raw(check_id: str) -> str:
    """Retrieve a previously submitted check without computed analytics.

    Returns claims, elements, evidence, and claim maps only. No _computed
    block. Smaller response payload. Use this when you will compute your
    own aggregations or only need specific fields from the raw data.

    Args:
        check_id: UUID returned by tru8_check.
    """
    client = _get_client()
    result = await client.get_check(check_id, computed=False)
    return _format(result)


def main():
    """Entry point for `python -m tru8_mcp`."""
    mcp.run()


if __name__ == "__main__":
    main()
