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
    TRU8_API_URL  — Optional. Default: https://api.tru8.app
"""

import json

from mcp.server.fastmcp import FastMCP

from .tools import Tru8APIClient

mcp = FastMCP(
    "tru8",
    instructions=(
        "Structured evidence research. Submit claims or URLs, retrieve evidence "
        "organized by source tier (primary/reporting/commentary) and type "
        "(data/official/news/analysis/opinion/academic), with element decomposition "
        "and relationship mapping (supports/challenges/context)."
    ),
)

_client: Tru8APIClient | None = None


def _get_client() -> Tru8APIClient:
    """Lazy-initialize the API client (reads env vars on first call)."""
    global _client
    if _client is None:
        _client = Tru8APIClient()
    return _client


def _format(data: dict) -> str:
    """Serialize API response as indented JSON for agent consumption."""
    return json.dumps(data, indent=2, default=str)


@mcp.tool()
async def tru8_check(
    claim: str,
    max_tier: str = "quick",
    max_age_hours: int | None = None,
    compact: bool = False,
) -> str:
    """Evidence research for any claim or URL.

    Returns structured evidence landscape with element decomposition and
    source classification (tier/type).

    Tiers (in fallback order):
    - lookup  (~$0.02, instant) — cached prior analysis
    - quick   (~$0.07, ~15s) — web search + heuristic classification
    - full    (~$0.15, ~90s) — 30+ sources, LLM classification, coverage recovery

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
    - _meta — execution metadata: executedTier, chargedCents, limitations

    Args:
        claim: A factual claim ("The Earth's average temperature rose 1.1°C
               since 1880") or a URL to an article.
        max_tier: Maximum tier to attempt — "lookup", "quick" (default), or "full".
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
