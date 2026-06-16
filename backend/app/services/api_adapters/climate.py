"""
Climate and Weather API Adapters

Adapters for climate and weather data:
- NOAA CDO (Climate Data Online)
- WeatherAPI (Weather forecasts and conditions)
- Open-Meteo (Free weather data, no API key required)
"""

import logging
import re
from typing import List, Dict, Any, Optional, Tuple
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


# ===== NF-18 helpers (NOAA-specific) =====
#
# NF-18 surfaced three Session-B regressions in NOAAAdapter:
#   Bug-1 (data-type rejection): search() classified climate data type by
#     scanning `query`, but Session B made `query` the cache-key shape
#     ("London|2022-07-19") which never contains climate keywords →
#     every NOAA call returned []. Fixed by classifying in prepare_query
#     where claim_text is in scope, and encoding the result in the cache
#     key prefix (data_type|location|date).
#   Bug-2 (date window): _search_*_data hardcoded the window to
#     now()-2y → now(), ignoring the DATE entity. A claim about July 2022
#     queried 2024-2026.
#   Bug-3 (location map): _extract_location_id only knew country/state
#     names, so "London" → None → unfiltered global query (US-heavy).
#     The CITY_TO_COUNTRY_FIPS map below restores city → country routing.
# Diagnostic record: audit/pipeline-issues/2026-04-22_remediation-plan.md §S8.

# Data-type classification keywords. Walked in declaration order — first
# match wins. Order matters: most-specific categories (precipitation,
# sea_level) come before temperature (the catch-all default). Keep terms
# narrow and unambiguous: generic words like "record" / "extreme" /
# "anomaly" are deliberately omitted because they appear in
# precipitation claims too ("rainfall record", "extreme flooding") and
# would mis-classify them as temperature.
_NOAA_DATA_TYPE_TERMS: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    (
        "precipitation",
        (
            "rain",
            "rainfall",
            "precipitation",
            "snow",
            "snowfall",
            "flood",
            "drought",
            "storm",
            "hurricane",
            "cyclone",
            "typhoon",
            "blizzard",
            "monsoon",
            "deluge",
        ),
    ),
    (
        "sea_level",
        (
            "sea level",
            "ocean",
            "coastal",
            "tide",
            "ice cap",
            "ice sheet",
            "glacier",
            "arctic",
            "antarctic",
            "permafrost",
            "iceberg",
        ),
    ),
    (
        "temperature",
        (
            "temperature",
            "warm",
            "cold",
            "heat",
            "hot",
            "freeze",
            "frost",
            "degree",
            "celsius",
            "fahrenheit",
            "heatwave",
            "heat wave",
            "warming",
            "warmest",
            "hottest",
            "coldest",
            "°c",
            "°f",
        ),
    ),
)


def _classify_noaa_data_type(
    claim_text: str,
    entities: Optional[List[Dict[str, str]]] = None,
) -> str:
    """Pick a NOAA data type ('temperature' / 'precipitation' / 'sea_level').

    Walks _NOAA_DATA_TYPE_TERMS in declaration order. First pass scans
    AMOUNT entities (most specific — units like "40.3°C" or "12 mm" are
    unambiguous); second pass scans the raw claim text. Defaults to
    "temperature" when nothing matches — temperature is NOAA's most
    populated dataset and the most common climate-claim type.
    """
    # Pass 1: AMOUNT entity scan (most specific).
    if entities:
        for ent in entities:
            if not isinstance(ent, dict):
                continue
            if ent.get("label") != "AMOUNT":
                continue
            etext = (ent.get("text") or "").lower().strip()
            if not etext:
                continue
            for data_type, terms in _NOAA_DATA_TYPE_TERMS:
                if any(t in etext for t in terms):
                    return data_type

    # Pass 2: raw claim text scan.
    cl = (claim_text or "").lower()
    for data_type, terms in _NOAA_DATA_TYPE_TERMS:
        if any(t in cl for t in terms):
            return data_type

    return "temperature"


