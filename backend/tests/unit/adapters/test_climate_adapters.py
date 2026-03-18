"""
Unit Tests for Climate API Adapters

Tests for the 3 climate/weather adapters:
- NOAA CDO (Climate Data Online)
- WeatherAPI (Weather forecasts and conditions)
- Open-Meteo (Free weather data, no API key required)
"""

import pytest
from datetime import datetime, timezone
from app.services.api_adapters import NOAAAdapter, WeatherAPIAdapter, OpenMeteoAdapter


class TestNOAAAdapter:
    """Test suite for NOAA CDO (Climate Data Online) adapter."""

    def test_instantiation(self):
        """Test NOAA adapter instantiates correctly."""
        adapter = NOAAAdapter()
        assert adapter.api_name == "NOAA CDO"
        assert "ncei.noaa.gov" in adapter.base_url
        assert adapter.cache_ttl == 86400  # 24 hours

    def test_is_relevant_for_domain(self):
        """Test NOAA domain relevance."""
        adapter = NOAAAdapter()

        # Should be relevant for Climate and Weather (any jurisdiction)
        assert adapter.is_relevant_for_domain("Climate", "Global") is True
        assert adapter.is_relevant_for_domain("Climate", "US") is True
        assert adapter.is_relevant_for_domain("Climate", "UK") is True
        assert adapter.is_relevant_for_domain("Weather", "Global") is True

        # Should not be relevant for other domains
        assert adapter.is_relevant_for_domain("Finance", "US") is False
        assert adapter.is_relevant_for_domain("Health", "Global") is False
        assert adapter.is_relevant_for_domain("Politics", "UK") is False

    def test_transform_response(self):
        """Test NOAA dataset response transformation."""
        adapter = NOAAAdapter()

        # _transform_response delegates to _transform_dataset_response
        mock_response = {
            "results": [
                {
                    "id": "GHCND",
                    "name": "Global Historical Climatology Network Daily",
                    "datacoverage": 1.0,
                    "mindate": "1763-01-01",
                    "maxdate": "2026-03-15",
                }
            ]
        }

        result = adapter._transform_response(mock_response)

        assert len(result) == 1
        assert "Global Historical Climatology Network Daily" in result[0]["title"]
        assert result[0]["external_source_provider"] == "NOAA CDO"
        assert result[0]["metadata"]["dataset_id"] == "GHCND"
        assert result[0]["metadata"]["data_coverage"] == 1.0
        assert "ncei.noaa.gov" in result[0]["url"]

    def test_transform_data_response(self):
        """Test NOAA observation data transformation."""
        adapter = NOAAAdapter()

        mock_response = {
            "results": [
                {
                    "date": "2026-01-15T00:00:00",
                    "datatype": "TAVG",
                    "station": "GHCND:USW00094728",
                    "value": 5.2,
                },
                {
                    "date": "2026-02-15T00:00:00",
                    "datatype": "TAVG",
                    "station": "GHCND:USW00094728",
                    "value": 7.8,
                },
                {
                    "date": "2026-03-15T00:00:00",
                    "datatype": "TAVG",
                    "station": "GHCND:USW00094728",
                    "value": 12.3,
                },
            ]
        }

        result = adapter._transform_data_response(mock_response, "temperature")

        assert len(result) == 1
        assert "Temperature" in result[0]["title"]
        assert result[0]["external_source_provider"] == "NOAA CDO"
        assert result[0]["metadata"]["data_type"] == "temperature"
        assert result[0]["metadata"]["observation_count"] == 3
        assert result[0]["metadata"]["min"] == 5.2
        assert result[0]["metadata"]["max"] == 12.3
        # Average of 5.2, 7.8, 12.3 = 8.43...
        assert abs(result[0]["metadata"]["average"] - 8.43) < 0.1
        assert "ncei.noaa.gov" in result[0]["url"]

    def test_empty_response(self):
        """Test NOAA returns empty list for empty/None input."""
        adapter = NOAAAdapter()

        assert adapter._transform_response({}) == []
        assert adapter._transform_response({"results": []}) == []
        assert adapter._transform_data_response({}, "temperature") == []
        assert adapter._transform_data_response({"results": []}, "temperature") == []


