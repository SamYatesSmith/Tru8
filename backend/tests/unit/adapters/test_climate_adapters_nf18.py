"""NF-18 sweep regression tests for Open-Meteo and WeatherAPI adapters.

NF-18 (2026-04-30) fixed NOAA CDO so it derived its date window from
the DATE entity rather than hardcoding ``now-2y``. The same
architectural bug class was present in two sibling climate adapters
but wasn't swept at the time:

  Open-Meteo:
    - search() classified historical-vs-forecast from query-string
      keyword scan ("last year", "average", ...). After Session B the
      ``query`` is the cache-key shape ``"{loc}|{date}"`` and never
      contains those keywords — Bug-1 class.
    - _get_historical() hardcoded now-365d → now regardless of DATE
      entity — Bug-2 class.

  WeatherAPI:
    - search() classified historical-vs-forecast-vs-current via
      keyword scan on the cache-key string — Bug-1 class.
    - _get_historical() hardcoded "yesterday" — Bug-2 class.

The fix wires both adapters through ``classify_temporal_intent``
(climate.py) for dispatch, and ``_parse_date_anchor`` for the actual
date-window selection inside ``_get_historical``. Reference shape:
:file:`test_noaa_nf18.py`.

Symptom this fixes (TRU-2F04-351D, 2026-05-12, post-NF-20-B): claim 2
"1.5°C ocean heat anomalies in Coral Sea" with inherited DATE "March
2024" routed to Open-Meteo's forecast endpoint (returned 7-day
forward forecast) instead of the archive (which has 1940-present
data). Same claim on WeatherAPI would have returned today's weather.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.services.api_adapters.climate import (
    OpenMeteoAdapter,
    WeatherAPIAdapter,
    _parse_date_anchor,
    _parse_date_window,
    classify_temporal_intent,
)


# =====================================================================
# _parse_date_anchor — returns None when unparseable (vs _parse_date_window's
# always-return-something-with-fallback semantics).
# =====================================================================


class TestParseDateAnchor:
    def test_day_month_year_string(self):
        result = _parse_date_anchor("19 July 2022")
        assert result is not None
        start, end = result
        assert start == datetime(2022, 6, 19, tzinfo=timezone.utc)
        assert end == datetime(2022, 8, 18, tzinfo=timezone.utc)

    def test_month_year_string(self):
        result = _parse_date_anchor("March 2024")
        assert result is not None
        start, end = result
        assert start == datetime(2024, 3, 1, tzinfo=timezone.utc)
        assert end == datetime(2024, 3, 31, tzinfo=timezone.utc)

    def test_year_only(self):
        result = _parse_date_anchor("2022")
        assert result is not None
        start, end = result
        assert start == datetime(2022, 1, 1, tzinfo=timezone.utc)
        assert end == datetime(2022, 12, 31, tzinfo=timezone.utc)

    def test_iso_day(self):
        result = _parse_date_anchor("2022-07-19")
        assert result is not None
        start, end = result
        assert start == datetime(2022, 6, 19, tzinfo=timezone.utc)
        assert end == datetime(2022, 8, 18, tzinfo=timezone.utc)

    def test_none_input_returns_none(self):
        assert _parse_date_anchor(None) is None

    def test_empty_string_returns_none(self):
        assert _parse_date_anchor("") is None
        assert _parse_date_anchor("   ") is None

    def test_unparseable_returns_none(self):
        # Distinguishes from _parse_date_window which would fall back.
        assert _parse_date_anchor("sometime last summer") is None
        assert _parse_date_anchor("a while ago") is None

    def test_invalid_date_combo_returns_none(self):
        # 31 Feb doesn't exist; safety branch returns None now.
        assert _parse_date_anchor("31 February 2022") is None


class TestParseDateWindowWrapsAnchor:
    """_parse_date_window must keep its existing NOAA-fallback semantics
    even though it now delegates to _parse_date_anchor internally. The
    NOAA NF-18 contract (now-fallback_years on no-DATE) is preserved."""

    def test_parseable_input_matches_anchor(self):
        # _parse_date_window converts the anchor to ISO strings.
        start_iso, end_iso = _parse_date_window("March 2024")
        assert start_iso == "2024-03-01"
        assert end_iso == "2024-03-31"

    def test_unparseable_falls_back_to_recency(self):
        today = datetime.now(timezone.utc)
        start_iso, end_iso = _parse_date_window(None)
        assert start_iso == datetime(today.year - 2, 1, 1).strftime("%Y-%m-%d")
        assert end_iso == today.strftime("%Y-%m-%d")


# =====================================================================
# classify_temporal_intent — used by Open-Meteo + WeatherAPI dispatch.
# =====================================================================


class TestClassifyTemporalIntent:
    def test_no_entities_is_current(self):
        assert classify_temporal_intent(None) == "current"
        assert classify_temporal_intent([]) == "current"

    def test_entities_without_date_is_current(self):
        assert (
            classify_temporal_intent([{"text": "Coral Sea", "label": "LOCATION"}])
            == "current"
        )

    def test_date_in_past_returns_past(self):
        # March 2024 is well before May 2026.
        assert (
            classify_temporal_intent([{"text": "March 2024", "label": "DATE"}])
            == "past"
        )

    def test_year_only_past_returns_past(self):
        assert classify_temporal_intent([{"text": "2022", "label": "DATE"}]) == "past"

    def test_date_far_in_future_returns_future(self):
        # 2050 is well after today.
        assert classify_temporal_intent([{"text": "2050", "label": "DATE"}]) == "future"

    def test_unparseable_date_is_current(self):
        # Empty-string DATE / unparseable text → current (cannot dispatch).
        assert (
            classify_temporal_intent(
                [{"text": "sometime last summer", "label": "DATE"}]
            )
            == "current"
        )

    def test_longest_date_wins(self):
        # extract_location_and_date picks longest DATE; classification
        # follows that one.
        entities = [
            {"text": "2024", "label": "DATE"},
            {"text": "19 July 2050", "label": "DATE"},
        ]
        # "19 July 2050" is longer → future.
        assert classify_temporal_intent(entities) == "future"

    def test_today_within_granularity_is_current(self):
        # A year-coarse DATE for the current year contains today.
        today = datetime.now(timezone.utc)
        current_year_str = str(today.year)
        assert (
            classify_temporal_intent([{"text": current_year_str, "label": "DATE"}])
            == "current"
        )

    def test_recent_month_in_past_is_past(self):
        # A specific month that has fully ended is past.
        today = datetime.now(timezone.utc)
        if today.month >= 2:
            # Use a month from earlier this year.
            month_name = datetime(today.year, 1, 1).strftime("%B")
            date_str = f"{month_name} {today.year}"
            # Only valid if today is not in January (otherwise the
            # window contains today).
            result = classify_temporal_intent([{"text": date_str, "label": "DATE"}])
            if today.month > 1:
                assert result == "past"


# =====================================================================
# Open-Meteo wired seam: search() must dispatch from DATE entity, not
# from query-string keyword scan.
# =====================================================================


class TestOpenMeteoDispatch:
    """The Bug-1 class fix — historical-vs-forecast routing must come
    from the DATE entity (post-NF-20-B every claim has one)."""

    def _adapter_with_mocked_paths(self):
        adapter = OpenMeteoAdapter()
        adapter._extract_location_coords = MagicMock(
            return_value=(-18.0, 147.5, "Coral Sea")
        )
        adapter._get_historical = MagicMock(return_value=[])
        adapter._get_forecast = MagicMock(return_value=[])
        return adapter

    def test_past_date_routes_to_historical(self):
        adapter = self._adapter_with_mocked_paths()
        entities = [
            {"text": "Coral Sea", "label": "LOCATION"},
            {"text": "March 2024", "label": "DATE"},
        ]
        adapter.search("coral sea|march 2024", "Climate", "Global", entities=entities)
        adapter._get_historical.assert_called_once()
        adapter._get_forecast.assert_not_called()
        # Entities are passed through so _get_historical can derive window.
        args, kwargs = adapter._get_historical.call_args
        # entities is the 5th positional arg (lat, lon, name, query, entities)
        passed_entities = args[4] if len(args) >= 5 else kwargs.get("entities")
        assert passed_entities == entities

    def test_future_date_routes_to_forecast(self):
        adapter = self._adapter_with_mocked_paths()
        entities = [
            {"text": "Coral Sea", "label": "LOCATION"},
            {"text": "2050", "label": "DATE"},
        ]
        adapter.search("coral sea|2050", "Climate", "Global", entities=entities)
        adapter._get_forecast.assert_called_once()
        adapter._get_historical.assert_not_called()

    def test_no_date_routes_to_forecast(self):
        # Pre-NF-20-B behaviour preserved: dateless query → forecast.
        adapter = self._adapter_with_mocked_paths()
        entities = [{"text": "Coral Sea", "label": "LOCATION"}]
        adapter.search("coral sea|", "Climate", "Global", entities=entities)
        adapter._get_forecast.assert_called_once()
        adapter._get_historical.assert_not_called()

    def test_keyword_query_no_longer_routes_to_historical(self):
        # Bug-1 regression: the OLD logic scanned for "average" /
        # "climate" / "in 20" in the query. With cache-key queries
        # those substrings can appear coincidentally (e.g. claim
        # mentions "Climate"), routing to historical with no DATE.
        # The fix routes from the entity bag instead. A keyword
        # match with no DATE entity must NOT route to historical.
        adapter = self._adapter_with_mocked_paths()
        entities = [{"text": "Coral Sea", "label": "LOCATION"}]
        adapter.search(
            "coral sea|climate average record",
            "Climate",
            "Global",
            entities=entities,
        )
        adapter._get_historical.assert_not_called()
        adapter._get_forecast.assert_called_once()


# =====================================================================
# Open-Meteo _get_historical: derive date window from entities.
# =====================================================================


class TestOpenMeteoHistoricalWindow:
    @patch("httpx.Client")
    def test_uses_entity_date_for_archive_query(self, mock_client_cls):
        # March 2024 DATE → start_date=2024-03-01, end_date=2024-03-31
        # rather than hardcoded now-365d.
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"daily": {"time": []}}
        mock_response.raise_for_status = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_response
        mock_client_cls.return_value = mock_client

        adapter = OpenMeteoAdapter()
        adapter._get_historical(
            lat=-18.0,
            lon=147.5,
            location_name="Coral Sea",
            query="coral sea|march 2024",
            entities=[{"text": "March 2024", "label": "DATE"}],
        )

        # Check the params passed to httpx.get
        mock_client.get.assert_called_once()
        call_kwargs = mock_client.get.call_args.kwargs
        params = call_kwargs.get("params") or mock_client.get.call_args.args[-1]
        assert params["start_date"] == "2024-03-01"
        assert params["end_date"] == "2024-03-31"

    @patch("httpx.Client")
    def test_falls_back_to_recent_when_no_date(self, mock_client_cls):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"daily": {"time": []}}
        mock_response.raise_for_status = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_response
        mock_client_cls.return_value = mock_client

        adapter = OpenMeteoAdapter()
        adapter._get_historical(
            lat=51.5,
            lon=-0.13,
            location_name="London",
            query="london|",
            entities=None,
        )

        call_kwargs = mock_client.get.call_args.kwargs
        params = call_kwargs.get("params") or mock_client.get.call_args.args[-1]
        # Fallback: 365-day window ending today.
        today = datetime.now(timezone.utc)
        expected_end = today.strftime("%Y-%m-%d")
        expected_start = (today - timedelta(days=365)).strftime("%Y-%m-%d")
        assert params["end_date"] == expected_end
        assert params["start_date"] == expected_start


# =====================================================================
# WeatherAPI wired seam: search() must dispatch from DATE entity.
# =====================================================================


class TestWeatherAPIDispatch:
    def _adapter_with_mocked_paths(self):
        adapter = WeatherAPIAdapter()
        adapter.api_key = "test-key"  # ensure the no-key short-circuit is not hit
        adapter._extract_location = MagicMock(return_value="Coral Sea")
        adapter._get_historical = MagicMock(return_value=[])
        adapter._get_forecast = MagicMock(return_value=[])
        adapter._get_current_weather = MagicMock(return_value=[])
        return adapter

    def test_past_date_routes_to_historical(self):
        adapter = self._adapter_with_mocked_paths()
        entities = [
            {"text": "Coral Sea", "label": "LOCATION"},
            {"text": "March 2024", "label": "DATE"},
        ]
        adapter.search("coral sea|march 2024", "Weather", "Global", entities=entities)
        adapter._get_historical.assert_called_once()
        adapter._get_forecast.assert_not_called()
        adapter._get_current_weather.assert_not_called()
        # entities pass-through so _get_historical can derive the target day.
        args, kwargs = adapter._get_historical.call_args
        passed_entities = args[2] if len(args) >= 3 else kwargs.get("entities")
        assert passed_entities == entities

    def test_future_date_routes_to_forecast(self):
        adapter = self._adapter_with_mocked_paths()
        entities = [
            {"text": "Coral Sea", "label": "LOCATION"},
            {"text": "2050", "label": "DATE"},
        ]
        adapter.search("coral sea|2050", "Weather", "Global", entities=entities)
        adapter._get_forecast.assert_called_once()
        adapter._get_historical.assert_not_called()
        adapter._get_current_weather.assert_not_called()

    def test_current_intent_routes_to_current_weather(self):
        # No DATE → current intent → current weather (preserves old default).
        adapter = self._adapter_with_mocked_paths()
        entities = [{"text": "Coral Sea", "label": "LOCATION"}]
        adapter.search("coral sea|", "Weather", "Global", entities=entities)
        adapter._get_current_weather.assert_called_once()
        adapter._get_historical.assert_not_called()
        adapter._get_forecast.assert_not_called()

    def test_yesterday_keyword_no_longer_routes_to_historical_without_date(self):
        # Bug-1 regression: OLD logic scanned for "yesterday" in the
        # query and routed to historical even when no DATE entity was
        # present. New logic ignores query keywords entirely.
        adapter = self._adapter_with_mocked_paths()
        entities = [{"text": "Coral Sea", "label": "LOCATION"}]
        adapter.search(
            "coral sea|yesterday last week historical",
            "Weather",
            "Global",
            entities=entities,
        )
        adapter._get_historical.assert_not_called()
        # No DATE entity → current.
        adapter._get_current_weather.assert_called_once()


# =====================================================================
# WeatherAPI _get_historical: derive target date from entities.
# =====================================================================


class TestWeatherAPIHistoricalDate:
    @patch("httpx.Client")
    def test_uses_entity_date_for_history_query(self, mock_client_cls):
        # March 2024 DATE → dt=2024-03-01 (start of granularity window).
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "location": {"name": "Coral Sea", "country": "Australia"},
            "forecast": {"forecastday": []},
        }
        mock_response.raise_for_status = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_response
        mock_client_cls.return_value = mock_client

        adapter = WeatherAPIAdapter()
        adapter.api_key = "test-key"
        adapter._get_historical(
            location="Coral Sea",
            query="coral sea|march 2024",
            entities=[{"text": "March 2024", "label": "DATE"}],
        )

        mock_client.get.assert_called_once()
        # WeatherAPI uses GET on a URL with dt= query param embedded in
        # the URL string. Capture the URL and verify dt=2024-03-01.
        called_url = mock_client.get.call_args.args[0]
        assert "dt=2024-03-01" in called_url

    @patch("httpx.Client")
    def test_falls_back_to_yesterday_when_no_date(self, mock_client_cls):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "location": {"name": "London", "country": "UK"},
            "forecast": {"forecastday": []},
        }
        mock_response.raise_for_status = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_response
        mock_client_cls.return_value = mock_client

        adapter = WeatherAPIAdapter()
        adapter.api_key = "test-key"
        adapter._get_historical(location="London", query="london|", entities=None)

        called_url = mock_client.get.call_args.args[0]
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        assert f"dt={yesterday}" in called_url

    @patch("httpx.Client")
    def test_iso_date_format_used(self, mock_client_cls):
        # Day-level DATE: "19 July 2022" → start = anchor - 30d = 2022-06-19
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "location": {"name": "London", "country": "UK"},
            "forecast": {"forecastday": []},
        }
        mock_response.raise_for_status = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_response
        mock_client_cls.return_value = mock_client

        adapter = WeatherAPIAdapter()
        adapter.api_key = "test-key"
        adapter._get_historical(
            location="London",
            query="london|19 july 2022",
            entities=[{"text": "19 July 2022", "label": "DATE"}],
        )

        called_url = mock_client.get.call_args.args[0]
        assert "dt=2022-06-19" in called_url
