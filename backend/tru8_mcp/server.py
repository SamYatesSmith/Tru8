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
from importlib.metadata import PackageNotFoundError, version as _package_version
from typing import Annotated, Optional

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import Field

from . import __version__
from .tools import Tru8APIClient

# Icon reached mcp.types with the 2025-11-25 spec; the floor we support (1.12)
# predates it. Import defensively rather than raising the floor further — an
# icon in serverInfo is a nicety, and the registries that matter carry their
# own.
try:  # pragma: no cover - exercised by whichever SDK the caller installed
    from mcp.types import Icon
except ImportError:
    Icon = None

mcp = FastMCP(
    "tru8",
    instructions=(
        "Structured evidence research. Submit a factual claim or article URL. "
        "Evidence is organised by source tier (primary/reporting/commentary) "
        "and type (data/official/news/analysis/opinion/academic), with element "
        "decomposition and relationship mapping (supports/challenges/context)."
    ),
)

# serverInfo.version — stated, not inherited (2026-08-05).
#
# FastMCP takes no `version` argument and the low-level Server defaults it to
# None, at which point the SDK reports ITS OWN version during initialize. So
# Smithery's capability scan advertised "name: tru8, version: 1.12.4" — the mcp
# library's version — on a listing where readers take it for ours.
# The installed distribution is authoritative for stdio users; the module
# constant covers the hosted transport, where the API imports this package from
# the source tree and no distribution is installed.
try:
    _SERVER_VERSION = _package_version("tru8-mcp")
except PackageNotFoundError:
    _SERVER_VERSION = __version__

mcp._mcp_server.version = _SERVER_VERSION

# serverInfo.websiteUrl + icons — the 2025-11-25 spec's own channel for "where
# does this server come from, what does it look like" (2026-08-06).
#
# Assignment, not a constructor argument, for the same reason `version` is: the
# low-level Server gained these fields after the floor we support, so on an
# older SDK these are inert attributes nobody reads, and on a current one they
# reach the client in the initialize response. Neither case raises.
#
# This does NOT feed Smithery's metadata score — that reads its own registry
# record, set via their API. It serves every other client and registry that
# reads what the server says about itself.
mcp._mcp_server.website_url = "https://www.trueight.com/developers"
if Icon is not None:
    mcp._mcp_server.icons = [
        Icon(
            src="https://www.trueight.com/apple-touch-icon.png",
            mimeType="image/png",
            sizes=["180x180"],
        )
    ]


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


@mcp.tool(
    annotations=ToolAnnotations(
        title="Evidence research",
        # Honest, not flattering. This tool creates a check and spends the
        # caller's credits, so a client that hides confirmation for read-only
        # tools must NOT hide it for this one. Repeating a call can charge
        # again, hence not idempotent; it searches the live web, hence open
        # world; it destroys nothing.
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=True,
    )
)
async def tru8_check(
    claim: Annotated[
        str,
        Field(
            description=(
                "A factual claim (\"The Earth's average temperature rose 1.1°C "
                'since 1880") or an article URL (https://example.com/article). '
                "URLs are auto-detected and the pipeline extracts claims from "
                "the page content."
            )
        ),
    ],
    max_tier: Annotated[
        str,
        Field(
            description=(
                'Maximum tier to attempt — "lookup", "consensus", "quick" or '
                '"full" (default). A CEILING, not a floor: cached and consensus '
                "hits still return instantly at their own lower price, so the "
                "default costs ~£0.15 only for claims never researched before. "
                'Set "quick" to cap spend at ~£0.07, accepting web-search-only '
                "sourcing and heuristic classification (see _meta.limitations)."
            )
        ),
    ] = "full",
    max_age_hours: Annotated[
        Optional[int],
        Field(
            description=(
                "Skip cache hits older than this many hours. Stale lookup hits "
                "are discarded and the pipeline re-runs at the next tier up to "
                "max_tier. 0 means never serve a cached result."
            )
        ),
    ] = None,
    compact: Annotated[
        bool,
        Field(
            description=(
                "If true, strip the full evidence arrays and computed analytics "
                "from the response, leaving claims and claim maps. Smaller "
                "payload for agents that only need orientation."
            )
        ),
    ] = False,
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

    Per-argument guidance lives on the parameters themselves (see the
    Annotated/Field declarations above), which is where a client can actually
    read it — a docstring "Args:" block never reaches the tool's inputSchema.
    """
    client = _get_client()
    result = await client.submit_with_fallback(
        claim,
        max_tier=max_tier,
        max_age_hours=max_age_hours,
        compact=compact,
    )
    return _format(result)


@mcp.tool(
    annotations=ToolAnnotations(
        title="Get result (with analytics)",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    )
)
async def tru8_get_result(
    check_id: Annotated[
        str,
        Field(
            description=(
                "The check UUID returned by tru8_check. Retrieval is free and "
                "limited to your own checks; a check still running returns its "
                "status rather than a result, so this is also the poll call."
            )
        ),
    ],
) -> str:
    """Retrieve a previously submitted check with pre-computed analytics.

    Returns the full result including a _computed block with tier/type
    distributions, corroboration groups, diagnostic values, timeline
    analysis, element state summaries, and per-claim dispositions.

    Use this over tru8_get_result_raw when you want structured analytics
    ready for summarisation or comparison without post-processing.
    """
    client = _get_client()
    result = await client.get_check(check_id, computed=True)
    return _format(result)


@mcp.tool(
    annotations=ToolAnnotations(
        title="Get result (raw)",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    )
)
async def tru8_get_result_raw(
    check_id: Annotated[
        str,
        Field(
            description=(
                "The check UUID returned by tru8_check. Same retrieval as "
                "tru8_get_result, without the computed analytics block."
            )
        ),
    ],
) -> str:
    """Retrieve a previously submitted check without computed analytics.

    Returns claims, elements, evidence, and claim maps only. No _computed
    block. Smaller response payload. Use this when you will compute your
    own aggregations or only need specific fields from the raw data.
    """
    client = _get_client()
    result = await client.get_check(check_id, computed=False)
    return _format(result)


def main():
    """Entry point for `python -m tru8_mcp`."""
    mcp.run()


if __name__ == "__main__":
    main()
