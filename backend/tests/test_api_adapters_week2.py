"""
Unit Tests for Week 2 API Adapters
Phase 5: Government API Integration

Tests for the 6 adapters implemented in Week 2:
- FRED, WHO, CrossRef
- GOV.UK, Hansard, Wikidata
"""

from unittest.mock import patch

import pytest
from app.services.api_adapters import (
    FREDAdapter,
    WHOAdapter,
    CrossRefAdapter,
    GovUKAdapter,
    HansardAdapter,
    WikidataAdapter,
)


class TestFREDAdapter:
    """Test suite for FRED (Federal Reserve Economic Data) adapter."""

    def test_instantiation(self):
        """Test FRED adapter instantiates correctly."""
        adapter = FREDAdapter()
        assert adapter.api_name == "FRED"
        assert "stlouisfed.org" in adapter.base_url
        assert adapter.cache_ttl == 86400 * 7  # 7 days

    def test_is_relevant_for_domain(self):
        """Test FRED domain relevance."""
        adapter = FREDAdapter()

        # Should be relevant for Finance + US
        assert adapter.is_relevant_for_domain("Finance", "US") == True
        assert adapter.is_relevant_for_domain("Finance", "Global") == True

        # Should not be relevant for other domains
        assert adapter.is_relevant_for_domain("Health", "US") == False
        assert adapter.is_relevant_for_domain("Finance", "UK") == False

    def test_transform_response(self):
        """Test FRED response transformation."""
        adapter = FREDAdapter()

        mock_response = {
            "seriess": [
                {
                    "id": "UNRATE",
                    "title": "Unemployment Rate",
                    "notes": "The unemployment rate represents...",
                    "observation_start": "1948-01-01",
                    "frequency": "Monthly",
                    "units": "Percent",
                    "seasonal_adjustment": "Seasonally Adjusted",
                }
            ]
        }

        result = adapter._transform_response(mock_response)

        assert len(result) == 1
        assert result[0]["title"] == "Unemployment Rate"
        assert result[0]["external_source_provider"] == "FRED"
        assert result[0]["metadata"]["series_id"] == "UNRATE"
        assert "fred.stlouisfed.org" in result[0]["url"]

    # ===== SC-09: keyword → series-ID mapping =====
    # FRED /series/search returns 0 on long claim sentences but hits the
    # right series reliably when given a series ID (verified live
    # 2026-04-23 — UNRATE 0-yield on every Finance/US claim).
    # _extract_fred_series_query picks the longest matching keyword.

    def test_sc09_extract_fred_series_unemployment_returns_unrate(self):
        adapter = FREDAdapter()
        assert (
            adapter._extract_fred_series_query(
                "US unemployment rate is 3.7% as of January 2026"
            )
            == "UNRATE"
        )
        # Bare keyword
        assert adapter._extract_fred_series_query("unemployment") == "UNRATE"
        # Synonym
        assert (
            adapter._extract_fred_series_query("Jobless claims rose in Q1") == "UNRATE"
        )

    def test_sc09_extract_fred_series_inflation_returns_cpiaucsl(self):
        adapter = FREDAdapter()
        assert (
            adapter._extract_fred_series_query("US inflation fell to 2.1% in 2025")
            == "CPIAUCSL"
        )
        assert adapter._extract_fred_series_query("CPI rose 0.3%") == "CPIAUCSL"

    def test_sc09_extract_fred_series_gdp_returns_gdp(self):
        adapter = FREDAdapter()
        assert (
            adapter._extract_fred_series_query("US GDP grew 2.4% in the third quarter")
            == "GDP"
        )
        assert (
            adapter._extract_fred_series_query("Gross Domestic Product expanded")
            == "GDP"
        )

    def test_sc09_extract_fred_series_fed_funds_returns_fedfunds(self):
        adapter = FREDAdapter()
        assert (
            adapter._extract_fred_series_query(
                "The Fed funds rate held at 5.25% in March"
            )
            == "FEDFUNDS"
        )
        assert (
            adapter._extract_fred_series_query("Federal funds rate was raised 25bp")
            == "FEDFUNDS"
        )

    def test_sc09_extract_fred_series_longest_match_wins(self):
        """SC-09: longest keyword wins so 'consumer price index' maps to
        CPIAUCSL via the full phrase, not via the bare 'cpi' substring.
        Both happen to map to the same series here, but the order matters
        for series where the long form is more specific (e.g. 'real gdp'
        → GDPC1 vs 'gdp' → GDP)."""
        adapter = FREDAdapter()
        # real gdp → GDPC1 (real, chained), not GDP (nominal)
        assert adapter._extract_fred_series_query("Real GDP growth was 2.4%") == "GDPC1"
        # gdp alone → GDP
        assert adapter._extract_fred_series_query("US GDP rose") == "GDP"

    def test_sc09_extract_fred_series_returns_none_when_no_match(self):
        adapter = FREDAdapter()
        assert (
            adapter._extract_fred_series_query(
                "Tesla stock surged after Q3 earnings beat"
            )
            is None
        )
        assert adapter._extract_fred_series_query("") is None
        assert adapter._extract_fred_series_query(None) is None

    def test_sc09_extract_fred_series_case_insensitive(self):
        adapter = FREDAdapter()
        assert adapter._extract_fred_series_query("UNEMPLOYMENT") == "UNRATE"
        assert adapter._extract_fred_series_query("Inflation") == "CPIAUCSL"
        assert adapter._extract_fred_series_query("gdp") == "GDP"

    def test_sc09_extract_fred_series_word_boundary_avoids_false_positives(self):
        """SC-09 hardening: short keys like 'gdp', 'cpi', 'ppi' must use
        word-boundary matching so they don't false-positive inside
        unrelated tokens. Most damaging case: 'GDPR' (EU privacy law)
        contains the substring 'gdp' but is unrelated to economic output.
        """
        adapter = FREDAdapter()
        # GDPR is a privacy regulation, not an economic indicator
        assert (
            adapter._extract_fred_series_query("GDPR fines exceeded $1B in 2024")
            is None
        )
        # 'scpi' is a French REIT category — not CPI
        assert adapter._extract_fred_series_query("SCPI funds outperformed") is None
        # bare GDP at word boundary still matches
        assert adapter._extract_fred_series_query("GDP rose 2.4%") == "GDP"
        # bare CPI at word boundary still matches
        assert adapter._extract_fred_series_query("CPI hit 3.1%") == "CPIAUCSL"

    def test_sc09_search_cascade_falls_back_to_targeted_query(self):
        """SC-09 hardening: when the series-ID search returns empty, the
        cascade must retry with the original targeted query. Pins the
        empty-response → fallback path so a future FRED response-shape
        change can't silently break it.
        """
        adapter = FREDAdapter()
        adapter.api_key = "test-key"  # bypass the no-key short-circuit

        empty = {"seriess": []}
        good = {
            "seriess": [
                {
                    "id": "UNRATE",
                    "title": "Unemployment Rate",
                    "notes": "test",
                    "observation_start": "1948-01-01",
                    "frequency": "Monthly",
                    "units": "Percent",
                    "seasonal_adjustment": "Seasonally Adjusted",
                }
            ]
        }

        with patch.object(adapter, "_make_request") as mock_req, patch.object(
            adapter, "_fetch_latest_observations", return_value=None
        ):
            # First call (series-ID "UNRATE") returns empty → cascade fires.
            # Second call (raw targeted query) returns the good payload.
            mock_req.side_effect = [empty, good]
            results = adapter.search(
                "US unemployment rate is 3.7% as of January 2026",
                "Finance",
                "US",
            )

        assert mock_req.call_count == 2, "cascade did not fire on empty response"
        first_search_text = mock_req.call_args_list[0].kwargs["params"]["search_text"]
        second_search_text = mock_req.call_args_list[1].kwargs["params"]["search_text"]
        assert first_search_text == "UNRATE", "first call should be the series ID"
        assert (
            "unemployment" in second_search_text.lower()
        ), "fallback should use the original targeted query, not the series ID"
        assert len(results) == 1
        assert results[0]["metadata"]["series_id"] == "UNRATE"


