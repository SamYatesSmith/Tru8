"""Tests for adapter prepare_query overrides (Session A: Hansard, GOV.UK, Companies House).

Two layers of contract here:
  1. Each migrated adapter's prepare_query returns the right shape for representative claims.
  2. The base default (un-migrated adapters) still returns claim_text unchanged — the
     pass-through guarantee that lets us migrate adapter-by-adapter without regression.
"""

from unittest.mock import patch

from app.services.api_adapters.business import CompaniesHouseAdapter, WikidataAdapter
from app.services.api_adapters.climate import (
    NOAAAdapter,
    OpenMeteoAdapter,
    WeatherAPIAdapter,
)
from app.services.api_adapters.economic import (
    FREDAdapter,
    MarketauxAdapter,
    ONSAdapter,
)
from app.services.api_adapters.health import WHOAdapter
from app.services.api_adapters.legal import (
    GovUKAdapter,
    HansardAdapter,
    UKParliamentBillsAdapter,
)
from app.services.api_adapters.nature import GBIFAdapter
from app.services.api_adapters.sports import FootballDataAdapter, TransfermarktAdapter


CLIMATE_CLAIM = (
    "The Climate Change Act 2008 set the UK's target of net zero emissions by 2050"
)
CLIMATE_ENTITIES = [
    {"text": "Climate Change Act 2008", "label": "LAW"},
    {"text": "UK", "label": "GPE"},
    {"text": "2050", "label": "DATE"},
]

BP_CLAIM = "BP reported record profits in 2023"
BP_ENTITIES = [
    {"text": "BP", "label": "ORG"},
    {"text": "2023", "label": "DATE"},
]


# ---------- Hansard ----------


class TestHansardPrepareQuery:
    def test_returns_law_entity_for_climate_claim(self):
        adapter = HansardAdapter()
        assert (
            adapter.prepare_query(CLIMATE_CLAIM, CLIMATE_ENTITIES)
            == "Climate Change Act 2008"
        )

    def test_falls_back_to_claim_when_no_topic_entity(self):
        adapter = HansardAdapter()
        entities = [{"text": "London", "label": "GPE"}]
        assert adapter.prepare_query(CLIMATE_CLAIM, entities) == CLIMATE_CLAIM

    def test_falls_back_to_claim_when_entities_none(self):
        adapter = HansardAdapter()
        assert adapter.prepare_query(CLIMATE_CLAIM, None) == CLIMATE_CLAIM


# ---------- GOV.UK ----------


class TestGovUKPrepareQuery:
    def test_returns_law_entity_for_climate_claim(self):
        adapter = GovUKAdapter()
        assert (
            adapter.prepare_query(CLIMATE_CLAIM, CLIMATE_ENTITIES)
            == "Climate Change Act 2008"
        )

    def test_returns_org_when_no_law_entity(self):
        adapter = GovUKAdapter()
        assert adapter.prepare_query(BP_CLAIM, BP_ENTITIES) == "BP"

    def test_falls_back_to_claim_when_entities_none(self):
        adapter = GovUKAdapter()
        assert adapter.prepare_query(CLIMATE_CLAIM, None) == CLIMATE_CLAIM


# ---------- Companies House ----------


class TestCompaniesHousePrepareQuery:
    def test_returns_org_entity(self):
        adapter = CompaniesHouseAdapter()
        assert adapter.prepare_query(BP_CLAIM, BP_ENTITIES) == "BP"

    def test_returns_empty_when_no_org_entity(self):
        adapter = CompaniesHouseAdapter()
        # CLIMATE_ENTITIES has LAW, GPE, DATE — no ORG.
        assert adapter.prepare_query(CLIMATE_CLAIM, CLIMATE_ENTITIES) == ""

    def test_returns_empty_when_entities_none(self):
        adapter = CompaniesHouseAdapter()
        assert adapter.prepare_query(BP_CLAIM, None) == ""

    def test_picks_longest_org_when_multiple(self):
        adapter = CompaniesHouseAdapter()
        entities = [
            {"text": "BP", "label": "ORG"},
            {"text": "British Petroleum PLC", "label": "ORG"},
        ]
        assert adapter.prepare_query(BP_CLAIM, entities) == "British Petroleum PLC"


