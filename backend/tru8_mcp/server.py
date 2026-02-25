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
async def tru8_check_claim(text: str) -> str:
    """Ground a factual claim or article in structured, source-traced evidence.

    USE THIS WHEN you need to verify, substantiate, or challenge an assertion
    with independently sourced evidence — and you need the full analysis:
    which specific elements of the claim are supported, disputed, or unresolved,
    and exactly which sources say what.

    DO NOT USE THIS for a quick "does evidence exist?" scan — use
    tru8_quick_check instead (significantly faster, less depth).

    Pipeline (typically 60-120s): extract claims → retrieve evidence from multiple
    independent sources → decompose each claim into verifiable elements →
    map evidence to elements with relationship labels.

    Output structure:
    - claims[].claimMap.elements[] — verifiable sub-claims with state
      (supported/disputed/unresolved)
    - claims[].claimMap.elements[].evidenceRefs[] — which evidence supports,
      challenges, or provides context for each element, with reasoning
    - claims[].evidence[] — sources classified by tier (primary data /
      news reporting / commentary) and type (data/official/news/analysis/
      opinion/academic)
    - claims[].claimMap.orientationLine — mechanical summary derived from
      element states (no editorial judgment)
    - _computed — pre-computed analytics: tier/type distributions,
      corroboration groups, diagnostic values, timeline, per-claim dispositions

    For URLs with multiple claims, all extracted claims (up to 5) are
    automatically selected for analysis.

    Args:
        text: A factual claim ("The Earth's average temperature rose 1.1°C
              since 1880") or a URL to an article.
    """
    client = _get_client()
    check_id = await client.submit_check(text, mode="full")
    result = await client.get_check(check_id, computed=True)
    return _format(result)


@mcp.tool()
async def tru8_quick_check(text: str) -> str:
    """Fast evidence scan — check what sources exist before committing to deep analysis.

    USE THIS WHEN you need to triage: does credible evidence exist for this
    claim? What source types are available? Is a full investigation warranted?
    Also use when speed matters more than analytical depth.

    DO NOT USE THIS when you need element-level analysis, evidence-to-claim
    mapping, or relationship labels — use tru8_check_claim instead.

    Pipeline (typically 15-30s): extract → retrieve → filter → classify
    by tier and type. Skips element decomposition and evidence mapping.

    Output structure:
    - claims[].text — extracted claims
    - claims[].evidence[] — sources with title, URL, snippet, tier
      (primary/reporting/commentary), type (data/official/news/analysis/
      opinion/academic)
    - No claimMap, no elements, no relationship labels, no orientation line

    Args:
        text: A claim or URL to scan for available evidence.
    """
    client = _get_client()
    check_id = await client.submit_check(text, mode="snapshot")
    result = await client.get_check(check_id, computed=False)
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
        check_id: UUID returned by tru8_check_claim or tru8_quick_check.
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
        check_id: UUID returned by tru8_check_claim or tru8_quick_check.
    """
    client = _get_client()
    result = await client.get_check(check_id, computed=False)
    return _format(result)


def main():
    """Entry point for `python -m tru8_mcp`."""
    mcp.run()


if __name__ == "__main__":
    main()
