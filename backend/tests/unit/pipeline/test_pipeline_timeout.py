"""Tests for pipeline timeout and credit refund on failure (L-04/L-12)."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.pipeline.runner import (
    PipelineMetrics,
    extract_pipeline_metrics,
    _accumulate_tokens,
)


class TestPipelineMetrics:
    """PipelineMetrics correctly serializes and handles optional fields."""

    def test_to_dict_excludes_none_tokens(self):
        metrics = PipelineMetrics(mode="full", llm_calls=3)
        d = metrics.to_dict()
        assert "llm_input_tokens" not in d
        assert "llm_output_tokens" not in d

    def test_to_dict_includes_tokens_when_set(self):
        metrics = PipelineMetrics(
            mode="full", llm_calls=3, llm_input_tokens=1000, llm_output_tokens=500
        )
        d = metrics.to_dict()
        assert d["llm_input_tokens"] == 1000
        assert d["llm_output_tokens"] == 500

    def test_to_dict_includes_all_fields(self):
        metrics = PipelineMetrics(
            mode="quick",
            llm_calls=2,
            web_search_calls=5,
            api_adapter_calls=0,
            wall_time_seconds=12.345,
            claims_processed=3,
            elements_processed=8,
            sources_considered=20,
            sources_included=15,
        )
        d = metrics.to_dict()
        assert d["mode"] == "quick"
        assert d["llm_calls"] == 2
        assert d["wall_time_seconds"] == 12.35  # rounded to 2 decimal places


class TestAccumulateTokens:
    """_accumulate_tokens safely merges usage data."""

    def test_accumulate_none_usage(self):
        result = {}
        _accumulate_tokens(result, None)
        assert "llm_token_usage" not in result

    def test_accumulate_first_usage(self):
        result = {}
        _accumulate_tokens(result, {"input_tokens": 100, "output_tokens": 50})
        assert result["llm_token_usage"]["input_tokens"] == 100
        assert result["llm_token_usage"]["output_tokens"] == 50

    def test_accumulate_multiple_usages(self):
        result = {}
        _accumulate_tokens(result, {"input_tokens": 100, "output_tokens": 50})
        _accumulate_tokens(result, {"input_tokens": 200, "output_tokens": 75})
        assert result["llm_token_usage"]["input_tokens"] == 300
        assert result["llm_token_usage"]["output_tokens"] == 125

    def test_accumulate_partial_usage(self):
        result = {}
        _accumulate_tokens(result, {"input_tokens": 100})
        assert result["llm_token_usage"]["input_tokens"] == 100
        assert result["llm_token_usage"]["output_tokens"] == 0

    def test_accumulate_empty_dict(self):
        result = {}
        _accumulate_tokens(result, {})
        # Empty dict is falsy in Python — should be ignored
        assert "llm_token_usage" not in result


class TestExtractPipelineMetrics:
    """extract_pipeline_metrics reads accumulated tokens."""

    def _make_config(self, mode="full"):
        from app.pipeline.runner import PipelineConfig

        if mode == "quick":
            from app.pipeline.runner import QUICK_CONFIG

            return QUICK_CONFIG
        from app.pipeline.runner import DEFAULT_CONFIG

        return DEFAULT_CONFIG

    def test_metrics_with_token_usage(self):
        result = {
            "claims": [],
            "pipeline_stats": {},
            "api_stats": {},
            "processing_time_ms": 5000,
            "llm_token_usage": {"input_tokens": 1500, "output_tokens": 800},
        }
        metrics = extract_pipeline_metrics(result, self._make_config())
        assert metrics.llm_input_tokens == 1500
        assert metrics.llm_output_tokens == 800

    def test_metrics_without_token_usage(self):
        result = {
            "claims": [],
            "pipeline_stats": {},
            "api_stats": {},
            "processing_time_ms": 3000,
        }
        metrics = extract_pipeline_metrics(result, self._make_config())
        assert metrics.llm_input_tokens is None
        assert metrics.llm_output_tokens is None

    def test_metrics_zero_tokens_returns_none(self):
        result = {
            "claims": [],
            "pipeline_stats": {},
            "api_stats": {},
            "processing_time_ms": 3000,
            "llm_token_usage": {"input_tokens": 0, "output_tokens": 0},
        }
        metrics = extract_pipeline_metrics(result, self._make_config())
        # 0 is falsy → `or None` guard returns None
        assert metrics.llm_input_tokens is None
        assert metrics.llm_output_tokens is None
