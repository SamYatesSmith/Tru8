"""
Climate and Weather API Adapters

Adapters for climate and weather data:
- NOAA CDO (Climate Data Online)
- WeatherAPI (Weather forecasts and conditions)
- Open-Meteo (Free weather data, no API key required)
"""

import logging
import re
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, timezone

from app.services.government_api_client import GovernmentAPIClient
from app.core.config import settings
from app.utils.adapter_query_helpers import extract_location_and_date

logger = logging.getLogger(__name__)


def _location_date_cache_key(
    entities: Optional[List[Dict[str, str]]] = None,
) -> str:
    """Shared B3.2/3/4 helper: produce a cache-keyable string from typed
    location/date entities, or "" to trigger the skip path.

    Climate adapters (NOAA CDO, WeatherAPI, Open-Meteo) all need a place
    and (typically) a time window to produce meaningful data. Without
    either, the API call returns garbage or fails outright — TRU-D44F-F326
    surfaced "Current Weather in London" results for a Climate Change Act
    claim because the adapters fell back to scanning claim text and
    matched "London" elsewhere.

    Returns ``f"{location}|{date}"`` (either half may be empty) when at
    least one is present, or ``""`` when both are absent. The combined
    string forms the search_with_cache cache key — different
    location/date combinations are kept in separate cache namespaces.
    """
    location, date = extract_location_and_date(entities)
    if not location and not date:
        return ""
    return f"{location or ''}|{date or ''}"


# ========== NOAA CDO ADAPTER (Global Climate Data) ==========


