"""
Unit tests for ClaimKeywordRouter

Tests keyword detection and adapter routing for cross-domain claims.
"""

import pytest
from unittest.mock import Mock, MagicMock
from app.utils.claim_keyword_router import (
    ClaimKeywordRouter,
    KeywordMatch,
    get_keyword_router,
)


class TestKeywordDetection:
    """Test keyword detection in claim text"""

    @pytest.fixture
    def router(self):
        """Fresh router instance for each test"""
        return ClaimKeywordRouter()

    def test_commodity_keywords_fall_through(self, router):
        """Commodity/forex/crypto keywords have no dedicated specialist adapter.

        Alpha Vantage was scrapped in PQ-06 (25 req/day free tier unusable) and
        its keyword rules removed. Until a replacement commodities source is
        added, these claims must fall through to the web-search cascade rather
        than silently match a non-existent adapter.
        """
        claims = [
            "Oil prices dropped 20% following the announcement",
            "Brent crude was up 2.5 percent to sixty dollars a barrel",
            "Bitcoin crossed $80,000 for the first time",
        ]

        for claim in claims:
            matches = router.detect_keywords(claim)
            adapter_names = [m.adapter_name for m in matches]
            assert "Alpha Vantage" not in adapter_names, (
                f"Alpha Vantage must not be keyword-routed (adapter unregistered). "
                f"Failed for: {claim}"
            )

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
        # This claim mentions both unemployment (FRED) and the Inflation Reduction Act (GovInfo)
        claim = "The Inflation Reduction Act of 2022 lowered unemployment to 3.5%"
        matches = router.detect_keywords(claim)
        adapter_names = [m.adapter_name for m in matches]

        assert "FRED" in adapter_names
        assert "GovInfo.gov" in adapter_names
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
            "UNEMPLOYMENT rate hit 4.2%",
            "Unemployment RATE hit 4.2%",
            "unemployment rate hit 4.2%",
            "UNEMPLOYMENT RATE HIT 4.2%",
        ]

        for claim in claims:
            matches = router.detect_keywords(claim)
            adapter_names = [m.adapter_name for m in matches]
            assert "FRED" in adapter_names, f"Failed for: {claim}"


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
        claim = "Unemployment rate hit 4.2%"

        # Simulate FRED already in adapters
        existing_adapter = Mock()
        existing_adapter.api_name = "FRED"
        current_adapters = [existing_adapter]

        additional = router.get_additional_adapters(
            claim, current_adapters, mock_registry
        )

        # FRED should NOT be added again
        additional_names = [a.api_name for a in additional]
        assert "FRED" not in additional_names

    def test_new_adapter_added_when_not_present(self, router, mock_registry):
        """Adapters not in current list should be added"""
        claim = "Unemployment rate hit 4.2%"

        # No existing adapters
        current_adapters = []

        additional = router.get_additional_adapters(
            claim, current_adapters, mock_registry
        )

        # FRED should be added
        additional_names = [a.api_name for a in additional]
        assert "FRED" in additional_names


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
        assert hasattr(router, "_compiled_patterns")
        assert len(router._compiled_patterns) > 0

        # Verify they're compiled regex objects
        for adapter_name, patterns in router._compiled_patterns.items():
            for compiled_pattern, keyword_desc in patterns:
                assert hasattr(compiled_pattern, "search")  # It's a compiled regex