# ---------- Pass-through default (un-migrated adapters) ----------


class TestBaseDefaultPassthrough:
    """Adapters without a prepare_query override must still receive claim_text unchanged."""

    # NOTE: this class previously held WikidataAdapter as the default-
    # passthrough exemplar. Wikidata now overrides prepare_query (B4.1)
    # via extract_topic_phrase, so the assertion has moved into
    # TestEntityAdaptersPrepareQuery below. We intentionally leave this
    # class (empty for now) as a reminder: when every adapter has an
    # override, B5 deletes the base default; until then, this is where
    # un-migrated-adapter passthrough tests would land.


# ---------- Entity adapters (B4.1/2/3) ----------


SPORTS_PERSON_CLAIM = "Lionel Messi scored 30 goals last season"
SPORTS_PERSON_ENTITIES = [
    {"text": "Lionel Messi", "label": "PERSON"},
    {"text": "30 goals", "label": "AMOUNT"},
]
SPORTS_CLUB_CLAIM = "Arsenal finished second in the 2023-24 Premier League"
SPORTS_CLUB_ENTITIES = [
    {"text": "Arsenal", "label": "ORG"},
    {"text": "Premier League", "label": "ORG"},
    {"text": "2023-24", "label": "DATE"},
]


class TestEntityAdaptersPrepareQuery:
    """Wikidata / Football-Data / Transfermarkt — entity-shaped adapters."""

    # --- Wikidata (B4.1): topic phrase, falls back to claim text ---

    def test_wikidata_returns_topic_phrase(self):
        adapter = WikidataAdapter()
        assert (
            adapter.prepare_query(CLIMATE_CLAIM, CLIMATE_ENTITIES)
            == "Climate Change Act 2008"
        )

    def test_wikidata_falls_back_to_claim_when_no_topic_entity(self):
        adapter = WikidataAdapter()
        # No LAW/EVENT/WORK_OF_ART/PRODUCT/ORG → falls back to claim text.
        entities = [
            {"text": "London", "label": "LOCATION"},
            {"text": "2024", "label": "DATE"},
        ]
        assert adapter.prepare_query(CLIMATE_CLAIM, entities) == CLIMATE_CLAIM

    def test_wikidata_falls_back_when_entities_none(self):
        adapter = WikidataAdapter()
        assert adapter.prepare_query(CLIMATE_CLAIM, None) == CLIMATE_CLAIM

    # --- Football-Data (B4.2): ORG only, skip on miss ---

    def test_football_data_returns_org_entity(self):
        adapter = FootballDataAdapter()
        assert (
            adapter.prepare_query(SPORTS_CLUB_CLAIM, SPORTS_CLUB_ENTITIES)
            == "Premier League"
        )

    def test_football_data_skips_when_no_org(self):
        adapter = FootballDataAdapter()
        assert adapter.prepare_query(CLIMATE_CLAIM, CLIMATE_ENTITIES) == ""

    def test_football_data_skips_on_person_only(self):
        adapter = FootballDataAdapter()
        # PERSON without ORG → skip (Football-Data is club/competition-scoped).
        assert adapter.prepare_query(SPORTS_PERSON_CLAIM, SPORTS_PERSON_ENTITIES) == ""

    # --- Transfermarkt (B4.3): PERSON preferred, ORG fallback ---

    def test_transfermarkt_returns_person(self):
        adapter = TransfermarktAdapter()
        assert (
            adapter.prepare_query(SPORTS_PERSON_CLAIM, SPORTS_PERSON_ENTITIES)
            == "Lionel Messi"
        )

    def test_transfermarkt_falls_back_to_org_when_no_person(self):
        adapter = TransfermarktAdapter()
        # Club claim with no PERSON; should pick the longest ORG.
        assert (
            adapter.prepare_query(SPORTS_CLUB_CLAIM, SPORTS_CLUB_ENTITIES)
            == "Premier League"
        )

    def test_transfermarkt_skips_on_neither(self):
        adapter = TransfermarktAdapter()
        assert adapter.prepare_query(CLIMATE_CLAIM, CLIMATE_ENTITIES) == ""

    def test_skip_path_routed_through_search_with_cache(self):
        for cls in [FootballDataAdapter, TransfermarktAdapter]:
            adapter = cls()
            adapter.api_key = "test-key"
            with patch.object(
                adapter.cache, "get_cached_api_response_sync"
            ) as mock_get:
                with patch.object(adapter, "search") as mock_search:
                    results = adapter.search_with_cache(
                        CLIMATE_CLAIM, "Sports", "Global", CLIMATE_ENTITIES
                    )
            assert results == [], f"{cls.__name__} should skip"
            assert not mock_get.called
            assert not mock_search.called


