"""Tests for quick pipeline mode configuration (L-04)."""

import pytest

from app.pipeline.runner import DEFAULT_CONFIG, QUICK_CONFIG, PipelineConfig


class TestPipelineConfig:
    """PipelineConfig correctly reduces stages for quick mode."""

    def test_quick_mode_name(self):
        assert QUICK_CONFIG.mode == "quick"

    def test_full_mode_name(self):
        assert DEFAULT_CONFIG.mode == "full"

    def test_quick_disables_llm_classifier(self):
        assert QUICK_CONFIG.enable_llm_classifier is False

    def test_full_enables_llm_classifier(self):
        assert DEFAULT_CONFIG.enable_llm_classifier is True

    def test_quick_disables_factcheck(self):
        assert QUICK_CONFIG.enable_factcheck_lookup is False

    def test_quick_disables_api_retrieval(self):
        assert QUICK_CONFIG.enable_api_adapters is False

    def test_quick_disables_llm_relevance_scorer(self):
        assert QUICK_CONFIG.enable_llm_relevance_scorer is False

    def test_quick_disables_coverage_recovery(self):
        assert QUICK_CONFIG.enable_coverage_recovery is False

    def test_quick_disables_query_answering(self):
        assert QUICK_CONFIG.enable_query_answering is False

    def test_quick_has_lower_wall_time(self):
        assert QUICK_CONFIG.max_wall_time_seconds < DEFAULT_CONFIG.max_wall_time_seconds

    def test_full_enables_all_stages(self):
        assert DEFAULT_CONFIG.enable_llm_classifier is True
        assert DEFAULT_CONFIG.enable_factcheck_lookup is True
        assert DEFAULT_CONFIG.enable_api_adapters is True
        assert DEFAULT_CONFIG.enable_llm_relevance_scorer is True

    def test_quick_fewer_queries_per_element(self):
        assert (
            QUICK_CONFIG.max_queries_per_element
            <= DEFAULT_CONFIG.max_queries_per_element
        )
