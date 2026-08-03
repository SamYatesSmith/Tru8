"""Count the search queries a check actually pays for.

Why this exists
---------------
``cost_constants.build_cost_telemetry`` reported ``estimated_cost_usd.search =
None`` since inception, with an honest note in its own docstring: the pipeline's
``web_search_calls`` metric is a RESULT count (raw sources reviewed), not a QUERY
count, so no per-query cost could be derived from it.

That gap mattered more than it looked. Console is GBP20 for 200 checks — 10p of
revenue per check — and on 2026-07-27 element-level retrieval took a claim from a
single synthetic query to a claim lane plus one lane per element. The COGS model
still in ``audit/cost_control_plan.md`` is dated April and assumes the old shape.
Nobody could say whether a fully-utilised subscriber was profitable, because the
largest variable cost was not measured at all.

How it works
------------
Every search provider makes exactly one HTTP request per ``_execute_search``, so
that is one billable query. Each provider records it here. A ``ContextVar`` holds
the tally, which means:

  * it survives the ``asyncio`` fan-out inside a check (contextvars propagate
    into tasks created within the context), and
  * concurrent checks in the same process cannot contaminate each other's count,
    which a module-level counter would not guarantee.

Billing units, not just queries
-------------------------------
Providers do not all bill per request. Serper charges **2 credits** when 11-100
results are requested and 1 credit for 10 or fewer — and the claim lane asks for
13 (``retrieve.CLAIM_LANE_MAX_RESULTS_PER_QUERY``), so a naive query count
understates Serper spend by nearly half. Billable units are tracked separately
from raw query counts for exactly this reason.
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Dict, Iterator, Optional

logger = logging.getLogger(__name__)

_meter: ContextVar[Optional[Dict[str, Any]]] = ContextVar(
    "tru8_search_meter", default=None
)

# Serper bills 1 credit for <=10 results and 2 for 11-100.
# https://serper.dev/pricing — re-verify before trusting the derived cost.
_SERPER_SECOND_CREDIT_THRESHOLD = 10


def _billable_units(provider: str, requested_results: int) -> int:
    """Billing units for one request to ``provider``."""
    if provider == "serper" and requested_results > _SERPER_SECOND_CREDIT_THRESHOLD:
        return 2
    return 1


@contextmanager
def meter_searches() -> Iterator[Dict[str, Any]]:
    """Collect search-query counts for the duration of one check."""
    tally: Dict[str, Any] = {"queries": {}, "billable_units": {}}
    token = _meter.set(tally)
    try:
        yield tally
    finally:
        _meter.reset(token)


def record_search(provider: str, requested_results: int) -> None:
    """Record one issued search query. No-op outside a metered context.

    Called immediately before the HTTP request, so a query is counted whether or
    not it returns usable results — the provider bills either way. Retries after
    a 429 are deliberately NOT counted again: rate-limited requests are not
    billed, and counting them would overstate spend.
    """
    tally = _meter.get()
    if tally is None:
        return  # not inside a metered check (tests, scripts, re-search) — fine
    try:
        units = _billable_units(provider, int(requested_results or 0))
        tally["queries"][provider] = tally["queries"].get(provider, 0) + 1
        tally["billable_units"][provider] = (
            tally["billable_units"].get(provider, 0) + units
        )
    except Exception:  # noqa: BLE001 — metering must never break a check
        logger.debug("[SEARCH_METER] failed to record a query", exc_info=True)


def metered(fn):
    """Meter every search a pipeline coroutine issues, and return the tally.

    Applied as a decorator so the metered region is one line rather than a
    re-indent of a large function. The tally is attached to the returned dict as
    ``search_meter``, because the caller that persists telemetry
    (``save_check_results_async``) runs AFTER the pipeline coroutine returns and
    is therefore outside the context — the counts have to ride out in the result.
    """
    import functools

    @functools.wraps(fn)
    async def wrapper(*args, **kwargs):
        with meter_searches():
            result = await fn(*args, **kwargs)
            if isinstance(result, dict):
                result["search_meter"] = snapshot()
            return result

    return wrapper


def snapshot() -> Optional[Dict[str, Any]]:
    """Current tally, or None outside a metered context."""
    tally = _meter.get()
    if tally is None:
        return None
    queries = dict(tally["queries"])
    units = dict(tally["billable_units"])
    return {
        "queries_by_provider": queries,
        "billable_units_by_provider": units,
        "total_queries": sum(queries.values()),
        "total_billable_units": sum(units.values()),
    }
