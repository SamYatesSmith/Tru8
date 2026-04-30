"""NF-18 regression tests for NOAAAdapter.

Three Session-B-era bugs are covered here. The original regression
slipped because no test wired ``prepare_query`` → ``search`` together —
``prepare_query`` was tested in isolation (cache-key shape) and
``_transform_*`` was tested in isolation (response parsing), but the
seam between them (``search()`` consuming the cache-key string) was
unexercised. These tests close that seam.

  Bug-1: data-type classification used to scan the cache-key string,
  which never contained climate keywords post-Session-B. Now classified
  in ``prepare_query`` where ``claim_text`` is in scope, encoded as a
  cache-key prefix.

  Bug-2: ``_search_*_data`` hardcoded the date window to ``now-2y → now``
  ignoring the DATE entity. London 2022 claim queried 2024-2026.

  Bug-3a: ``_extract_location_id`` read ``entity.get("type")`` and
  looked for legacy NER labels ``GPE`` / ``LOC``. NF-15 (2026-04-28)
  remapped entities to ``{text, label}`` with ``LOCATION`` value, so
  the location filter has been silently no-op since NF-15 shipped.

  Bug-3b: ``location_map`` knew countries / states but not cities,
  so ``London`` returned ``None`` even before NF-15.
"""

from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from app.services.api_adapters.climate import (
    NOAAAdapter,
    _classify_noaa_data_type,
    _parse_date_window,
    _NOAA_CITY_TO_FIPS,
)


# =====================================================================
# Bug-1: data-type classification
# =====================================================================


class TestClassifyNoaaDataType:
    def test_temperature_from_claim_text(self):
        assert (
            _classify_noaa_data_type(
                "London hit 40.3°C on 19 July 2022 in a heatwave", entities=None
            )
            == "temperature"
        )

    def test_precipitation_from_claim_text(self):
        assert (
            _classify_noaa_data_type(
                "Hurricane Ian flooded coastal Florida in October 2022",
                entities=None,
            )
            == "precipitation"
        )

    def test_sea_level_from_claim_text(self):
        assert (
            _classify_noaa_data_type(
                "Arctic ice cover declined sharply in 2023", entities=None
            )
            == "sea_level"
        )

    def test_amount_entity_overrides_text_fallback(self):
        # Entity scan runs before claim-text scan; AMOUNT entity with
        # temperature unit wins over a claim-text "rain" hit.
        result = _classify_noaa_data_type(
            "It was raining when the temperature hit a record",
            entities=[{"text": "40.3°C", "label": "AMOUNT"}],
        )
        assert result == "temperature"

    def test_default_is_temperature(self):
        # Empty claim, no entities → fall to default.
        assert _classify_noaa_data_type("", entities=None) == "temperature"

    def test_no_match_falls_to_temperature(self):
        # "London on 19 July 2022" alone doesn't contain a data-type
        # keyword. The keyword router upstream gates the call so this
        # path is unlikely in practice; default is still safe.
        assert (
            _classify_noaa_data_type("London on 19 July 2022", entities=None)
            == "temperature"
        )

    def test_amount_entity_unit_only_no_value(self):
        # An AMOUNT entity holding just "mm" still classifies precipitation.
        assert (
            _classify_noaa_data_type(
                "rainfall record",
                entities=[{"text": "12 mm", "label": "AMOUNT"}],
            )
            == "precipitation"
        )

    def test_handles_non_dict_entities(self):
        # Defensive: entities sometimes carry junk; should not crash.
        assert (
            _classify_noaa_data_type(
                "heatwave",
                entities=["not-a-dict", None, {"label": "AMOUNT", "text": ""}],
            )
            == "temperature"
        )


# =====================================================================
# Bug-2: date-window parsing
# =====================================================================