class TestWeatherAPIAdapter:
    """Test suite for WeatherAPI adapter."""

    def test_instantiation(self):
        """Test WeatherAPI adapter instantiates correctly."""
        adapter = WeatherAPIAdapter()
        assert adapter.api_name == "WeatherAPI"
        assert "api.weatherapi.com" in adapter.base_url
        assert adapter.cache_ttl == 1800  # 30 minutes

    def test_is_relevant_for_domain(self):
        """Test WeatherAPI domain relevance."""
        adapter = WeatherAPIAdapter()

        # Should be relevant for Weather and Climate (any jurisdiction)
        assert adapter.is_relevant_for_domain("Weather", "Global") is True
        assert adapter.is_relevant_for_domain("Weather", "UK") is True
        assert adapter.is_relevant_for_domain("Weather", "US") is True
        assert adapter.is_relevant_for_domain("Climate", "Global") is True

        # Should not be relevant for other domains
        assert adapter.is_relevant_for_domain("Finance", "US") is False
        assert adapter.is_relevant_for_domain("Health", "Global") is False
        assert adapter.is_relevant_for_domain("Politics", "UK") is False

    def test_transform_response(self):
        """Test WeatherAPI response transformation.

        WeatherAPI handles transformation inline in specific methods
        (_get_forecast, _get_current_weather, _get_historical) rather than
        through _transform_response. Verify the evidence format from those
        methods by testing the evidence dict structure they produce.
        """
        adapter = WeatherAPIAdapter()

        # _transform_response returns [] because transformation is handled
        # by _get_forecast/_get_current_weather/_get_historical directly.
        # Verify _create_evidence_dict produces correct format.
        evidence = adapter._create_evidence_dict(
            title="Current Weather in London, United Kingdom",
            snippet="Temperature: 12°C (feels like 10°C)\nConditions: Partly cloudy",
            url="https://www.weatherapi.com/weather/q/London",
            source_date=None,
            metadata={
                "api_source": "WeatherAPI",
                "data_type": "current_weather",
                "location": "London, United Kingdom",
                "temperature_c": 12,
                "condition": "Partly cloudy",
            },
        )

        assert evidence["title"] == "Current Weather in London, United Kingdom"
        assert evidence["external_source_provider"] == "WeatherAPI"
        assert evidence["metadata"]["api_source"] == "WeatherAPI"
        assert evidence["metadata"]["data_type"] == "current_weather"
        assert evidence["metadata"]["temperature_c"] == 12
        assert "weatherapi.com" in evidence["url"]

    def test_empty_response(self):
        """Test WeatherAPI returns empty list for empty/None input."""
        adapter = WeatherAPIAdapter()

        assert adapter._transform_response({}) == []
        assert adapter._transform_response(None) == []
        assert adapter._transform_response({"current": {}}) == []

    def test_extract_location(self):
        """Test WeatherAPI location extraction from entities."""
        adapter = WeatherAPIAdapter()

        # With entities
        entities = [{"label": "GPE", "text": "London"}]
        assert adapter._extract_location("weather in London", entities) == "London"

        # Without entities — regex extraction
        result = adapter._extract_location("weather in London tomorrow", None)
        assert result == "London"

        # No location found
        assert adapter._extract_location("what is the temperature", None) is None