class TestWHOAdapter:
    """Test suite for WHO (World Health Organization) adapter."""

    def test_instantiation(self):
        """Test WHO adapter instantiates correctly."""
        adapter = WHOAdapter()
        assert adapter.api_name == "WHO"
        assert "ghoapi.azureedge.net" in adapter.base_url
        assert adapter.cache_ttl == 86400 * 7  # 7 days

    def test_is_relevant_for_domain(self):
        """Test WHO domain relevance."""
        adapter = WHOAdapter()

        # Should be relevant for Health globally
        assert adapter.is_relevant_for_domain("Health", "Global") == True
        assert adapter.is_relevant_for_domain("Health", "UK") == True
        assert adapter.is_relevant_for_domain("Health", "US") == True

        # Should not be relevant for other domains
        assert adapter.is_relevant_for_domain("Finance", "Global") == False

    def test_transform_response(self):
        """Test WHO response transformation."""
        adapter = WHOAdapter()

        mock_response = {
            "indicators": [
                {
                    "IndicatorCode": "WHS9_86",
                    "IndicatorName": "Life expectancy at birth (years)",
                    "Definition": "Average number of years...",
                    "Language": "EN",
                }
            ]
        }

        result = adapter._transform_response(mock_response)

        assert len(result) == 1
        assert "Life expectancy" in result[0]["title"]
        assert result[0]["external_source_provider"] == "WHO"
        assert result[0]["metadata"]["indicator_code"] == "WHS9_86"