class TestParseDateWindow:
    def test_day_month_year_string(self):
        # "19 July 2022" → ±30 days centred on the day.
        start, end = _parse_date_window("19 July 2022")
        assert start == "2022-06-19"
        assert end == "2022-08-18"

    def test_iso_day_month_year(self):
        start, end = _parse_date_window("2022-07-19")
        assert start == "2022-06-19"
        assert end == "2022-08-18"

    def test_month_year_string(self):
        # Whole calendar month.
        start, end = _parse_date_window("July 2022")
        assert start == "2022-07-01"
        assert end == "2022-07-31"

    def test_iso_month_year(self):
        start, end = _parse_date_window("2022-07")
        assert start == "2022-07-01"
        assert end == "2022-07-31"

    def test_year_only(self):
        start, end = _parse_date_window("2022")
        assert start == "2022-01-01"
        assert end == "2022-12-31"

    def test_february_month_end(self):
        # Non-leap year February.
        start, end = _parse_date_window("February 2023")
        assert start == "2023-02-01"
        assert end == "2023-02-28"

    def test_december_month_end(self):
        # December must use Dec 31 (the rollover branch).
        start, end = _parse_date_window("December 2022")
        assert start == "2022-12-01"
        assert end == "2022-12-31"

    def test_missing_falls_back_to_recent(self):
        # No date → 2-year recency window ending today.
        today = datetime.now(timezone.utc)
        start, end = _parse_date_window(None)
        assert start == datetime(today.year - 2, 1, 1).strftime("%Y-%m-%d")
        assert end == today.strftime("%Y-%m-%d")

    def test_unparseable_falls_back_to_recent(self):
        today = datetime.now(timezone.utc)
        start, end = _parse_date_window("sometime last summer")
        assert start == datetime(today.year - 2, 1, 1).strftime("%Y-%m-%d")
        assert end == today.strftime("%Y-%m-%d")

    def test_invalid_date_combo_falls_back(self):
        # 31 February doesn't exist; the safety branch returns the
        # recency window rather than raising.
        today = datetime.now(timezone.utc)
        start, end = _parse_date_window("31 February 2022")
        # Safety branch: parse fails, falls through to recency window.
        assert start == datetime(today.year - 2, 1, 1).strftime("%Y-%m-%d")
        assert end == today.strftime("%Y-%m-%d")


# =====================================================================
# Bug-3a + Bug-3b: location extraction
# =====================================================================


class TestExtractLocationId:
    def test_country_match_via_label(self):
        # NF-15 entities use `label`, not `type`.
        adapter = NOAAAdapter()
        result = adapter._extract_location_id(
            [{"text": "United Kingdom", "label": "LOCATION"}]
        )
        assert result == "FIPS:UK"

    def test_us_state_match(self):
        adapter = NOAAAdapter()
        result = adapter._extract_location_id(
            [{"text": "California", "label": "LOCATION"}]
        )
        assert result == "FIPS:06"

    def test_uk_city_falls_through_to_country(self):
        # Bug-3b: London should resolve to FIPS:UK via city map.
        adapter = NOAAAdapter()
        result = adapter._extract_location_id([{"text": "London", "label": "LOCATION"}])
        assert result == "FIPS:UK"

    def test_us_city_falls_through_to_state(self):
        adapter = NOAAAdapter()
        result = adapter._extract_location_id(
            [{"text": "Los Angeles", "label": "LOCATION"}]
        )
        assert result == "FIPS:06"

    def test_legacy_gpe_label_still_accepted(self):
        # Back-compat: pre-NF-15 callers may still send GPE.
        adapter = NOAAAdapter()
        result = adapter._extract_location_id([{"text": "London", "label": "GPE"}])
        assert result == "FIPS:UK"

    def test_legacy_type_field_still_accepted(self):
        # Back-compat: very-pre-NF-15 callers may still send `type`.
        adapter = NOAAAdapter()
        result = adapter._extract_location_id([{"text": "London", "type": "LOCATION"}])
        assert result == "FIPS:UK"

    def test_skips_non_location_entities(self):
        adapter = NOAAAdapter()
        result = adapter._extract_location_id(
            [
                {"text": "BP", "label": "ORG"},
                {"text": "40.3°C", "label": "AMOUNT"},
                {"text": "London", "label": "LOCATION"},
            ]
        )
        assert result == "FIPS:UK"

    def test_returns_none_when_no_match(self):
        # Some obscure place that's neither in country map nor city map
        # → None (signals: don't filter, query globally).
        adapter = NOAAAdapter()
        result = adapter._extract_location_id(
            [{"text": "Llanfairpwllgwyngyll", "label": "LOCATION"}]
        )
        assert result is None

    def test_global_sentinel_returns_none(self):
        # "Global" / "World" intentionally return None (no filter).
        adapter = NOAAAdapter()
        result = adapter._extract_location_id([{"text": "Global", "label": "LOCATION"}])
        assert result is None

    def test_handles_empty_and_none_entities(self):
        adapter = NOAAAdapter()
        assert adapter._extract_location_id(None) is None
        assert adapter._extract_location_id([]) is None
        assert adapter._extract_location_id([{}, None, "junk"]) is None

    def test_city_map_consistency(self):
        # Sanity: every city in _NOAA_CITY_TO_FIPS maps to a value
        # starting with "FIPS:". Catches typos in the map itself.
        for city, fips in _NOAA_CITY_TO_FIPS.items():
            assert isinstance(fips, str)
            assert fips.startswith("FIPS:"), f"{city} → {fips}"


