"""Unit tests for per-check COGS telemetry (P1).

Pins the pricing-critical logic that feeds the P5 decision: model-aware costing,
substring rate matching, residual-token accounting, honest field naming, and
graceful handling of missing/malformed pipeline results.
"""

import pytest

from app.core.cost_constants import (
    build_cost_telemetry,
    estimate_llm_cost_usd,
    _rate,
    _priciest,
    _DEFAULT_LLM,
    LLM_PRICING_USD_PER_1M,
)


def _results():
    return {
        "llm_token_usage": {"input_tokens": 110_000, "output_tokens": 18_000},
        "llm_usage_by_stage": {
            "analyzer": {
                "input_tokens": 80_000,
                "output_tokens": 15_000,
                "models_used": {"map": "gemini-2.5-flash-thinking"},
            },
            "classifier": {
                "input_tokens": 30_000,
                "output_tokens": 3_000,
                "models_used": {"classify": "gemini-2.5-flash-lite"},
            },
        },
        "pipeline_metrics": {
            "llm_calls": 8,
            "web_search_calls": 30,  # upstream RESULT count, not query count
            "api_adapter_calls": 5,
        },
        "provider_status": {"Serper": {"status": "ok", "count": 30}},
        "processing_time_ms": 42_000,
    }


# --- _rate substring matching --------------------------------------------------


def test_rate_prefers_longest_match():
    # flash-lite must NOT collide with the shorter "flash" entry
    assert _rate("gemini-2.5-flash-lite")["output"] == 0.40
    assert _rate("gemini-2.5-flash")["output"] == 2.50
    # an unknown flash variant matches the "flash" family, not lite
    assert _rate("gemini-2.5-flash-thinking")["output"] == 2.50


def test_rate_unknown_and_none_fall_back_to_default():
    default = LLM_PRICING_USD_PER_1M[_DEFAULT_LLM]
    assert _rate("some-unknown-model") == default
    assert _rate(None) == default
    assert _rate("") == default


def test_priciest_picks_highest_output_rate_and_handles_empty():
    assert _priciest(["gemini-2.5-flash-lite", "gemini-2.5-pro"]) == "gemini-2.5-pro"
    assert _priciest([]) is None


# --- estimate_llm_cost_usd -----------------------------------------------------


def test_model_aware_cost_no_residual():
    # totals == sum(by_stage) → residual branch contributes nothing
    by_stage = _results()["llm_usage_by_stage"]
    cost = estimate_llm_cost_usd(110_000, 18_000, by_stage)
    # analyzer @ flash (0.30/2.50) + classifier @ flash-lite (0.10/0.40)
    expected = (80_000 * 0.30 + 15_000 * 2.50) / 1e6 + (
        30_000 * 0.10 + 3_000 * 0.40
    ) / 1e6
    assert cost == pytest.approx(round(expected, 6))


def test_residual_tokens_costed_at_default():
    # totals exceed by_stage sums → 10k in / 2k out residual at default (flash-lite)
    by_stage = _results()["llm_usage_by_stage"]
    cost = estimate_llm_cost_usd(120_000, 20_000, by_stage)
    base = (80_000 * 0.30 + 15_000 * 2.50) / 1e6 + (30_000 * 0.10 + 3_000 * 0.40) / 1e6
    residual = (10_000 * 0.10 + 2_000 * 0.40) / 1e6
    assert cost == pytest.approx(round(base + residual, 6))


def test_no_by_stage_uses_default_model():
    cost = estimate_llm_cost_usd(100_000, 10_000, None)
    expected = (100_000 * 0.10 + 10_000 * 0.40) / 1e6
    assert cost == pytest.approx(round(expected, 6))


# --- build_cost_telemetry ------------------------------------------------------


def test_build_basic_shape_and_honest_naming():
    out = build_cost_telemetry(_results())
    assert out["llm"]["input_tokens"] == 110_000
    assert out["llm"]["output_tokens"] == 18_000
    assert "coverage" in out["llm"]
    # M1 fix: result-counts under honest names; NO "call count" keys, NO per-query cost
    assert out["search"]["web_results_reviewed"] == 30
    assert out["search"]["api_adapters_with_results"] == 5
    assert "web_search_calls" not in out["search"]
    assert "api_adapter_calls" not in out["search"]
    assert out["estimated_cost_usd"]["search"] is None
    assert "llm_partial" in out["estimated_cost_usd"]
    assert out["timing"]["wall_time_ms"] == 42_000


def test_build_empty_results_is_safe():
    out = build_cost_telemetry({})
    assert out["llm"]["input_tokens"] == 0
    assert out["llm"]["output_tokens"] == 0
    assert out["search"]["web_results_reviewed"] == 0
    assert out["estimated_cost_usd"]["llm_partial"] == 0.0
    assert out["estimated_cost_usd"]["search"] is None


def test_build_tolerates_malformed_inputs():
    # by_stage as a list, models missing, None token values — must not raise
    bad = {
        "llm_token_usage": {"input_tokens": None, "output_tokens": None},
        "llm_usage_by_stage": ["not", "a", "dict"],
        "pipeline_metrics": {"web_search_calls": None},
    }
    out = build_cost_telemetry(bad)
    assert out["llm"]["input_tokens"] == 0
    assert out["search"]["web_results_reviewed"] == 0
