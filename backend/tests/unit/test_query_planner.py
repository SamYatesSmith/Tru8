"""
Unit tests for Query Planning Agent.

Tests the LLM-powered query planning functionality for semantic claim understanding.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock


class TestLLMQueryPlanner:
    """Test the LLMQueryPlanner class."""

    def test_get_site_filter_with_priority_sources(self):
        """Test site filter generation with LLM-provided priority sources."""
        from app.utils.query_planner import LLMQueryPlanner

        planner = LLMQueryPlanner()

        # Test with priority sources from LLM
        result = planner.get_site_filter(
            ["example.com", "authority.org", "data.gov"],
            ""  # claim_type is now unused
        )

        # Should use first 2 sources
        assert "site:example.com" in result
        assert "site:authority.org" in result
        assert "OR" in result

    def test_get_site_filter_empty_without_priority_sources(self):
        """Test site filter is empty when no priority sources provided (dynamic system)."""
        from app.utils.query_planner import LLMQueryPlanner

        planner = LLMQueryPlanner()

        # With no priority sources, should return empty (let search engine decide)
        result = planner.get_site_filter([], "any_claim_type")

        # No hardcoded defaults anymore - dynamic system relies on LLM
        assert result == ""

    def test_get_site_filter_limits_to_two_sources(self):
        """Test site filter limits to first 2 sources to keep queries short."""
        from app.utils.query_planner import LLMQueryPlanner

        planner = LLMQueryPlanner()

        # Pass more than 2 sources
        result = planner.get_site_filter(
            ["site1.com", "site2.com", "site3.com", "site4.com"],
            ""
        )

        # Should only include 2 sources
        assert result.count("site:") == 2
        assert "site:site1.com" in result
        assert "site:site2.com" in result
        assert "site:site3.com" not in result

    def test_validate_plans_normalizes_structure(self):
        """Test plan validation normalizes various response formats."""
        from app.utils.query_planner import LLMQueryPlanner

        planner = LLMQueryPlanner()

        # Test with various input formats
        plans = [
            {
                "claim_index": 0,
                "claim_type": "squad_composition",
                "priority_sources": "premierleague.com",  # String instead of list
                "queries": "Arsenal squad 2025"  # String instead of list
            },
            {
                "claim_type": "player_statistics",
                "queries": ["query1", "query2", "query3", "query4", "query5"]  # Too many queries
            }
        ]

        validated = planner._validate_plans(plans, 2)

        # Check normalization
        assert len(validated) == 2

        # First plan - string converted to list
        assert isinstance(validated[0]["priority_sources"], list)
        assert isinstance(validated[0]["queries"], list)

        # Second plan - queries limited to 4
        assert len(validated[1]["queries"]) <= 4

    def test_validate_plans_handles_missing_fields(self):
        """Test plan validation handles missing fields gracefully."""
        from app.utils.query_planner import LLMQueryPlanner

        planner = LLMQueryPlanner()

        plans = [
            {"claim_type": "match_result"},  # Missing claim_index, queries, priority_sources
        ]

        validated = planner._validate_plans(plans, 1)

        # Should fill in defaults
        assert validated[0]["claim_index"] == 0
        assert validated[0]["queries"] == []
        assert validated[0]["priority_sources"] == []

    def test_validate_plans_filters_non_dicts(self):
        """Test plan validation filters out non-dict entries."""
        from app.utils.query_planner import LLMQueryPlanner

        planner = LLMQueryPlanner()

        plans = [
            {"claim_type": "general", "queries": ["test"]},
            "invalid string entry",
            None,
            123,
            {"claim_type": "stats", "queries": ["another"]}
        ]

        validated = planner._validate_plans(plans, 5)

        # Should only have 2 valid dict entries
        assert len(validated) == 2


class TestQueryPlannerIntegration:
    """Integration tests for query planner with mocked LLM."""

    @pytest.mark.asyncio
    async def test_plan_queries_batch_success(self):
        """Test successful batch query planning."""
        from app.utils.query_planner import LLMQueryPlanner

        planner = LLMQueryPlanner()

        # Mock the httpx client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": '''{"plans": [
                        {
                            "claim_index": 0,
                            "claim_type": "squad_composition",
                            "priority_sources": ["arsenal.com", "premierleague.com"],
                            "queries": ["Arsenal squad 2025", "Viktor Gyokeres Arsenal"]
                        }
                    ]}'''
                }
            }]
        }

        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            claims = [{"text": "Arsenal has Viktor Gyokeres in their squad"}]
            result = await planner.plan_queries_batch(claims)

            assert result is not None
            assert len(result) == 1
            assert result[0]["claim_type"] == "squad_composition"
            assert len(result[0]["queries"]) == 2

    @pytest.mark.asyncio
    async def test_plan_queries_batch_no_api_key(self):
        """Test graceful handling when API key is missing."""
        from app.utils.query_planner import LLMQueryPlanner

        planner = LLMQueryPlanner()
        planner.openai_api_key = None  # Simulate missing key

        claims = [{"text": "Some claim"}]
        result = await planner.plan_queries_batch(claims)

        # Should return None when no API key
        assert result is None

    @pytest.mark.asyncio
    async def test_plan_queries_batch_empty_claims(self):
        """Test handling of empty claims list."""
        from app.utils.query_planner import LLMQueryPlanner

        planner = LLMQueryPlanner()

        result = await planner.plan_queries_batch([])

        # Should return empty list for empty input
        assert result == []

    @pytest.mark.asyncio
    async def test_plan_queries_batch_timeout_fallback(self):
        """Test fallback on timeout."""
        from app.utils.query_planner import LLMQueryPlanner
        import httpx

        planner = LLMQueryPlanner()

        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            claims = [{"text": "Test claim"}]
            result = await planner.plan_queries_batch(claims)

            # Should return None on timeout (triggering fallback)
            assert result is None


class TestQueryPlannerSingleton:
    """Test the query planner singleton."""

    def test_get_query_planner_returns_same_instance(self):
        """Test singleton pattern."""
        from app.utils.query_planner import get_query_planner

        planner1 = get_query_planner()
        planner2 = get_query_planner()

        assert planner1 is planner2


class TestDynamicFreshness:
    """Test dynamic freshness system (replaced hardcoded claim types)."""

    def test_freshness_validation_in_plans(self):
        """Test that freshness values are validated in query plans."""
        from app.utils.query_planner import LLMQueryPlanner

        planner = LLMQueryPlanner()

        # Test plans with various freshness values
        plans = [
            {"claim_index": 0, "queries": ["test"], "freshness": "pw"},  # Valid
            {"claim_index": 1, "queries": ["test"], "freshness": "invalid"},  # Invalid -> py
            {"claim_index": 2, "queries": ["test"]},  # Missing -> py
        ]

        validated = planner._validate_plans(plans, 3)

        assert validated[0]["freshness"] == "pw"
        assert validated[1]["freshness"] == "py"  # Default for invalid
        assert validated[2]["freshness"] == "py"  # Default for missing

    def test_valid_freshness_values(self):
        """Test all valid freshness values are accepted."""
        from app.utils.query_planner import LLMQueryPlanner

        planner = LLMQueryPlanner()
        valid_values = ["pd", "pw", "pm", "py", "2y"]

        for freshness in valid_values:
            plans = [{"claim_index": 0, "queries": ["test"], "freshness": freshness}]
            validated = planner._validate_plans(plans, 1)
            assert validated[0]["freshness"] == freshness

    def test_default_freshness_function(self):
        """Test get_freshness_for_claim_type returns default values."""
        from app.utils.query_planner import get_freshness_for_claim_type

        # All claim types should return the same DEFAULT_FRESHNESS now
        result = get_freshness_for_claim_type("any_type")
        assert result["brave_freshness"] == "py"
        assert result["max_age_days"] == 365

    def test_check_evidence_staleness_with_freshness(self):
        """Test evidence staleness check uses freshness parameter."""
        from app.utils.query_planner import check_evidence_staleness
        from datetime import datetime

        # Test with fresh evidence and strict freshness
        result = check_evidence_staleness(
            evidence_date="2025-12-01",
            freshness="pw",  # Past week
            reference_date=datetime(2025, 12, 2)
        )
        assert result["is_stale"] is False
        assert result["max_age_days"] == 7

        # Test with stale evidence and strict freshness
        result = check_evidence_staleness(
            evidence_date="2025-11-01",
            freshness="pw",  # Past week
            reference_date=datetime(2025, 12, 2)
        )
        assert result["is_stale"] is True

        # Test with lenient freshness
        result = check_evidence_staleness(
            evidence_date="2025-11-01",
            freshness="py",  # Past year
            reference_date=datetime(2025, 12, 2)
        )
        assert result["is_stale"] is False


class TestArticleContextIntegration:
    """Test article context is passed to query planner."""

    @pytest.mark.asyncio
    async def test_plan_queries_with_article_context(self):
        """Test query planning receives article context."""
        from app.utils.query_planner import LLMQueryPlanner
        from unittest.mock import MagicMock

        planner = LLMQueryPlanner()

        # Mock the httpx client to capture the request
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": '''{"plans": [
                        {
                            "claim_index": 0,
                            "queries": ["test query"],
                            "freshness": "pw",
                            "source_hints": "Official sources",
                            "reasoning": "Fast-changing data"
                        }
                    ]}'''
                }
            }]
        }

        captured_request = {}

        async def capture_post(*args, **kwargs):
            captured_request.update(kwargs.get("json", {}))
            return mock_response

        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post = capture_post
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            claims = [{"text": "Test claim"}]
            article_context = {
                "primary_domain": "Politics",
                "temporal_context": "December 2024 election coverage",
                "key_entities": ["Congress", "Senate"],
                "evidence_guidance": "Use official government sources"
            }

            result = await planner.plan_queries_batch(claims, article_context=article_context)

            # Verify article context was included in the prompt
            user_message = captured_request.get("messages", [{}])[-1].get("content", "")
            assert "Politics" in user_message
            assert "December 2024" in user_message
            assert "Congress" in user_message