# =====================================================================
# Wired path — prepare_query → search → _make_request integration
#
# This is the seam where the original regression slipped. We mock
# _make_request so the API isn't called, but verify the params that
# *would* be sent — proving prepare_query produces a key that search()
# can dispatch on, and that the params reflect the date entity.
# =====================================================================


LONDON_HEATWAVE_CLAIM = (
    "London hit 40.3°C on 19 July 2022 during a record-breaking heatwave."
)
LONDON_HEATWAVE_ENTITIES = [
    {"text": "London", "label": "LOCATION"},
    {"text": "40.3°C", "label": "AMOUNT"},
    {"text": "19 July 2022", "label": "DATE"},
]


class TestWiredPrepareQueryToSearch:
    def test_london_heatwave_dispatches_to_temperature(self):
        adapter = NOAAAdapter()
        adapter.api_key = "test-key"

        # Cache key produced by prepare_query
        cache_key = adapter.prepare_query(
            LONDON_HEATWAVE_CLAIM, LONDON_HEATWAVE_ENTITIES
        )
        assert cache_key == "temperature|London|19 July 2022"

        # search() consumes the cache key, dispatches to temperature,
        # and the request params reflect the DATE entity (Bug-2 fixed)
        # and the LONDON → FIPS:UK mapping (Bug-3a/b fixed).
        with patch.object(
            adapter, "_make_request", return_value={"results": []}
        ) as mock_req:
            adapter.search(cache_key, "Climate", "Global", LONDON_HEATWAVE_ENTITIES)

        assert mock_req.called
        path, kwargs = mock_req.call_args[0][0], mock_req.call_args.kwargs
        assert path == "data"
        params = kwargs["params"]
        assert params["datatypeid"] == "TAVG"
        assert params["locationid"] == "FIPS:UK"
        assert params["startdate"] == "2022-06-19"
        assert params["enddate"] == "2022-08-18"

    def test_florida_hurricane_dispatches_to_precipitation(self):
        adapter = NOAAAdapter()
        adapter.api_key = "test-key"

        claim = "Hurricane Ian flooded Miami in October 2022"
        entities = [
            {"text": "Miami", "label": "LOCATION"},
            {"text": "October 2022", "label": "DATE"},
            {"text": "Hurricane Ian", "label": "EVENT"},
        ]
        cache_key = adapter.prepare_query(claim, entities)
        assert cache_key == "precipitation|Miami|October 2022"

        with patch.object(
            adapter, "_make_request", return_value={"results": []}
        ) as mock_req:
            adapter.search(cache_key, "Climate", "Global", entities)

        params = mock_req.call_args.kwargs["params"]
        assert params["datatypeid"] == "PRCP"
        assert params["locationid"] == "FIPS:12"  # Miami → Florida state
        assert params["startdate"] == "2022-10-01"
        assert params["enddate"] == "2022-10-31"

    def test_sea_level_claim_dispatches_to_mmsl(self):
        adapter = NOAAAdapter()
        adapter.api_key = "test-key"

        claim = "Arctic sea level rose by 2mm in 2023"
        entities = [
            {"text": "Arctic", "label": "LOCATION"},
            {"text": "2023", "label": "DATE"},
        ]
        cache_key = adapter.prepare_query(claim, entities)
        assert cache_key.startswith("sea_level|")

        with patch.object(
            adapter, "_make_request", return_value={"results": []}
        ) as mock_req:
            adapter.search(cache_key, "Climate", "Global", entities)

        params = mock_req.call_args.kwargs["params"]
        assert params["datatypeid"] == "MMSL"
        assert params["startdate"] == "2023-01-01"
        assert params["enddate"] == "2023-12-31"

    def test_legacy_unprefixed_cache_key_defaults_to_temperature(self):
        # Pre-NF-18 cached entries had the bare "{location}|{date}"
        # shape. search() should tolerate them by defaulting to
        # temperature rather than crashing or returning [].
        adapter = NOAAAdapter()
        adapter.api_key = "test-key"

        with patch.object(
            adapter, "_make_request", return_value={"results": []}
        ) as mock_req:
            adapter.search(
                "London|19 July 2022",
                "Climate",
                "Global",
                LONDON_HEATWAVE_ENTITIES,
            )

        params = mock_req.call_args.kwargs["params"]
        assert params["datatypeid"] == "TAVG"

    def test_search_skips_when_domain_irrelevant(self):
        adapter = NOAAAdapter()
        adapter.api_key = "test-key"
        with patch.object(adapter, "_make_request") as mock_req:
            result = adapter.search(
                "temperature|London|19 July 2022",
                "Finance",  # NOAA only serves Climate/Weather
                "Global",
                LONDON_HEATWAVE_ENTITIES,
            )
        assert result == []
        assert not mock_req.called

    def test_search_skips_when_api_key_missing(self):
        adapter = NOAAAdapter()
        adapter.api_key = ""
        with patch.object(adapter, "_make_request") as mock_req:
            result = adapter.search(
                "temperature|London|19 July 2022",
                "Climate",
                "Global",
                LONDON_HEATWAVE_ENTITIES,
            )
        assert result == []
        assert not mock_req.called