class TestCrossRefAdapter:
    """Test suite for CrossRef (Academic Research) adapter."""

    def test_instantiation(self):
        """Test CrossRef adapter instantiates correctly."""
        adapter = CrossRefAdapter()
        assert adapter.api_name == "CrossRef"
        assert "api.crossref.org" in adapter.base_url
        assert adapter.cache_ttl == 86400 * 14  # 14 days

    def test_is_relevant_for_domain(self):
        """Test CrossRef domain relevance."""
        adapter = CrossRefAdapter()

        # Should be relevant for Science globally
        assert adapter.is_relevant_for_domain("Science", "Global") == True
        assert adapter.is_relevant_for_domain("Science", "UK") == True
        assert adapter.is_relevant_for_domain("Science", "US") == True

        # Should not be relevant for other domains
        assert adapter.is_relevant_for_domain("Finance", "Global") == False

    def test_transform_response(self):
        """Test CrossRef response transformation."""
        adapter = CrossRefAdapter()

        mock_response = {
            "items": [
                {
                    "DOI": "10.1038/nature12345",
                    "title": ["Climate change impacts on global biodiversity"],
                    "abstract": "This study examines the impact...",
                    "published-print": {"date-parts": [[2024, 3, 15]]},
                    "publisher": "Nature Publishing Group",
                    "author": [
                        {"given": "John", "family": "Smith"},
                        {"given": "Jane", "family": "Doe"},
                    ],
                }
            ]
        }

        result = adapter._transform_response(mock_response)

        assert len(result) == 1
        assert "Climate change" in result[0]["title"]
        assert result[0]["external_source_provider"] == "CrossRef"
        assert result[0]["metadata"]["doi"] == "10.1038/nature12345"
        assert "doi.org" in result[0]["url"]


