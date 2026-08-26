"""Per-check COGS estimation (P1 telemetry — 2026-06-15).

GROUND TRUTH is the raw token + count data captured by the pipeline and persisted
on ``Check.cost_telemetry``. The prices below are a DERIVED view used only for a
convenience ``estimated_cost_usd`` field. Because the raw data is stored, any
check's cost can be recomputed when rates change — correct a price here and every
historical check reprices, with no backfill and no migration.

As of 2026-08-25 the LLM rates are VERIFIED against vendor pages; the SEARCH
rates are still placeholders taken from list pricing rather than our invoices.
Treat an LLM figure as sound and a search figure as indicative.

TWO KNOWN LIMITATIONS (do not oversell this data):
  1. LLM tokens cover the analyzer + classifier + distiller stages only — the
     stages that expose ``get_token_usage()``. Extract, the relevance scorer, and
     the query-answer call are NOT yet accumulated, so token totals UNDERCOUNT
     real LLM spend. Wiring those is a P5b follow-up.
  2. The pipeline's ``web_search_calls`` / ``api_adapter_calls`` metrics are
     RESULT counts (raw sources reviewed / adapters returning >=1 result), NOT
     query counts. We therefore store them under honest names and DO NOT derive a
     per-query search cost from them. True per-query call counts need threading
     from retrieve.py / the search service (P5b follow-up).

VERIFY before relying on the numbers:
  - Google Gemini:  https://ai.google.dev/gemini-api/docs/pricing
  - OpenAI:         https://openai.com/api/pricing
  - Search providers (Serper/Brave/SerpAPI): their dashboards
Last set: 2026-08-25 — LLM rates verified against vendor pages; search rates
  still placeholders (see SEARCH_PRICING_USD_PER_UNIT).
"""

from typing import Any, Dict, Iterable, Optional

PRICING_VERSION = "2026-08-25-LLM-VERIFIED-SEARCH-UNVERIFIED"

# USD per 1,000,000 tokens. Keys are matched as case-insensitive substrings of
# the model name recorded in telemetry (so "gemini-2.5-flash-thinking" matches
# the "gemini-2.5-flash" entry).
#
# ✅ LLM RATES VERIFIED 2026-08-25 against vendor primary sources
# (ai.google.dev/gemini-api/docs/pricing, developers.openai.com/api/docs/pricing).
# They had been carrying an UNVERIFIED stamp since 2026-06-15 while being exactly
# right — which is its own hazard: an accurate number nobody trusts gets
# re-derived by hand every time it is needed. SEARCH rates below remain
# genuinely unverified; they are the ones to treat with suspicion.
LLM_PRICING_USD_PER_1M: Dict[str, Dict[str, float]] = {
    # --- Gemini 2.5 — RETIRES 16 OCTOBER 2026 ---------------------------------
    "gemini-2.5-flash-lite": {"input": 0.10, "output": 0.40},
    "gemini-2.5-flash": {"input": 0.30, "output": 2.50},
    "gemini-2.5-pro": {"input": 1.25, "output": 10.00},
    # --- Gemini 3.x — migration candidates ------------------------------------
    # ⚠️ Google DELETED the price point we were on. There is no cheap Gemini 3
    # tier: the nearest equivalent to 2.5-flash-lite costs 3x input / 6x output.
    # Cost rises on every available migration path. Longest key wins the
    # substring match below, so "gemini-3.5-flash-lite" is matched before
    # "gemini-3.5-flash" would be.
    "gemini-3.5-flash-lite": {"input": 0.30, "output": 2.50},
    "gemini-3.6-flash": {"input": 0.75, "output": 3.75},
    "gemini-3.7-flash": {"input": 0.75, "output": 3.75},
    # --- OpenAI ---------------------------------------------------------------
    "gpt-5.6-luna": {"input": 0.20, "output": 1.20},
    "gpt-5.4-mini": {"input": 0.75, "output": 4.50},
    "gpt-5-mini": {"input": 0.25, "output": 2.00},
    "gpt-5-nano": {"input": 0.05, "output": 0.40},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4o": {"input": 2.50, "output": 10.00},
}

# ⚠️ 3.6/3.7-flash are on INTRODUCTORY pricing that ENDS 31 DECEMBER 2026.
# From 1 January 2027 both DOUBLE to $1.50 input / $7.50 output. If either is in
# production on that date, this table starts understating cost by 2x overnight
# and nothing will fail — the estimate simply goes quiet and wrong.
GEMINI3_FLASH_STANDARD_FROM_2027: Dict[str, Dict[str, float]] = {
    "gemini-3.6-flash": {"input": 1.50, "output": 7.50},
    "gemini-3.7-flash": {"input": 1.50, "output": 7.50},
}
_DEFAULT_LLM = "gemini-2.5-flash-lite"