# ---------- ONS (B3.1) ----------


class TestONSPrepareQuery:
    """ONS skips on irrelevant claims; shapes the call when a UK economic concept matches."""

    def test_inflation_claim_returns_shaped_query(self):
        adapter = ONSAdapter()
        claim = "UK inflation hit 3.2% in March 2024"
        entities = [
            {"text": "UK", "label": "LOCATION"},
            {"text": "March 2024", "label": "DATE"},
        ]
        # "inflation" matches via claim-text fallback.
        assert adapter.prepare_query(claim, entities) == "consumer price inflation"

    def test_gdp_growth_specific_keyword_wins(self):
        adapter = ONSAdapter()
        # "gdp growth" is listed before "gdp" in the mapping; specific wins.
        claim = "UK GDP growth slowed in Q2 2024"
        assert adapter.prepare_query(claim, []) == "GDP growth"

    def test_unemployment_rate_concept_via_other_entity(self):
        adapter = ONSAdapter()
        claim = "Joblessness in Britain rose last quarter"
        entities = [{"text": "unemployment rate", "label": "OTHER"}]
        # OTHER entity with the concept name; pass-1 match wins.
        assert adapter.prepare_query(claim, entities) == "unemployment rate"

    def test_skips_on_irrelevant_company_claim(self):
        adapter = ONSAdapter()
        # The TRU-87D3-6415 dump pattern: BP profits should NOT fire ONS.
        claim = "BP plc reported record profits of $40 billion in 2022"
        entities = [
            {"text": "BP plc", "label": "ORG"},
            {"text": "$40 billion", "label": "AMOUNT"},
            {"text": "2022", "label": "DATE"},
        ]
        assert adapter.prepare_query(claim, entities) == ""

    def test_skips_on_climate_law_claim(self):
        adapter = ONSAdapter()
        # Law / Climate domain — should not fire ONS.
        claim = "The Climate Change Act 2008 set a UK net-zero target"
        entities = [
            {"text": "Climate Change Act 2008", "label": "LAW"},
            {"text": "UK", "label": "LOCATION"},
            {"text": "2008", "label": "DATE"},
        ]
        assert adapter.prepare_query(claim, entities) == ""

    def test_skips_when_entities_none_and_no_concept_in_text(self):
        adapter = ONSAdapter()
        assert adapter.prepare_query("Some unrelated claim about food", None) == ""

    def test_skip_path_routed_through_search_with_cache(self):
        """Empty prepare_query result must trigger search_with_cache to skip
        cache + API entirely (the same skip path as Companies House).
        """
        adapter = ONSAdapter()
        with patch.object(adapter.cache, "get_cached_api_response_sync") as mock_get:
            with patch.object(adapter, "search") as mock_search:
                results = adapter.search_with_cache(
                    "BP profits in 2022",
                    "Finance",
                    "UK",
                    [{"text": "BP", "label": "ORG"}],
                )
        assert results == []
        assert not mock_get.called
        assert not mock_search.called

    def test_match_path_routes_shaped_query_to_cache_key(self):
        adapter = ONSAdapter()
        with patch.object(
            adapter.cache, "get_cached_api_response_sync", return_value=[]
        ) as mock_get:
            with patch.object(adapter, "search", return_value=[]):
                adapter.search_with_cache(
                    "UK inflation hit 3.2% in March 2024",
                    "Finance",
                    "UK",
                    None,
                )
        assert mock_get.called
        called_query = mock_get.call_args[0][1]
        assert called_query == "consumer price inflation"