class TestGovUKAdapter:
    """Test suite for GOV.UK Content API adapter."""

    def test_instantiation(self):
        """Test GOV.UK adapter instantiates correctly."""
        adapter = GovUKAdapter()
        assert adapter.api_name == "GOV.UK Content API"
        assert "gov.uk" in adapter.base_url
        assert adapter.cache_ttl == 86400  # 1 day

    def test_is_relevant_for_domain(self):
        """Test GOV.UK domain relevance."""
        adapter = GovUKAdapter()

        # Should be relevant for Politics + UK
        assert adapter.is_relevant_for_domain("Politics", "UK") == True
        assert adapter.is_relevant_for_domain("General", "UK") == True

        # Should not be relevant for other jurisdictions (UK-only adapter)
        assert adapter.is_relevant_for_domain("Politics", "Global") == False
        assert adapter.is_relevant_for_domain("Politics", "US") == False

    def test_transform_response(self):
        """Test GOV.UK response transformation."""
        adapter = GovUKAdapter()

        mock_response = {
            "results": [
                {
                    "title": "Government announces new policy",
                    "description": "The government has announced...",
                    "link": "/government/news/policy-announcement",
                    "public_timestamp": "2024-03-15T10:00:00Z",
                    "format": "news_article",
                    "organisations": ["HM Treasury"],
                }
            ]
        }

        result = adapter._transform_response(mock_response)

        assert len(result) == 1
        assert "policy" in result[0]["title"].lower()
        assert result[0]["external_source_provider"] == "GOV.UK Content API"
        assert "gov.uk" in result[0]["url"]

    def test_nf10_absolute_link_not_prepended_with_base_url(self):
        """NF-10: GOV.UK search API sometimes returns an absolute URL in the
        `link` field (e.g. pointing to legislation.gov.uk as a cross-reference).
        Prepending `https://www.gov.uk` unconditionally produced malformed URLs
        like `https://www.gov.ukhttps://www.legislation.gov.uk/` that urlparse
        then mangled into domain `www.gov.ukhttps:`.

        Observed on TRU-A0C5-05DB (Data Protection Act 2018 check): GOV.UK API
        returned Legislation.gov.uk as result[0] with an absolute `link` field.
        """
        adapter = GovUKAdapter()

        mock_response = {
            "results": [
                {
                    "title": "Legislation.gov.uk",
                    "description": "UK statutory instruments",
                    "link": "https://www.legislation.gov.uk/",
                    "public_timestamp": "2024-03-15T10:00:00Z",
                },
                {
                    "title": "Relative-link guidance",
                    "description": "A guidance page",
                    "link": "/guidance/data-protection",
                    "public_timestamp": "2024-03-15T10:00:00Z",
                },
            ]
        }

        result = adapter._transform_response(mock_response)

        assert len(result) == 2

        # Absolute link: must be used as-is, NOT re-prefixed.
        assert result[0]["url"] == "https://www.legislation.gov.uk/"
        assert "gov.ukhttps" not in result[0]["url"]
        assert not result[0]["url"].startswith("https://www.gov.ukhttps")

        # Relative link: must get the standard base-URL prefix.
        assert result[1]["url"] == "https://www.gov.uk/guidance/data-protection"

    def test_nf10_link_protocol_variants_handled(self):
        """NF-10: both http:// and https:// absolute links must pass through
        unchanged. Guard on the scheme, not a specific protocol."""
        adapter = GovUKAdapter()

        for absolute in [
            "http://example.com/page",
            "https://www.example.com/page",
            "https://external.gov.uk/resource",
        ]:
            result = adapter._transform_response(
                {"results": [{"title": "x", "description": "x", "link": absolute}]}
            )
            assert result[0]["url"] == absolute, (
                f"Absolute link {absolute!r} must pass through unchanged; "
                f"got {result[0]['url']!r}"
            )


