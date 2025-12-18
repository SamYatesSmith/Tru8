"""
Unit tests for ClaimKeywordRouter

Tests keyword detection and adapter routing for cross-domain claims.
"""

import pytest
from unittest.mock import Mock, MagicMock
from app.utils.claim_keyword_router import ClaimKeywordRouter, KeywordMatch, get_keyword_router


class TestKeywordDetection:
    """Test keyword detection in claim text"""

    @pytest.fixture
    def router(self):
        """Fresh router instance for each test"""
        return ClaimKeywordRouter()

    def test_oil_keywords_match_alpha_vantage(self, router):
        """Claims mentioning oil/crude should match Alpha Vantage"""
        claims = [
            "Oil prices dropped 20% following the announcement",
            "Brent crude was up 2.5 percent to sixty dollars a barrel",
            "WTI crude oil futures fell sharply",
            "Natural gas prices hit record highs",
        ]

        for claim in claims:
            matches = router.detect_keywords(claim)
            adapter_names = [m.adapter_name for m in matches]
            assert "Alpha Vantage" in adapter_names, f"Failed for: {claim}"

    def test_legislation_keywords_match_govinfo(self, router):
        """Claims mentioning 'Act of YYYY' should match GovInfo"""
        claims = [
            "The DROP Act of 2025 requires annual reports",
            "The 1964 Civil Rights Act prohibits discrimination",
            "H.R. 1234 was passed by the House",
            "Public law requires disclosure",
            "Congress passed new legislation yesterday",
        ]

        for claim in claims:
            matches = router.detect_keywords(claim)
            adapter_names = [m.adapter_name for m in matches]
            assert "GovInfo.gov" in adapter_names, f"Failed for: {claim}"

    def test_medical_keywords_match_pubmed(self, router):
        """Claims mentioning vaccines/trials should match PubMed"""
        claims = [
            "The vaccine is 95% effective against the virus",
            "A clinical trial showed positive results",
            "Study shows the treatment reduces symptoms",
            "The disease affects 1 in 1000 people",
            "Cancer rates have declined by 15%",
        ]

        for claim in claims:
            matches = router.detect_keywords(claim)
            adapter_names = [m.adapter_name for m in matches]
            assert "PubMed" in adapter_names, f"Failed for: {claim}"

    def test_economic_keywords_match_fred(self, router):
        """Claims mentioning economic data should match FRED"""
        claims = [
            "The unemployment rate fell to 3.5%",
            "US GDP grew by 2.1% last quarter",
            "Inflation is at its highest in 40 years",
            "The Fed raised interest rates again",
            "Consumer price index rose sharply",
        ]

        for claim in claims:
            matches = router.detect_keywords(claim)
            adapter_names = [m.adapter_name for m in matches]
            assert "FRED" in adapter_names, f"Failed for: {claim}"

    def test_climate_keywords_match_noaa(self, router):
        """Claims mentioning climate/weather records should match NOAA"""
        claims = [
            "This was the hottest temperature record ever",
            "Sea level has risen by 3 inches",
            "Precipitation levels were above normal",
            "The hurricane caused billions in damage",
        ]

        for claim in claims:
            matches = router.detect_keywords(claim)
            adapter_names = [m.adapter_name for m in matches]
            assert "NOAA CDO" in adapter_names, f"Failed for: {claim}"

    def test_uk_keywords_match_ons(self, router):
        """Claims mentioning UK statistics should match ONS"""
        claims = [
            "UK unemployment fell to record lows",
            "UK GDP grew by 0.5% this quarter",
            "UK population reached 67 million",
            "The British economy is recovering",
        ]

        for claim in claims:
            matches = router.detect_keywords(claim)
            adapter_names = [m.adapter_name for m in matches]
            assert "ONS Economic Statistics" in adapter_names, f"Failed for: {claim}"

    def test_football_keywords_match_football_data(self, router):
        """Claims mentioning football stats should match Football-Data.org"""
        claims = [
            "The team is top of the league standings",
            "He is the top scorer with 20 goals",
            "Premier League table shows close race",
            "The match result was 2-1",
        ]

        for claim in claims:
            matches = router.detect_keywords(claim)
            adapter_names = [m.adapter_name for m in matches]
            assert "Football-Data.org" in adapter_names, f"Failed for: {claim}"

    def test_transfer_keywords_match_transfermarkt(self, router):
        """Claims mentioning transfers should match Transfermarkt"""
        claims = [
            "The transfer fee was 100 million euros",
            "He signed for Manchester United",
            "His market value is estimated at 80 million",
            "The release clause is 150 million",
        ]

        for claim in claims:
            matches = router.detect_keywords(claim)
            adapter_names = [m.adapter_name for m in matches]
            assert "Transfermarkt" in adapter_names, f"Failed for: {claim}"

    def test_weather_forecast_keywords_match_weatherapi(self, router):
        """Claims mentioning weather forecasts should match WeatherAPI"""
        claims = [
            "The weather forecast predicts rain",
            "Temperature tomorrow will reach 30C",
            "It will rain heavily next week",
            "Snow is expected for the weekend",
        ]

        for claim in claims:
            matches = router.detect_keywords(claim)
            adapter_names = [m.adapter_name for m in matches]
            assert "WeatherAPI" in adapter_names, f"Failed for: {claim}"

    def test_biodiversity_keywords_match_gbif(self, router):
        """Claims mentioning species/biodiversity should match GBIF"""
        claims = [
            "This species is found only in Madagascar",
            "The animal is endangered according to experts",
            "The habitat has been destroyed",
            "Biodiversity loss is accelerating",
        ]

        for claim in claims:
            matches = router.detect_keywords(claim)
            adapter_names = [m.adapter_name for m in matches]
            assert "GBIF" in adapter_names, f"Failed for: {claim}"

    def test_multiple_keyword_matches(self, router):
        """Claim with multiple domains should return multiple adapters"""
        # This claim mentions both oil (Alpha Vantage) and GDP (FRED)
        claim = "Oil prices impacted GDP growth significantly"
        matches = router.detect_keywords(claim)
        adapter_names = [m.adapter_name for m in matches]

        assert "Alpha Vantage" in adapter_names
        assert "FRED" in adapter_names
        assert len(matches) >= 2

    def test_no_keywords_returns_empty(self, router):
        """Claims without trigger keywords should return empty list"""
        claims = [
            "The president gave a speech yesterday",
            "The company announced new products",
            "People attended the event",
            "It was a sunny day",
        ]

        for claim in claims:
            matches = router.detect_keywords(claim)
            # These general claims shouldn't match specialized adapters
            assert len(matches) == 0, f"Unexpected match for: {claim}"

    def test_case_insensitive_matching(self, router):
        """Keywords should match regardless of case"""
        claims = [
            "OIL prices dropped",
            "Oil PRICES dropped",
            "oil prices dropped",
            "OIL PRICES DROPPED",
        ]

        for claim in claims:
            matches = router.detect_keywords(claim)
            adapter_names = [m.adapter_name for m in matches]
            assert "Alpha Vantage" in adapter_names, f"Failed for: {claim}"