class NOAAAdapter(GovernmentAPIClient):
    """
    NOAA Climate Data Online (CDO) API Adapter.

    Covers: Climate
    Jurisdiction: Global (primarily US, but includes worldwide data)
    Rate limits: 5 requests/second, 10,000 requests/day
    API key: Required (token in header)

    Key datasets:
    - GHCND: Global Historical Climatology Network Daily
    - GSOM: Global Summary of Month
    - GSOY: Global Summary of Year
    - NORMAL_DLY/MLY/ANN: Climate normals
    """

    # NOAA dataset IDs for different climate data types
    DATASETS = {
        "daily": "GHCND",  # Global Historical Climatology Network Daily
        "monthly": "GSOM",  # Global Summary of Month
        "yearly": "GSOY",  # Global Summary of Year
        "normals": "NORMAL_ANN",  # Climate Normals
    }

    # Data type IDs for common climate variables
    DATA_TYPES = {
        "temperature": ["TAVG", "TMAX", "TMIN"],  # Average, max, min temp
        "precipitation": ["PRCP", "SNOW", "SNWD"],  # Precip, snowfall, snow depth
        "wind": ["AWND", "WSF2", "WSF5"],  # Avg wind, fastest 2-min, 5-sec
        "sea_level": ["MMSL"],  # Mean sea level
    }

    def __init__(self):
        super().__init__(
            api_name="NOAA CDO",
            base_url="https://www.ncei.noaa.gov/cdo-web/api/v2",
            api_key=settings.NOAA_API_KEY,
            cache_ttl=86400,  # 24 hours (climate data updates daily at most)
            timeout=15,
            max_results=10,
            emits_structural_metadata=True,  # NF-07-v2: climate observations, structural
        )

        # NOAA uses token header authentication
        if self.api_key:
            self.headers["token"] = self.api_key
            # Remove default Authorization header
            if "Authorization" in self.headers:
                del self.headers["Authorization"]

    def is_relevant_for_domain(self, domain: str, jurisdiction: str) -> bool:
        """NOAA covers Climate and Weather globally (historical climate data)."""
        return domain in ["Climate", "Weather"]

    def prepare_query(
        self,
        claim_text: str,
        entities: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        """B3.4: NOAA CDO needs a place and a time window. Skip when neither is named.

        NOAA's existing keyword router already self-rejects on claims with
        no climate-relevant keywords (verified TRU-D44F-F326). This adds
        the structural cache-key correctness so two claims about the same
        location/date share a cache namespace, and a third claim about
        unrelated topics doesn't poison that namespace via raw-claim-text
        keying.
        """
        del claim_text  # location/date come from entities only
        return _location_date_cache_key(entities)

    def search(
        self,
        query: str,
        domain: str,
        jurisdiction: str,
        entities: Optional[List[Dict[str, str]]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search NOAA CDO for climate data.

        Strategy:
        1. First get relevant datasets
        2. Then query for actual data based on claim type

        Args:
            query: Search query (e.g., "average temperature 2024", "sea level rise")
            domain: Climate
            jurisdiction: Any (NOAA has global data)
            entities: Optional NER entities for location extraction

        Returns:
            List of evidence dictionaries
        """
        if not self.is_relevant_for_domain(domain, jurisdiction):
            return []

        if not self.api_key:
            logger.warning("NOAA API key not configured, skipping")
            return []

        query_lower = query.lower()
        evidence = []

        try:
            # Fix 4a: Expanded keyword matching for better climate data retrieval
            temp_terms = [
                "temperature",
                "warm",
                "cold",
                "heat",
                "hot",
                "freeze",
                "frost",
                "record",
                "extreme",
                "anomaly",
                "degree",
                "celsius",
                "fahrenheit",
            ]
            precip_terms = [
                "rain",
                "precipitation",
                "snow",
                "flood",
                "drought",
                "storm",
                "hurricane",
                "cyclone",
            ]
            sea_terms = [
                "sea level",
                "ocean",
                "coastal",
                "tide",
                "ice",
                "glacier",
                "arctic",
                "antarctic",
            ]

            # Determine what type of climate data to fetch
            if any(term in query_lower for term in temp_terms):
                evidence.extend(self._search_temperature_data(query, entities))
            elif any(term in query_lower for term in precip_terms):
                evidence.extend(self._search_precipitation_data(query, entities))
            elif any(term in query_lower for term in sea_terms):
                evidence.extend(self._search_sea_level_data(query, entities))
            else:
                # Fix 4b: No keyword match - return empty instead of metadata catalog
                logger.info(
                    f"[NOAA] No keyword match for query, returning empty: {query[:50]}..."
                )
                return []

            return evidence

        except Exception as e:
            logger.error(f"NOAA search failed for '{query}': {e}")
            return []

    def _search_datasets(self, query: str) -> List[Dict[str, Any]]:
        """Dataset catalog search disabled (Fix 4b) - returns metadata, not evidence.

        Note: This method previously returned NOAA dataset catalog info like
        'GHCND: 1.0 data coverage...' which is not useful as evidence.
        Now returns empty to prevent confusing metadata in results.
        """
        logger.info(f"[NOAA] Dataset search bypassed (returns metadata, not evidence)")
        return []

    def _search_temperature_data(
        self, query: str, entities: Optional[List[Dict[str, str]]] = None
    ) -> List[Dict[str, Any]]:
        """Search for temperature-related climate data. Returns empty on failure."""
        location_id = self._extract_location_id(entities)

        params = {
            "datasetid": "GSOM",  # Global Summary of Month
            "datatypeid": "TAVG",  # Average temperature
            "limit": self.max_results,
            "sortfield": "date",
            "sortorder": "desc",
        }

        if location_id:
            params["locationid"] = location_id

        end_date = datetime.now(timezone.utc)
        start_date = datetime(end_date.year - 2, 1, 1)
        params["startdate"] = start_date.strftime("%Y-%m-%d")
        params["enddate"] = end_date.strftime("%Y-%m-%d")

        try:
            response = self._make_request("data", params=params)
            if response and "results" in response:
                return self._transform_data_response(response, "temperature")
        except Exception as e:
            logger.warning(f"NOAA temperature search failed: {e}")

        # PQ-06: Honest failure — no hardcoded fallback strings
        logger.info("[NOAA] Temperature data query returned no results")
        return []

    def _search_precipitation_data(
        self, query: str, entities: Optional[List[Dict[str, str]]] = None
    ) -> List[Dict[str, Any]]:
        """Search for precipitation-related climate data. Returns empty on failure."""
        location_id = self._extract_location_id(entities)

        params = {
            "datasetid": "GSOM",
            "datatypeid": "PRCP",  # Precipitation
            "limit": self.max_results,
            "sortfield": "date",
            "sortorder": "desc",
        }

        if location_id:
            params["locationid"] = location_id

        end_date = datetime.now(timezone.utc)
        start_date = datetime(end_date.year - 2, 1, 1)
        params["startdate"] = start_date.strftime("%Y-%m-%d")
        params["enddate"] = end_date.strftime("%Y-%m-%d")

        try:
            response = self._make_request("data", params=params)
            if response and "results" in response:
                return self._transform_data_response(response, "precipitation")
        except Exception as e:
            logger.warning(f"NOAA precipitation search failed: {e}")

        # PQ-06: Honest failure — no hardcoded fallback strings
        logger.info("[NOAA] Precipitation data query returned no results")
        return []

    def _search_sea_level_data(
        self, query: str, entities: Optional[List[Dict[str, str]]] = None
    ) -> List[Dict[str, Any]]:
        """Search for sea level data via NOAA CDO."""
        location_id = self._extract_location_id(entities)

        # Query GSOM dataset for mean sea level (MMSL) observations
        params = {
            "datasetid": "GSOM",
            "datatypeid": "MMSL",  # Mean sea level
            "limit": self.max_results,
            "sortfield": "date",
            "sortorder": "desc",
        }

        if location_id:
            params["locationid"] = location_id

        end_date = datetime.now(timezone.utc)
        start_date = datetime(end_date.year - 2, 1, 1)
        params["startdate"] = start_date.strftime("%Y-%m-%d")
        params["enddate"] = end_date.strftime("%Y-%m-%d")

        try:
            response = self._make_request("data", params=params)
            if response and "results" in response:
                return self._transform_data_response(response, "sea_level")
        except Exception as e:
            logger.warning(f"NOAA sea level search failed: {e}")

        # PQ-06: Honest failure — no hardcoded fallback strings
        logger.info("[NOAA] Sea level data query returned no results")
        return []

    def _extract_location_id(
        self, entities: Optional[List[Dict[str, str]]] = None
    ) -> Optional[str]:
        """Extract NOAA location ID from NER entities."""
        if not entities:
            return None

        # NOAA uses FIPS codes for US states and country codes globally
        # Example: FIPS:06 = California, FIPS:36 = New York
        for entity in entities:
            if entity.get("type") in ["GPE", "LOC"]:
                location = entity.get("text", "").upper()
                # Fix 4c: Expanded location mapping for global climate queries
                location_map = {
                    # US
                    "US": "FIPS:US",
                    "USA": "FIPS:US",
                    "UNITED STATES": "FIPS:US",
                    "CALIFORNIA": "FIPS:06",
                    "NEW YORK": "FIPS:36",
                    "TEXAS": "FIPS:48",
                    "FLORIDA": "FIPS:12",
                    "ALASKA": "FIPS:02",
                    "ARIZONA": "FIPS:04",
                    "COLORADO": "FIPS:08",
                    # UK
                    "UK": "FIPS:UK",
                    "UNITED KINGDOM": "FIPS:UK",
                    "BRITAIN": "FIPS:UK",
                    "ENGLAND": "FIPS:UK",
                    # Europe (NOAA uses FIPS 2-letter country codes)
                    "EUROPE": "FIPS:EU",
                    "GERMANY": "FIPS:GM",
                    "FRANCE": "FIPS:FR",
                    "SPAIN": "FIPS:SP",
                    "ITALY": "FIPS:IT",
                    "NETHERLANDS": "FIPS:NL",
                    "BELGIUM": "FIPS:BE",
                    "SWEDEN": "FIPS:SW",
                    "NORWAY": "FIPS:NO",
                    "DENMARK": "FIPS:DA",
                    "FINLAND": "FIPS:FI",
                    "POLAND": "FIPS:PL",
                    "AUSTRIA": "FIPS:AU",
                    # Asia-Pacific
                    "JAPAN": "FIPS:JA",
                    "CHINA": "FIPS:CH",
                    "AUSTRALIA": "FIPS:AS",
                    "INDIA": "FIPS:IN",
                    "SOUTH KOREA": "FIPS:KS",
                    # Other
                    "CANADA": "FIPS:CA",
                    "MEXICO": "FIPS:MX",
                    "BRAZIL": "FIPS:BR",
                    # Global - no filter for global queries
                    "GLOBAL": None,
                    "WORLD": None,
                    "WORLDWIDE": None,
                }
                if location in location_map:
                    return location_map[location]

        return None

    def _create_climate_evidence(
        self, title: str, snippet: str, url: str
    ) -> List[Dict[str, Any]]:
        """Create climate evidence dictionary."""
        evidence = self._create_evidence_dict(
            title=title,
            snippet=snippet,
            url=url,
            source_date=datetime.now(timezone.utc),
            metadata={
                "api_source": "NOAA CDO",
                "data_type": "climate",
                "authority": "US Government",
            },
        )
        return [evidence]

    def _transform_dataset_response(self, raw_response: Any) -> List[Dict[str, Any]]:
        """Transform NOAA dataset list response."""
        evidence_list = []

        for item in raw_response.get("results", []):
            try:
                evidence = self._create_evidence_dict(
                    title=item.get("name", "NOAA Dataset"),
                    snippet=f"{item.get('name')}: {item.get('datacoverage', 'N/A')} data coverage. "
                    f"Date range: {item.get('mindate', 'N/A')} to {item.get('maxdate', 'N/A')}",
                    url=f"https://www.ncei.noaa.gov/cdo-web/datasets/{item.get('id')}",
                    source_date=datetime.now(timezone.utc),
                    metadata={
                        "api_source": "NOAA CDO",
                        "dataset_id": item.get("id"),
                        "data_coverage": item.get("datacoverage"),
                    },
                )
                evidence_list.append(evidence)

            except Exception as e:
                logger.warning(f"Failed to parse NOAA dataset item: {e}")
                continue

        return evidence_list

    def _transform_data_response(
        self, raw_response: Any, data_type: str
    ) -> List[Dict[str, Any]]:
        """Transform NOAA data query response."""
        evidence_list = []

        # Group results by station for cleaner output
        results = raw_response.get("results", [])
        if not results:
            return []

        # Create summary evidence from results
        values = [r.get("value") for r in results if r.get("value") is not None]
        dates = [r.get("date") for r in results if r.get("date")]

        if values:
            avg_value = sum(values) / len(values)
            min_value = min(values)
            max_value = max(values)

            unit = "°C" if data_type == "temperature" else "mm"
            snippet = (
                f"NOAA {data_type} data summary: Average {avg_value:.1f}{unit}, "
                f"Range {min_value:.1f}-{max_value:.1f}{unit}. "
                f"Based on {len(values)} observations."
            )

            if dates:
                snippet += f" Data period: {dates[-1][:10]} to {dates[0][:10]}."

            evidence = self._create_evidence_dict(
                title=f"NOAA {data_type.title()} Observations",
                snippet=snippet,
                url="https://www.ncei.noaa.gov/cdo-web/",
                source_date=datetime.now(timezone.utc),
                metadata={
                    "api_source": "NOAA CDO",
                    "data_type": data_type,
                    "observation_count": len(values),
                    "average": avg_value,
                    "min": min_value,
                    "max": max_value,
                },
            )
            evidence_list.append(evidence)

        return evidence_list

    def _transform_response(self, raw_response: Any) -> List[Dict[str, Any]]:
        """Generic transform - delegates to specific methods."""
        return self._transform_dataset_response(raw_response)


# ========== WEATHERAPI ADAPTER ==========


class WeatherAPIAdapter(GovernmentAPIClient):
    """
    WeatherAPI.com Adapter.

    Covers: Weather (forecasts, current conditions, historical)
    Jurisdiction: Global
    Rate limits: 1,000,000 requests/month (free tier), commercial use OK
    API key: Required

    Features:
    - 3-day forecast (free tier)
    - Current conditions
    - Historical weather
    - Search/autocomplete locations
    """

    def __init__(self):
        super().__init__(
            api_name="WeatherAPI",
            base_url="https://api.weatherapi.com/v1",
            api_key=settings.WEATHER_API_KEY,
            cache_ttl=1800,  # 30 mins (weather updates frequently)
            timeout=10,
            max_results=5,
            emits_structural_metadata=True,  # NF-07-v2: weather observations, structural
        )

    def is_relevant_for_domain(self, domain: str, jurisdiction: str) -> bool:
        """WeatherAPI covers Weather globally."""
        return domain in ["Weather", "Climate"]

    def prepare_query(
        self,
        claim_text: str,
        entities: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        """B3.2: skip WeatherAPI when neither location nor date is in the claim.

        TRU-D44F-F326 surfaced "Current Weather in London" results for a
        Climate Change Act claim because the adapter fell back to scanning
        the raw claim text. Skipping cleanly is preferable to returning
        ostensibly-relevant-but-actually-noise results.
        """
        del claim_text
        return _location_date_cache_key(entities)

    def search(
        self,
        query: str,
        domain: str,
        jurisdiction: str,
        entities: Optional[List[Dict[str, str]]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search WeatherAPI for weather data.

        Args:
            query: Search query (e.g., "weather in London tomorrow", "temperature forecast")
            domain: Weather or Climate
            jurisdiction: Any (global coverage)
            entities: Optional NER entities for location extraction

        Returns:
            List of evidence dictionaries
        """
        if not self.is_relevant_for_domain(domain, jurisdiction):
            return []

        if not self.api_key:
            logger.warning("WeatherAPI key not configured, skipping")
            return []

        query_lower = query.lower()
        evidence = []

        try:
            # Extract location from entities or query
            location = self._extract_location(query, entities)

            if not location:
                logger.warning(
                    f"WeatherAPI: Could not determine location for query '{query}'"
                )
                return []

            # Determine what type of weather data to fetch
            if any(
                term in query_lower
                for term in ["forecast", "tomorrow", "next week", "will it"]
            ):
                evidence.extend(self._get_forecast(location, query))
            elif any(
                term in query_lower
                for term in ["yesterday", "last week", "was it", "historical"]
            ):
                evidence.extend(self._get_historical(location, query))
            else:
                # Default: get current conditions
                evidence.extend(self._get_current_weather(location, query))

            return evidence

        except Exception as e:
            logger.error(f"WeatherAPI search failed for '{query}': {e}")
            return []

    def _extract_location(
        self, query: str, entities: Optional[List[Dict[str, str]]] = None
    ) -> Optional[str]:
        """
        Extract location from query or entities.

        Returns:
            Location string (city name, coordinates, etc.) or None
        """
        location_name = None

        # Try to extract from entities first
        if entities:
            for entity in entities:
                if entity.get("label") in ["GPE", "LOC", "LOCATION"]:
                    location_name = entity.get("text")
                    break

        # If no entity, try to extract from query
        if not location_name:
            patterns = [
                r"(?:in|at|for|near)\s+([A-Z][a-zA-Z\s]+?)(?:\s+(?:today|tomorrow|this|next|will|is|was)|\?|$)",
                r"([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)\s+(?:weather|temperature|forecast|rain)",
            ]
            for pattern in patterns:
                match = re.search(pattern, query)
                if match:
                    location_name = match.group(1).strip()
                    break

        return location_name or None

    def _get_forecast(self, location: str, query: str) -> List[Dict[str, Any]]:
        """Get weather forecast for location."""
        evidence = []

        try:
            import httpx
            from urllib.parse import quote

            url = f"{self.base_url}/forecast.json?key={self.api_key}&q={quote(location)}&days=3&aqi=no"

            with httpx.Client(timeout=10) as client:
                response = client.get(url)
                response.raise_for_status()
                data = response.json()

            if not data or "forecast" not in data:
                return []

            location_info = data.get("location", {})
            location_name = f"{location_info.get('name', location)}, {location_info.get('country', '')}"
            forecast_days = data["forecast"].get("forecastday", [])

            # Build forecast summary
            forecast_lines = []
            for day in forecast_days:
                date = day.get("date", "")
                day_data = day.get("day", {})
                condition = day_data.get("condition", {}).get("text", "Unknown")
                max_temp = day_data.get("maxtemp_c", "N/A")
                min_temp = day_data.get("mintemp_c", "N/A")
                precip = day_data.get("totalprecip_mm", 0)

                line = f"{date}: {min_temp}°C - {max_temp}°C, {condition}"
                if precip > 0:
                    line += f", {precip}mm precipitation"
                forecast_lines.append(line)

            evidence.append(
                {
                    "title": f"3-Day Weather Forecast for {location_name}",
                    "url": f"https://www.weatherapi.com/weather/q/{quote(location)}",
                    "snippet": "\n".join(forecast_lines),
                    "source": "WeatherAPI.com",
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "metadata": {
                        "api_source": "WeatherAPI",
                        "data_type": "weather_forecast",
                        "location": location_name,
                        "forecast_days": len(forecast_days),
                    },
                }
            )

            return evidence

        except Exception as e:
            logger.error(f"WeatherAPI forecast fetch failed: {e}")
            return []

    def _get_current_weather(self, location: str, query: str) -> List[Dict[str, Any]]:
        """Get current weather conditions."""
        evidence = []

        try:
            import httpx
            from urllib.parse import quote

            url = f"{self.base_url}/current.json?key={self.api_key}&q={quote(location)}&aqi=no"

            with httpx.Client(timeout=10) as client:
                response = client.get(url)
                response.raise_for_status()
                data = response.json()

            if not data or "current" not in data:
                return []

            location_info = data.get("location", {})
            location_name = f"{location_info.get('name', location)}, {location_info.get('country', '')}"
            current = data["current"]

            temp = current.get("temp_c", "N/A")
            feels_like = current.get("feelslike_c", "N/A")
            humidity = current.get("humidity", "N/A")
            wind_kph = current.get("wind_kph", "N/A")
            condition = current.get("condition", {}).get("text", "Unknown")

            snippet = (
                f"Current weather in {location_name}:\n"
                f"Temperature: {temp}°C (feels like {feels_like}°C)\n"
                f"Conditions: {condition}\n"
                f"Humidity: {humidity}%\n"
                f"Wind: {wind_kph} km/h"
            )

            evidence.append(
                {
                    "title": f"Current Weather in {location_name}",
                    "url": f"https://www.weatherapi.com/weather/q/{quote(location)}",
                    "snippet": snippet,
                    "source": "WeatherAPI.com",
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "metadata": {
                        "api_source": "WeatherAPI",
                        "data_type": "current_weather",
                        "location": location_name,
                        "temperature_c": temp,
                        "condition": condition,
                    },
                }
            )

            return evidence

        except Exception as e:
            logger.error(f"WeatherAPI current weather fetch failed: {e}")
            return []

    def _get_historical(self, location: str, query: str) -> List[Dict[str, Any]]:
        """Get historical weather data (yesterday)."""
        evidence = []

        try:
            import httpx
            from urllib.parse import quote

            # Get yesterday's date
            yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
            url = f"{self.base_url}/history.json?key={self.api_key}&q={quote(location)}&dt={yesterday}"

            with httpx.Client(timeout=10) as client:
                response = client.get(url)
                response.raise_for_status()
                data = response.json()

            if not data or "forecast" not in data:
                return []

            location_info = data.get("location", {})
            location_name = f"{location_info.get('name', location)}, {location_info.get('country', '')}"
            forecast_days = data["forecast"].get("forecastday", [])

            if not forecast_days:
                return []

            day = forecast_days[0]
            day_data = day.get("day", {})
            condition = day_data.get("condition", {}).get("text", "Unknown")
            max_temp = day_data.get("maxtemp_c", "N/A")
            min_temp = day_data.get("mintemp_c", "N/A")
            avg_temp = day_data.get("avgtemp_c", "N/A")
            precip = day_data.get("totalprecip_mm", 0)

            snippet = (
                f"Weather in {location_name} on {yesterday}:\n"
                f"Temperature: {min_temp}°C - {max_temp}°C (avg: {avg_temp}°C)\n"
                f"Conditions: {condition}\n"
                f"Precipitation: {precip}mm"
            )

            evidence.append(
                {
                    "title": f"Historical Weather for {location_name} ({yesterday})",
                    "url": f"https://www.weatherapi.com/weather/q/{quote(location)}",
                    "snippet": snippet,
                    "source": "WeatherAPI.com",
                    "date": yesterday,
                    "metadata": {
                        "api_source": "WeatherAPI",
                        "data_type": "historical_weather",
                        "location": location_name,
                        "date": yesterday,
                    },
                }
            )

            return evidence

        except Exception as e:
            logger.error(f"WeatherAPI historical fetch failed: {e}")
            return []

    def _transform_response(self, raw_response: Any) -> List[Dict[str, Any]]:
        """Transform WeatherAPI response to standardized evidence format."""
        # Handled by specific methods above
        return []


# ========== OPEN-METEO ADAPTER ==========


class OpenMeteoAdapter(GovernmentAPIClient):
    """
    Open-Meteo Weather API Adapter.

    Covers: Weather, Climate
    Jurisdiction: Global (worldwide coverage)
    Free tier: Unlimited for non-commercial; commercial plans available
    API key: Not required
    Docs: https://open-meteo.com/en/docs
    """

    # Common city coordinates for location resolution
    CITY_COORDS = {
        "london": (51.51, -0.13),
        "new york": (40.71, -74.01),
        "washington": (38.90, -77.04),
        "los angeles": (34.05, -118.24),
        "chicago": (41.88, -87.63),
        "paris": (48.86, 2.35),
        "berlin": (52.52, 13.41),
        "tokyo": (35.68, 139.69),
        "sydney": (-33.87, 151.21),
        "beijing": (37.91, 116.39),
        "moscow": (55.76, 37.62),
        "mumbai": (19.08, 72.88),
        "dubai": (25.20, 55.27),
        "singapore": (1.35, 103.82),
        "toronto": (43.65, -79.38),
        "mexico city": (19.43, -99.13),
        "sao paulo": (-23.55, -46.63),
        "cairo": (30.04, 31.24),
        "lagos": (6.52, 3.38),
        "nairobi": (-1.29, 36.82),
        "manchester": (53.48, -2.24),
        "birmingham": (52.49, -1.90),
        "edinburgh": (55.95, -3.19),
        "glasgow": (55.86, -4.25),
        "dublin": (53.35, -6.26),
        "rome": (41.90, 12.50),
        "madrid": (40.42, -3.70),
        "amsterdam": (52.37, 4.90),
        "brussels": (50.85, 4.35),
        "zurich": (47.38, 8.54),
        "stockholm": (59.33, 18.07),
        "oslo": (59.91, 10.75),
        "copenhagen": (55.68, 12.57),
        "vienna": (48.21, 16.37),
        "warsaw": (52.23, 21.01),
        "athens": (37.98, 23.73),
        "istanbul": (41.01, 28.98),
        "bangkok": (13.76, 100.50),
        "hong kong": (22.32, 114.17),
        "seoul": (37.57, 127.00),
        "jakarta": (-6.21, 106.85),
        "buenos aires": (-34.60, -58.38),
        "lima": (-12.05, -77.04),
        "bogota": (4.71, -74.07),
        "johannesburg": (-26.20, 28.05),
        "cape town": (-33.93, 18.42),
    }

    def __init__(self):
        super().__init__(
            api_name="Open-Meteo",
            base_url="https://api.open-meteo.com/v1",
            api_key=None,
            cache_ttl=3600,  # 1 hour — weather data is time-sensitive
            timeout=10,
            max_results=3,
            emits_structural_metadata=True,  # NF-07-v2: weather observations, structural
        )
        # No auth headers needed
        self.headers = {}

    def is_relevant_for_domain(self, domain: str, jurisdiction: str) -> bool:
        """Open-Meteo covers Weather and Climate for all jurisdictions."""
        return domain in ["Weather", "Climate"]

    def prepare_query(
        self,
        claim_text: str,
        entities: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        """B3.3: skip Open-Meteo when neither location nor date is in the claim.

        TRU-D44F-F326 surfaced an irrelevant Open-Meteo item for a Climate
        Change Act claim. Same skip pattern as WeatherAPI / NOAA CDO —
        weather APIs need a place + a time, otherwise the result is
        guaranteed noise.
        """
        del claim_text
        return _location_date_cache_key(entities)

    def _extract_location_coords(
        self, query: str, entities: Optional[List[Dict[str, Any]]] = None
    ) -> Optional[tuple]:
        """Extract location coordinates from query or entities.

        Returns (lat, lon, location_name) or None.
        """
        location_name = None

        # Try entities first
        if entities:
            for entity in entities:
                if entity.get("label") in ["GPE", "LOC", "LOCATION"]:
                    location_name = entity.get("text")
                    break

        # Try regex extraction from query
        if not location_name:
            patterns = [
                r"(?:in|at|for|near)\s+([A-Z][a-zA-Z\s]+?)(?:\s+(?:today|tomorrow|this|next|will|is|was)|\?|$)",
                r"([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)\s+(?:weather|temperature|forecast|rain|snow|wind)",
            ]
            for pattern in patterns:
                match = re.search(pattern, query)
                if match:
                    location_name = match.group(1).strip()
                    break

        if not location_name:
            return None

        # Look up coordinates from our city map
        key = location_name.lower().strip()
        if key in self.CITY_COORDS:
            lat, lon = self.CITY_COORDS[key]
            return (lat, lon, location_name)

        # Try geocoding via Open-Meteo's geocoding API
        try:
            import httpx

            with httpx.Client(timeout=5) as client:
                resp = client.get(
                    "https://geocoding-api.open-meteo.com/v1/search",
                    params={"name": location_name, "count": 1, "format": "json"},
                )
                resp.raise_for_status()
                data = resp.json()
                results = data.get("results", [])
                if results:
                    r = results[0]
                    return (r["latitude"], r["longitude"], r.get("name", location_name))
        except Exception as e:
            logger.warning(f"Open-Meteo geocoding failed for '{location_name}': {e}")

        return None

    def search(
        self,
        query: str,
        domain: str,
        jurisdiction: str,
        entities: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        if not self.is_relevant_for_domain(domain, jurisdiction):
            return []

        coords = self._extract_location_coords(query, entities)
        if not coords:
            logger.info(f"Open-Meteo: Could not determine location for query '{query}'")
            return []

        lat, lon, location_name = coords
        query_lower = query.lower()
        evidence = []

        try:
            # Decide: forecast or historical
            is_historical = any(
                term in query_lower
                for term in [
                    "last year",
                    "historical",
                    "average",
                    "record",
                    "was the",
                    "in 20",
                    "in 19",
                    "climate",
                ]
            )

            if is_historical:
                evidence.extend(self._get_historical(lat, lon, location_name, query))
            else:
                evidence.extend(self._get_forecast(lat, lon, location_name, query))

        except Exception as e:
            logger.error(f"Open-Meteo search failed: {e}")

        return evidence

    def _get_forecast(
        self, lat: float, lon: float, location_name: str, query: str
    ) -> List[Dict[str, Any]]:
        """Get 7-day weather forecast."""
        try:
            import httpx

            params = {
                "latitude": lat,
                "longitude": lon,
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,weathercode",
                "timezone": "auto",
                "forecast_days": 7,
            }

            with httpx.Client(timeout=self.timeout) as client:
                resp = client.get(f"{self.base_url}/forecast", params=params)
                resp.raise_for_status()
                data = resp.json()

            daily = data.get("daily", {})
            dates = daily.get("time", [])
            max_temps = daily.get("temperature_2m_max", [])
            min_temps = daily.get("temperature_2m_min", [])
            precip = daily.get("precipitation_sum", [])

            if not dates:
                return []

            # Build forecast summary
            lines = []
            for i, date in enumerate(dates):
                t_max = max_temps[i] if i < len(max_temps) else "?"
                t_min = min_temps[i] if i < len(min_temps) else "?"
                rain = precip[i] if i < len(precip) else 0
                line = f"{date}: {t_min}°C – {t_max}°C"
                if rain and rain > 0:
                    line += f", {rain}mm rain"
                lines.append(line)

            snippet = (
                f"7-day forecast for {location_name}: {'; '.join(lines)}. "
                f"Source: Open-Meteo (ERA5 + ECMWF)."
            )

            return [
                self._create_evidence_dict(
                    title=f"Weather Forecast — {location_name}",
                    snippet=snippet,
                    url=f"https://open-meteo.com/en/docs#latitude={lat}&longitude={lon}",
                    source_date=datetime.fromisoformat(dates[0]) if dates else None,
                    metadata={
                        "location": location_name,
                        "latitude": lat,
                        "longitude": lon,
                        "forecast_days": len(dates),
                        "data_source": "ECMWF IFS",
                    },
                )
            ]

        except Exception as e:
            logger.error(f"Open-Meteo forecast failed: {e}")
            return []

    def _get_historical(
        self, lat: float, lon: float, location_name: str, query: str
    ) -> List[Dict[str, Any]]:
        """Get historical climate data (last 12 months)."""
        try:
            import httpx

            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=365)

            params = {
                "latitude": lat,
                "longitude": lon,
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d"),
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
                "timezone": "auto",
            }

            with httpx.Client(timeout=self.timeout) as client:
                resp = client.get(
                    "https://archive-api.open-meteo.com/v1/archive", params=params
                )
                resp.raise_for_status()
                data = resp.json()

            daily = data.get("daily", {})
            max_temps = daily.get("temperature_2m_max", [])
            min_temps = daily.get("temperature_2m_min", [])
            precip_vals = daily.get("precipitation_sum", [])

            if not max_temps:
                return []

            # Compute summary statistics
            valid_max = [t for t in max_temps if t is not None]
            valid_min = [t for t in min_temps if t is not None]
            valid_precip = [p for p in precip_vals if p is not None]

            avg_max = sum(valid_max) / len(valid_max) if valid_max else 0
            avg_min = sum(valid_min) / len(valid_min) if valid_min else 0
            total_precip = sum(valid_precip)
            peak_max = max(valid_max) if valid_max else 0
            lowest_min = min(valid_min) if valid_min else 0

            snippet = (
                f"Historical weather for {location_name} "
                f"({start_date.strftime('%b %Y')} – {end_date.strftime('%b %Y')}): "
                f"Average high {avg_max:.1f}°C, average low {avg_min:.1f}°C. "
                f"Peak high {peak_max:.1f}°C, lowest low {lowest_min:.1f}°C. "
                f"Total precipitation {total_precip:.0f}mm. "
                f"Source: Open-Meteo (ERA5 reanalysis)."
            )

            return [
                self._create_evidence_dict(
                    title=f"Historical Climate Data — {location_name}",
                    snippet=snippet,
                    url=f"https://open-meteo.com/en/docs#latitude={lat}&longitude={lon}",
                    source_date=end_date,
                    metadata={
                        "location": location_name,
                        "latitude": lat,
                        "longitude": lon,
                        "period_start": start_date.strftime("%Y-%m-%d"),
                        "period_end": end_date.strftime("%Y-%m-%d"),
                        "avg_high_c": round(avg_max, 1),
                        "avg_low_c": round(avg_min, 1),
                        "total_precip_mm": round(total_precip, 0),
                        "data_source": "ERA5 reanalysis",
                    },
                )
            ]

        except Exception as e:
            logger.error(f"Open-Meteo historical fetch failed: {e}")
            return []

    def _transform_response(self, raw_response: Any) -> List[Dict[str, Any]]:
        """Generic transform — handled by specific methods above."""
        return []