class TestKeywordMatchDataclass:
    """Test KeywordMatch dataclass"""

    def test_keyword_match_creation(self):
        """KeywordMatch should store all fields correctly"""
        match = KeywordMatch(
            keyword="unemployment",
            pattern=r"\bunemployment\b",
            adapter_name="FRED",
            confidence=0.9,
        )

        assert match.keyword == "unemployment"
        assert match.pattern == r"\bunemployment\b"
        assert match.adapter_name == "FRED"
        assert match.confidence == 0.9

    def test_keyword_match_default_confidence(self):
        """KeywordMatch should have default confidence of 0.8"""
        match = KeywordMatch(
            keyword="unemployment", pattern=r"\bunemployment\b", adapter_name="FRED"
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
        long_claim = "This is a claim about unemployment. " * 100
        matches = router.detect_keywords(long_claim)
        adapter_names = [m.adapter_name for m in matches]
        assert "FRED" in adapter_names

    def test_special_characters_in_claim(self, router):
        """Claims with special characters should be handled"""
        claim = "Unemployment: 4.2%! (up 0.3pp)"
        matches = router.detect_keywords(claim)
        adapter_names = [m.adapter_name for m in matches]
        assert "FRED" in adapter_names

    def test_unicode_in_claim(self, router):
        """Claims with unicode should be handled"""
        claim = "Unemployment rose to 4.2% — the highest since 2021"
        matches = router.detect_keywords(claim)
        adapter_names = [m.adapter_name for m in matches]
        assert "FRED" in adapter_names


class TestKeywordDriftGuardrail:
    """H4 — keyword-router-vs-registry drift detection.

    Until H4 landed, a keyword rule pointing at an adapter the registry didn't
    know (e.g. Alpha Vantage after PQ-06 unregistered it but left 75 keyword
    rules in place) produced a `logger.warning` per claim — a Sentry breadcrumb
    only, never an issue. The drift went unnoticed for weeks. H4 upgrades the
    first occurrence of each missing name to `logger.error` (which Sentry's
    logging integration captures as a first-class event) and deduplicates
    subsequent occurrences to DEBUG level to prevent log/Sentry floods.

    These tests pin both behaviours.
    """

    @pytest.fixture
    def router(self):
        """Fresh router with the process-local dedup set cleared.

        `_reported_missing_adapters` is a class attribute by design (process-
        local dedup across claims), but tests need independence — the fixture
        resets it so each test starts from a clean slate.
        """
        ClaimKeywordRouter._reported_missing_adapters.clear()
        return ClaimKeywordRouter()

    def _registry_returning_none(self):
        """Mock registry where every adapter lookup misses."""
        registry = MagicMock()
        registry.get_adapter_by_name.return_value = None
        return registry

    def test_missing_adapter_logs_error_once(self, router, caplog):
        """First time a keyword route points at an unregistered adapter, the
        drift must be logged at ERROR level with the `[KEYWORD DRIFT]` marker
        so Sentry captures it as an event."""
        import logging

        registry = self._registry_returning_none()

        with caplog.at_level(logging.ERROR):
            router.get_additional_adapters(
                "UK unemployment fell to record lows",
                current_adapters=[],
                api_registry=registry,
            )

        drift_errors = [
            r
            for r in caplog.records
            if r.levelno == logging.ERROR and "[KEYWORD DRIFT]" in r.message
        ]
        assert (
            len(drift_errors) >= 1
        ), "Missing adapter must produce at least one ERROR-level [KEYWORD DRIFT] log"

    def test_repeated_missing_adapter_does_not_re_log(self, router, caplog):
        """Second and subsequent occurrences of the SAME missing adapter must
        NOT produce another ERROR log — dedup prevents Sentry flood."""
        import logging

        registry = self._registry_returning_none()
        claim = "UK unemployment fell to record lows"

        # First call — should ERROR
        with caplog.at_level(logging.ERROR):
            router.get_additional_adapters(
                claim, current_adapters=[], api_registry=registry
            )
        first_errors = [r for r in caplog.records if "[KEYWORD DRIFT]" in r.message]
        assert len(first_errors) >= 1

        caplog.clear()

        # Second call with same missing adapter — should NOT ERROR again
        with caplog.at_level(logging.ERROR):
            router.get_additional_adapters(
                claim, current_adapters=[], api_registry=registry
            )
        second_errors = [r for r in caplog.records if "[KEYWORD DRIFT]" in r.message]
        assert (
            len(second_errors) == 0
        ), "Repeated missing-adapter warnings must be deduped — no second ERROR"

    def test_different_missing_adapters_each_log_once(self, router, caplog):
        """Dedup is per-adapter-name, not global. A second missing adapter with
        a different name must trigger its own ERROR log — otherwise two
        concurrent drifts would mask each other."""
        import logging

        registry = self._registry_returning_none()

        with caplog.at_level(logging.ERROR):
            # UK claim → ONS keyword route
            router.get_additional_adapters(
                "UK unemployment fell to record lows",
                current_adapters=[],
                api_registry=registry,
            )
            # US econ claim → FRED keyword route (different adapter name)
            router.get_additional_adapters(
                "US GDP grew by 2.1% last quarter",
                current_adapters=[],
                api_registry=registry,
            )

        drift_errors = [r for r in caplog.records if "[KEYWORD DRIFT]" in r.message]
        drifted_names = {
            name
            for r in drift_errors
            for name in ("ONS Economic Statistics", "FRED")
            if name in r.message
        }
        assert drifted_names == {
            "ONS Economic Statistics",
            "FRED",
        }, f"Expected both ONS and FRED drift errors, got {drifted_names}"

    def test_registered_adapter_produces_no_drift_error(self, router, caplog):
        """When the registry does return an adapter for a keyword match, no
        drift error should fire — this is the normal healthy path."""
        import logging

        registry = MagicMock()
        real_adapter = Mock()
        real_adapter.api_name = "ONS Economic Statistics"
        registry.get_adapter_by_name.return_value = real_adapter

        with caplog.at_level(logging.ERROR):
            result = router.get_additional_adapters(
                "UK unemployment fell to record lows",
                current_adapters=[],
                api_registry=registry,
            )

        drift_errors = [r for r in caplog.records if "[KEYWORD DRIFT]" in r.message]
        assert drift_errors == []
        assert real_adapter in result