# USD per BILLABLE UNIT, per search provider. A "unit" is what the provider
# actually charges for, which is not always one request: Serper bills 2 credits
# when 11-100 results are requested, and the claim lane asks for 13. See
# app/core/search_meter.py, which does that conversion.
#
# ⚠️ SET THESE FROM YOUR OWN INVOICES. Serper's list price runs from $1.00 per
# 1,000 credits at entry volume down to $0.30 at the top tier, so the same
# pipeline can be margin-positive or margin-negative on the SAME query count
# depending only on which pack was bought. The entry rate is used below because
# assuming the volume discount would flatter the estimate, and a cost model
# should fail pessimistic.
#   Serper:  https://serper.dev/pricing
#   Brave:   https://brave.com/search/api/
#   SerpAPI: https://serpapi.com/pricing
SEARCH_PRICING_USD_PER_UNIT: Dict[str, float] = {
    "serper": 0.001,  # $1.00 / 1,000 credits (entry tier)
    "brave": 0.005,  # $5.00 / 1,000 queries (Data for Search, base paid tier)
    "serpapi": 0.015,  # $75 / 5,000 searches
}
_DEFAULT_SEARCH_UNIT_USD = 0.001


def estimate_search_cost_usd(meter: Optional[Dict[str, Any]]) -> Optional[float]:
    """Search spend for one check, from measured billable units.

    Returns None when the check predates metering, so an un-instrumented check is
    reported as unknown rather than as free — a silent zero here would read as
    "search is costless", which is the opposite of true.
    """
    if not isinstance(meter, dict):
        return None
    units = meter.get("billable_units_by_provider")
    if not isinstance(units, dict):
        return None

    total = 0.0
    for provider, count in units.items():
        rate = SEARCH_PRICING_USD_PER_UNIT.get(provider, _DEFAULT_SEARCH_UNIT_USD)
        try:
            total += int(count) * rate
        except (TypeError, ValueError):
            continue
    return round(total, 6)


def _rate(model: Optional[str]) -> Dict[str, float]:
    """Resolve a model name to a pricing row by case-insensitive substring match."""
    if model:
        m = model.lower()
        # Longest key first so "gemini-2.5-flash-lite" wins over "gemini-2.5-flash".
        for key in sorted(LLM_PRICING_USD_PER_1M, key=len, reverse=True):
            if key in m:
                return LLM_PRICING_USD_PER_1M[key]
    return LLM_PRICING_USD_PER_1M[_DEFAULT_LLM]


def _cost(
    input_tokens: int,
    output_tokens: int,
    model: Optional[str],
    thinking_tokens: int = 0,
) -> float:
    # Google bills thought tokens (thoughtsTokenCount) at the output-token rate;
    # they are reported separately from candidatesTokenCount, never inside it.
    r = _rate(model)
    return (
        (input_tokens / 1_000_000) * r["input"]
        + ((output_tokens + thinking_tokens) / 1_000_000) * r["output"]
    )


def _priciest(models: Iterable[str]) -> Optional[str]:
    """Pick the most expensive model among those used in a stage (conservative)."""
    best: Optional[str] = None
    best_out = -1.0
    for model in models:
        out = _rate(model)["output"]
        if out > best_out:
            best_out, best = out, model
    return best


def estimate_llm_cost_usd(
    input_tokens: int,
    output_tokens: int,
    by_stage: Optional[Dict[str, Any]] = None,
    thinking_tokens: int = 0,
) -> float:
    """Model-aware LLM cost estimate.

    When per-stage data is available, price each stage at the priciest model it
    used (so a Flash-thinking mapping stage isn't under-counted at Flash-Lite
    rates), then cost any residual tokens not attributed to a stage at the
    default rate. Falls back to default-model pricing on the totals.
    Thinking (reasoning) tokens are priced at the output rate.
    """
    if not by_stage or not isinstance(by_stage, dict):
        return round(
            _cost(input_tokens, output_tokens, _DEFAULT_LLM, thinking_tokens), 6
        )

    cost = 0.0
    seen_in = seen_out = seen_think = 0
    for stage in by_stage.values():
        if not isinstance(stage, dict):
            continue
        si = int(stage.get("input_tokens", 0) or 0)
        so = int(stage.get("output_tokens", 0) or 0)
        st = int(stage.get("thinking_tokens", 0) or 0)
        models = stage.get("models_used") or {}
        model = (
            _priciest(models.values())
            if isinstance(models, dict) and models
            else _DEFAULT_LLM
        )
        cost += _cost(si, so, model, st)
        seen_in += si
        seen_out += so
        seen_think += st

    rem_in = max(0, int(input_tokens) - seen_in)
    rem_out = max(0, int(output_tokens) - seen_out)
    rem_think = max(0, int(thinking_tokens) - seen_think)
    if rem_in or rem_out or rem_think:
        cost += _cost(rem_in, rem_out, _DEFAULT_LLM, rem_think)
    return round(cost, 6)


