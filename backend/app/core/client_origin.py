"""Resolve the calling client from the `X-Tru8-Client` request header.

First-party clients (the MCP package, future CLI/SDKs) send a header of the
form ``<name>/<version>`` (e.g. ``mcp/1.0.1``). We persist the normalised name
on ``Check.client`` so usage can be attributed per client without overloading
``initiated_via`` (which has an exact-match consumer in services/consensus.py).

Returns None when the header is absent or unrecognised — i.e. ordinary
dashboard/API traffic — so the column stays NULL for everything pre-existing.
"""

from typing import Optional

from fastapi import Request

# Cap to keep a hostile/oversized header out of the column.
_MAX_TAG_LEN = 32
_ALLOWED = set("abcdefghijklmnopqrstuvwxyz0123456789-_")


def resolve_client(request: Optional[Request]) -> Optional[str]:
    """Extract a normalised client tag from the X-Tru8-Client header.

    ``"mcp/1.0.1"`` -> ``"mcp"``. Returns None if the header is missing,
    empty, or contains nothing usable after normalisation.
    """
    if request is None:
        return None

    raw = request.headers.get("X-Tru8-Client")
    if not raw:
        return None

    # Take the name before the version separator, lowercase, keep safe chars.
    name = raw.split("/", 1)[0].strip().lower()
    tag = "".join(c for c in name if c in _ALLOWED)[:_MAX_TAG_LEN]
    return tag or None