# ---------- Marketaux (B3.5) ----------


class TestMarketauxPrepareQuery:
    """Marketaux skips when no ORG entity is named — same pattern as Companies House."""

    def test_returns_org_entity(self):
        adapter = MarketauxAdapter()
        assert adapter.prepare_query(BP_CLAIM, BP_ENTITIES) == "BP"

    def test_returns_longest_org_when_multiple(self):
        adapter = MarketauxAdapter()
        entities = [
            {"text": "BP", "label": "ORG"},
            {"text": "British Petroleum", "label": "ORG"},
        ]
        assert adapter.prepare_query("anything", entities) == "British Petroleum"

    def test_skips_on_no_org_entity(self):
        # The TRU-87D3-6415 noise pattern: Marketaux returned "Photon Energy NV"
        # for a generic-energy claim. Skip cleanly when no company is named.
        adapter = MarketauxAdapter()
        assert adapter.prepare_query(CLIMATE_CLAIM, CLIMATE_ENTITIES) == ""

    def test_skips_on_law_only_entities(self):
        adapter = MarketauxAdapter()
        entities = [
            {"text": "Energy Act 2008", "label": "LAW"},
            {"text": "UK", "label": "LOCATION"},
        ]
        assert adapter.prepare_query("UK Energy Act provisions", entities) == ""

    def test_skips_when_entities_none(self):
        adapter = MarketauxAdapter()
        assert adapter.prepare_query("Some news headline", None) == ""

    def test_skip_path_routed_through_search_with_cache(self):
        adapter = MarketauxAdapter()
        adapter.api_key = "test-key"
        with patch.object(adapter.cache, "get_cached_api_response_sync") as mock_get:
            with patch.object(adapter, "search") as mock_search:
                results = adapter.search_with_cache(
                    CLIMATE_CLAIM, "Finance", "Global", CLIMATE_ENTITIES
                )
        assert results == []
        assert not mock_get.called
        assert not mock_search.called

    def test_match_path_routes_shaped_query_to_cache_key(self):
        adapter = MarketauxAdapter()
        adapter.api_key = "test-key"
        with patch.object(
            adapter.cache, "get_cached_api_response_sync", return_value=[]
        ) as mock_get:
            with patch.object(adapter, "search", return_value=[]):
                adapter.search_with_cache(BP_CLAIM, "Finance", "Global", BP_ENTITIES)
        assert mock_get.called
        called_query = mock_get.call_args[0][1]
        assert called_query == "BP"


# ---------- Climate batch (B3.2/3/4) ----------
# All three adapters share the same prepare_query shape: location|date or "".


WEATHER_CLAIM = "Paris temperature exceeded 40°C in July 2019"
WEATHER_ENTITIES = [
    {"text": "Paris", "label": "LOCATION"},
    {"text": "40°C", "label": "AMOUNT"},
    {"text": "July 2019", "label": "DATE"},
]