class TestHansardAdapter:
    """Test suite for UK Parliament Hansard adapter."""

    def test_instantiation(self):
        """Test Hansard adapter instantiates correctly."""
        adapter = HansardAdapter()
        assert adapter.api_name == "UK Parliament Hansard"
        assert "hansard-api.parliament.uk" in adapter.base_url
        assert adapter.cache_ttl == 86400 * 7  # 7 days

    def test_is_relevant_for_domain(self):
        """Test Hansard domain relevance."""
        adapter = HansardAdapter()

        # Should be relevant for Politics, Law, and Finance + UK
        # (P2.1: Finance was wrongly excluded — Treasury questions, Budget/Autumn
        # Statement debates are Hansard content; fiscal claims classify as Finance.)
        assert adapter.is_relevant_for_domain("Politics", "UK") == True
        assert adapter.is_relevant_for_domain("Law", "UK") == True
        assert adapter.is_relevant_for_domain("Finance", "UK") == True

        # Should not be relevant for other domains/jurisdictions (UK-only adapter)
        assert adapter.is_relevant_for_domain("Politics", "Global") == False
        assert adapter.is_relevant_for_domain("Politics", "US") == False

    def test_transform_response(self):
        """NF-06: Hansard /search.json response transformation.

        Real API response shape:
        - Top-level arrays (no "Response" wrapper): Debates, Contributions, ...
        - Debate item fields: Title, SittingDate, House, DebateSection,
          DebateSectionExtId, Rank
        - Contribution item fields: ContributionText, ContributionTextFull,
          DebateSectionExtId (cross-match key), MemberName, SittingDate, ...
        """
        adapter = HansardAdapter()

        mock_response = {
            "Debates": [
                {
                    "Title": "Online Safety Act 2023: Repeal",
                    "SittingDate": "2025-12-15T00:00:00",
                    "House": "Commons",
                    "DebateSection": "Westminster Hall",
                    "DebateSectionExtId": "DA0F7CFE-CCED-4864-BCCF-160E0AF56F92",
                    "Rank": 112,
                },
                {
                    "Title": "Online Safety Act 2023 (Priority Offences)",
                    "SittingDate": "2025-12-09T00:00:00",
                    "House": "Lords",
                    "DebateSection": "Lords Chamber",
                    "DebateSectionExtId": "A6E27AC8-61B2-4946-BE31-225F1BD16252",
                    "Rank": 112,
                },
            ],
            "Contributions": [
                {
                    # Matches first debate by ExtId — should be picked up as snippet
                    "DebateSectionExtId": "DA0F7CFE-CCED-4864-BCCF-160E0AF56F92",
                    "ContributionText": (
                        " The Online Safety Act 2023 introduced duties on "
                        "platforms to assess and mitigate risks of harmful "
                        "content accessible to children..."
                    ),
                    "ContributionTextFull": "The Online Safety Act 2023 ...",
                    "MemberName": "Hon. Member",
                    "SittingDate": "2025-12-15T00:00:00",
                },
                # Second debate has no matching contribution — tests fallback
            ],
            "TotalDebates": 2,
            "TotalContributions": 1,
        }

        result = adapter._transform_response(mock_response)

        assert len(result) == 2

        # First result: snippet sourced from matching Contribution text
        first = result[0]
        assert "Online Safety Act 2023: Repeal" in first["title"]
        assert "introduced duties on" in first["snippet"]
        assert first["external_source_provider"] == "UK Parliament Hansard"
        assert "hansard.parliament.uk" in first["url"]
        assert "DA0F7CFE-CCED-4864-BCCF-160E0AF56F92" in first["url"]
        assert "Commons" in first["url"]
        assert "2025-12-15" in first["url"]
        assert first["metadata"]["house"] == "Commons"
        assert (
            first["metadata"]["debate_ext_id"] == "DA0F7CFE-CCED-4864-BCCF-160E0AF56F92"
        )

        # Second result: no matching Contribution — falls back to synthesised snippet
        second = result[1]
        assert "Online Safety Act 2023 (Priority Offences)" in second["title"]
        assert "UK Parliament Lords debate" in second["snippet"]
        assert "2025-12-09" in second["snippet"]
        assert second["metadata"]["house"] == "Lords"

    def test_transform_response_handles_empty(self):
        """NF-06: empty Debates list returns empty evidence (no crash)."""
        adapter = HansardAdapter()
        assert adapter._transform_response({"Debates": [], "Contributions": []}) == []
        assert adapter._transform_response({}) == []

    def test_nf06_uses_search_json_not_search_debates_json(self):
        """NF-06 regression guard: adapter must call /search.json.

        /search/debates.json returns debate headings only (no URL, no excerpt),
        which produced empty evidence even when matching debates existed. The
        /search.json endpoint returns Debates + Contributions together, enabling
        snippet cross-matching. Reverting to /search/debates.json reintroduces
        the silent-zero-results bug surfaced by prod check TRU-5767-018D.
        """
        import inspect

        search_source = inspect.getsource(HansardAdapter.search)
        # Match only the quoted string literal passed to _make_request, not
        # any incidental mention in comments about what was fixed.
        assert (
            '"/search.json"' in search_source
        ), "NF-06 regression: adapter must call /search.json for Debates+Contributions."
        assert (
            '"/search/debates.json"' not in search_source
        ), "NF-06 regression: /search/debates.json returns no URL or excerpt; reverting breaks Hansard evidence."

    def test_nf06_response_envelope_has_no_response_wrapper(self):
        """NF-06 regression guard: adapter must read top-level Debates key.

        The real Hansard API response has no "Response" wrapper around the
        arrays. Reading response["Response"]["Results"] silently rejects
        every real response and returns 0 items (the NF-06 root cause).
        """
        import inspect

        transform_source = inspect.getsource(HansardAdapter._transform_response)
        search_source = inspect.getsource(HansardAdapter.search)
        combined = transform_source + search_source
        # Must read the top-level Debates key
        assert (
            'get("Debates"' in transform_source or '"Debates"' in transform_source
        ), "NF-06 regression: _transform_response must iterate the top-level Debates array."
        # Must not reintroduce the phantom Response-wrapper access pattern.
        # Target specific code shapes (dict-get or bracket access) so that
        # documentation / comments mentioning the old 'Response' envelope
        # don't trigger a false positive.
        assert (
            'get("Response"' not in combined and '["Response"]' not in combined
        ), "NF-06 regression: Hansard responses have NO 'Response' wrapper. Reading response['Response']['Results'] returns 0 items on every query."


