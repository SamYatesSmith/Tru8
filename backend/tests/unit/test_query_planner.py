"""
Unit tests for Query Planning Agent.

Tests the LLM-powered query planning functionality for semantic claim understanding.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock


class TestLLMQueryPlanner:
    """Test the LLMQueryPlanner class."""

    def test_get_site_filter_with_priority_sources(self):
        """Test site filter generation with priority sources."""
        from app.utils.query_planner import LLMQueryPlanner

        planner = LLMQueryPlanner()

        # Test with priority sources
        result = planner.get_site_filter(
            ["premierleague.com", "arsenal.com", "transfermarkt.com"],
            "squad_composition"
        )

        # Should use first 2 sources
        assert "site:premierleague.com" in result
        assert "site:arsenal.com" in result
        assert "OR" in result

    def test_get_site_filter_fallback_to_defaults(self):
        """Test site filter falls back to default sources by claim type."""
        from app.utils.query_planner import LLMQueryPlanner

        planner = LLMQueryPlanner()

        # Test with no priority sources - should use defaults
        result = planner.get_site_filter([], "player_statistics")

        # Should use default sources for player_statistics
        assert "site:fbref.com" in result or "site:transfermarkt.com" in result

    def test_get_site_filter_empty_for_general(self):
        """Test site filter is empty for general claim type."""
        from app.utils.query_planner import LLMQueryPlanner

        planner = LLMQueryPlanner()

        # General claims should have no site filter
        result = planner.get_site_filter([], "general")

        assert result == ""

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


class TestClaimTypes:
    """Test claim type detection and routing."""

    @pytest.fixture
    def sample_sports_claims(self):
        """Sample sports claims for testing."""
        return [
            {"text": "Arsenal has Viktor Gyokeres in their squad for 2025"},
            {"text": "Bukayo Saka scored 15 goals this season"},
            {"text": "Kai Havertz contract expires in 2027"},
            {"text": "Manchester United interested in signing Marcus Rashford"},
            {"text": "Arsenal beat Chelsea 3-1 in the Premier League"},
            {"text": "Liverpool top the Premier League table with 45 points"}
        ]

    def test_claim_type_mapping(self):
        """Test that claim types map to correct source priorities."""
        from app.utils.query_planner import LLMQueryPlanner

        planner = LLMQueryPlanner()

        # Verify default source mappings
        assert planner.get_site_filter([], "squad_composition") != ""
        assert planner.get_site_filter([], "player_statistics") != ""
        assert planner.get_site_filter([], "contract_info") != ""
        assert planner.get_site_filter([], "transfer_rumor") != ""
        assert planner.get_site_filter([], "match_result") != ""
        assert planner.get_site_filter([], "league_standing") != ""
        assert planner.get_site_filter([], "general") == ""
