"""Tests for adapter prepare_query overrides (Session A: Hansard, GOV.UK, Companies House).

Two layers of contract here:
  1. Each migrated adapter's prepare_query returns the right shape for representative claims.
  2. The base default (un-migrated adapters) still returns claim_text unchanged — the
     pass-through guarantee that lets us migrate adapter-by-adapter without regression.
"""

from unittest.mock import patch

from app.services.api_adapters.business import CompaniesHouseAdapter, WikidataAdapter
from app.services.api_adapters.economic import MarketauxAdapter, ONSAdapter
from app.services.api_adapters.legal import GovUKAdapter, HansardAdapter


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
    """Adapters without an override must still receive claim_text unchanged."""

    def test_wikidata_default_returns_claim_text(self):
        # WikidataAdapter has no prepare_query override yet (Session B).
        adapter = WikidataAdapter()
        assert adapter.prepare_query(CLIMATE_CLAIM, CLIMATE_ENTITIES) == CLIMATE_CLAIM

    def test_wikidata_default_with_no_entities(self):
        adapter = WikidataAdapter()
        assert adapter.prepare_query(CLIMATE_CLAIM, None) == CLIMATE_CLAIM


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