class TestWikidataAdapter:
    """Test suite for Wikidata adapter."""

    def test_instantiation(self):
        """Test Wikidata adapter instantiates correctly."""
        adapter = WikidataAdapter()
        assert adapter.api_name == "Wikidata"
        assert "wikidata.org" in adapter.base_url
        assert adapter.cache_ttl == 86400 * 30  # 30 days

    def test_is_relevant_for_domain(self):
        """Test Wikidata domain relevance."""
        adapter = WikidataAdapter()

        # Should be relevant for General only
        assert adapter.is_relevant_for_domain("General", "Global") == True
        assert adapter.is_relevant_for_domain("General", "UK") == True

        # Should not be relevant for specific domains
        assert adapter.is_relevant_for_domain("Finance", "Global") == False
        assert adapter.is_relevant_for_domain("Health", "Global") == False

    def test_transform_response(self):
        """Test Wikidata response transformation."""
        adapter = WikidataAdapter()

        mock_response = {
            "search": [
                {
                    "id": "Q42",
                    "label": "Douglas Adams",
                    "description": "English author and humorist",
                    "concepturi": "http://www.wikidata.org/entity/Q42",
                }
            ]
        }

        result = adapter._transform_response(mock_response)

        assert len(result) == 1
        assert "Douglas Adams" in result[0]["title"]
        assert result[0]["external_source_provider"] == "Wikidata"
        assert result[0]["metadata"]["entity_id"] == "Q42"
        assert "wikidata.org/wiki/Q42" in result[0]["url"]


class TestAdapterRegistry:
    """Test that all Week 2 adapters integrate with the registry."""

    def test_all_adapters_registered(self):
        """Test that all adapters can be registered."""
        from app.services.government_api_client import APIAdapterRegistry

        registry = APIAdapterRegistry()

        # Register all Week 2 adapters
        adapters = [
            FREDAdapter(),
            WHOAdapter(),
            CrossRefAdapter(),
            GovUKAdapter(),
            HansardAdapter(),
            WikidataAdapter(),
        ]

        for adapter in adapters:
            registry.register(adapter)

        # Verify all registered (6 adapters in the list above)
        assert len(registry.get_all_adapters()) == 6

    def test_get_adapters_for_finance_us(self):
        """Test getting relevant adapters for Finance + US domain."""
        from app.services.government_api_client import APIAdapterRegistry

        registry = APIAdapterRegistry()
        registry.register(FREDAdapter())
        registry.register(WHOAdapter())
        registry.register(CrossRefAdapter())

        relevant = registry.get_adapters_for_domain("Finance", "US")

        # Should only return FRED
        assert len(relevant) == 1
        assert relevant[0].api_name == "FRED"

    def test_get_adapters_for_health_global(self):
        """Test getting relevant adapters for Health + Global domain."""
        from app.services.government_api_client import APIAdapterRegistry

        registry = APIAdapterRegistry()
        registry.register(WHOAdapter())
        registry.register(FREDAdapter())
        registry.register(WikidataAdapter())

        relevant = registry.get_adapters_for_domain("Health", "Global")

        # Should only return WHO
        assert len(relevant) == 1
        assert relevant[0].api_name == "WHO"

    def test_get_adapters_for_government_uk(self):
        """Test getting relevant adapters for Politics + UK domain."""
        from app.services.government_api_client import APIAdapterRegistry

        registry = APIAdapterRegistry()
        registry.register(GovUKAdapter())
        registry.register(HansardAdapter())
        registry.register(FREDAdapter())

        relevant = registry.get_adapters_for_domain("Politics", "UK")

        # Should return GOV.UK and Hansard
        assert len(relevant) == 2
        api_names = {a.api_name for a in relevant}
        assert "GOV.UK Content API" in api_names
        assert "UK Parliament Hansard" in api_names


class TestCommonAdapterFeatures:
    """Test common features across all Week 2 adapters."""

    @pytest.mark.parametrize(
        "adapter_class",
        [
            FREDAdapter,
            WHOAdapter,
            CrossRefAdapter,
            GovUKAdapter,
            HansardAdapter,
            WikidataAdapter,
        ],
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
        [
            FREDAdapter,
            WHOAdapter,
            CrossRefAdapter,
            GovUKAdapter,
            HansardAdapter,
            WikidataAdapter,
        ],
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
        [
            FREDAdapter,
            WHOAdapter,
            CrossRefAdapter,
            GovUKAdapter,
            HansardAdapter,
            WikidataAdapter,
        ],
    )
    def test_adapter_creates_valid_evidence_dict(self, adapter_class):
        """Test each adapter creates valid evidence dictionaries."""
        adapter = adapter_class()

        # Create test evidence
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