class TestOpenMeteoAdapter:
    """Test suite for Open-Meteo adapter."""

    def test_instantiation(self):
        """Test Open-Meteo adapter instantiates correctly."""
        adapter = OpenMeteoAdapter()
        assert adapter.api_name == "Open-Meteo"
        assert "api.open-meteo.com" in adapter.base_url
        assert adapter.cache_ttl == 3600  # 1 hour

    def test_is_relevant_for_domain(self):
        """Test Open-Meteo domain relevance."""
        adapter = OpenMeteoAdapter()

        # Should be relevant for Weather and Climate (any jurisdiction)
        assert adapter.is_relevant_for_domain("Weather", "Global") is True
        assert adapter.is_relevant_for_domain("Weather", "UK") is True
        assert adapter.is_relevant_for_domain("Weather", "US") is True
        assert adapter.is_relevant_for_domain("Climate", "Global") is True
        assert adapter.is_relevant_for_domain("Climate", "UK") is True

        # Should not be relevant for other domains
        assert adapter.is_relevant_for_domain("Finance", "US") is False
        assert adapter.is_relevant_for_domain("Health", "Global") is False
        assert adapter.is_relevant_for_domain("Politics", "UK") is False

    def test_transform_response(self):
        """Test Open-Meteo response transformation.

        Open-Meteo handles transformation inline in _get_forecast and
        _get_historical rather than through _transform_response. Verify
        the evidence dict structure produced by _create_evidence_dict.
        """
        adapter = OpenMeteoAdapter()

        # Verify _create_evidence_dict produces correct format for Open-Meteo
        evidence = adapter._create_evidence_dict(
            title="Weather Forecast — London",
            snippet="7-day forecast for London: 2026-03-10: 4°C – 11°C; "
            "2026-03-11: 5°C – 13°C. Source: Open-Meteo (ERA5 + ECMWF).",
            url="https://open-meteo.com/en/docs#latitude=51.51&longitude=-0.13",
            source_date=datetime(2026, 3, 10, tzinfo=timezone.utc),
            metadata={
                "location": "London",
                "latitude": 51.51,
                "longitude": -0.13,
                "forecast_days": 7,
                "data_source": "ECMWF IFS",
            },
        )

        assert evidence["title"] == "Weather Forecast — London"
        assert evidence["external_source_provider"] == "Open-Meteo"
        assert evidence["metadata"]["location"] == "London"
        assert evidence["metadata"]["latitude"] == 51.51
        assert evidence["metadata"]["longitude"] == -0.13
        assert evidence["metadata"]["forecast_days"] == 7
        assert evidence["metadata"]["data_source"] == "ECMWF IFS"
        assert "open-meteo.com" in evidence["url"]

    def test_empty_response(self):
        """Test Open-Meteo returns empty list for empty/None input."""
        adapter = OpenMeteoAdapter()

        assert adapter._transform_response({}) == []
        assert adapter._transform_response(None) == []
        assert adapter._transform_response({"daily": {}}) == []

    def test_city_coords_lookup(self):
        """Test Open-Meteo built-in city coordinate lookup."""
        adapter = OpenMeteoAdapter()

        assert "london" in adapter.CITY_COORDS
        assert adapter.CITY_COORDS["london"] == (51.51, -0.13)

        assert "new york" in adapter.CITY_COORDS
        assert adapter.CITY_COORDS["new york"] == (40.71, -74.01)

        assert "tokyo" in adapter.CITY_COORDS
        assert adapter.CITY_COORDS["tokyo"] == (35.68, 139.69)


class TestClimateAdapterCommonFeatures:
    """Test common features across all climate adapters."""

    @pytest.mark.parametrize(
        "adapter_class",
        [NOAAAdapter, WeatherAPIAdapter, OpenMeteoAdapter],
    )
    def test_adapter_has_required_methods(self, adapter_class):
        """Test each climate adapter implements required methods."""
        adapter = adapter_class()

        assert hasattr(adapter, "search")
        assert hasattr(adapter, "_transform_response")
        assert hasattr(adapter, "is_relevant_for_domain")
        assert callable(adapter.search)
        assert callable(adapter._transform_response)
        assert callable(adapter.is_relevant_for_domain)

    @pytest.mark.parametrize(
        "adapter_class",
        [NOAAAdapter, WeatherAPIAdapter, OpenMeteoAdapter],
    )
    def test_adapter_has_correct_attributes(self, adapter_class):
        """Test each climate adapter has correct attributes."""
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
        [NOAAAdapter, WeatherAPIAdapter, OpenMeteoAdapter],
    )
    def test_adapter_creates_valid_evidence_dict(self, adapter_class):
        """Test each climate adapter creates valid evidence dictionaries."""
        adapter = adapter_class()

        evidence = adapter._create_evidence_dict(
            title="Test Climate Title",
            snippet="Test climate snippet",
            url="https://example.com/climate",
            source_date=None,
            metadata={"test": "climate_data"},
        )

        # Verify required fields
        assert "title" in evidence
        assert "snippet" in evidence
        assert "url" in evidence
        assert "source" in evidence
        assert "external_source_provider" in evidence
        assert "metadata" in evidence

        # Verify values
        assert evidence["title"] == "Test Climate Title"
        assert evidence["snippet"] == "Test climate snippet"
        assert evidence["url"] == "https://example.com/climate"
        assert evidence["external_source_provider"] == adapter.api_name