# City → NOAA FIPS country code (or US state FIPS). Mirrors
# OpenMeteoAdapter.CITY_COORDS so the three climate adapters agree on
# which city names are recognised, then maps to the country/state code
# NOAA's locationid parameter expects.
#
# Maintained centrally rather than per-adapter so adding a new city is
# one edit. Country granularity is sufficient for NOAA — non-US data is
# served as a single rolled-up station per country (e.g. GHCND:UK000000000).
_NOAA_CITY_TO_FIPS: Dict[str, str] = {
    # UK
    "london": "FIPS:UK",
    "manchester": "FIPS:UK",
    "birmingham": "FIPS:UK",
    "edinburgh": "FIPS:UK",
    "glasgow": "FIPS:UK",
    "liverpool": "FIPS:UK",
    "cardiff": "FIPS:UK",
    "belfast": "FIPS:UK",
    "leeds": "FIPS:UK",
    "bristol": "FIPS:UK",
    # US (city → state FIPS where the city is unambiguous)
    "new york": "FIPS:36",
    "new york city": "FIPS:36",
    "los angeles": "FIPS:06",
    "san francisco": "FIPS:06",
    "san diego": "FIPS:06",
    "sacramento": "FIPS:06",
    "chicago": "FIPS:17",
    "houston": "FIPS:48",
    "dallas": "FIPS:48",
    "austin": "FIPS:48",
    "san antonio": "FIPS:48",
    "miami": "FIPS:12",
    "orlando": "FIPS:12",
    "jacksonville": "FIPS:12",
    "phoenix": "FIPS:04",
    "philadelphia": "FIPS:42",
    "boston": "FIPS:25",
    "seattle": "FIPS:53",
    "denver": "FIPS:08",
    "washington": "FIPS:DC",
    "washington dc": "FIPS:DC",
    "washington d.c.": "FIPS:DC",
    # Ireland
    "dublin": "FIPS:EI",
    # Continental Europe
    "paris": "FIPS:FR",
    "marseille": "FIPS:FR",
    "lyon": "FIPS:FR",
    "berlin": "FIPS:GM",
    "munich": "FIPS:GM",
    "hamburg": "FIPS:GM",
    "rome": "FIPS:IT",
    "milan": "FIPS:IT",
    "madrid": "FIPS:SP",
    "barcelona": "FIPS:SP",
    "amsterdam": "FIPS:NL",
    "brussels": "FIPS:BE",
    "zurich": "FIPS:SZ",
    "geneva": "FIPS:SZ",
    "stockholm": "FIPS:SW",
    "oslo": "FIPS:NO",
    "copenhagen": "FIPS:DA",
    "vienna": "FIPS:AU",
    "warsaw": "FIPS:PL",
    "athens": "FIPS:GR",
    # Middle East / Asia / Pacific
    "istanbul": "FIPS:TU",
    "tokyo": "FIPS:JA",
    "osaka": "FIPS:JA",
    "beijing": "FIPS:CH",
    "shanghai": "FIPS:CH",
    "hong kong": "FIPS:HK",
    "seoul": "FIPS:KS",
    "bangkok": "FIPS:TH",
    "jakarta": "FIPS:ID",
    "singapore": "FIPS:SN",
    "mumbai": "FIPS:IN",
    "new delhi": "FIPS:IN",
    "delhi": "FIPS:IN",
    "dubai": "FIPS:AE",
    "abu dhabi": "FIPS:AE",
    "sydney": "FIPS:AS",
    "melbourne": "FIPS:AS",
    # Americas (non-US)
    "toronto": "FIPS:CA",
    "vancouver": "FIPS:CA",
    "montreal": "FIPS:CA",
    "mexico city": "FIPS:MX",
    "sao paulo": "FIPS:BR",
    "rio de janeiro": "FIPS:BR",
    "buenos aires": "FIPS:AR",
    "lima": "FIPS:PE",
    "bogota": "FIPS:CO",
    # Africa
    "cairo": "FIPS:EG",
    "lagos": "FIPS:NI",
    "nairobi": "FIPS:KE",
    "johannesburg": "FIPS:SF",
    "cape town": "FIPS:SF",
}