# Law-only claim: only a LAW entity, no LOCATION and no DATE — the
# pure case for the "both-none skip" path. The CLIMATE_ENTITIES fixture
# above does include a DATE ("2050"), which intentionally produces a
# "|2050" key (date-only, location-empty) — the plan's "skip if both
# None" rule treats date-alone as legitimate cache namespace.
LAW_ONLY_ENTITIES = [
    {"text": "Climate Change Act 2008", "label": "LAW"},
]


class TestClimateAdaptersPrepareQuery:
    """WeatherAPI / Open-Meteo / NOAA CDO all use _location_date_cache_key."""

    def test_weatherapi_returns_location_pipe_date(self):
        adapter = WeatherAPIAdapter()
        assert (
            adapter.prepare_query(WEATHER_CLAIM, WEATHER_ENTITIES) == "Paris|July 2019"
        )

    def test_openmeteo_returns_location_pipe_date(self):
        adapter = OpenMeteoAdapter()
        assert (
            adapter.prepare_query(WEATHER_CLAIM, WEATHER_ENTITIES) == "Paris|July 2019"
        )

    def test_noaa_returns_data_type_prefixed_key(self):
        # NF-18: NOAA's cache key includes a data-type prefix so search()
        # can dispatch to the right NOAA endpoint without re-classifying
        # on the cache-key string (the original Session B regression).
        adapter = NOAAAdapter()
        # WEATHER_CLAIM contains "temperature" → temperature data type.
        assert (
            adapter.prepare_query(WEATHER_CLAIM, WEATHER_ENTITIES)
            == "temperature|Paris|July 2019"
        )

    def test_weatherapi_skips_on_law_only_claim(self):
        # Law-only claim with neither LOCATION nor DATE entities — the
        # pure "both-none skip" case.
        adapter = WeatherAPIAdapter()
        assert adapter.prepare_query(CLIMATE_CLAIM, LAW_ONLY_ENTITIES) == ""

    def test_openmeteo_skips_on_law_only_claim(self):
        adapter = OpenMeteoAdapter()
        assert adapter.prepare_query(CLIMATE_CLAIM, LAW_ONLY_ENTITIES) == ""

    def test_noaa_skips_on_law_only_claim(self):
        adapter = NOAAAdapter()
        assert adapter.prepare_query(CLIMATE_CLAIM, LAW_ONLY_ENTITIES) == ""

    def test_returns_location_only_when_date_absent(self):
        adapter = WeatherAPIAdapter()
        entities = [{"text": "Berlin", "label": "LOCATION"}]
        assert adapter.prepare_query("anything", entities) == "Berlin|"

    def test_returns_date_only_when_location_absent(self):
        adapter = OpenMeteoAdapter()
        entities = [{"text": "March 2024", "label": "DATE"}]
        assert adapter.prepare_query("anything", entities) == "|March 2024"

    def test_skips_when_entities_none(self):
        for adapter in [WeatherAPIAdapter(), OpenMeteoAdapter(), NOAAAdapter()]:
            assert adapter.prepare_query("anything", None) == ""

    def test_skip_path_routed_through_search_with_cache(self):
        """All three adapters skip cache + API on no location/date."""
        for cls in [WeatherAPIAdapter, OpenMeteoAdapter, NOAAAdapter]:
            adapter = cls()
            adapter.api_key = "test-key"
            with patch.object(
                adapter.cache, "get_cached_api_response_sync"
            ) as mock_get:
                with patch.object(adapter, "search") as mock_search:
                    results = adapter.search_with_cache(
                        CLIMATE_CLAIM, "Climate", "Global", LAW_ONLY_ENTITIES
                    )
            assert results == [], f"{cls.__name__} should skip"
            assert not mock_get.called, f"{cls.__name__} cache must not be consulted"
            assert not mock_search.called, f"{cls.__name__} search must not be called"

    def test_match_path_uses_combined_key(self):
        # WeatherAPI and Open-Meteo share the bare "{location}|{date}"
        # cache-key shape. NOAA's NF-18 prefix is asserted separately.
        for cls in [WeatherAPIAdapter, OpenMeteoAdapter]:
            adapter = cls()
            adapter.api_key = "test-key"
            with patch.object(
                adapter.cache, "get_cached_api_response_sync", return_value=[]
            ) as mock_get:
                with patch.object(adapter, "search", return_value=[]):
                    adapter.search_with_cache(
                        WEATHER_CLAIM, "Climate", "Global", WEATHER_ENTITIES
                    )
            assert mock_get.called
            assert mock_get.call_args[0][1] == "Paris|July 2019"

    def test_noaa_match_path_uses_data_type_prefixed_key(self):
        # NF-18: NOAA cache key carries the data-type prefix.
        adapter = NOAAAdapter()
        adapter.api_key = "test-key"
        with patch.object(
            adapter.cache, "get_cached_api_response_sync", return_value=[]
        ) as mock_get:
            with patch.object(adapter, "search", return_value=[]):
                adapter.search_with_cache(
                    WEATHER_CLAIM, "Climate", "Global", WEATHER_ENTITIES
                )
        assert mock_get.called
        assert mock_get.call_args[0][1] == "temperature|Paris|July 2019"


