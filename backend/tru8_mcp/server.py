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
    """Submit text or a URL for full evidence research.

    Runs the complete Tru8 pipeline: claim extraction, multi-source evidence
    retrieval, element decomposition, and evidence-to-element mapping with
    relationship labels (supports/challenges/context).

    Processing takes 60-120 seconds. Returns the result with pre-computed
    analytics including tier/type distributions, corroboration groups,
    diagnostic values, timeline, and per-claim dispositions.

    For URLs with multiple claims, all extracted claims (up to 5) are
    automatically selected for analysis.

    Args:
        text: A claim ("The Earth's average temperature rose 1.1°C since 1880")
              or a URL (https://example.com/article).
    """
    client = _get_client()
    check_id = await client.submit_check(text, mode="full")
    result = await client.get_check(check_id, computed=True)
    return _format(result)


@mcp.tool()
async def tru8_quick_check(text: str) -> str:
    """Quick evidence snapshot — fast scan without deep analysis.

    Runs a reduced pipeline (12-18 seconds): claim extraction and evidence
    retrieval only. Skips element decomposition and evidence mapping.

    Returns claims with raw evidence (title, URL, snippet, tier, type) but
    no claim maps, elements, or relationship labels. Use when you need a
    rapid survey of available evidence.

    Args:
        text: A claim or URL to scan for evidence.
    """
    client = _get_client()
    check_id = await client.submit_check(text, mode="snapshot")
    result = await client.get_check(check_id, computed=False)
    return _format(result)


@mcp.tool()
async def tru8_get_result(check_id: str) -> str:
    """Retrieve a completed check with pre-computed analytics.

    Returns claims, elements, evidence, claim maps, and a _computed block:
    tier/type distributions, corroboration groups, diagnostic values,
    timeline analysis, element state summaries, per-claim dispositions.

    Args:
        check_id: The check ID from a previous tru8_check_claim or
                  tru8_quick_check call.
    """
    client = _get_client()
    result = await client.get_check(check_id, computed=True)
    return _format(result)


@mcp.tool()
async def tru8_get_result_raw(check_id: str) -> str:
    """Retrieve raw check data without computed analytics.

    Returns claims, elements, evidence, and claim maps. No _computed block.
    Use when you need the raw data for your own analysis or want a smaller
    response payload.

    Args:
        check_id: The check ID from a previous tru8_check_claim or
                  tru8_quick_check call.
    """
    client = _get_client()
    result = await client.get_check(check_id, computed=False)
    return _format(result)


def main():
    """Entry point for `python -m tru8_mcp`."""
    mcp.run()


if __name__ == "__main__":
    main()
