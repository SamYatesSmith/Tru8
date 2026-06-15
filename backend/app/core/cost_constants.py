"""Per-check COGS estimation (P1 telemetry — 2026-06-15).

GROUND TRUTH is the raw token + count data captured by the pipeline and persisted
on ``Check.cost_telemetry``. The prices below are a DERIVED view used only for a
convenience ``estimated_cost_usd`` field. They are UNVERIFIED placeholders —
because the raw data is stored, any check's cost can be recomputed once real rates
are confirmed. Do NOT treat the estimate as authoritative for the P5 pricing
decision; treat the raw data as the input and re-derive from verified rates.

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
Last set: 2026-06-15 (placeholders).
"""

from typing import Any, Dict, Iterable, Optional

PRICING_VERSION = "2026-06-15-UNVERIFIED"

# USD per 1,000,000 tokens. Keys are matched as case-insensitive substrings of
# the model name recorded in telemetry (so "gemini-2.5-flash-thinking" matches
# the "gemini-2.5-flash" entry). UNVERIFIED — confirm against official pricing.
LLM_PRICING_USD_PER_1M: Dict[str, Dict[str, float]] = {
    "gemini-2.5-flash-lite": {"input": 0.10, "output": 0.40},
    "gemini-2.5-flash": {"input": 0.30, "output": 2.50},
    "gemini-2.5-pro": {"input": 1.25, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4o": {"input": 2.50, "output": 10.00},
}
_DEFAULT_LLM = "gemini-2.5-flash-lite"


def _rate(model: Optional[str]) -> Dict[str, float]:
    """Resolve a model name to a pricing row by case-insensitive substring match."""
    if model:
        m = model.lower()
        # Longest key first so "gemini-2.5-flash-lite" wins over "gemini-2.5-flash".
        for key in sorted(LLM_PRICING_USD_PER_1M, key=len, reverse=True):
            if key in m:
                return LLM_PRICING_USD_PER_1M[key]
    return LLM_PRICING_USD_PER_1M[_DEFAULT_LLM]


def _cost(input_tokens: int, output_tokens: int, model: Optional[str]) -> float:
    r = _rate(model)
    return (input_tokens / 1_000_000) * r["input"] + (output_tokens / 1_000_000) * r[
        "output"
    ]


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
) -> float:
    """Model-aware LLM cost estimate.

    When per-stage data is available, price each stage at the priciest model it
    used (so a Flash-thinking mapping stage isn't under-counted at Flash-Lite
    rates), then cost any residual tokens not attributed to a stage at the
    default rate. Falls back to default-model pricing on the totals.
    """
    if not by_stage or not isinstance(by_stage, dict):
        return round(_cost(input_tokens, output_tokens, _DEFAULT_LLM), 6)

    cost = 0.0
    seen_in = seen_out = 0
    for stage in by_stage.values():
        if not isinstance(stage, dict):
            continue
        si = int(stage.get("input_tokens", 0) or 0)
        so = int(stage.get("output_tokens", 0) or 0)
        models = stage.get("models_used") or {}
        model = (
            _priciest(models.values())
            if isinstance(models, dict) and models
            else _DEFAULT_LLM
        )
        cost += _cost(si, so, model)
        seen_in += si
        seen_out += so

    rem_in = max(0, int(input_tokens) - seen_in)
    rem_out = max(0, int(output_tokens) - seen_out)
    if rem_in or rem_out:
        cost += _cost(rem_in, rem_out, _DEFAULT_LLM)
    return round(cost, 6)


def build_cost_telemetry(results: Dict[str, Any]) -> Dict[str, Any]:
    """Assemble the per-check COGS telemetry blob from a pipeline ``results`` dict.

    Pure function of ``results`` — safe to call at save time. Raw tokens/counts
    are the durable record; ``estimated_cost_usd`` is a convenience view.
    """
    tok = results.get("llm_token_usage") or {}
    in_tok = int(tok.get("input_tokens", 0) or 0)
    out_tok = int(tok.get("output_tokens", 0) or 0)
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
    llm_cost = estimate_llm_cost_usd(in_tok, out_tok, by_stage)

    return {
        "pricing_version": PRICING_VERSION,
        "llm": {
            "input_tokens": in_tok,
            "output_tokens": out_tok,
            "calls": llm_calls,
            "by_stage": by_stage,
            "coverage": "analyzer+classifier+distiller only; excludes extract/relevance-scorer/query",
        },
        "search": {
            "web_results_reviewed": web_results_reviewed,
            "api_adapters_with_results": api_adapters_with_results,
            "provider_status": results.get("provider_status"),
            "note": "result counts, NOT query counts — true per-query call counts not yet instrumented",
        },
        "timing": {"wall_time_ms": int(results.get("processing_time_ms", 0) or 0)},
        "estimated_cost_usd": {
            "llm_partial": llm_cost,
            "search": None,  # not computable without true query counts
            "note": (
                "ESTIMATE — raw token/count data is ground truth. LLM cost is "
                "PARTIAL (captured stages only); search cost omitted (no query "
                f"counts). Prices {PRICING_VERSION}; recompute when rates + full "
                "instrumentation land."
            ),
        },
    }