# ---------- WHO (B3.6) ----------


class TestWHOPrepareQuery:
    """WHO skips when no global-health concept is mentioned."""

    def test_life_expectancy_claim(self):
        adapter = WHOAdapter()
        claim = "Global life expectancy rose by 6 years between 2000 and 2019"
        assert adapter.prepare_query(claim, []) == "Life expectancy"

    def test_tuberculosis_via_other_entity(self):
        adapter = WHOAdapter()
        entities = [{"text": "tuberculosis", "label": "OTHER"}]
        assert adapter.prepare_query("TB rates remain high", entities) == "Tuberculosis"

    def test_under_5_mortality_specific_wins(self):
        adapter = WHOAdapter()
        # "under-5 mortality" listed before "child mortality"; both map to
        # the same value. Either match is acceptable.
        result = adapter.prepare_query("Under-5 mortality fell sharply", [])
        assert result == "Under-five mortality"

    def test_skips_on_irrelevant_finance_claim(self):
        adapter = WHOAdapter()
        assert adapter.prepare_query("BP profits hit record highs", BP_ENTITIES) == ""

    def test_skips_on_climate_claim(self):
        adapter = WHOAdapter()
        assert adapter.prepare_query(CLIMATE_CLAIM, CLIMATE_ENTITIES) == ""

    def test_skips_when_entities_none_and_no_concept(self):
        adapter = WHOAdapter()
        assert adapter.prepare_query("Some unrelated text", None) == ""

    def test_skip_path_routed_through_search_with_cache(self):
        adapter = WHOAdapter()
        with patch.object(adapter.cache, "get_cached_api_response_sync") as mock_get:
            with patch.object(adapter, "search") as mock_search:
                results = adapter.search_with_cache(
                    BP_CLAIM, "Health", "Global", BP_ENTITIES
                )
        assert results == []
        assert not mock_get.called
        assert not mock_search.called

    def test_match_path_routes_shaped_query_to_cache_key(self):
        adapter = WHOAdapter()
        with patch.object(
            adapter.cache, "get_cached_api_response_sync", return_value=[]
        ) as mock_get:
            with patch.object(adapter, "search", return_value=[]):
                adapter.search_with_cache(
                    "Global life expectancy at 73 in 2020",
                    "Health",
                    "Global",
                    None,
                )
        assert mock_get.called
        assert mock_get.call_args[0][1] == "Life expectancy"


# ---------- Working-adapter migrations (B2.1/2/3) ----------