# =====================================================================
# End-to-end via search_with_cache (the runner's actual call site)
# =====================================================================


class TestEndToEndViaSearchWithCache:
    def test_runner_path_for_london_heatwave(self):
        # Wire through the same adapter.search_with_cache(...) call that
        # retrieve.py:2091 makes. Cache miss → API call → params verified.
        adapter = NOAAAdapter()
        adapter.api_key = "test-key"

        # Mock cache miss + write
        with patch.object(
            adapter.cache, "get_cached_api_response_sync", return_value=None
        ) as mock_get, patch.object(
            adapter.cache, "cache_api_response_sync"
        ) as mock_set, patch.object(
            adapter, "_make_request", return_value={"results": []}
        ) as mock_req:
            adapter.search_with_cache(
                LONDON_HEATWAVE_CLAIM,
                "Climate",
                "Global",
                LONDON_HEATWAVE_ENTITIES,
            )

        # Cache key reflects the data-type prefix
        assert mock_get.call_args[0][1] == "temperature|London|19 July 2022"
        # Request params reflect the date entity and city → country mapping
        params = mock_req.call_args.kwargs["params"]
        assert params["locationid"] == "FIPS:UK"
        assert params["startdate"] == "2022-06-19"
        # Empty results → cache.set is NOT called
        assert not mock_set.called
