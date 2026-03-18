"""
Unit Tests for Sports API Adapters

Tests for the 2 sports adapters:
- TransfermarktAdapter: Historical player/club data (transfers, stats, achievements)
- FootballDataAdapter: Real-time football statistics (standings, results, scorers)
"""

import pytest
from app.services.api_adapters import TransfermarktAdapter, FootballDataAdapter


class TestTransfermarktAdapter:
    """Test suite for Transfermarkt (Historical Sports Data) adapter."""

    def test_instantiation(self):
        """Test Transfermarkt adapter instantiates correctly."""
        adapter = TransfermarktAdapter()
        assert adapter.api_name == "Transfermarkt"
        assert "transfermarkt-api.fly.dev" in adapter.base_url
        assert adapter.cache_ttl == 3600  # 1 hour

    def test_is_relevant_for_domain(self):
        """Test Transfermarkt domain relevance."""
        adapter = TransfermarktAdapter()

        # Should be relevant for Sports globally
        assert adapter.is_relevant_for_domain("Sports", "Global") == True
        assert adapter.is_relevant_for_domain("Sports", "UK") == True
        assert adapter.is_relevant_for_domain("Sports", "US") == True

        # Should not be relevant for other domains
        assert adapter.is_relevant_for_domain("Finance", "Global") == False
        assert adapter.is_relevant_for_domain("Health", "UK") == False
        assert adapter.is_relevant_for_domain("Politics", "US") == False

    def test_transform_response(self):
        """Test Transfermarkt response transformation.

        Note: TransfermarktAdapter._transform_response returns [] because
        transformation is handled inline by specific search sub-methods
        (player search, club search, etc.). We verify the adapter can
        produce valid evidence dicts via _create_evidence_dict.
        """
        adapter = TransfermarktAdapter()

        # _transform_response delegates to specific methods, returns []
        mock_response = {
            "results": [
                {
                    "id": "123456",
                    "name": "Harry Kane",
                    "position": "Centre-Forward",
                    "club": {"name": "Bayern Munich"},
                    "marketValue": {"value": 100000000},
                }
            ]
        }

        result = adapter._transform_response(mock_response)
        assert result == []

        # Verify the adapter produces valid evidence via _create_evidence_dict
        evidence = adapter._create_evidence_dict(
            title="Harry Kane - Transfer History",
            snippet="Harry Kane transferred from Tottenham Hotspur to Bayern Munich in 2023 for EUR 95m.",
            url="https://www.transfermarkt.com/player/123456",
            source_date=None,
            metadata={
                "api_source": "Transfermarkt",
                "player_id": "123456",
                "data_type": "transfers",
                "transfer_count": 2,
            },
        )

        assert evidence["title"] == "Harry Kane - Transfer History"
        assert "Harry Kane" in evidence["snippet"]
        assert "transfermarkt.com" in evidence["url"]
        assert evidence["external_source_provider"] == "Transfermarkt"
        assert evidence["metadata"]["player_id"] == "123456"
        assert evidence["metadata"]["data_type"] == "transfers"
        assert evidence["metadata"]["transfer_count"] == 2

    def test_empty_response(self):
        """Test Transfermarkt handles empty/None input gracefully."""
        adapter = TransfermarktAdapter()

        assert adapter._transform_response(None) == []
        assert adapter._transform_response({}) == []
        assert adapter._transform_response([]) == []
        assert adapter._transform_response({"results": []}) == []


class TestFootballDataAdapter:
    """Test suite for Football-Data.org (Real-time Sports Statistics) adapter."""

    def test_instantiation(self):
        """Test Football-Data.org adapter instantiates correctly."""
        adapter = FootballDataAdapter()
        assert adapter.api_name == "Football-Data.org"
        assert "api.football-data.org" in adapter.base_url
        assert adapter.cache_ttl == 300  # 5 minutes

    def test_is_relevant_for_domain(self):
        """Test Football-Data.org domain relevance."""
        adapter = FootballDataAdapter()

        # Should be relevant for Sports globally
        assert adapter.is_relevant_for_domain("Sports", "Global") == True
        assert adapter.is_relevant_for_domain("Sports", "UK") == True
        assert adapter.is_relevant_for_domain("Sports", "US") == True

        # Should not be relevant for other domains
        assert adapter.is_relevant_for_domain("Finance", "Global") == False
        assert adapter.is_relevant_for_domain("Health", "UK") == False
        assert adapter.is_relevant_for_domain("Politics", "US") == False

    def test_transform_response(self):
        """Test Football-Data.org response transformation.

        Note: FootballDataAdapter._transform_response returns [] because
        transformation is handled inline by specific search sub-methods
        (standings, team info, match results, top scorers). We verify the
        adapter can produce valid evidence dicts via _create_evidence_dict.
        """
        adapter = FootballDataAdapter()

        # _transform_response delegates to specific methods, returns []
        mock_response = {
            "competition": {
                "name": "Premier League",
                "code": "PL",
            },
            "standings": [
                {
                    "table": [
                        {
                            "position": 1,
                            "team": {"id": 57, "name": "Arsenal"},
                            "points": 71,
                            "playedGames": 30,
                            "won": 22,
                            "draw": 5,
                            "lost": 3,
                        }
                    ]
                }
            ],
        }

        result = adapter._transform_response(mock_response)
        assert result == []

        # Verify the adapter produces valid evidence via _create_evidence_dict
        evidence = adapter._create_evidence_dict(
            title="Premier League Standings - Matchday 30",
            snippet="1. Arsenal - 71 pts (22W 5D 3L)\n2. Liverpool - 68 pts (20W 8D 2L)",
            url="https://www.football-data.org/competition/PL",
            source_date=None,
            metadata={
                "api_source": "Football-Data.org",
                "competition": "PL",
                "matchday": 30,
                "data_type": "standings",
            },
        )

        assert evidence["title"] == "Premier League Standings - Matchday 30"
        assert "Arsenal" in evidence["snippet"]
        assert "football-data.org" in evidence["url"]
        assert evidence["external_source_provider"] == "Football-Data.org"
        assert evidence["metadata"]["competition"] == "PL"
        assert evidence["metadata"]["data_type"] == "standings"
        assert evidence["metadata"]["matchday"] == 30

    def test_empty_response(self):
        """Test Football-Data.org handles empty/None input gracefully."""
        adapter = FootballDataAdapter()

        assert adapter._transform_response(None) == []
        assert adapter._transform_response({}) == []
        assert adapter._transform_response([]) == []
        assert adapter._transform_response({"standings": []}) == []


