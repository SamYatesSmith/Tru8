"""
Climate and Weather API Adapters

Adapters for climate and weather data:
- NOAA CDO (Climate Data Online)
- WeatherAPI (Weather forecasts and conditions)
"""

import logging
import re
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from app.services.government_api_client import GovernmentAPIClient
from app.core.config import settings

logger = logging.getLogger(__name__)


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
        """Search for temperature-related climate data."""
        # Extract location from entities if available
        location_id = self._extract_location_id(entities)

        # Get recent temperature data
        params = {
            "datasetid": "GSOM",  # Global Summary of Month
            "datatypeid": "TAVG",  # Average temperature
            "limit": self.max_results,
            "sortfield": "date",
            "sortorder": "desc",
        }

        if location_id:
            params["locationid"] = location_id

        # Set date range (last 2 years)
        end_date = datetime.utcnow()
        start_date = datetime(end_date.year - 2, 1, 1)
        params["startdate"] = start_date.strftime("%Y-%m-%d")
        params["enddate"] = end_date.strftime("%Y-%m-%d")

        try:
            response = self._make_request("data", params=params)
            if response and "results" in response:
                return self._transform_data_response(response, "temperature")
        except Exception as e:
            logger.warning(f"NOAA temperature search failed: {e}")

        # Fallback to dataset info
        return self._create_climate_evidence(
            "NOAA Global Temperature Data",
            "NOAA maintains comprehensive temperature records from thousands of weather stations worldwide, "
            "including the Global Historical Climatology Network (GHCND) with daily temperature observations.",
            "https://www.ncei.noaa.gov/access/monitoring/climate-at-a-glance/global/time-series",
        )

    def _search_precipitation_data(
        self, query: str, entities: Optional[List[Dict[str, str]]] = None
    ) -> List[Dict[str, Any]]:
        """Search for precipitation-related climate data."""
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

        end_date = datetime.utcnow()
        start_date = datetime(end_date.year - 2, 1, 1)
        params["startdate"] = start_date.strftime("%Y-%m-%d")
        params["enddate"] = end_date.strftime("%Y-%m-%d")

        try:
            response = self._make_request("data", params=params)
            if response and "results" in response:
                return self._transform_data_response(response, "precipitation")
        except Exception as e:
            logger.warning(f"NOAA precipitation search failed: {e}")

        return self._create_climate_evidence(
            "NOAA Precipitation Data",
            "NOAA provides precipitation data including rainfall, snowfall, and drought indices "
            "from the Global Historical Climatology Network and other monitoring systems.",
            "https://www.ncei.noaa.gov/access/monitoring/climate-at-a-glance/global/time-series",
        )

    def _search_sea_level_data(
        self, query: str, entities: Optional[List[Dict[str, str]]] = None
    ) -> List[Dict[str, Any]]:
        """Search for sea level data."""
        # Sea level data requires specific tide gauge stations
        # Return authoritative NOAA sea level info
        return self._create_climate_evidence(
            "NOAA Sea Level Rise Data",
            "NOAA's tide gauge and satellite altimetry data shows global mean sea level has risen "
            "about 3.4 mm per year since 1993. Long-term records from tide gauges show approximately "
            "8-9 inches of sea level rise since 1880.",
            "https://www.climate.gov/news-features/understanding-climate/climate-change-global-sea-level",
        )

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
            source_date=datetime.utcnow(),
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
                    source_date=datetime.utcnow(),
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
                source_date=datetime.utcnow(),
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
        )

    def is_relevant_for_domain(self, domain: str, jurisdiction: str) -> bool:
        """WeatherAPI covers Weather globally."""
        return domain in ["Weather", "Climate"]

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

        # Default to London if no location found
        return location_name or "London"

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