# Date-string parsing patterns, walked in priority order. Each returns
# the parsed components present in the string. We don't use dateutil to
# avoid surprising autocorrects on partial dates like "2022".
_NOAA_MONTH_NAMES: Dict[str, int] = {
    "january": 1,
    "jan": 1,
    "february": 2,
    "feb": 2,
    "march": 3,
    "mar": 3,
    "april": 4,
    "apr": 4,
    "may": 5,
    "june": 6,
    "jun": 6,
    "july": 7,
    "jul": 7,
    "august": 8,
    "aug": 8,
    "september": 9,
    "sep": 9,
    "sept": 9,
    "october": 10,
    "oct": 10,
    "november": 11,
    "nov": 11,
    "december": 12,
    "dec": 12,
}


def _parse_date_anchor(
    date_text: Optional[str],
) -> Optional[Tuple[datetime, datetime]]:
    """Parse a DATE entity text into a granularity-matched (start, end) window.

    Returns ``None`` when ``date_text`` is missing or no year can be
    extracted. Unlike :func:`_parse_date_window` there is no fallback —
    callers can distinguish "could not determine temporal scope" from
    "found a parseable window".

    Granularity inference (mirrors :func:`_parse_date_window`):
      * day+month+year ("19 July 2022", "2022-07-19")  → ±30 days
      * month+year ("July 2022", "2022-07")            → whole month
      * year only ("2022")                              → whole year

    Used by :func:`classify_temporal_intent` for adapter dispatch (Open-Meteo
    and WeatherAPI both pick historical vs forecast vs current based on
    where today sits relative to this window — NF-18 sweep 2026-05-12).
    """
    if not date_text:
        return None

    text = date_text.strip().lower()

    # ISO-like: YYYY-MM-DD, YYYY-MM, YYYY
    iso_match = re.match(r"^(\d{4})(?:-(\d{1,2}))?(?:-(\d{1,2}))?$", text)
    if iso_match:
        year = int(iso_match.group(1))
        month = int(iso_match.group(2)) if iso_match.group(2) else None
        day = int(iso_match.group(3)) if iso_match.group(3) else None
    else:
        year_match = re.search(r"\b(19|20)\d{2}\b", text)
        if not year_match:
            return None
        year = int(year_match.group(0))

        month: Optional[int] = None
        for name, num in _NOAA_MONTH_NAMES.items():
            if re.search(rf"\b{name}\b", text):
                month = num
                break

        day_match = re.search(r"\b([1-9]|[12][0-9]|3[01])\b(?!\d)", text)
        day = None
        if day_match and month is not None:
            candidate = int(day_match.group(1))
            if candidate != (year // 100) and candidate != (year - 2000):
                day = candidate

    try:
        if day and month:
            anchor = datetime(year, month, day, tzinfo=timezone.utc)
            start = anchor - timedelta(days=30)
            end = anchor + timedelta(days=30)
        elif month:
            start = datetime(year, month, 1, tzinfo=timezone.utc)
            if month == 12:
                end = datetime(year, 12, 31, tzinfo=timezone.utc)
            else:
                end = datetime(year, month + 1, 1, tzinfo=timezone.utc) - timedelta(
                    days=1
                )
        else:
            start = datetime(year, 1, 1, tzinfo=timezone.utc)
            end = datetime(year, 12, 31, tzinfo=timezone.utc)
    except (ValueError, OverflowError):
        return None

    return start, end


def _parse_date_window(
    date_text: Optional[str],
    fallback_years: int = 2,
) -> Tuple[str, str]:
    """Derive (startdate, enddate) ISO strings for a NOAA query.

    Thin wrapper over :func:`_parse_date_anchor` that adds the
    historical-fallback semantics NOAA needs: when no parseable DATE,
    return ``(now-fallback_years, now)``. Open-Meteo / WeatherAPI use
    the same fallback when their callers haven't propagated DATE
    (NF-18 sweep 2026-05-12).
    """
    today = datetime.now(timezone.utc)
    parsed = _parse_date_anchor(date_text)
    if parsed is None:
        return (
            datetime(today.year - fallback_years, 1, 1).strftime("%Y-%m-%d"),
            today.strftime("%Y-%m-%d"),
        )
    start, end = parsed
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")


def classify_temporal_intent(
    entities: Optional[List[Dict[str, str]]] = None,
) -> str:
    """Return ``"past"``, ``"future"``, or ``"current"`` from DATE entities.

    Weather/climate adapter dispatch helper. After NF-20-B propagation
    (2026-05-12), every claim in a date-anchored article carries a DATE
    entity, so this classification is reliable for the historical-vs-
    forecast routing decision.

    Comparison is granularity-matched: today is checked against the
    DATE entity's window (a year-coarse DATE has a year-wide
    "tolerance"):

      * today AFTER window  → ``"past"``    (route to archive API)
      * today BEFORE window → ``"future"``  (route to forecast API)
      * today WITHIN window → ``"current"`` (route to current
                                              conditions / forecast)

    Returns ``"current"`` when no DATE entity is present or the DATE
    text cannot be parsed. Selection rule mirrors
    :func:`extract_location_and_date` — the longest DATE entity text
    wins (longer phrases are more specific).
    """
    _, date_text = extract_location_and_date(entities)
    parsed = _parse_date_anchor(date_text)
    if parsed is None:
        return "current"

    start, end = parsed
    today = datetime.now(timezone.utc)
    if today > end:
        return "past"
    if today < start:
        return "future"
    return "current"


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
        """NF-18: produce a NOAA cache key that encodes the data type.

        Cache-key shape: ``"{data_type}|{location}|{date}"`` where
        ``data_type`` is one of ``temperature`` / ``precipitation`` /
        ``sea_level``. The data-type classification happens here because
        ``claim_text`` is in scope; ``search()`` only sees the prepared
        ``query`` argument (Session B contract, see government_api_client
        line 294) so it can no longer classify on the raw claim.

        Skip path: returns ``""`` when neither LOCATION nor DATE entity
        is present — same B3.4 rule as before, weather APIs need a place
        + time to produce meaningful data.

        Two claims about the same location/date but different data types
        (e.g. heatwave vs flood at the same place) now have distinct
        cache namespaces, which is correct — they call different NOAA
        endpoints with different params and produce different evidence.
        """
        loc_date = _location_date_cache_key(entities)
        if not loc_date:
            return ""
        data_type = _classify_noaa_data_type(claim_text, entities)
        return f"{data_type}|{loc_date}"

    def search(
        self,
        query: str,
        domain: str,
        jurisdiction: str,
        entities: Optional[List[Dict[str, str]]] = None,
    ) -> List[Dict[str, Any]]:
        """Dispatch to the right NOAA dataset based on the data-type prefix.

        ``query`` is the cache key produced by ``prepare_query`` —
        ``"{data_type}|{location}|{date}"``. We split off the prefix and
        delegate to the appropriate ``_search_*_data`` method, which
        reads the location + date directly from ``entities``.
        """
        if not self.is_relevant_for_domain(domain, jurisdiction):
            return []

        if not self.api_key:
            logger.warning("NOAA API key not configured, skipping")
            return []

        # Cache key shape: "{data_type}|{location}|{date}". Tolerate the
        # legacy "{location}|{date}" shape (cached pre-NF-18 entries) by
        # defaulting to temperature.
        if query.startswith(("temperature|", "precipitation|", "sea_level|")):
            data_type, _ = query.split("|", 1)
        else:
            data_type = "temperature"

        try:
            if data_type == "temperature":
                return self._search_temperature_data(entities)
            if data_type == "precipitation":
                return self._search_precipitation_data(entities)
            if data_type == "sea_level":
                return self._search_sea_level_data(entities)
            return []
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

    def _build_data_query_params(
        self,
        datatypeid: str,
        entities: Optional[List[Dict[str, str]]],
    ) -> Dict[str, Any]:
        """Build common params for a NOAA /data query.

        NF-18 Bug-2: derive the date window from the DATE entity instead
        of hardcoding ``now()-2y → now()``. A claim about July 2022 was
        previously querying 2024-2026 and silently returning zero.
        """
        _, date_text = extract_location_and_date(entities)
        startdate, enddate = _parse_date_window(date_text)

        params: Dict[str, Any] = {
            "datasetid": "GSOM",  # Global Summary of Month
            "datatypeid": datatypeid,
            "limit": self.max_results,
            "sortfield": "date",
            "sortorder": "desc",
            "startdate": startdate,
            "enddate": enddate,
        }

        location_id = self._extract_location_id(entities)
        if location_id:
            params["locationid"] = location_id

        return params

    def _search_temperature_data(
        self, entities: Optional[List[Dict[str, str]]] = None
    ) -> List[Dict[str, Any]]:
        """Search for temperature-related climate data. Returns empty on failure."""
        params = self._build_data_query_params("TAVG", entities)
        try:
            response = self._make_request("data", params=params)
            if response and "results" in response:
                return self._transform_data_response(response, "temperature")
        except Exception as e:
            logger.warning(f"NOAA temperature search failed: {e}")

        logger.info("[NOAA] Temperature data query returned no results")
        return []

    def _search_precipitation_data(
        self, entities: Optional[List[Dict[str, str]]] = None
    ) -> List[Dict[str, Any]]:
        """Search for precipitation-related climate data. Returns empty on failure."""
        params = self._build_data_query_params("PRCP", entities)
        try:
            response = self._make_request("data", params=params)
            if response and "results" in response:
                return self._transform_data_response(response, "precipitation")
        except Exception as e:
            logger.warning(f"NOAA precipitation search failed: {e}")

        logger.info("[NOAA] Precipitation data query returned no results")
        return []

    def _search_sea_level_data(
        self, entities: Optional[List[Dict[str, str]]] = None
    ) -> List[Dict[str, Any]]:
        """Search for sea level data via NOAA CDO."""
        params = self._build_data_query_params("MMSL", entities)
        try:
            response = self._make_request("data", params=params)
            if response and "results" in response:
                return self._transform_data_response(response, "sea_level")
        except Exception as e:
            logger.warning(f"NOAA sea level search failed: {e}")

        logger.info("[NOAA] Sea level data query returned no results")
        return []

    # Country / US-state name → NOAA FIPS code. Class attribute so the
    # tests can introspect it without instantiating an adapter.
    _COUNTRY_FIPS: Dict[str, Optional[str]] = {
        # US
        "US": "FIPS:US",
        "USA": "FIPS:US",
        "UNITED STATES": "FIPS:US",
        # US states → 2-digit FIPS (NOAA locationid). Full set so any US-state
        # claim resolves; previously only ~6 states were mapped, so e.g.
        # "Louisiana" returned no locationid and NOAA got a locationless query
        # that 500s (the storm/hurricane 0-yield bug).
        "ALABAMA": "FIPS:01",
        "ALASKA": "FIPS:02",
        "ARIZONA": "FIPS:04",
        "ARKANSAS": "FIPS:05",
        "CALIFORNIA": "FIPS:06",
        "COLORADO": "FIPS:08",
        "CONNECTICUT": "FIPS:09",
        "DELAWARE": "FIPS:10",
        "FLORIDA": "FIPS:12",
        "GEORGIA": "FIPS:13",
        "HAWAII": "FIPS:15",
        "IDAHO": "FIPS:16",
        "ILLINOIS": "FIPS:17",
        "INDIANA": "FIPS:18",
        "IOWA": "FIPS:19",
        "KANSAS": "FIPS:20",
        "KENTUCKY": "FIPS:21",
        "LOUISIANA": "FIPS:22",
        "MAINE": "FIPS:23",
        "MARYLAND": "FIPS:24",
        "MASSACHUSETTS": "FIPS:25",
        "MICHIGAN": "FIPS:26",
        "MINNESOTA": "FIPS:27",
        "MISSISSIPPI": "FIPS:28",
        "MISSOURI": "FIPS:29",
        "MONTANA": "FIPS:30",
        "NEBRASKA": "FIPS:31",
        "NEVADA": "FIPS:32",
        "NEW HAMPSHIRE": "FIPS:33",
        "NEW JERSEY": "FIPS:34",
        "NEW MEXICO": "FIPS:35",
        "NEW YORK": "FIPS:36",
        "NORTH CAROLINA": "FIPS:37",
        "NORTH DAKOTA": "FIPS:38",
        "OHIO": "FIPS:39",
        "OKLAHOMA": "FIPS:40",
        "OREGON": "FIPS:41",
        "PENNSYLVANIA": "FIPS:42",
        "RHODE ISLAND": "FIPS:44",
        "SOUTH CAROLINA": "FIPS:45",
        "SOUTH DAKOTA": "FIPS:46",
        "TENNESSEE": "FIPS:47",
        "TEXAS": "FIPS:48",
        "UTAH": "FIPS:49",
        "VERMONT": "FIPS:50",
        "VIRGINIA": "FIPS:51",
        "WASHINGTON": "FIPS:53",
        "WEST VIRGINIA": "FIPS:54",
        "WISCONSIN": "FIPS:55",
        "WYOMING": "FIPS:56",
        # UK
        "UK": "FIPS:UK",
        "UNITED KINGDOM": "FIPS:UK",
        "BRITAIN": "FIPS:UK",
        "ENGLAND": "FIPS:UK",
        "SCOTLAND": "FIPS:UK",
        "WALES": "FIPS:UK",
        "NORTHERN IRELAND": "FIPS:UK",
        # Europe
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
        "IRELAND": "FIPS:EI",
        "GREECE": "FIPS:GR",
        "PORTUGAL": "FIPS:PO",
        "SWITZERLAND": "FIPS:SZ",
        # Asia-Pacific
        "JAPAN": "FIPS:JA",
        "CHINA": "FIPS:CH",
        "AUSTRALIA": "FIPS:AS",
        "INDIA": "FIPS:IN",
        "SOUTH KOREA": "FIPS:KS",
        "INDONESIA": "FIPS:ID",
        "THAILAND": "FIPS:TH",
        "SINGAPORE": "FIPS:SN",
        "PHILIPPINES": "FIPS:RP",
        # Americas
        "CANADA": "FIPS:CA",
        "MEXICO": "FIPS:MX",
        "BRAZIL": "FIPS:BR",
        "ARGENTINA": "FIPS:AR",
        "COLOMBIA": "FIPS:CO",
        "PERU": "FIPS:PE",
        # Africa / Middle East
        "EGYPT": "FIPS:EG",
        "SOUTH AFRICA": "FIPS:SF",
        "KENYA": "FIPS:KE",
        "NIGERIA": "FIPS:NI",
        "TURKEY": "FIPS:TU",
        "UNITED ARAB EMIRATES": "FIPS:AE",
        "UAE": "FIPS:AE",
        # No-filter sentinels — claims that explicitly reference global
        # scope shouldn't filter to one country
        "GLOBAL": None,
        "WORLD": None,
        "WORLDWIDE": None,
        "EARTH": None,
    }

    def _extract_location_id(
        self, entities: Optional[List[Dict[str, str]]] = None
    ) -> Optional[str]:
        """Extract NOAA location ID from typed entities.

        NF-18 Bug-3:
        * Pre-fix this read ``entity.get("type")`` and looked for legacy
          NER labels ``"GPE"`` / ``"LOC"``. NF-15 (2026-04-28) remapped
          entities to ``{text, label}`` with NF-15 vocabulary
          (``"LOCATION"``), so the filter has been silently returning
          ``None`` for every entity since NF-15 shipped.
        * The ``location_map`` only knew countries / US states, so even
          before NF-15 a city like "London" returned ``None`` and the
          NOAA call fell back to an unfiltered global query (US-heavy).

        Walks entities in order, picking the first match in:
          1. Direct country / US-state lookup (``_COUNTRY_FIPS``).
          2. Major-city → country FIPS fallback (``_NOAA_CITY_TO_FIPS``).
        Accepts ``LOCATION`` (NF-15) as the primary label; ``GPE`` /
        ``LOC`` are kept for back-compat in case any caller still sends
        legacy labels.
        """
        if not entities:
            return None

        accepted_labels = {"LOCATION", "GPE", "LOC"}

        for entity in entities:
            if not isinstance(entity, dict):
                continue
            label = entity.get("label") or entity.get("type")
            if label not in accepted_labels:
                continue
            raw = (entity.get("text") or "").strip()
            if not raw:
                continue

            upper = raw.upper()
            if upper in self._COUNTRY_FIPS:
                return self._COUNTRY_FIPS[upper]

            lower = raw.lower()
            if lower in _NOAA_CITY_TO_FIPS:
                return _NOAA_CITY_TO_FIPS[lower]

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

        evidence = []

        try:
            # Extract location from entities or query
            location = self._extract_location(query, entities)

            if not location:
                logger.warning(
                    f"WeatherAPI: Could not determine location for query '{query}'"
                )
                return []

            # NF-18 sweep (2026-05-12): route from DATE entity, not query
            # keywords. ``query`` is the cache-key shape ``"{loc}|{date}"``
            # post-Session-B; the historical/forecast/current dispatch
            # below was scanning that key and matching nothing. After
            # NF-20-B propagation every date-anchored claim has a DATE
            # entity, so classify_temporal_intent routes deterministically.
            intent = classify_temporal_intent(entities)
            if intent == "past":
                evidence.extend(self._get_historical(location, query, entities))
            elif intent == "future":
                evidence.extend(self._get_forecast(location, query))
            else:
                # Intent "current" — DATE absent, unparseable, or its
                # granularity window contains today. Return current
                # conditions as the most representative snapshot.
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

    def _get_historical(
        self,
        location: str,
        query: str,
        entities: Optional[List[Dict[str, str]]] = None,
    ) -> List[Dict[str, Any]]:
        """Get historical weather data for the DATE the claim anchors.

        NF-18 sweep (2026-05-12): derive the target date from the DATE
        entity rather than hardcoding "yesterday". Pre-fix, a Coral Sea
        March 2024 claim was getting yesterday's weather. WeatherAPI
        history.json takes a single date param, so we use the START of
        the DATE entity's granularity window — for "March 2024" that's
        2024-03-01, which the API will accept on plans that cover that
        period. Older periods may return empty (free-tier limit ~7
        days back); empty result is safer than wrong-date noise.

        Fall back to yesterday only when no parseable DATE is present.
        """
        evidence = []

        try:
            import httpx
            from urllib.parse import quote

            _, date_text = extract_location_and_date(entities)
            parsed = _parse_date_anchor(date_text)
            if parsed is None:
                target_date_str = (datetime.now() - timedelta(days=1)).strftime(
                    "%Y-%m-%d"
                )
            else:
                start, _ = parsed
                target_date_str = start.strftime("%Y-%m-%d")
            url = f"{self.base_url}/history.json?key={self.api_key}&q={quote(location)}&dt={target_date_str}"

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
                f"Weather in {location_name} on {target_date_str}:\n"
                f"Temperature: {min_temp}°C - {max_temp}°C (avg: {avg_temp}°C)\n"
                f"Conditions: {condition}\n"
                f"Precipitation: {precip}mm"
            )

            evidence.append(
                {
                    "title": f"Historical Weather for {location_name} ({target_date_str})",
                    "url": f"https://www.weatherapi.com/weather/q/{quote(location)}",
                    "snippet": snippet,
                    "source": "WeatherAPI.com",
                    "date": target_date_str,
                    "metadata": {
                        "api_source": "WeatherAPI",
                        "data_type": "historical_weather",
                        "location": location_name,
                        "date": target_date_str,
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
        evidence = []

        # NF-18 sweep (2026-05-12): route from DATE entity, not query
        # keywords. ``query`` is the cache-key shape ``"{loc}|{date}"`` —
        # never contains historical-vs-forecast keywords. After NF-20-B
        # propagation every date-anchored claim carries a DATE entity.
        try:
            intent = classify_temporal_intent(entities)
            if intent == "past":
                evidence.extend(
                    self._get_historical(lat, lon, location_name, query, entities)
                )
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
        self,
        lat: float,
        lon: float,
        location_name: str,
        query: str,
        entities: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        """Get historical climate data for the period the DATE entity anchors.

        NF-18 sweep (2026-05-12): derive the date window from the DATE
        entity rather than hardcoding ``now-365d → now``. Pre-fix, a
        claim about Coral Sea March 2024 was returning 2025-2026 data
        (today's archive window) instead of the actual claim period.

        Fall back to ``now-365d → now`` only when no parseable DATE
        is present (matches the old behaviour for ad-hoc weather
        queries that lack temporal anchoring).
        """
        try:
            import httpx

            _, date_text = extract_location_and_date(entities)
            parsed = _parse_date_anchor(date_text)
            if parsed is None:
                end_date = datetime.now(timezone.utc)
                start_date = end_date - timedelta(days=365)
            else:
                start_date, end_date = parsed

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