class TestAdapterDeduplication:
    """Test that adapters are properly deduplicated"""

    @pytest.fixture
    def router(self):
        return ClaimKeywordRouter()

    @pytest.fixture
    def mock_registry(self):
        """Mock API registry with test adapters"""
        registry = Mock()

        def get_adapter(name):
            adapter = Mock()
            adapter.api_name = name
            return adapter

        registry.get_adapter_by_name = get_adapter
        return registry

    def test_duplicate_adapter_prevention(self, router, mock_registry):
        """Same adapter shouldn't be added twice"""
        claim = "Oil prices dropped 20%"

        # Simulate Alpha Vantage already in adapters
        existing_adapter = Mock()
        existing_adapter.api_name = "Alpha Vantage"
        current_adapters = [existing_adapter]

        additional = router.get_additional_adapters(
            claim, current_adapters, mock_registry
        )

        # Alpha Vantage should NOT be added again
        additional_names = [a.api_name for a in additional]
        assert "Alpha Vantage" not in additional_names

    def test_new_adapter_added_when_not_present(self, router, mock_registry):
        """Adapters not in current list should be added"""
        claim = "Oil prices dropped 20%"

        # No existing adapters
        current_adapters = []

        additional = router.get_additional_adapters(
            claim, current_adapters, mock_registry
        )

        # Alpha Vantage should be added
        additional_names = [a.api_name for a in additional]
        assert "Alpha Vantage" in additional_names


class TestSingletonPattern:
    """Test singleton behavior of keyword router"""

    def test_get_keyword_router_returns_same_instance(self):
        """get_keyword_router should return the same instance"""
        router1 = get_keyword_router()
        router2 = get_keyword_router()
        assert router1 is router2

    def test_patterns_compiled_once(self):
        """Patterns should be compiled at init, not per call"""
        router = get_keyword_router()

        # Check that patterns are pre-compiled
        assert hasattr(router, '_compiled_patterns')
        assert len(router._compiled_patterns) > 0

        # Verify they're compiled regex objects
        for adapter_name, patterns in router._compiled_patterns.items():
            for compiled_pattern, keyword_desc in patterns:
                assert hasattr(compiled_pattern, 'search')  # It's a compiled regex


class TestKeywordMatchDataclass:
    """Test KeywordMatch dataclass"""

    def test_keyword_match_creation(self):
        """KeywordMatch should store all fields correctly"""
        match = KeywordMatch(
            keyword="oil",
            pattern=r"\boil\b",
            adapter_name="Alpha Vantage",
            confidence=0.9
        )

        assert match.keyword == "oil"
        assert match.pattern == r"\boil\b"
        assert match.adapter_name == "Alpha Vantage"
        assert match.confidence == 0.9

    def test_keyword_match_default_confidence(self):
        """KeywordMatch should have default confidence of 0.8"""
        match = KeywordMatch(
            keyword="oil",
            pattern=r"\boil\b",
            adapter_name="Alpha Vantage"
        )

        assert match.confidence == 0.8


class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    @pytest.fixture
    def router(self):
        return ClaimKeywordRouter()

    def test_empty_claim_text(self, router):
        """Empty claim should return no matches"""
        matches = router.detect_keywords("")
        assert len(matches) == 0

    def test_whitespace_only_claim(self, router):
        """Whitespace-only claim should return no matches"""
        matches = router.detect_keywords("   \t\n   ")
        assert len(matches) == 0

    def test_very_long_claim(self, router):
        """Very long claim should still work"""
        long_claim = "This is a claim about oil. " * 100
        matches = router.detect_keywords(long_claim)
        adapter_names = [m.adapter_name for m in matches]
        assert "Alpha Vantage" in adapter_names

    def test_special_characters_in_claim(self, router):
        """Claims with special characters should be handled"""
        claim = "Oil prices: $60/barrel! (up 2.5%)"
        matches = router.detect_keywords(claim)
        adapter_names = [m.adapter_name for m in matches]
        assert "Alpha Vantage" in adapter_names

    def test_unicode_in_claim(self, router):
        """Claims with unicode should be handled"""
        claim = "Oil prices rose to €60 per barrel"
        matches = router.detect_keywords(claim)
        adapter_names = [m.adapter_name for m in matches]
        assert "Alpha Vantage" in adapter_names