class TestWorkingAdapterMigrations:
    """B2.1/2/3: GBIF, FRED, Bills now expose existing SC-XX trims via
    prepare_query. The shape of the returned query must match the existing
    private trim contract — no behaviour regression.
    """

    # --- B2.1 GBIF: _extract_species_query ---

    def test_gbif_prepare_query_matches_extract_species(self):
        adapter = GBIFAdapter()
        claim = "The North Atlantic right whale population fell below 350 individuals"
        # Direct call to the private trim — the contract we must preserve.
        expected = adapter._extract_species_query(claim)
        assert adapter.prepare_query(claim, []) == expected
        # Sanity: trim does shorten the claim.
        assert expected != claim
        assert "right whale" in expected.lower()

    # --- B2.2 FRED: _extract_fred_series_query (mapped concept) ---

    def test_fred_prepare_query_returns_series_id_when_concept_matches(self):
        adapter = FREDAdapter()
        claim = "US unemployment rose to 4.2% in September 2024"
        result = adapter.prepare_query(claim, [])
        # SC-09 mapping returns the series ID for "unemployment".
        assert result == "UNRATE"

    def test_fred_prepare_query_falls_back_to_claim_when_no_concept(self):
        adapter = FREDAdapter()
        claim = "The European Central Bank raised rates"  # no FRED concept
        # Falls back to claim text so search() can still try natural-language search.
        assert adapter.prepare_query(claim, []) == claim

    # --- B2.3 UK Bills: _extract_bill_query (year stripping) ---

    def test_bills_prepare_query_strips_year(self):
        adapter = UKParliamentBillsAdapter()
        claim = "The Online Safety Act 2023 requires platforms to verify users' ages"
        result = adapter.prepare_query(claim, [])
        # SC-15 trim drops the 4-digit year so Bills API matches the short title.
        assert "2023" not in result
        assert "Online Safety" in result

    def test_bills_prepare_query_matches_extract_bill_query(self):
        adapter = UKParliamentBillsAdapter()
        claim = "The Online Safety Act 2023 requires platforms to verify users' ages"
        expected = adapter._extract_bill_query(claim)
        assert adapter.prepare_query(claim, []) == expected


# ---------- Cache-key seam: prepare_query must run before cache lookup ----------


class TestCacheKeyShaping:
    """The shaped query — not the raw claim — must be the cache key.

    Verified by patching the cache get/set methods and confirming the key passed
    is the prepare_query output, not the input claim_text.
    """

    def test_companies_house_cache_keyed_on_shaped_query(self):
        adapter = CompaniesHouseAdapter()
        # Force api_key truthy so search() doesn't early-return on missing key.
        adapter.api_key = "test-key"

        with patch.object(
            adapter.cache, "get_cached_api_response_sync", return_value=[]
        ) as mock_get:
            adapter.search_with_cache(BP_CLAIM, "Finance", "UK", BP_ENTITIES)

        # Cache lookup must have been called with the shaped query "BP",
        # not the full claim text.
        assert mock_get.called
        called_query = mock_get.call_args[0][1]
        assert called_query == "BP"

    def test_companies_house_skips_when_no_org_entity(self):
        """prepare_query returns "" → search_with_cache must skip cache + API entirely."""
        adapter = CompaniesHouseAdapter()
        adapter.api_key = "test-key"

        with patch.object(adapter.cache, "get_cached_api_response_sync") as mock_get:
            with patch.object(adapter, "search") as mock_search:
                results = adapter.search_with_cache(
                    CLIMATE_CLAIM, "Finance", "UK", CLIMATE_ENTITIES
                )

        assert results == []
        assert not mock_get.called, "cache must not be consulted on empty query"
        assert not mock_search.called, "search must not be called on empty query"

    def test_hansard_cache_keyed_on_shaped_query(self):
        adapter = HansardAdapter()
        with patch.object(
            adapter.cache, "get_cached_api_response_sync", return_value=[]
        ) as mock_get:
            adapter.search_with_cache(CLIMATE_CLAIM, "Law", "UK", CLIMATE_ENTITIES)
        called_query = mock_get.call_args[0][1]
        assert called_query == "Climate Change Act 2008"