def build_cost_telemetry(results: Dict[str, Any]) -> Dict[str, Any]:
    """Assemble the per-check COGS telemetry blob from a pipeline ``results`` dict.

    Pure function of ``results`` — safe to call at save time. Raw tokens/counts
    are the durable record; ``estimated_cost_usd`` is a convenience view.
    """
    tok = results.get("llm_token_usage") or {}
    in_tok = int(tok.get("input_tokens", 0) or 0)
    out_tok = int(tok.get("output_tokens", 0) or 0)
    think_tok = int(tok.get("thinking_tokens", 0) or 0)
    by_stage = results.get("llm_usage_by_stage")

    metrics = results.get("pipeline_metrics") or {}
    llm_calls = int(metrics.get("llm_calls", 0) or 0)
    # Upstream metrics mislabel these: `web_search_calls` is a RESULT count (raw
    # sources reviewed) and `api_adapter_calls` is the number of adapters that
    # returned >=1 result — NOT query counts. Store under honest names; do not
    # derive a per-query search cost from them (limitation #2 in module docstring).
    web_results_reviewed = int(metrics.get("web_search_calls", 0) or 0)
    api_adapters_with_results = int(metrics.get("api_adapter_calls", 0) or 0)

    # PARTIAL — captured LLM stages only (limitation #1 in module docstring).
    llm_cost = estimate_llm_cost_usd(in_tok, out_tok, by_stage, thinking_tokens=think_tok)

    # Measured search spend (2026-08-03). None for checks that predate metering.
    search_meter = results.get("search_meter")
    search_cost = estimate_search_cost_usd(search_meter)

    # Per-stage wall-clock (seconds) — measured every run by the pipeline
    # (runner.py stage_timings) but previously discarded at save time.
    # Rounded to 2dp; non-numeric values filtered defensively; None when the
    # results dict carries no pipeline_stats (e.g. legacy callers).
    raw_stage_timings = (results.get("pipeline_stats") or {}).get("stage_timings")
    if isinstance(raw_stage_timings, dict):
        stage_timings_s: Optional[Dict[str, float]] = {
            k: round(v, 2)
            for k, v in raw_stage_timings.items()
            if isinstance(v, (int, float)) and not isinstance(v, bool)
        }
    else:
        stage_timings_s = None

    return {
        "pricing_version": PRICING_VERSION,
        "llm": {
            "input_tokens": in_tok,
            "output_tokens": out_tok,
            "thinking_tokens": think_tok,
            "calls": llm_calls,
            "by_stage": by_stage,
            "coverage": "analyzer+classifier+distiller only; excludes extract/relevance-scorer/query",
        },
        "search": {
            "web_results_reviewed": web_results_reviewed,
            "api_adapters_with_results": api_adapters_with_results,
            "provider_status": results.get("provider_status"),
            # Measured query counts (2026-08-03). The two fields above remain
            # RESULT counts and are kept for continuity with historical rows;
            # everything cost-bearing now comes from the meter.
            "queries_by_provider": (search_meter or {}).get("queries_by_provider"),
            "billable_units_by_provider": (search_meter or {}).get(
                "billable_units_by_provider"
            ),
            "total_queries": (search_meter or {}).get("total_queries"),
            "total_billable_units": (search_meter or {}).get("total_billable_units"),
            "note": (
                "queries/billable units are MEASURED per check; a billable unit is "
                "what the provider charges for (Serper bills 2 credits for 11-100 "
                "results). web_results_reviewed remains a RESULT count, kept for "
                "continuity with pre-2026-08-03 rows."
            ),
        },
        "timing": {
            "wall_time_ms": int(results.get("processing_time_ms", 0) or 0),
            "stage_timings_s": stage_timings_s,
        },
        "estimated_cost_usd": {
            "llm_partial": llm_cost,
            "search": search_cost,
            # The number that actually decides whether a Console subscriber is
            # profitable. Console is GBP20 for 200 checks = 10p (~$0.128) of
            # revenue per check, so compare against that. None when either half
            # is unknown, rather than a misleading partial sum.
            "total_partial": (
                round(llm_cost + search_cost, 6) if search_cost is not None else None
            ),
            "note": (
                "ESTIMATE — raw token/count data is ground truth. Search cost is "
                "now MEASURED from per-provider billable units, priced at ENTRY "
                "tier (pessimistic by design; volume discounts would flatter it). "
                "LLM cost remains PARTIAL — captured stages only, excluding "
                "extract, the relevance scorer and the query stage — so "
                "total_partial is a FLOOR, not a full COGS figure. Prices "
                f"{PRICING_VERSION}; reset them from real invoices."
            ),
        },
    }