class TestSportsAdapterRegistry:
    """Test that sports adapters integrate with the registry."""

    def test_all_sports_adapters_registered(self):
        """Test that both sports adapters can be registered."""
        from app.services.government_api_client import APIAdapterRegistry

        registry = APIAdapterRegistry()

        adapters = [
            TransfermarktAdapter(),
            FootballDataAdapter(),
        ]

        for adapter in adapters:
            registry.register(adapter)

        assert len(registry.get_all_adapters()) == 2

    def test_get_adapters_for_sports_global(self):
        """Test getting relevant adapters for Sports + Global domain."""
        from app.services.government_api_client import APIAdapterRegistry

        registry = APIAdapterRegistry()
        registry.register(TransfermarktAdapter())
        registry.register(FootballDataAdapter())

        relevant = registry.get_adapters_for_domain("Sports", "Global")

        # Both should be relevant for Sports
        assert len(relevant) == 2
        api_names = {a.api_name for a in relevant}
        assert "Transfermarkt" in api_names
        assert "Football-Data.org" in api_names

    def test_sports_adapters_not_returned_for_other_domains(self):
        """Test that sports adapters are not returned for non-Sports domains."""
        from app.services.government_api_client import APIAdapterRegistry

        registry = APIAdapterRegistry()
        registry.register(TransfermarktAdapter())
        registry.register(FootballDataAdapter())

        assert len(registry.get_adapters_for_domain("Finance", "Global")) == 0
        assert len(registry.get_adapters_for_domain("Health", "UK")) == 0
        assert len(registry.get_adapters_for_domain("Politics", "US")) == 0


class TestCommonSportsAdapterFeatures:
    """Test common features across sports adapters."""

    @pytest.mark.parametrize(
        "adapter_class",
        [TransfermarktAdapter, FootballDataAdapter],
    )
    def test_adapter_has_required_methods(self, adapter_class):
        """Test each adapter implements required methods."""
        adapter = adapter_class()

        assert hasattr(adapter, "search")
        assert hasattr(adapter, "_transform_response")
        assert hasattr(adapter, "is_relevant_for_domain")
        assert callable(adapter.search)
        assert callable(adapter._transform_response)
        assert callable(adapter.is_relevant_for_domain)

    @pytest.mark.parametrize(
        "adapter_class",
        [TransfermarktAdapter, FootballDataAdapter],
    )
    def test_adapter_has_correct_attributes(self, adapter_class):
        """Test each adapter has correct attributes."""
        adapter = adapter_class()

        assert hasattr(adapter, "api_name")
        assert hasattr(adapter, "base_url")
        assert hasattr(adapter, "cache_ttl")
        assert hasattr(adapter, "timeout")
        assert hasattr(adapter, "max_results")

        assert isinstance(adapter.api_name, str)
        assert isinstance(adapter.base_url, str)
        assert isinstance(adapter.cache_ttl, int)
        assert adapter.cache_ttl > 0

    @pytest.mark.parametrize(
        "adapter_class",
        [TransfermarktAdapter, FootballDataAdapter],
    )
    def test_adapter_creates_valid_evidence_dict(self, adapter_class):
        """Test each adapter creates valid evidence dictionaries."""
        adapter = adapter_class()

        evidence = adapter._create_evidence_dict(
            title="Test Title",
            snippet="Test snippet",
            url="https://example.com",
            source_date=None,
            metadata={"test": "data"},
        )

        # Verify required fields
        assert "title" in evidence
        assert "snippet" in evidence
        assert "url" in evidence
        assert "source" in evidence
        assert "external_source_provider" in evidence
        assert "metadata" in evidence

        # Verify values
        assert evidence["title"] == "Test Title"
        assert evidence["snippet"] == "Test snippet"
        assert evidence["url"] == "https://example.com"
        assert evidence["external_source_provider"] == adapter.api_name
