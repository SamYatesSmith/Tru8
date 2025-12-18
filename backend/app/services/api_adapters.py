"""
Government API Adapters
Phase 5: Government API Integration

Concrete implementations of API adapters for:
- ONS Economic Statistics (UK) - Finance, Demographics
- FRED (US) - Finance
- Companies House (UK) - Government
- PubMed (US/Global) - Health, Science
- WHO (Global) - Health
- WeatherAPI (Global) - Weather, Climate
- CrossRef (Global) - Science
- GovUK Content (UK) - Government
- Hansard (UK) - Law, Parliament
- Wikidata (Global) - General
- GovInfo.gov (US) - Law, Federal Statutes
- GBIF (Global) - Animals, Biodiversity, Species Taxonomy

Each adapter extends GovernmentAPIClient and implements:
- search(): Query the API with claim-specific parameters
- _transform_response(): Convert API response to standardized evidence format
- is_relevant_for_domain(): Define which domains/jurisdictions this API covers
"""

import logging
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.services.government_api_client import GovernmentAPIClient
from app.core.config import settings
from app.services.legal_search import LegalSearchService

logger = logging.getLogger(__name__)


# ========== ONS ECONOMIC STATISTICS ADAPTER ==========

class ONSAdapter(GovernmentAPIClient):
    """
    Office for National Statistics (UK) API Adapter.

    Covers: Finance, Demographics
    Jurisdiction: UK
    Free tier: No API key required, rate limit ~300 requests/hour
    """

    def __init__(self):
        super().__init__(
            api_name="ONS Economic Statistics",
            base_url="https://api.beta.ons.gov.uk/v1",
            api_key=None,  # No API key required
            cache_ttl=86400,  # 24 hours
            timeout=15,
            max_results=10
        )

        # ONS-specific headers
        self.headers.update({
            "Accept": "application/json"
        })

    def is_relevant_for_domain(self, domain: str, jurisdiction: str) -> bool:
        """ONS covers Finance and Demographics for UK only."""
        return (
            domain in ["Finance", "Demographics"] and
            jurisdiction in ["UK", "Global"]  # Global allows UK data
        )

    def search(self, query: str, domain: str, jurisdiction: str, entities: Optional[List[Dict[str, str]]] = None) -> List[Dict[str, Any]]:
        """
        Search ONS datasets for economic/demographic data.

        Args:
            query: Search query (e.g., "unemployment rate 2024")
            domain: Finance or Demographics
            jurisdiction: UK

        Returns:
            List of evidence dictionaries
        """
        if not self.is_relevant_for_domain(domain, jurisdiction):
            return []

        query = self._sanitize_query(query)

        # ONS API endpoint for dataset search
        params = {
            "q": query,
            "limit": self.max_results
        }

        try:
            response = self._make_request("datasets", params=params)

            if not response or "items" not in response:
                logger.warning(f"ONS API returned empty response for: {query}")
                return []

            return self._transform_response(response)

        except Exception as e:
            logger.error(f"ONS search failed for '{query}': {e}")
            return []

    def _transform_response(self, raw_response: Any) -> List[Dict[str, Any]]:
        """
        Transform ONS API response to standardized evidence format.

        ONS response structure:
        {
          "items": [
            {
              "title": "Labour Market Statistics",
              "description": "UK unemployment rate...",
              "links": {"self": {"href": "https://..."}},
              "release_date": "2024-01-15"
            }
          ]
        }
        """
        evidence_list = []

        for item in raw_response.get("items", []):
            try:
                title = item.get("title", "ONS Dataset")
                description = item.get("description", "")

                # Extract URL
                links = item.get("links", {})
                url = links.get("self", {}).get("href", "https://www.ons.gov.uk")

                # Parse release date
                release_date_str = item.get("release_date")
                source_date = None
                if release_date_str:
                    try:
                        source_date = datetime.fromisoformat(release_date_str.replace("Z", "+00:00"))
                    except Exception:
                        pass

                # Extract key statistics from description
                snippet = description[:300] if description else title

                # ONS-specific metadata
                metadata = {
                    "api_source": "ONS",
                    "dataset_id": item.get("id"),
                    "dataset_type": item.get("type"),
                    "contact_name": item.get("contacts", [{}])[0].get("name") if item.get("contacts") else None
                }

                evidence = self._create_evidence_dict(
                    title=title,
                    snippet=snippet,
                    url=url,
                    source_date=source_date,
                    metadata=metadata
                )

                evidence_list.append(evidence)

            except Exception as e:
                logger.warning(f"Failed to parse ONS item: {e}")
                continue

        logger.info(f"ONS returned {len(evidence_list)} evidence items")
        return evidence_list


# ========== PUBMED ADAPTER ==========

class PubMedAdapter(GovernmentAPIClient):
    """
    PubMed (NCBI) API Adapter.

    Covers: Health, Science
    Jurisdiction: Global
    Free tier: 3 requests/second, no daily limit
    API key: Optional (increases rate limit to 10/sec)
    """

    def __init__(self):
        api_key = os.getenv("PUBMED_API_KEY")  # Optional

        super().__init__(
            api_name="PubMed",
            base_url="https://eutils.ncbi.nlm.nih.gov/entrez/eutils",
            api_key=api_key,
            cache_ttl=86400 * 7,  # 7 days (medical research doesn't change often)
            timeout=10,
            max_results=10
        )

        # PubMed uses API key as query parameter, not header
        if self.api_key:
            del self.headers["Authorization"]

    def is_relevant_for_domain(self, domain: str, jurisdiction: str) -> bool:
        """PubMed covers biomedical and life sciences globally."""
        return domain in ["Health", "Science", "Climate", "Animals"]

    def search(self, query: str, domain: str, jurisdiction: str, entities: Optional[List[Dict[str, str]]] = None) -> List[Dict[str, Any]]:
        """
        Search PubMed for medical/scientific research.

        Args:
            query: Search query (e.g., "COVID vaccine efficacy")
            domain: Health or Science
            jurisdiction: Any (PubMed is global)

        Returns:
            List of evidence dictionaries
        """
        if not self.is_relevant_for_domain(domain, jurisdiction):
            return []

        query = self._sanitize_query(query)

        # Step 1: Search for article IDs
        search_params = {
            "db": "pubmed",
            "term": query,
            "retmax": self.max_results,
            "retmode": "json",
            "sort": "relevance"
        }

        if self.api_key:
            search_params["api_key"] = self.api_key

        try:
            search_response = self._make_request("esearch.fcgi", params=search_params)

            if not search_response or "esearchresult" not in search_response:
                logger.warning(f"PubMed search returned empty response for: {query}")
                return []

            id_list = search_response["esearchresult"].get("idlist", [])

            if not id_list:
                logger.info(f"PubMed found no results for: {query}")
                return []

            # Step 2: Fetch article details
            fetch_params = {
                "db": "pubmed",
                "id": ",".join(id_list),
                "retmode": "xml"
            }

            if self.api_key:
                fetch_params["api_key"] = self.api_key

            fetch_response = self._make_request("efetch.fcgi", params=fetch_params)

            if not fetch_response:
                logger.warning(f"PubMed fetch failed for IDs: {id_list}")
                return []

            return self._transform_response({"ids": id_list, "xml": fetch_response})

        except Exception as e:
            logger.error(f"PubMed search failed for '{query}': {e}")
            return []

    def _transform_response(self, raw_response: Any) -> List[Dict[str, Any]]:
        """
        Transform PubMed XML response to standardized evidence format.

        Parses XML to extract title, abstract, authors, and publication date.
        """
        import xml.etree.ElementTree as ET

        evidence_list = []
        xml_data = raw_response.get("xml", "")

        if not xml_data:
            logger.warning("PubMed returned empty XML response")
            return []

        try:
            # Parse XML response
            root = ET.fromstring(xml_data)

            # Iterate through each article
            for article in root.findall('.//PubmedArticle'):
                try:
                    # Extract PMID
                    pmid_elem = article.find('.//PMID')
                    pmid = pmid_elem.text if pmid_elem is not None else "unknown"

                    # Extract title
                    title_elem = article.find('.//ArticleTitle')
                    title = title_elem.text if title_elem is not None else f"PubMed Article {pmid}"

                    # Extract abstract (may have multiple AbstractText elements)
                    abstract_parts = []
                    for abstract_text in article.findall('.//AbstractText'):
                        if abstract_text.text:
                            abstract_parts.append(abstract_text.text)

                    abstract = " ".join(abstract_parts) if abstract_parts else "No abstract available."
                    snippet = abstract[:300] + "..." if len(abstract) > 300 else abstract

                    # Extract publication date
                    pub_date_elem = article.find('.//PubDate')
                    source_date = None
                    if pub_date_elem is not None:
                        year_elem = pub_date_elem.find('Year')
                        month_elem = pub_date_elem.find('Month')

                        if year_elem is not None:
                            try:
                                year = int(year_elem.text)
                                month = 1

                                # Try to parse month
                                if month_elem is not None:
                                    month_text = month_elem.text
                                    month_map = {
                                        "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4,
                                        "May": 5, "Jun": 6, "Jul": 7, "Aug": 8,
                                        "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12
                                    }
                                    month = month_map.get(month_text, int(month_text) if month_text.isdigit() else 1)

                                source_date = datetime(year, month, 1)
                            except (ValueError, TypeError):
                                pass

                    # Extract authors (first 3)
                    authors = []
                    for author in article.findall('.//Author')[:3]:
                        last_name = author.findtext('LastName', '')
                        fore_name = author.findtext('ForeName', '')
                        if last_name:
                            authors.append(f"{fore_name} {last_name}".strip())

                    authors_str = ", ".join(authors) if authors else "Authors not listed"

                    # Build URL
                    url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"

                    # Create evidence dictionary
                    evidence = self._create_evidence_dict(
                        title=title,
                        snippet=snippet,
                        url=url,
                        source_date=source_date,
                        metadata={
                            "api_source": "PubMed",
                            "pmid": pmid,
                            "database": "pubmed",
                            "authors": authors_str
                        }
                    )

                    evidence_list.append(evidence)

                except Exception as e:
                    logger.warning(f"Failed to parse PubMed article: {e}")
                    continue

        except ET.ParseError as e:
            logger.error(f"Failed to parse PubMed XML: {e}")
            # Fallback: Use IDs if XML parsing fails
            for pmid in raw_response.get("ids", []):
                evidence_list.append(self._create_evidence_dict(
                    title=f"PubMed Article {pmid}",
                    snippet="Medical research article from PubMed database.",
                    url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                    source_date=None,
                    metadata={"pmid": pmid, "api_source": "PubMed"}
                ))

        logger.info(f"PubMed returned {len(evidence_list)} evidence items")
        return evidence_list


# ========== COMPANIES HOUSE ADAPTER ==========

class CompaniesHouseAdapter(GovernmentAPIClient):
    """
    Companies House (UK) API Adapter.

    Covers: Government, Finance
    Jurisdiction: UK
    Free tier: 600 requests/hour
    API key: Required (get from https://developer.company-information.service.gov.uk/)
    """

    def __init__(self):
        api_key = os.getenv("COMPANIES_HOUSE_API_KEY")

        super().__init__(
            api_name="Companies House",
            base_url="https://api.company-information.service.gov.uk",
            api_key=api_key,
            cache_ttl=86400 * 3,  # 3 days (company data changes slowly)
            timeout=10,
            max_results=10
        )

        # Companies House uses HTTP Basic Auth with API key as username
        if self.api_key:
            import base64
            credentials = base64.b64encode(f"{self.api_key}:".encode()).decode()
            self.headers["Authorization"] = f"Basic {credentials}"

    def is_relevant_for_domain(self, domain: str, jurisdiction: str) -> bool:
        """Companies House covers Government and Finance for UK only."""
        return (
            domain in ["Government", "Finance"] and
            jurisdiction in ["UK", "Global"]  # Global allows UK data
        )

    def search(self, query: str, domain: str, jurisdiction: str, entities: Optional[List[Dict[str, str]]] = None) -> List[Dict[str, Any]]:
        """
        Search Companies House for UK company information.

        Args:
            query: Search query (e.g., "BP PLC")
            domain: Government or Finance
            jurisdiction: UK

        Returns:
            List of evidence dictionaries
        """
        if not self.is_relevant_for_domain(domain, jurisdiction):
            return []

        if not self.api_key:
            logger.warning("Companies House API key not configured, skipping")
            return []

        query = self._sanitize_query(query)

        # Companies House search endpoint
        params = {
            "q": query,
            "items_per_page": self.max_results
        }

        try:
            response = self._make_request("/search/companies", params=params)

            if not response or "items" not in response:
                logger.warning(f"Companies House returned empty response for: {query}")
                return []

            return self._transform_response(response)

        except Exception as e:
            logger.error(f"Companies House search failed for '{query}': {e}")
            return []

    def _transform_response(self, raw_response: Any) -> List[Dict[str, Any]]:
        """
        Transform Companies House API response to standardized evidence format.

        Companies House response structure:
        {
          "items": [
            {
              "title": "BP P.L.C.",
              "company_number": "00102498",
              "company_status": "active",
              "date_of_creation": "1909-04-14",
              "company_type": "plc",
              "address": {...}
            }
          ]
        }
        """
        evidence_list = []

        for item in raw_response.get("items", []):
            try:
                title = item.get("title", "UK Company")
                company_number = item.get("company_number")
                company_status = item.get("company_status", "unknown")
                company_type = item.get("company_type", "")

                # Build URL to company page
                url = f"https://find-and-update.company-information.service.gov.uk/company/{company_number}"

                # Build snippet
                snippet = (
                    f"{title} (Company No. {company_number}). "
                    f"Status: {company_status}. "
                    f"Type: {company_type}."
                )

                # Parse creation date
                creation_date_str = item.get("date_of_creation")
                source_date = None
                if creation_date_str:
                    try:
                        source_date = datetime.fromisoformat(creation_date_str)
                    except Exception:
                        pass

                # Companies House metadata
                metadata = {
                    "api_source": "Companies House",
                    "company_number": company_number,
                    "company_status": company_status,
                    "company_type": company_type,
                    "address": item.get("address", {})
                }

                evidence = self._create_evidence_dict(
                    title=title,
                    snippet=snippet,
                    url=url,
                    source_date=source_date,
                    metadata=metadata
                )

                evidence_list.append(evidence)

            except Exception as e:
                logger.warning(f"Failed to parse Companies House item: {e}")
                continue

        logger.info(f"Companies House returned {len(evidence_list)} evidence items")
        return evidence_list


# ========== FRED ADAPTER (US Federal Reserve Economic Data) ==========

class FREDAdapter(GovernmentAPIClient):
    """
    FRED (Federal Reserve Economic Data) API Adapter.

    Covers: Finance
    Jurisdiction: US
    Free tier: 1,000 requests/day
    API key: Required
    """

    def __init__(self):
        api_key = os.getenv("FRED_API_KEY")

        super().__init__(
            api_name="FRED",
            base_url="https://api.stlouisfed.org/fred",
            api_key=api_key,
            cache_ttl=86400 * 7,  # 7 days (economic data changes slowly)
            timeout=10,
            max_results=10
        )

        # FRED uses API key as query parameter
        if self.api_key:
            del self.headers["Authorization"]

    def is_relevant_for_domain(self, domain: str, jurisdiction: str) -> bool:
        """FRED covers Finance for US."""
        return domain == "Finance" and jurisdiction in ["US", "Global"]

    def search(self, query: str, domain: str, jurisdiction: str, entities: Optional[List[Dict[str, str]]] = None) -> List[Dict[str, Any]]:
        """
        Search FRED for US economic data series.

        Args:
            query: Search query (e.g., "unemployment rate")
            domain: Finance
            jurisdiction: US

        Returns:
            List of evidence dictionaries
        """
        if not self.is_relevant_for_domain(domain, jurisdiction):
            return []

        if not self.api_key:
            logger.warning("FRED API key not configured, skipping")
            return []

        query = self._sanitize_query(query)

        # FRED series search
        params = {
            "search_text": query,
            "api_key": self.api_key,
            "file_type": "json",
            "limit": self.max_results
        }

        try:
            response = self._make_request("/series/search", params=params)

            if not response or "seriess" not in response:
                logger.warning(f"FRED returned empty response for: {query}")
                return []

            return self._transform_response(response)

        except Exception as e:
            logger.error(f"FRED search failed for '{query}': {e}")
            return []

    def _transform_response(self, raw_response: Any) -> List[Dict[str, Any]]:
        """Transform FRED API response to standardized evidence format."""
        evidence_list = []

        for series in raw_response.get("seriess", []):
            try:
                series_id = series.get("id")
                title = series.get("title", f"FRED Series {series_id}")
                notes = series.get("notes", "")

                # Build URL
                url = f"https://fred.stlouisfed.org/series/{series_id}"

                # Build snippet from notes
                snippet = notes[:300] if notes else f"Economic data series: {title}"

                # Parse dates
                observation_start = series.get("observation_start")
                source_date = None
                if observation_start:
                    try:
                        source_date = datetime.fromisoformat(observation_start)
                    except Exception:
                        pass

                metadata = {
                    "api_source": "FRED",
                    "series_id": series_id,
                    "frequency": series.get("frequency"),
                    "units": series.get("units"),
                    "seasonal_adjustment": series.get("seasonal_adjustment")
                }

                evidence = self._create_evidence_dict(
                    title=title,
                    snippet=snippet,
                    url=url,
                    source_date=source_date,
                    metadata=metadata
                )

                evidence_list.append(evidence)

            except Exception as e:
                logger.warning(f"Failed to parse FRED series: {e}")
                continue

        logger.info(f"FRED returned {len(evidence_list)} evidence items")
        return evidence_list


# ========== WHO ADAPTER (World Health Organization) ==========

class WHOAdapter(GovernmentAPIClient):
    """
    WHO (World Health Organization) API Adapter.

    Covers: Health
    Jurisdiction: Global
    Free tier: No explicit limit
    API key: Not required
    """

    def __init__(self):
        super().__init__(
            api_name="WHO",
            base_url="https://ghoapi.azureedge.net/api",
            api_key=None,
            cache_ttl=86400 * 7,  # 7 days (health data changes slowly)
            timeout=15,
            max_results=10
        )

    def is_relevant_for_domain(self, domain: str, jurisdiction: str) -> bool:
        """WHO covers Health globally."""
        return domain == "Health"

    def search(self, query: str, domain: str, jurisdiction: str, entities: Optional[List[Dict[str, str]]] = None) -> List[Dict[str, Any]]:
        """
        Search WHO Global Health Observatory for health data.

        Args:
            query: Search query (e.g., "COVID-19 cases")
            domain: Health
            jurisdiction: Any

        Returns:
            List of evidence dictionaries
        """
        if not self.is_relevant_for_domain(domain, jurisdiction):
            return []

        query = self._sanitize_query(query)

        # Search indicators
        try:
            # First, search for relevant indicators
            indicator_response = self._make_request("/Indicator")

            if not indicator_response or "value" not in indicator_response:
                logger.warning(f"WHO returned empty indicator response")
                return []

            # Filter indicators by query terms
            query_lower = query.lower()
            matching_indicators = [
                ind for ind in indicator_response.get("value", [])
                if query_lower in ind.get("IndicatorName", "").lower()
            ][:self.max_results]

            return self._transform_response({"indicators": matching_indicators})

        except Exception as e:
            logger.error(f"WHO search failed for '{query}': {e}")
            return []

    def _transform_response(self, raw_response: Any) -> List[Dict[str, Any]]:
        """Transform WHO API response to standardized evidence format."""
        evidence_list = []

        for indicator in raw_response.get("indicators", []):
            try:
                indicator_code = indicator.get("IndicatorCode")
                title = indicator.get("IndicatorName", f"WHO Indicator {indicator_code}")
                description = indicator.get("Definition", "")

                url = f"https://www.who.int/data/gho/data/indicators/indicator-details/GHO/{indicator_code}"

                snippet = description[:300] if description else f"WHO health indicator: {title}"

                metadata = {
                    "api_source": "WHO",
                    "indicator_code": indicator_code,
                    "language": indicator.get("Language", "EN")
                }

                evidence = self._create_evidence_dict(
                    title=title,
                    snippet=snippet,
                    url=url,
                    source_date=None,
                    metadata=metadata
                )

                evidence_list.append(evidence)

            except Exception as e:
                logger.warning(f"Failed to parse WHO indicator: {e}")
                continue

        logger.info(f"WHO returned {len(evidence_list)} evidence items")
        return evidence_list


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
        "daily": "GHCND",      # Global Historical Climatology Network Daily
        "monthly": "GSOM",     # Global Summary of Month
        "yearly": "GSOY",      # Global Summary of Year
        "normals": "NORMAL_ANN"  # Climate Normals
    }

    # Data type IDs for common climate variables
    DATA_TYPES = {
        "temperature": ["TAVG", "TMAX", "TMIN"],  # Average, max, min temp
        "precipitation": ["PRCP", "SNOW", "SNWD"],  # Precip, snowfall, snow depth
        "wind": ["AWND", "WSF2", "WSF5"],  # Avg wind, fastest 2-min, 5-sec
        "sea_level": ["MMSL"]  # Mean sea level
    }

    def __init__(self):
        super().__init__(
            api_name="NOAA CDO",
            base_url="https://www.ncei.noaa.gov/cdo-web/api/v2",
            api_key=settings.NOAA_API_KEY,
            cache_ttl=86400,  # 24 hours (climate data updates daily at most)
            timeout=15,
            max_results=10
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

    def search(self, query: str, domain: str, jurisdiction: str, entities: Optional[List[Dict[str, str]]] = None) -> List[Dict[str, Any]]:
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
            # Determine what type of climate data to fetch
            if any(term in query_lower for term in ["temperature", "warm", "cold", "heat", "hot"]):
                evidence.extend(self._search_temperature_data(query, entities))
            elif any(term in query_lower for term in ["rain", "precipitation", "snow", "flood"]):
                evidence.extend(self._search_precipitation_data(query, entities))
            elif any(term in query_lower for term in ["sea level", "ocean", "coastal"]):
                evidence.extend(self._search_sea_level_data(query, entities))
            else:
                # General climate search - get dataset info
                evidence.extend(self._search_datasets(query))

            return evidence

        except Exception as e:
            logger.error(f"NOAA search failed for '{query}': {e}")
            return []

    def _search_datasets(self, query: str) -> List[Dict[str, Any]]:
        """Search available NOAA datasets."""
        try:
            response = self._make_request("datasets", params={"limit": 10})

            if not response or "results" not in response:
                return []

            return self._transform_dataset_response(response)

        except Exception as e:
            logger.error(f"NOAA dataset search failed: {e}")
            return []

    def _search_temperature_data(self, query: str, entities: Optional[List[Dict[str, str]]] = None) -> List[Dict[str, Any]]:
        """Search for temperature-related climate data."""
        # Extract location from entities if available
        location_id = self._extract_location_id(entities)

        # Get recent temperature data
        params = {
            "datasetid": "GSOM",  # Global Summary of Month
            "datatypeid": "TAVG",  # Average temperature
            "limit": self.max_results,
            "sortfield": "date",
            "sortorder": "desc"
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
            "https://www.ncei.noaa.gov/access/monitoring/climate-at-a-glance/global/time-series"
        )

    def _search_precipitation_data(self, query: str, entities: Optional[List[Dict[str, str]]] = None) -> List[Dict[str, Any]]:
        """Search for precipitation-related climate data."""
        location_id = self._extract_location_id(entities)

        params = {
            "datasetid": "GSOM",
            "datatypeid": "PRCP",  # Precipitation
            "limit": self.max_results,
            "sortfield": "date",
            "sortorder": "desc"
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
            "https://www.ncei.noaa.gov/access/monitoring/climate-at-a-glance/global/time-series"
        )

    def _search_sea_level_data(self, query: str, entities: Optional[List[Dict[str, str]]] = None) -> List[Dict[str, Any]]:
        """Search for sea level data."""
        # Sea level data requires specific tide gauge stations
        # Return authoritative NOAA sea level info
        return self._create_climate_evidence(
            "NOAA Sea Level Rise Data",
            "NOAA's tide gauge and satellite altimetry data shows global mean sea level has risen "
            "about 3.4 mm per year since 1993. Long-term records from tide gauges show approximately "
            "8-9 inches of sea level rise since 1880.",
            "https://www.climate.gov/news-features/understanding-climate/climate-change-global-sea-level"
        )

    def _extract_location_id(self, entities: Optional[List[Dict[str, str]]] = None) -> Optional[str]:
        """Extract NOAA location ID from NER entities."""
        if not entities:
            return None

        # NOAA uses FIPS codes for US states and country codes globally
        # Example: FIPS:06 = California, FIPS:36 = New York
        for entity in entities:
            if entity.get("type") in ["GPE", "LOC"]:
                location = entity.get("text", "").upper()
                # Map common locations to NOAA IDs
                location_map = {
                    "US": "FIPS:US",
                    "USA": "FIPS:US",
                    "UNITED STATES": "FIPS:US",
                    "UK": "FIPS:UK",
                    "CALIFORNIA": "FIPS:06",
                    "NEW YORK": "FIPS:36",
                    "TEXAS": "FIPS:48",
                    "FLORIDA": "FIPS:12",
                }
                if location in location_map:
                    return location_map[location]

        return None

    def _create_climate_evidence(self, title: str, snippet: str, url: str) -> List[Dict[str, Any]]:
        """Create climate evidence dictionary."""
        evidence = self._create_evidence_dict(
            title=title,
            snippet=snippet,
            url=url,
            source_date=datetime.utcnow(),
            metadata={
                "api_source": "NOAA CDO",
                "data_type": "climate",
                "authority": "US Government"
            }
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
                        "data_coverage": item.get("datacoverage")
                    }
                )
                evidence_list.append(evidence)

            except Exception as e:
                logger.warning(f"Failed to parse NOAA dataset item: {e}")
                continue

        return evidence_list

    def _transform_data_response(self, raw_response: Any, data_type: str) -> List[Dict[str, Any]]:
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
                    "max": max_value
                }
            )
            evidence_list.append(evidence)

        return evidence_list

    def _transform_response(self, raw_response: Any) -> List[Dict[str, Any]]:
        """Generic transform - delegates to specific methods."""
        return self._transform_dataset_response(raw_response)


# ========== ALPHA VANTAGE ADAPTER (Stocks, Forex, Crypto, News) ==========

class AlphaVantageAdapter(GovernmentAPIClient):
    """
    Alpha Vantage API Adapter.

    Covers: Finance (stocks, forex, crypto, news sentiment)
    Jurisdiction: Global (primarily US stocks)
    Rate limits: 25 requests/day (free tier)
    API key: Required

    Key endpoints:
    - GLOBAL_QUOTE: Latest stock price
    - TIME_SERIES_DAILY: Historical daily prices
    - NEWS_SENTIMENT: News with AI sentiment
    - CURRENCY_EXCHANGE_RATE: Forex rates
    """

    def __init__(self):
        super().__init__(
            api_name="Alpha Vantage",
            base_url="https://www.alphavantage.co/query",
            api_key=settings.ALPHA_VANTAGE_API_KEY,
            cache_ttl=300,  # 5 minutes (stock data changes frequently)
            timeout=15,
            max_results=10
        )

        # Alpha Vantage uses apikey as query parameter, not header
        if "Authorization" in self.headers:
            del self.headers["Authorization"]

    def is_relevant_for_domain(self, domain: str, jurisdiction: str) -> bool:
        """Alpha Vantage covers Finance globally."""
        return domain == "Finance"

    def search(self, query: str, domain: str, jurisdiction: str, entities: Optional[List[Dict[str, str]]] = None) -> List[Dict[str, Any]]:
        """
        Search Alpha Vantage for financial data.

        Args:
            query: Search query (e.g., "Apple stock price", "Bitcoin price")
            domain: Finance
            jurisdiction: Any
            entities: Optional NER entities for ticker extraction

        Returns:
            List of evidence dictionaries
        """
        # Domain check removed - adapter selection already filters by relevance
        # This was blocking calls from secondary domain routing and keyword routing

        if not self.api_key:
            logger.warning("Alpha Vantage API key not configured, skipping")
            return []

        query_lower = query.lower()
        evidence = []

        try:
            # Extract ticker symbol from entities or query
            ticker = self._extract_ticker(query, entities)

            # Determine what type of financial data to fetch
            # NOTE: Order matters! Check specific commodities/crypto BEFORE generic terms like "price"
            # because "oil price" should match commodity, not stock
            if any(term in query_lower for term in ["oil", "crude", "brent", "wti", "petroleum", "natural gas", "commodity", "barrel"]):
                evidence.extend(self._get_commodity_price(query))
            elif any(term in query_lower for term in ["bitcoin", "crypto", "ethereum", "btc", "eth"]):
                evidence.extend(self._get_crypto_rate(query))
            elif any(term in query_lower for term in ["exchange rate", "forex", "currency", "usd", "eur", "gbp"]):
                evidence.extend(self._get_forex_rate(query))
            elif any(term in query_lower for term in ["stock", "share", "price", "trading"]):
                if ticker:
                    evidence.extend(self._get_stock_quote(ticker))
                else:
                    evidence.extend(self._search_symbol(query))
            elif any(term in query_lower for term in ["news", "sentiment", "market"]):
                evidence.extend(self._get_news_sentiment(ticker or query))
            else:
                # Default: try stock quote if ticker found, else search
                if ticker:
                    evidence.extend(self._get_stock_quote(ticker))
                else:
                    evidence.extend(self._search_symbol(query))

            return evidence

        except Exception as e:
            logger.error(f"Alpha Vantage search failed for '{query}': {e}")
            return []

    def _extract_ticker(self, query: str, entities: Optional[List[Dict[str, str]]] = None) -> Optional[str]:
        """Extract stock ticker from query or entities."""
        # Common company to ticker mapping
        company_tickers = {
            "apple": "AAPL", "microsoft": "MSFT", "google": "GOOGL", "alphabet": "GOOGL",
            "amazon": "AMZN", "tesla": "TSLA", "meta": "META", "facebook": "META",
            "nvidia": "NVDA", "netflix": "NFLX", "intel": "INTC", "amd": "AMD",
            "ibm": "IBM", "oracle": "ORCL", "salesforce": "CRM", "adobe": "ADBE",
            "paypal": "PYPL", "uber": "UBER", "airbnb": "ABNB", "spotify": "SPOT",
            "twitter": "X", "snap": "SNAP", "pinterest": "PINS", "zoom": "ZM",
            "shopify": "SHOP", "square": "SQ", "block": "SQ", "coinbase": "COIN",
            "disney": "DIS", "warner": "WBD", "comcast": "CMCSA", "verizon": "VZ",
            "at&t": "T", "boeing": "BA", "lockheed": "LMT", "raytheon": "RTX",
            "jpmorgan": "JPM", "goldman": "GS", "morgan stanley": "MS", "citi": "C",
            "bank of america": "BAC", "wells fargo": "WFC", "visa": "V", "mastercard": "MA",
            "walmart": "WMT", "target": "TGT", "costco": "COST", "home depot": "HD",
            "nike": "NKE", "starbucks": "SBUX", "mcdonald": "MCD", "coca-cola": "KO",
            "pepsi": "PEP", "procter": "PG", "johnson": "JNJ", "pfizer": "PFE",
            "moderna": "MRNA", "exxon": "XOM", "chevron": "CVX", "shell": "SHEL",
        }

        query_lower = query.lower()

        # Check for company name matches
        for company, ticker in company_tickers.items():
            if company in query_lower:
                return ticker

        # Check for direct ticker symbols (uppercase, 1-5 chars)
        import re
        ticker_match = re.search(r'\b([A-Z]{1,5})\b', query)
        if ticker_match:
            potential_ticker = ticker_match.group(1)
            # Verify it's likely a ticker (not a common word)
            common_words = {"A", "I", "THE", "AND", "OR", "FOR", "TO", "IN", "ON", "AT", "IS", "IT", "BE", "AS", "BY"}
            if potential_ticker not in common_words:
                return potential_ticker

        # Check entities for ORG type
        if entities:
            for entity in entities:
                if entity.get("type") == "ORG":
                    org_name = entity.get("text", "").lower()
                    for company, ticker in company_tickers.items():
                        if company in org_name:
                            return ticker

        return None

    def _get_stock_quote(self, ticker: str) -> List[Dict[str, Any]]:
        """Get latest stock quote for a ticker."""
        params = {
            "function": "GLOBAL_QUOTE",
            "symbol": ticker,
            "apikey": self.api_key
        }

        try:
            response = self._make_request("", params=params)

            if not response or "Global Quote" not in response:
                logger.warning(f"Alpha Vantage returned no quote for {ticker}")
                return []

            quote = response["Global Quote"]
            if not quote:
                return []

            price = quote.get("05. price", "N/A")
            change = quote.get("09. change", "N/A")
            change_pct = quote.get("10. change percent", "N/A")
            volume = quote.get("06. volume", "N/A")
            latest_day = quote.get("07. latest trading day", "N/A")

            snippet = (
                f"{ticker} stock price: ${price} (Change: {change} / {change_pct}). "
                f"Volume: {volume}. Latest trading day: {latest_day}."
            )

            evidence = self._create_evidence_dict(
                title=f"{ticker} Stock Quote - Alpha Vantage",
                snippet=snippet,
                url=f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={ticker}",
                source_date=datetime.utcnow(),
                metadata={
                    "api_source": "Alpha Vantage",
                    "data_type": "stock_quote",
                    "ticker": ticker,
                    "price": price,
                    "change": change,
                    "change_percent": change_pct,
                    "volume": volume
                }
            )
            return [evidence]

        except Exception as e:
            logger.error(f"Alpha Vantage stock quote failed for {ticker}: {e}")
            return []

    def _search_symbol(self, query: str) -> List[Dict[str, Any]]:
        """Search for stock symbols matching a query."""
        params = {
            "function": "SYMBOL_SEARCH",
            "keywords": query[:50],  # Limit query length
            "apikey": self.api_key
        }

        try:
            response = self._make_request("", params=params)

            if not response or "bestMatches" not in response:
                return []

            evidence_list = []
            for match in response["bestMatches"][:5]:
                symbol = match.get("1. symbol", "")
                name = match.get("2. name", "")
                match_type = match.get("3. type", "")
                region = match.get("4. region", "")

                evidence = self._create_evidence_dict(
                    title=f"{symbol} - {name}",
                    snippet=f"{name} ({symbol}): {match_type} listed in {region}.",
                    url=f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}",
                    source_date=datetime.utcnow(),
                    metadata={
                        "api_source": "Alpha Vantage",
                        "data_type": "symbol_search",
                        "ticker": symbol,
                        "company_name": name,
                        "type": match_type,
                        "region": region
                    }
                )
                evidence_list.append(evidence)

            return evidence_list

        except Exception as e:
            logger.error(f"Alpha Vantage symbol search failed: {e}")
            return []

    def _get_crypto_rate(self, query: str) -> List[Dict[str, Any]]:
        """Get cryptocurrency exchange rate."""
        # Determine crypto symbol
        crypto_map = {
            "bitcoin": "BTC", "btc": "BTC",
            "ethereum": "ETH", "eth": "ETH",
            "litecoin": "LTC", "ltc": "LTC",
            "ripple": "XRP", "xrp": "XRP",
            "dogecoin": "DOGE", "doge": "DOGE",
            "cardano": "ADA", "ada": "ADA",
            "solana": "SOL", "sol": "SOL",
        }

        query_lower = query.lower()
        crypto = "BTC"  # Default to Bitcoin
        for name, symbol in crypto_map.items():
            if name in query_lower:
                crypto = symbol
                break

        params = {
            "function": "CURRENCY_EXCHANGE_RATE",
            "from_currency": crypto,
            "to_currency": "USD",
            "apikey": self.api_key
        }

        try:
            response = self._make_request("", params=params)

            if not response or "Realtime Currency Exchange Rate" not in response:
                return []

            rate_data = response["Realtime Currency Exchange Rate"]
            rate = rate_data.get("5. Exchange Rate", "N/A")
            from_name = rate_data.get("2. From_Currency Name", crypto)
            last_refresh = rate_data.get("6. Last Refreshed", "N/A")

            snippet = f"{from_name} ({crypto}) price: ${rate} USD. Last updated: {last_refresh}."

            evidence = self._create_evidence_dict(
                title=f"{crypto}/USD Exchange Rate - Alpha Vantage",
                snippet=snippet,
                url=f"https://www.alphavantage.co/query?function=CURRENCY_EXCHANGE_RATE&from_currency={crypto}&to_currency=USD",
                source_date=datetime.utcnow(),
                metadata={
                    "api_source": "Alpha Vantage",
                    "data_type": "crypto_rate",
                    "crypto": crypto,
                    "rate_usd": rate
                }
            )
            return [evidence]

        except Exception as e:
            logger.error(f"Alpha Vantage crypto rate failed: {e}")
            return []

    def _get_forex_rate(self, query: str) -> List[Dict[str, Any]]:
        """Get forex exchange rate."""
        # Extract currency pair from query
        currencies = {
            "usd": "USD", "dollar": "USD",
            "eur": "EUR", "euro": "EUR",
            "gbp": "GBP", "pound": "GBP", "sterling": "GBP",
            "jpy": "JPY", "yen": "JPY",
            "cad": "CAD", "canadian": "CAD",
            "aud": "AUD", "australian": "AUD",
            "chf": "CHF", "swiss": "CHF",
        }

        query_lower = query.lower()
        from_curr = "USD"
        to_curr = "EUR"

        found = []
        for name, code in currencies.items():
            if name in query_lower and code not in found:
                found.append(code)
                if len(found) >= 2:
                    break

        if len(found) >= 2:
            from_curr, to_curr = found[0], found[1]
        elif len(found) == 1:
            from_curr = found[0]
            to_curr = "USD" if from_curr != "USD" else "EUR"

        params = {
            "function": "CURRENCY_EXCHANGE_RATE",
            "from_currency": from_curr,
            "to_currency": to_curr,
            "apikey": self.api_key
        }

        try:
            response = self._make_request("", params=params)

            if not response or "Realtime Currency Exchange Rate" not in response:
                return []

            rate_data = response["Realtime Currency Exchange Rate"]
            rate = rate_data.get("5. Exchange Rate", "N/A")
            last_refresh = rate_data.get("6. Last Refreshed", "N/A")

            snippet = f"{from_curr}/{to_curr} exchange rate: {rate}. Last updated: {last_refresh}."

            evidence = self._create_evidence_dict(
                title=f"{from_curr}/{to_curr} Exchange Rate - Alpha Vantage",
                snippet=snippet,
                url=f"https://www.alphavantage.co/query?function=CURRENCY_EXCHANGE_RATE&from_currency={from_curr}&to_currency={to_curr}",
                source_date=datetime.utcnow(),
                metadata={
                    "api_source": "Alpha Vantage",
                    "data_type": "forex_rate",
                    "from_currency": from_curr,
                    "to_currency": to_curr,
                    "rate": rate
                }
            )
            return [evidence]

        except Exception as e:
            logger.error(f"Alpha Vantage forex rate failed: {e}")
            return []

    def _get_commodity_price(self, query: str) -> List[Dict[str, Any]]:
        """
        Get commodity prices from Alpha Vantage.

        Supports: Brent Crude, WTI Crude, Natural Gas, and other commodities.

        Args:
            query: Search query containing commodity keywords

        Returns:
            List of evidence dictionaries with commodity price data
        """
        # Map query terms to Alpha Vantage commodity functions
        commodity_map = {
            "brent": ("BRENT", "Brent Crude Oil"),
            "wti": ("WTI", "WTI Crude Oil"),
            "crude": ("BRENT", "Brent Crude Oil"),  # Default crude to Brent
            "oil": ("BRENT", "Brent Crude Oil"),  # Default oil to Brent
            "petroleum": ("BRENT", "Brent Crude Oil"),
            "natural gas": ("NATURAL_GAS", "Natural Gas"),
            "gas": ("NATURAL_GAS", "Natural Gas"),
            "copper": ("COPPER", "Copper"),
            "aluminum": ("ALUMINUM", "Aluminum"),
            "wheat": ("WHEAT", "Wheat"),
            "corn": ("CORN", "Corn"),
            "cotton": ("COTTON", "Cotton"),
            "sugar": ("SUGAR", "Sugar"),
            "coffee": ("COFFEE", "Coffee"),
        }

        query_lower = query.lower()

        # Find matching commodity
        function_name = "BRENT"  # Default
        commodity_name = "Brent Crude Oil"

        for term, (func, name) in commodity_map.items():
            if term in query_lower:
                function_name = func
                commodity_name = name
                break

        params = {
            "function": function_name,
            "interval": "daily",
            "apikey": self.api_key
        }

        try:
            response = self._make_request("", params=params)

            if not response or "data" not in response:
                logger.warning(f"Alpha Vantage returned no data for commodity {function_name}")
                return []

            # Get the most recent data point
            data = response.get("data", [])
            if not data:
                return []

            # Get latest price
            latest = data[0]
            current_value = latest.get("value", "N/A")
            current_date = latest.get("date", "N/A")

            # Calculate percentage change if we have historical data
            pct_change = None
            prev_value = None
            if len(data) >= 2:
                try:
                    current = float(current_value)
                    previous = float(data[1].get("value", 0))
                    if previous > 0:
                        pct_change = ((current - previous) / previous) * 100
                        prev_value = previous
                except (ValueError, TypeError):
                    pass

            # Build detailed snippet
            if pct_change is not None:
                change_direction = "up" if pct_change > 0 else "down"
                snippet = (
                    f"{commodity_name} price: ${current_value}/barrel as of {current_date}. "
                    f"Price {change_direction} {abs(pct_change):.2f}% from previous close (${prev_value:.2f})."
                )
            else:
                snippet = f"{commodity_name} price: ${current_value}/barrel as of {current_date}."

            # Parse date
            source_date = datetime.utcnow()
            if current_date and current_date != "N/A":
                try:
                    source_date = datetime.strptime(current_date, "%Y-%m-%d")
                except:
                    pass

            evidence = self._create_evidence_dict(
                title=f"{commodity_name} Price - Alpha Vantage",
                snippet=snippet,
                url=f"https://www.alphavantage.co/query?function={function_name}&interval=daily",
                source_date=source_date,
                metadata={
                    "api_source": "Alpha Vantage",
                    "data_type": "commodity_price",
                    "commodity": function_name,
                    "commodity_name": commodity_name,
                    "price": current_value,
                    "date": current_date,
                    "pct_change": round(pct_change, 2) if pct_change else None,
                    "unit": "USD/barrel" if "Oil" in commodity_name else "USD"
                }
            )

            logger.info(f"Alpha Vantage commodity price: {commodity_name} = ${current_value}")
            return [evidence]

        except Exception as e:
            logger.error(f"Alpha Vantage commodity price failed for {function_name}: {e}")
            return []

    def _get_news_sentiment(self, query: str) -> List[Dict[str, Any]]:
        """Get news with sentiment analysis."""
        params = {
            "function": "NEWS_SENTIMENT",
            "tickers": query if query.isupper() and len(query) <= 5 else "",
            "topics": "" if query.isupper() else query[:50],
            "limit": 5,
            "apikey": self.api_key
        }

        # Remove empty params
        params = {k: v for k, v in params.items() if v}
        params["apikey"] = self.api_key
        params["function"] = "NEWS_SENTIMENT"
        params["limit"] = 5

        try:
            response = self._make_request("", params=params)

            if not response or "feed" not in response:
                return []

            evidence_list = []
            for article in response["feed"][:5]:
                title = article.get("title", "Financial News")
                summary = article.get("summary", "")[:300]
                url = article.get("url", "")
                sentiment = article.get("overall_sentiment_label", "Neutral")
                sentiment_score = article.get("overall_sentiment_score", 0)
                time_published = article.get("time_published", "")

                # Parse date
                source_date = None
                if time_published:
                    try:
                        source_date = datetime.strptime(time_published[:8], "%Y%m%d")
                    except:
                        source_date = datetime.utcnow()

                snippet = f"{summary} [Sentiment: {sentiment} ({sentiment_score:.2f})]"

                evidence = self._create_evidence_dict(
                    title=title,
                    snippet=snippet,
                    url=url,
                    source_date=source_date or datetime.utcnow(),
                    metadata={
                        "api_source": "Alpha Vantage",
                        "data_type": "news_sentiment",
                        "sentiment_label": sentiment,
                        "sentiment_score": sentiment_score
                    }
                )
                evidence_list.append(evidence)

            return evidence_list

        except Exception as e:
            logger.error(f"Alpha Vantage news sentiment failed: {e}")
            return []

    def _transform_response(self, raw_response: Any) -> List[Dict[str, Any]]:
        """Generic transform - handled by specific methods."""
        return []


# ========== MARKETAUX ADAPTER (Financial News) ==========

class MarketauxAdapter(GovernmentAPIClient):
    """
    Marketaux API Adapter.

    Covers: Finance (financial news, sentiment)
    Jurisdiction: Global
    Rate limits: 100 requests/day (free tier)
    API key: Required

    Key endpoints:
    - /news/all: Financial news with entity filtering
    - /entity/search: Find companies/stocks
    - /entity/trending: Trending entities
    """

    def __init__(self):
        super().__init__(
            api_name="Marketaux",
            base_url="https://api.marketaux.com/v1",
            api_key=settings.MARKETAUX_API_KEY,
            cache_ttl=600,  # 10 minutes (news updates frequently)
            timeout=15,
            max_results=10
        )

        # Marketaux uses api_token as query parameter
        if "Authorization" in self.headers:
            del self.headers["Authorization"]

    def is_relevant_for_domain(self, domain: str, jurisdiction: str) -> bool:
        """Marketaux covers Finance globally (news focus)."""
        return domain == "Finance"

    def search(self, query: str, domain: str, jurisdiction: str, entities: Optional[List[Dict[str, str]]] = None) -> List[Dict[str, Any]]:
        """
        Search Marketaux for financial news.

        Args:
            query: Search query (e.g., "Tesla news", "market crash")
            domain: Finance
            jurisdiction: Any
            entities: Optional NER entities

        Returns:
            List of evidence dictionaries
        """
        if not self.is_relevant_for_domain(domain, jurisdiction):
            return []

        if not self.api_key:
            logger.warning("Marketaux API key not configured, skipping")
            return []

        try:
            # Extract ticker symbol if available
            ticker = self._extract_ticker(query, entities)

            # Search for news
            evidence = self._search_news(query, ticker)

            return evidence

        except Exception as e:
            logger.error(f"Marketaux search failed for '{query}': {e}")
            return []

    def _extract_ticker(self, query: str, entities: Optional[List[Dict[str, str]]] = None) -> Optional[str]:
        """Extract stock ticker from query or entities."""
        # Common company to ticker mapping (same as Alpha Vantage)
        company_tickers = {
            "apple": "AAPL", "microsoft": "MSFT", "google": "GOOGL", "alphabet": "GOOGL",
            "amazon": "AMZN", "tesla": "TSLA", "meta": "META", "facebook": "META",
            "nvidia": "NVDA", "netflix": "NFLX", "intel": "INTC", "amd": "AMD",
            "ibm": "IBM", "disney": "DIS", "boeing": "BA", "nike": "NKE",
            "jpmorgan": "JPM", "goldman": "GS", "visa": "V", "mastercard": "MA",
            "walmart": "WMT", "coca-cola": "KO", "pepsi": "PEP", "pfizer": "PFE",
            "exxon": "XOM", "chevron": "CVX",
        }

        query_lower = query.lower()

        for company, ticker in company_tickers.items():
            if company in query_lower:
                return ticker

        # Check for direct ticker symbols
        import re
        ticker_match = re.search(r'\b([A-Z]{1,5})\b', query)
        if ticker_match:
            potential_ticker = ticker_match.group(1)
            common_words = {"A", "I", "THE", "AND", "OR", "FOR", "TO", "IN", "ON", "AT", "IS", "IT", "BE", "AS", "BY"}
            if potential_ticker not in common_words:
                return potential_ticker

        return None

    def _search_news(self, query: str, ticker: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search for financial news."""
        params = {
            "api_token": self.api_key,
            "language": "en",
            "limit": 5
        }

        if ticker:
            params["symbols"] = ticker
        else:
            params["search"] = query[:100]

        try:
            response = self._make_request("news/all", params=params)

            if not response or "data" not in response:
                logger.warning(f"Marketaux returned no news for {query}")
                return []

            evidence_list = []
            for article in response["data"][:5]:
                title = article.get("title", "Financial News")
                description = article.get("description", "")[:400]
                url = article.get("url", "")
                published = article.get("published_at", "")
                source_name = article.get("source", "")

                # Extract sentiment if available
                sentiment = article.get("sentiment", {})
                sentiment_score = sentiment.get("score", 0) if isinstance(sentiment, dict) else 0

                # Parse date
                source_date = None
                if published:
                    try:
                        source_date = datetime.fromisoformat(published.replace("Z", "+00:00"))
                    except:
                        source_date = datetime.utcnow()

                # Extract relevant entities
                entities = article.get("entities", [])
                entity_names = [e.get("name", "") for e in entities[:3]] if entities else []
                entity_str = f" [Related: {', '.join(entity_names)}]" if entity_names else ""

                snippet = f"{description}{entity_str}"
                if sentiment_score:
                    snippet += f" [Sentiment: {sentiment_score:.2f}]"

                evidence = self._create_evidence_dict(
                    title=title,
                    snippet=snippet,
                    url=url,
                    source_date=source_date or datetime.utcnow(),
                    metadata={
                        "api_source": "Marketaux",
                        "data_type": "financial_news",
                        "source_name": source_name,
                        "sentiment_score": sentiment_score,
                        "entities": entity_names
                    }
                )
                evidence_list.append(evidence)

            logger.info(f"Marketaux returned {len(evidence_list)} news items")
            return evidence_list

        except Exception as e:
            logger.error(f"Marketaux news search failed: {e}")
            return []

    def _transform_response(self, raw_response: Any) -> List[Dict[str, Any]]:
        """Generic transform - handled by _search_news."""
        return []


# ========== CROSSREF ADAPTER (Academic Research Metadata) ==========

class CrossRefAdapter(GovernmentAPIClient):
    """
    CrossRef API Adapter.

    Covers: Science
    Jurisdiction: Global
    Free tier: Unlimited (polite usage with contact email)
    API key: Not required
    """

    def __init__(self):
        super().__init__(
            api_name="CrossRef",
            base_url="https://api.crossref.org",
            api_key=None,
            cache_ttl=86400 * 14,  # 14 days (research metadata stable)
            timeout=10,
            max_results=10
        )

        # CrossRef requests User-Agent with contact email
        self.headers.update({
            "User-Agent": "Tru8FactChecker/1.0 (https://tru8.com; mailto:contact@tru8.com)"
        })

    def is_relevant_for_domain(self, domain: str, jurisdiction: str) -> bool:
        """CrossRef covers academic papers across knowledge domains."""
        return domain in [
            "Science", "Climate", "History", "Health",
            "Politics", "Law", "Demographics", "Animals"
        ]

    def search(self, query: str, domain: str, jurisdiction: str, entities: Optional[List[Dict[str, str]]] = None) -> List[Dict[str, Any]]:
        """
        Search CrossRef for academic research.

        Args:
            query: Search query (e.g., "climate change impact")
            domain: Science
            jurisdiction: Any

        Returns:
            List of evidence dictionaries
        """
        if not self.is_relevant_for_domain(domain, jurisdiction):
            return []

        query = self._sanitize_query(query)

        params = {
            "query": query,
            "rows": self.max_results,
            "sort": "relevance",
            "select": "title,author,published-print,DOI,publisher,abstract"
        }

        try:
            response = self._make_request("/works", params=params)

            if not response or "message" not in response:
                logger.warning(f"CrossRef returned empty response for: {query}")
                return []

            return self._transform_response(response["message"])

        except Exception as e:
            logger.error(f"CrossRef search failed for '{query}': {e}")
            return []

    def _transform_response(self, raw_response: Any) -> List[Dict[str, Any]]:
        """Transform CrossRef API response to standardized evidence format."""
        evidence_list = []

        for item in raw_response.get("items", []):
            try:
                doi = item.get("DOI")
                title_list = item.get("title", [])
                title = title_list[0] if title_list else f"Research Article {doi}"

                # Extract abstract if available
                abstract = item.get("abstract", "")
                snippet = abstract[:300] if abstract else f"Academic research: {title}"

                # Build URL
                url = f"https://doi.org/{doi}" if doi else "https://www.crossref.org/"

                # Extract publication date
                pub_date = item.get("published-print") or item.get("published-online")
                source_date = None
                if pub_date and "date-parts" in pub_date:
                    date_parts = pub_date["date-parts"][0]
                    if len(date_parts) >= 3:
                        source_date = datetime(date_parts[0], date_parts[1], date_parts[2])
                    elif len(date_parts) >= 1:
                        source_date = datetime(date_parts[0], 1, 1)

                # Extract authors
                authors = item.get("author", [])
                author_names = [
                    f"{a.get('given', '')} {a.get('family', '')}".strip()
                    for a in authors[:3]
                ]

                metadata = {
                    "api_source": "CrossRef",
                    "doi": doi,
                    "publisher": item.get("publisher"),
                    "authors": ", ".join(author_names) if author_names else "Authors not listed"
                }

                evidence = self._create_evidence_dict(
                    title=title,
                    snippet=snippet,
                    url=url,
                    source_date=source_date,
                    metadata=metadata
                )

                evidence_list.append(evidence)

            except Exception as e:
                logger.warning(f"Failed to parse CrossRef item: {e}")
                continue

        logger.info(f"CrossRef returned {len(evidence_list)} evidence items")
        return evidence_list


# ========== GOV.UK CONTENT API ADAPTER ==========

class GovUKAdapter(GovernmentAPIClient):
    """
    GOV.UK Content API Adapter.

    Covers: Government, General
    Jurisdiction: UK
    Free tier: Unlimited
    API key: Not required
    """

    def __init__(self):
        super().__init__(
            api_name="GOV.UK Content API",
            base_url="https://www.gov.uk/api/search.json",
            api_key=None,
            cache_ttl=86400,  # 1 day
            timeout=10,
            max_results=10
        )

    def is_relevant_for_domain(self, domain: str, jurisdiction: str) -> bool:
        """GOV.UK covers Government, History, and Law for UK."""
        return domain in ["Government", "General", "History", "Law"] and jurisdiction in ["UK", "Global"]

    def search(self, query: str, domain: str, jurisdiction: str, entities: Optional[List[Dict[str, str]]] = None) -> List[Dict[str, Any]]:
        """
        Search GOV.UK content.

        Args:
            query: Search query
            domain: Government or General
            jurisdiction: UK

        Returns:
            List of evidence dictionaries
        """
        if not self.is_relevant_for_domain(domain, jurisdiction):
            return []

        query = self._sanitize_query(query)

        params = {
            "q": query,
            "count": self.max_results
        }

        try:
            # GOV.UK search doesn't use /api/ prefix in base_url
            response = self._make_request("", params=params)

            if not response or "results" not in response:
                logger.warning(f"GOV.UK returned empty response for: {query}")
                return []

            return self._transform_response(response)

        except Exception as e:
            logger.error(f"GOV.UK search failed for '{query}': {e}")
            return []

    def _transform_response(self, raw_response: Any) -> List[Dict[str, Any]]:
        """Transform GOV.UK API response to standardized evidence format."""
        evidence_list = []

        for item in raw_response.get("results", []):
            try:
                title = item.get("title", "GOV.UK Content")
                description = item.get("description", "")
                url = f"https://www.gov.uk{item.get('link', '')}"

                snippet = description[:300] if description else title

                # Parse public timestamp
                public_timestamp = item.get("public_timestamp")
                source_date = None
                if public_timestamp:
                    try:
                        source_date = datetime.fromisoformat(public_timestamp.replace("Z", "+00:00"))
                    except Exception:
                        pass

                metadata = {
                    "api_source": "GOV.UK",
                    "format": item.get("format"),
                    "organisations": item.get("organisations", [])
                }

                evidence = self._create_evidence_dict(
                    title=title,
                    snippet=snippet,
                    url=url,
                    source_date=source_date,
                    metadata=metadata
                )

                evidence_list.append(evidence)

            except Exception as e:
                logger.warning(f"Failed to parse GOV.UK item: {e}")
                continue

        logger.info(f"GOV.UK returned {len(evidence_list)} evidence items")
        return evidence_list


# ========== UK PARLIAMENT HANSARD ADAPTER ==========

class HansardAdapter(GovernmentAPIClient):
    """
    UK Parliament Hansard API Adapter.

    Covers: Government, Law
    Jurisdiction: UK
    Free tier: Unlimited
    API key: Not required
    """

    def __init__(self):
        super().__init__(
            api_name="UK Parliament Hansard",
            base_url="https://hansard-api.parliament.uk",
            api_key=None,
            cache_ttl=86400 * 7,  # 7 days (historical records)
            timeout=15,
            max_results=10
        )

    def is_relevant_for_domain(self, domain: str, jurisdiction: str) -> bool:
        """Hansard covers Government and Law for UK."""
        return domain in ["Government", "Law"] and jurisdiction in ["UK", "Global"]

    def search(self, query: str, domain: str, jurisdiction: str, entities: Optional[List[Dict[str, str]]] = None) -> List[Dict[str, Any]]:
        """
        Search UK Parliament Hansard debates.

        Args:
            query: Search query
            domain: Government or Law
            jurisdiction: UK

        Returns:
            List of evidence dictionaries
        """
        if not self.is_relevant_for_domain(domain, jurisdiction):
            return []

        query = self._sanitize_query(query)

        params = {
            "searchTerm": query,
            "take": self.max_results
        }

        try:
            response = self._make_request("/search/debates.json", params=params)

            if not response or "Response" not in response:
                logger.warning(f"Hansard returned empty response for: {query}")
                return []

            return self._transform_response(response)

        except Exception as e:
            logger.error(f"Hansard search failed for '{query}': {e}")
            return []

    def _transform_response(self, raw_response: Any) -> List[Dict[str, Any]]:
        """Transform Hansard API response to standardized evidence format."""
        evidence_list = []

        for item in raw_response.get("Response", {}).get("Results", []):
            try:
                title = item.get("Title", "Parliamentary Debate")
                excerpt = item.get("Excerpt", "")
                url = item.get("Url", "https://hansard.parliament.uk/")

                snippet = excerpt[:300] if excerpt else title

                # Parse date
                date_str = item.get("Date")
                source_date = None
                if date_str:
                    try:
                        source_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                    except Exception:
                        pass

                metadata = {
                    "api_source": "UK Parliament Hansard",
                    "debate_type": item.get("DebateType"),
                    "member": item.get("Member")
                }

                evidence = self._create_evidence_dict(
                    title=title,
                    snippet=snippet,
                    url=url,
                    source_date=source_date,
                    metadata=metadata
                )

                evidence_list.append(evidence)

            except Exception as e:
                logger.warning(f"Failed to parse Hansard item: {e}")
                continue

        logger.info(f"Hansard returned {len(evidence_list)} evidence items")
        return evidence_list


# ========== WIKIDATA ADAPTER ==========

class WikidataAdapter(GovernmentAPIClient):
    """
    Wikidata Query Service Adapter.

    Covers: General
    Jurisdiction: Global
    Free tier: Unlimited (polite usage)
    API key: Not required
    """

    def __init__(self):
        super().__init__(
            api_name="Wikidata",
            base_url="https://www.wikidata.org/w/api.php",
            api_key=None,
            cache_ttl=86400 * 30,  # 30 days (structured data stable)
            timeout=15,
            max_results=10
        )

    def is_relevant_for_domain(self, domain: str, jurisdiction: str) -> bool:
        """Wikidata covers structured data across most domains."""
        return domain in [
            "General", "History", "Politics", "Entertainment",
            "Sports", "Science", "Animals", "Climate", "Health"
        ]

    def search(self, query: str, domain: str, jurisdiction: str, entities: Optional[List[Dict[str, str]]] = None) -> List[Dict[str, Any]]:
        """
        Search Wikidata entities.

        Args:
            query: Search query
            domain: General
            jurisdiction: Any

        Returns:
            List of evidence dictionaries
        """
        if not self.is_relevant_for_domain(domain, jurisdiction):
            return []

        query = self._sanitize_query(query)

        params = {
            "action": "wbsearchentities",
            "search": query,
            "language": "en",
            "limit": self.max_results,
            "format": "json"
        }

        try:
            response = self._make_request("", params=params)

            if not response or "search" not in response:
                logger.warning(f"Wikidata returned empty response for: {query}")
                return []

            return self._transform_response(response)

        except Exception as e:
            logger.error(f"Wikidata search failed for '{query}': {e}")
            return []

    def _transform_response(self, raw_response: Any) -> List[Dict[str, Any]]:
        """Transform Wikidata API response to standardized evidence format."""
        evidence_list = []

        for item in raw_response.get("search", []):
            try:
                entity_id = item.get("id")
                title = item.get("label", f"Wikidata Entity {entity_id}")
                description = item.get("description", "")

                url = f"https://www.wikidata.org/wiki/{entity_id}"

                snippet = description if description else f"Wikidata entity: {title}"

                metadata = {
                    "api_source": "Wikidata",
                    "entity_id": entity_id,
                    "concepturi": item.get("concepturi")
                }

                evidence = self._create_evidence_dict(
                    title=title,
                    snippet=snippet,
                    url=url,
                    source_date=None,
                    metadata=metadata
                )

                evidence_list.append(evidence)

            except Exception as e:
                logger.warning(f"Failed to parse Wikidata item: {e}")
                continue

        logger.info(f"Wikidata returned {len(evidence_list)} evidence items")
        return evidence_list


# ========== GOVINFO.GOV LEGAL STATUTES ADAPTER ==========

class GovInfoAdapter(GovernmentAPIClient):
    """
    GovInfo.gov API Adapter for US Legal Statutes.

    Wraps the existing LegalSearchService (Phase 4) to integrate with
    Phase 5 Government API adapter system.

    Coverage:
    - US federal statutes and legislation
    - Congress.gov for bills and laws
    - Direct citation lookup (fastest)
    - Year + keyword search (filtered)
    - Full-text search (broad)

    Domain: Law
    Jurisdiction: US
    API: GovInfo.gov (requires GOVINFO_API_KEY)
    """

    def __init__(self):
        from app.core.config import settings

        # Initialize legal search service (handles GovInfo + Congress APIs)
        self.legal_service = LegalSearchService()

        super().__init__(
            api_name="GovInfo.gov",
            base_url="https://api.govinfo.gov",
            timeout=settings.LEGAL_API_TIMEOUT_SECONDS if hasattr(settings, 'LEGAL_API_TIMEOUT_SECONDS') else 10,
            max_results=5  # Statutes are high-quality, don't need many
        )

        # Check if API key is configured
        if not settings.GOVINFO_API_KEY:
            logger.warning("GOVINFO_API_KEY not configured - GovInfo adapter will return empty results")

    def is_relevant_for_domain(self, domain: str, jurisdiction: str) -> bool:
        """
        GovInfo covers Law, Politics, and History for US jurisdiction.

        Political articles frequently reference legislation (e.g., "DROP Act of 2025"),
        so we include Politics to ensure congressional acts are properly verified.

        Args:
            domain: Domain classification (Law, History, Politics, etc.)
            jurisdiction: US, UK, EU, Global

        Returns:
            True if this adapter can handle the domain/jurisdiction
        """
        return domain in ["Law", "History", "Politics"] and jurisdiction in ["US", "Global"]

    def search(self, query: str, domain: str, jurisdiction: str, entities: Optional[List[Dict[str, str]]] = None) -> List[Dict[str, Any]]:
        """
        Search US federal statutes and legislation.

        Uses three-tier search strategy:
        1. Direct citation lookup (if citation detected)
        2. Year + keyword search (if year detected)
        3. Full-text search (fallback)

        Args:
            query: Search query (claim text)
            domain: Law
            jurisdiction: US

        Returns:
            List of evidence dictionaries with statute excerpts
        """
        logger.info(f"[GOVINFO] search() CALLED - query: '{query[:100]}...', domain: {domain}, jurisdiction: {jurisdiction}")

        if not self.is_relevant_for_domain(domain, jurisdiction):
            logger.info(f"   [GOVINFO] Not relevant for domain={domain}, jurisdiction={jurisdiction}")
            return []

        logger.info(f"   [GOVINFO] Domain/jurisdiction match confirmed")

        try:
            # Extract legal metadata from query using classifier
            # (This is fast - just regex patterns)
            from app.utils.legal_claim_detector import LegalClaimDetector
            detector = LegalClaimDetector()
            result = detector.classify(query)

            # Only proceed if classified as legal
            if not result.get("is_legal"):
                logger.info(f"GovInfo: Query not classified as legal, skipping: {query[:50]}")
                return []

            legal_metadata = result.get("metadata", {})

            logger.info(
                f"GovInfo: Searching for legal claim with metadata: "
                f"year={legal_metadata.get('year')}, "
                f"jurisdiction={legal_metadata.get('jurisdiction')}"
            )

            # Call legal search service (async, so we need to run it)
            import asyncio
            try:
                # Try to get running loop
                loop = asyncio.get_running_loop()
                # We're in a sync context called from async via asyncio.to_thread
                # So we can't use await here, but the service handles this
                results = asyncio.run(self.legal_service.search_statutes(query, legal_metadata))
            except RuntimeError:
                # No running loop, create new one
                results = asyncio.run(self.legal_service.search_statutes(query, legal_metadata))

            # Transform legal search results to standardized evidence format
            return self._transform_response(results)

        except Exception as e:
            logger.error(f"GovInfo search failed for '{query}': {e}", exc_info=True)
            return []

    def _transform_response(self, legal_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Transform LegalSearchService results to standardized evidence format.

        LegalSearchService returns:
        {
            "title": "Act name and section",
            "text": "Statute text excerpt",
            "url": "govinfo.gov or legislation.gov.uk URL",
            "source_date": "YYYY-MM-DD",
            "citation": "Formal citation",
            "jurisdiction": "US" or "UK"
        }

        Standardized format:
        {
            "text": "Evidence text",
            "source": "GovInfo.gov",
            "url": "...",
            "title": "...",
            "published_date": "...",
            "credibility_score": 0.95,
            "external_source_provider": "GovInfo.gov",
            "metadata": {...}
        }
        """
        evidence_list = []

        for item in legal_results:
            try:
                # Extract fields from legal search result
                title = item.get("title", "Federal Statute")
                text = item.get("text", "")
                url = item.get("url", "")
                citation = item.get("citation", "")
                jurisdiction = item.get("jurisdiction", "US")

                # Parse source_date (may be string or datetime)
                source_date = item.get("source_date")
                if source_date and isinstance(source_date, str):
                    try:
                        source_date = datetime.fromisoformat(source_date.replace('Z', '+00:00'))
                    except (ValueError, AttributeError):
                        source_date = None

                # Create metadata dict with legal-specific fields
                metadata = {
                    "citation": citation,
                    "jurisdiction": jurisdiction,
                    "statute_type": item.get("statute_type", "federal"),
                    "section": item.get("section"),
                    "year": item.get("year")
                }

                # Create standardized evidence dict using base class helper
                evidence = self._create_evidence_dict(
                    title=title,
                    snippet=text,
                    url=url,
                    source_date=source_date,
                    metadata=metadata
                )

                # Override credibility for legal statutes (very high)
                evidence["credibility_score"] = 0.95

                evidence_list.append(evidence)

            except Exception as e:
                logger.warning(f"Failed to parse GovInfo legal result: {e}")
                continue

        logger.info(f"GovInfo returned {len(evidence_list)} statute excerpts")
        return evidence_list


# ========== TRANSFERMARKT ADAPTER (Historical Sports Data) ==========

class TransfermarktAdapter(GovernmentAPIClient):
    """
    Transfermarkt API Adapter for Historical Sports Data.

    Coverage:
    - Player transfers, career stats, achievements, market values
    - Club profiles and rosters
    - Historical data (complements Football-Data.org's real-time data)

    Domain: Sports
    Jurisdiction: Global
    API: Community-hosted transfermarkt-api (no key required)
    """

    def __init__(self):
        super().__init__(
            api_name="Transfermarkt",
            base_url="https://transfermarkt-api.fly.dev",
            api_key=None,  # No API key required
            cache_ttl=3600,  # 1 hour (historical data stable)
            timeout=15,
            max_results=5
        )
        # NO HARDCODED LISTS - use NER entities passed from pipeline

    def is_relevant_for_domain(self, domain: str, jurisdiction: str) -> bool:
        """Transfermarkt covers Sports domain globally."""
        return domain == "Sports"

    def search(
        self,
        query: str,
        domain: str,
        jurisdiction: str,
        entities: Optional[List[Dict[str, str]]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search Transfermarkt for historical football data.

        Uses dynamic entity extraction from NER - NO HARDCODED LISTS!

        Supports:
        - Player transfers (e.g., "Neymar transfer to PSG")
        - Career stats (e.g., "Messi career goals")
        - Achievements (e.g., "Ronaldo Ballon d'Or")
        - Market values (e.g., "Haaland market value")
        - Club info (e.g., "Manchester United squad value")

        Args:
            query: Search query (claim text)
            domain: Sports
            jurisdiction: Any
            entities: NER entities [{"text": "Karim Adeyemi", "label": "PERSON"}, ...]

        Returns:
            List of evidence dictionaries with historical data
        """
        if not self.is_relevant_for_domain(domain, jurisdiction):
            return []

        query_lower = query.lower()
        evidence = []

        try:
            # Detect query type and fetch appropriate data

            # TYPE 1: Transfer history
            if any(term in query_lower for term in ["transfer", "signed for", "joined", "left", "fee", "moved to", "sold"]):
                player_evidence = self._search_player_with_transfers(query_lower, entities)
                if player_evidence:
                    evidence.extend(player_evidence)

            # TYPE 2: Achievements / Trophies
            elif any(term in query_lower for term in ["won", "winner", "champion", "trophy", "title", "ballon d'or", "golden boot", "best player"]):
                player_evidence = self._search_player_with_achievements(query_lower, entities)
                if player_evidence:
                    evidence.extend(player_evidence)

            # TYPE 3: Career stats
            elif any(term in query_lower for term in ["career", "total goals", "all-time", "scored for", "appearances", "caps", "scored", "goals"]):
                player_evidence = self._search_player_with_stats(query_lower, entities)
                if player_evidence:
                    evidence.extend(player_evidence)

            # TYPE 4: Market value
            elif any(term in query_lower for term in ["worth", "value", "valued at", "market value", "price"]):
                player_evidence = self._search_player_with_value(query_lower, entities)
                if player_evidence:
                    evidence.extend(player_evidence)

            # TYPE 5: Club info (fallback)
            else:
                club_evidence = self._search_club(query_lower, entities)
                if club_evidence:
                    evidence.extend(club_evidence)

            logger.info(f"Transfermarkt returned {len(evidence)} evidence items")
            return evidence[:self.max_results]

        except Exception as e:
            logger.error(f"Transfermarkt search failed for '{query}': {e}", exc_info=True)
            return []

    def _extract_person_names(self, entities: Optional[List[Dict[str, str]]]) -> List[str]:
        """
        Extract PERSON entity names from NER results.

        Uses dynamic NER entities. Also accepts ENTITY labels as fallback
        if they look like person names (2+ capitalized words).

        Args:
            entities: List of NER entities [{"text": "Karim Adeyemi", "label": "PERSON"}, ...]

        Returns:
            List of person names to search for
        """
        persons = []
        entity_fallbacks = []

        if entities:
            for ent in entities:
                if not isinstance(ent, dict):
                    continue

                text = ent.get("text", "")
                label = ent.get("label", "")

                if label == "PERSON":
                    persons.append(text)
                elif label == "ENTITY":
                    # Fallback: Check if it looks like a person name
                    # (2+ words, all capitalized, no org-like suffixes)
                    words = text.split()
                    org_indicators = ("FC", "United", "City", "Club", "League", "Inc", "Ltd")
                    if (len(words) >= 2 and
                        all(w[0].isupper() for w in words if w) and
                        not any(ind in text for ind in org_indicators)):
                        entity_fallbacks.append(text)

        # Use PERSON entities first, fall back to ENTITY if none found
        return persons if persons else entity_fallbacks

    def _extract_org_names(self, entities: Optional[List[Dict[str, str]]]) -> List[str]:
        """
        Extract ORG entity names (clubs/teams) from NER results.

        Uses dynamic NER entities. Also accepts ENTITY labels as fallback
        if they look like organization names (contain org-like suffixes).

        Args:
            entities: List of NER entities [{"text": "Arsenal", "label": "ORG"}, ...]

        Returns:
            List of organization/club names to search for
        """
        orgs = []
        entity_fallbacks = []

        # Common sports/org indicators
        org_indicators = (
            "FC", "United", "City", "Rovers", "Athletic", "Club",
            "Dortmund", "Arsenal", "Chelsea", "Munich", "Madrid", "Barcelona",
            "Milan", "Inter", "Juventus", "PSG", "Bayern", "Liverpool",
            "League", "Association", "Federation", "UEFA", "FIFA"
        )

        if entities:
            for ent in entities:
                if not isinstance(ent, dict):
                    continue

                text = ent.get("text", "")
                label = ent.get("label", "")

                if label == "ORG":
                    orgs.append(text)
                elif label == "ENTITY":
                    # Fallback: Check if it looks like an organization
                    if any(ind in text for ind in org_indicators):
                        entity_fallbacks.append(text)

        # Use ORG entities first, fall back to ENTITY if none found
        return orgs if orgs else entity_fallbacks

    def _search_player_with_transfers(
        self,
        query_lower: str,
        entities: Optional[List[Dict[str, str]]] = None
    ) -> List[Dict[str, Any]]:
        """Search for player and return transfer history using NER entities."""
        person_names = self._extract_person_names(entities)
        if not person_names:
            logger.debug("Transfermarkt: No PERSON entities found for transfer search")
            return []

        all_evidence = []

        for player_name in person_names:
            try:
                # Search for player using API's own fuzzy matching
                search_response = self._make_request(f"/players/search/{player_name}")
                if not search_response or "results" not in search_response:
                    continue

                results = search_response.get("results", [])
                if not results:
                    continue

                # Get first matching player
                player = results[0]
                player_id = player.get("id")
                player_name_full = player.get("name", player_name)

                # Get transfer history
                transfers_response = self._make_request(f"/players/{player_id}/transfers")
                if not transfers_response or "transfers" not in transfers_response:
                    continue

                transfers = transfers_response.get("transfers", [])

                # Build transfer history evidence
                transfer_text = f"Transfer History for {player_name_full}:\n"
                for t in transfers[:10]:
                    date = t.get("date", "Unknown")
                    from_club = t.get("from", {}).get("clubName", "Unknown")
                    to_club = t.get("to", {}).get("clubName", "Unknown")
                    fee = t.get("fee", "Undisclosed")

                    transfer_text += f"- {date}: {from_club} → {to_club} ({fee})\n"

                all_evidence.append(self._create_evidence_dict(
                    title=f"{player_name_full} - Transfer History",
                    snippet=transfer_text.strip(),
                    url=f"https://www.transfermarkt.com/player/{player_id}",
                    source_date=datetime.utcnow(),
                    metadata={
                        "api_source": "Transfermarkt",
                        "player_id": player_id,
                        "data_type": "transfers",
                        "transfer_count": len(transfers)
                    }
                ))

            except Exception as e:
                logger.error(f"Transfermarkt player transfer search failed for {player_name}: {e}")
                continue

        return all_evidence

    def _search_player_with_achievements(
        self,
        query_lower: str,
        entities: Optional[List[Dict[str, str]]] = None
    ) -> List[Dict[str, Any]]:
        """Search for player and return achievements/trophies using NER entities."""
        person_names = self._extract_person_names(entities)
        if not person_names:
            logger.debug("Transfermarkt: No PERSON entities found for achievements search")
            return []

        all_evidence = []

        for player_name in person_names:
            try:
                # Search for player
                search_response = self._make_request(f"/players/search/{player_name}")
                if not search_response or "results" not in search_response:
                    continue

                results = search_response.get("results", [])
                if not results:
                    continue

                player = results[0]
                player_id = player.get("id")
                player_name_full = player.get("name", player_name)

                # Get achievements
                achievements_response = self._make_request(f"/players/{player_id}/achievements")
                if not achievements_response or "achievements" not in achievements_response:
                    continue

                achievements = achievements_response.get("achievements", [])

                # Build achievements evidence
                achievements_text = f"Achievements for {player_name_full}:\n"
                for a in achievements[:15]:
                    title = a.get("title", "Unknown")
                    count = a.get("count", 1)

                    if count > 1:
                        achievements_text += f"- {title} ({count}x)\n"
                    else:
                        achievements_text += f"- {title}\n"

                all_evidence.append(self._create_evidence_dict(
                    title=f"{player_name_full} - Career Achievements",
                    snippet=achievements_text.strip(),
                    url=f"https://www.transfermarkt.com/player/{player_id}",
                    source_date=datetime.utcnow(),
                    metadata={
                        "api_source": "Transfermarkt",
                        "player_id": player_id,
                        "data_type": "achievements",
                        "achievement_count": len(achievements)
                    }
                ))

            except Exception as e:
                logger.error(f"Transfermarkt player achievements search failed for {player_name}: {e}")
                continue

        return all_evidence

    def _search_player_with_stats(
        self,
        query_lower: str,
        entities: Optional[List[Dict[str, str]]] = None
    ) -> List[Dict[str, Any]]:
        """Search for player and return career statistics using NER entities."""
        person_names = self._extract_person_names(entities)
        if not person_names:
            logger.debug("Transfermarkt: No PERSON entities found for stats search")
            return []

        all_evidence = []

        for player_name in person_names:
            try:
                # Search for player
                search_response = self._make_request(f"/players/search/{player_name}")
                if not search_response or "results" not in search_response:
                    continue

                results = search_response.get("results", [])
                if not results:
                    continue

                player = results[0]
                player_id = player.get("id")
                player_name_full = player.get("name", player_name)

                # Get stats
                stats_response = self._make_request(f"/players/{player_id}/stats")
                if not stats_response or "stats" not in stats_response:
                    continue

                stats = stats_response.get("stats", [])

                # Build career stats evidence
                stats_text = f"Career Statistics for {player_name_full}:\n"
                total_goals = 0
                total_assists = 0
                total_apps = 0

                for s in stats:
                    competition = s.get("competitionName", "Unknown")
                    goals = s.get("goals", 0) or 0
                    assists = s.get("assists", 0) or 0
                    appearances = s.get("appearances", 0) or 0

                    total_goals += goals
                    total_assists += assists
                    total_apps += appearances

                    if appearances > 0:
                        stats_text += f"- {competition}: {appearances} apps, {goals} goals, {assists} assists\n"

                stats_text += f"\nCareer Totals: {total_apps} appearances, {total_goals} goals, {total_assists} assists"

                all_evidence.append(self._create_evidence_dict(
                    title=f"{player_name_full} - Career Statistics",
                    snippet=stats_text.strip(),
                    url=f"https://www.transfermarkt.com/player/{player_id}",
                    source_date=datetime.utcnow(),
                    metadata={
                        "api_source": "Transfermarkt",
                        "player_id": player_id,
                        "data_type": "career_stats",
                        "total_goals": total_goals,
                        "total_assists": total_assists,
                        "total_appearances": total_apps
                    }
                ))

            except Exception as e:
                logger.error(f"Transfermarkt player stats search failed for {player_name}: {e}")
                continue

        return all_evidence

    def _search_player_with_value(
        self,
        query_lower: str,
        entities: Optional[List[Dict[str, str]]] = None
    ) -> List[Dict[str, Any]]:
        """Search for player and return market value history using NER entities."""
        person_names = self._extract_person_names(entities)
        if not person_names:
            logger.debug("Transfermarkt: No PERSON entities found for value search")
            return []

        all_evidence = []

        for player_name in person_names:
            try:
                # Search for player
                search_response = self._make_request(f"/players/search/{player_name}")
                if not search_response or "results" not in search_response:
                    continue

                results = search_response.get("results", [])
                if not results:
                    continue

                player = results[0]
                player_id = player.get("id")
                player_name_full = player.get("name", player_name)
                current_value = player.get("marketValue", "Unknown")

                # Get market value history
                value_response = self._make_request(f"/players/{player_id}/market_value")

                value_text = f"Market Value for {player_name_full}:\n"
                value_text += f"Current Value: {current_value}\n"

                if value_response and "marketValueHistory" in value_response:
                    history = value_response.get("marketValueHistory", [])
                    if history:
                        value_text += "\nValue History:\n"
                        for h in history[:5]:  # Last 5 entries
                            date = h.get("date", "Unknown")
                            value = h.get("value", "Unknown")
                            club = h.get("clubName", "Unknown")
                            value_text += f"- {date}: {value} ({club})\n"

                all_evidence.append(self._create_evidence_dict(
                    title=f"{player_name_full} - Market Value",
                    snippet=value_text.strip(),
                    url=f"https://www.transfermarkt.com/player/{player_id}",
                    source_date=datetime.utcnow(),
                    metadata={
                        "api_source": "Transfermarkt",
                        "player_id": player_id,
                        "data_type": "market_value",
                        "current_value": current_value
                    }
                ))

            except Exception as e:
                logger.error(f"Transfermarkt player value search failed for {player_name}: {e}")
                continue

        return all_evidence

    def _search_club(
        self,
        query_lower: str,
        entities: Optional[List[Dict[str, str]]] = None
    ) -> List[Dict[str, Any]]:
        """Search for club and return profile using NER entities - NO HARDCODED LISTS!"""
        org_names = self._extract_org_names(entities)
        if not org_names:
            logger.debug("Transfermarkt: No ORG entities found for club search")
            return []

        all_evidence = []

        for club_name in org_names:
            try:
                # Search for club using API's own fuzzy matching
                search_response = self._make_request(f"/clubs/search/{club_name}")
                if not search_response or "results" not in search_response:
                    continue

                results = search_response.get("results", [])
                if not results:
                    continue

                club = results[0]
                club_id = club.get("id")
                club_name_full = club.get("name", club_name)
                market_value = club.get("marketValue", "Unknown")
                squad_size = club.get("squadSize", "Unknown")

                club_text = f"{club_name_full}\n"
                club_text += f"Squad Size: {squad_size} players\n"
                club_text += f"Total Market Value: {market_value}\n"

                all_evidence.append(self._create_evidence_dict(
                    title=f"{club_name_full} - Club Profile",
                    snippet=club_text.strip(),
                    url=f"https://www.transfermarkt.com/club/{club_id}",
                    source_date=datetime.utcnow(),
                    metadata={
                        "api_source": "Transfermarkt",
                        "club_id": club_id,
                        "data_type": "club_profile",
                        "market_value": market_value
                    }
                ))

            except Exception as e:
                logger.error(f"Transfermarkt club search failed for {club_name}: {e}")
                continue

        return all_evidence

    def _transform_response(self, raw_response: Any) -> List[Dict[str, Any]]:
        """Transform Transfermarkt API response to standardized evidence format."""
        # Handled by specific methods above
        return []


# ========== FOOTBALL-DATA.ORG ADAPTER (Sports Statistics) ==========

class FootballDataAdapter(GovernmentAPIClient):
    """
    Football-Data.org API Adapter for Sports Statistics.

    Coverage:
    - Premier League, La Liga, Serie A, Bundesliga, Ligue 1
    - Current standings, match results, team info
    - Player statistics (limited on free tier)

    Domain: Sports
    Jurisdiction: Global (European football)
    API: Football-Data.org (requires API key, free tier: 10 calls/min)
    """

    def __init__(self):
        # Use settings instead of os.getenv - .env loaded by pydantic-settings
        api_key = settings.FOOTBALL_DATA_API_KEY

        super().__init__(
            api_name="Football-Data.org",
            base_url="https://api.football-data.org/v4",
            api_key=api_key,
            cache_ttl=300,  # 5 minutes - sports data changes frequently
            timeout=10,
            max_results=10
        )

        # Football-Data.org uses X-Auth-Token header
        if self.api_key:
            del self.headers["Authorization"]
            self.headers["X-Auth-Token"] = self.api_key

        # Competition codes for major leagues (free tier)
        # NOTE: These are official API identifiers, NOT entity matching (OK to keep)
        self.competitions = {
            # Top 5 European leagues
            "PL": "Premier League",
            "PD": "La Liga",
            "BL1": "Bundesliga",
            "SA": "Serie A",
            "FL1": "Ligue 1",
            # European competitions
            "CL": "Champions League",
            "EC": "European Championship",
            # Additional competitions
            "WC": "FIFA World Cup",
            "ELC": "EFL Championship",
            "DED": "Eredivisie",
            "PPL": "Primeira Liga",
            "BSA": "Campeonato Brasileiro Série A",
        }
        # NO HARDCODED team_aliases - use NER entities passed from pipeline

    def is_relevant_for_domain(self, domain: str, jurisdiction: str) -> bool:
        """Football-Data covers Sports domain globally."""
        return domain == "Sports"

    def search(
        self,
        query: str,
        domain: str,
        jurisdiction: str,
        entities: Optional[List[Dict[str, str]]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search Football-Data.org for sports statistics.

        Uses dynamic entity extraction from NER - NO HARDCODED LISTS!

        Supports:
        - League standings (e.g., "Premier League standings")
        - Team info (e.g., "Arsenal squad")
        - Match results (e.g., "Arsenal vs Chelsea")

        Args:
            query: Search query (claim text)
            domain: Sports
            jurisdiction: Any
            entities: NER entities [{"text": "Arsenal", "label": "ORG"}, ...]

        Returns:
            List of evidence dictionaries with sports data
        """
        if not self.is_relevant_for_domain(domain, jurisdiction):
            return []

        if not self.api_key:
            logger.warning("Football-Data.org API key not configured, skipping")
            return []

        query_lower = query.lower()
        evidence = []

        try:
            # Detect query type and fetch appropriate data

            # TYPE 1: League standings (most common for fact-checking)
            if any(term in query_lower for term in ["top", "standing", "table", "points", "lead", "ahead", "behind", "position"]):
                evidence.extend(self._get_standings(query_lower, entities))

            # TYPE 2: Team info / squad
            if any(term in query_lower for term in ["squad", "player", "signed", "transferred", "manager", "coach"]):
                evidence.extend(self._get_team_info(query_lower, entities))

            # TYPE 3: Match results
            if any(term in query_lower for term in ["beat", "won", "lost", "draw", "match", "game", "vs", "versus"]):
                evidence.extend(self._get_match_results(query_lower))

            # TYPE 4: Top scorers / goal statistics
            if any(term in query_lower for term in ["scorer", "goals scored", "golden boot", "top goal", "leading scorer", "most goals"]):
                evidence.extend(self._get_top_scorers(query_lower))

            # If no specific type detected, try standings as default (most useful for fact-checking)
            if not evidence:
                evidence.extend(self._get_standings(query_lower, entities))

            logger.info(f"Football-Data.org returned {len(evidence)} evidence items")
            return evidence[:self.max_results]

        except Exception as e:
            logger.error(f"Football-Data.org search failed for '{query}': {e}", exc_info=True)
            return []

    def _extract_org_names(self, entities: Optional[List[Dict[str, str]]]) -> List[str]:
        """
        Extract ORG entity names (clubs/teams) from NER results.

        Uses dynamic NER entities. Also accepts ENTITY labels as fallback
        if they look like organization names (contain club/team indicators).

        Args:
            entities: List of NER entities [{"text": "Arsenal", "label": "ORG"}, ...]

        Returns:
            List of organization/club names to search for
        """
        orgs = []
        entity_fallbacks = []

        # Common sports/org indicators
        org_indicators = (
            "FC", "United", "City", "Rovers", "Athletic", "Club",
            "Dortmund", "Arsenal", "Chelsea", "Munich", "Madrid", "Barcelona",
            "Milan", "Inter", "Juventus", "PSG", "Bayern", "Liverpool",
            "League", "Association", "Federation", "UEFA", "FIFA"
        )

        if entities:
            for ent in entities:
                if not isinstance(ent, dict):
                    continue

                text = ent.get("text", "")
                label = ent.get("label", "")

                if label == "ORG":
                    orgs.append(text)
                elif label == "ENTITY":
                    # Fallback: Check if it looks like an organization
                    if any(ind in text for ind in org_indicators):
                        entity_fallbacks.append(text)

        # Use ORG entities first, fall back to ENTITY if none found
        return orgs if orgs else entity_fallbacks

    def _get_standings(
        self,
        query_lower: str,
        entities: Optional[List[Dict[str, str]]] = None
    ) -> List[Dict[str, Any]]:
        """Get league standings for fact-checking using NER entities."""
        evidence = []

        # Detect which league from query
        competition_code = "PL"  # Default to Premier League
        for code, name in self.competitions.items():
            if name.lower() in query_lower:
                competition_code = code
                break

        # Extract org names from entities for team matching
        org_names = self._extract_org_names(entities)
        org_names_lower = [name.lower() for name in org_names]

        try:
            response = self._make_request(f"/competitions/{competition_code}/standings")

            if not response or "standings" not in response:
                return []

            standings_data = response.get("standings", [])
            competition_name = response.get("competition", {}).get("name", "League")
            season = response.get("season", {})
            current_matchday = season.get("currentMatchday", "Unknown")

            # Find TOTAL standings (not home/away split)
            total_standings = None
            for standing_type in standings_data:
                if standing_type.get("type") == "TOTAL":
                    total_standings = standing_type.get("table", [])
                    break

            if not total_standings:
                return []

            # Build evidence from top positions
            top_teams = total_standings[:6]  # Top 6 teams

            # Create main standings evidence
            standings_text = f"Current {competition_name} standings (Matchday {current_matchday}):\n"
            for team in top_teams:
                pos = team.get("position")
                name = team.get("team", {}).get("name", "Unknown")
                points = team.get("points")
                played = team.get("playedGames")
                won = team.get("won")
                drawn = team.get("draw")
                lost = team.get("lost")
                gd = team.get("goalDifference", 0)
                gd_str = f"+{gd}" if gd > 0 else str(gd)

                standings_text += f"{pos}. {name} - {points} pts (P:{played} W:{won} D:{drawn} L:{lost} GD:{gd_str})\n"

            # Calculate point gaps
            if len(top_teams) >= 2:
                leader = top_teams[0]
                second = top_teams[1]
                gap = leader.get("points", 0) - second.get("points", 0)
                standings_text += f"\n{leader.get('team', {}).get('name', 'Leader')} leads by {gap} points over {second.get('team', {}).get('name', 'Second')}."

            evidence.append(self._create_evidence_dict(
                title=f"{competition_name} Standings - Matchday {current_matchday}",
                snippet=standings_text.strip(),
                url=f"https://www.football-data.org/competition/{competition_code}",
                source_date=datetime.utcnow(),
                metadata={
                    "api_source": "Football-Data.org",
                    "competition": competition_code,
                    "matchday": current_matchday,
                    "data_type": "standings"
                }
            ))

            # Add individual team evidence for teams mentioned via NER entities
            for team in total_standings[:20]:  # Check more teams
                team_name = team.get("team", {}).get("name", "")
                team_name_lower = team_name.lower()

                # Check if this team matches any ORG entity from NER
                team_mentioned = False
                for org_name in org_names_lower:
                    # Fuzzy match - check if entity name is contained in team name or vice versa
                    if org_name in team_name_lower or team_name_lower in org_name:
                        team_mentioned = True
                        break
                    # Also check partial match (e.g., "Arsenal" matches "Arsenal FC")
                    for word in org_name.split():
                        if len(word) > 3 and word in team_name_lower:
                            team_mentioned = True
                            break

                if team_mentioned:
                    pos = team.get("position")
                    points = team.get("points")
                    played = team.get("playedGames")

                    evidence.append(self._create_evidence_dict(
                        title=f"{team_name} - {competition_name} Position",
                        snippet=f"{team_name} is currently {pos}{'st' if pos == 1 else 'nd' if pos == 2 else 'rd' if pos == 3 else 'th'} in the {competition_name} with {points} points from {played} matches.",
                        url=f"https://www.football-data.org/team/{team.get('team', {}).get('id')}",
                        source_date=datetime.utcnow(),
                        metadata={
                            "api_source": "Football-Data.org",
                            "team_id": team.get("team", {}).get("id"),
                            "position": pos,
                            "points": points,
                            "data_type": "team_standing"
                        }
                    ))

            return evidence

        except Exception as e:
            logger.error(f"Football-Data standings fetch failed: {e}")
            return []

    def _get_team_info(
        self,
        query_lower: str,
        entities: Optional[List[Dict[str, str]]] = None
    ) -> List[Dict[str, Any]]:
        """Get team/squad information using NER entities - NO HARDCODED LISTS!"""
        evidence = []

        # Extract org names from NER entities
        org_names = self._extract_org_names(entities)
        if not org_names:
            logger.debug("Football-Data: No ORG entities found for team info search")
            return []

        try:
            # Get all teams from API
            teams_response = self._make_request("/teams", params={"limit": 500})

            if not teams_response or "teams" not in teams_response:
                return []

            all_teams = teams_response.get("teams", [])

            # Find matching teams for each org entity
            for org_name in org_names:
                org_lower = org_name.lower()

                # Find best matching team
                team_id = None
                team_name_match = None

                for team in all_teams:
                    team_name = team.get("name", "")
                    team_lower = team_name.lower()

                    # Fuzzy match - check if entity matches team name
                    if org_lower in team_lower or team_lower in org_lower:
                        team_id = team.get("id")
                        team_name_match = team_name
                        break
                    # Partial match for common variations
                    for word in org_lower.split():
                        if len(word) > 3 and word in team_lower:
                            team_id = team.get("id")
                            team_name_match = team_name
                            break
                    if team_id:
                        break

                if not team_id:
                    continue

                # Get team details
                team_response = self._make_request(f"/teams/{team_id}")

                if not team_response:
                    continue

                team_info = team_response
                squad = team_info.get("squad", [])
                coach = team_info.get("coach", {})

                # Build squad evidence
                squad_text = f"{team_info.get('name')} Squad:\n"
                squad_text += f"Manager: {coach.get('name', 'Unknown')}\n\n"

                # Group by position
                positions = {"Goalkeeper": [], "Defence": [], "Midfield": [], "Offence": []}
                for player in squad:
                    pos = player.get("position", "Unknown")
                    if pos in positions:
                        positions[pos].append(player.get("name"))

                for pos, players in positions.items():
                    if players:
                        squad_text += f"{pos}: {', '.join(players[:5])}\n"

                evidence.append(self._create_evidence_dict(
                    title=f"{team_info.get('name')} Squad Information",
                    snippet=squad_text.strip(),
                    url=team_info.get("website", f"https://www.football-data.org/team/{team_id}"),
                    source_date=datetime.utcnow(),
                    metadata={
                        "api_source": "Football-Data.org",
                        "team_id": team_id,
                        "squad_size": len(squad),
                        "data_type": "squad"
                    }
                ))

            return evidence

        except Exception as e:
            logger.error(f"Football-Data team info fetch failed: {e}")
            return []

    def _get_match_results(self, query_lower: str) -> List[Dict[str, Any]]:
        """Get recent match results for detected competition."""
        evidence = []

        # Detect which competition from query (same logic as standings)
        competition_code = "PL"  # Default to Premier League
        for code, name in self.competitions.items():
            if name.lower() in query_lower:
                competition_code = code
                break

        try:
            response = self._make_request(f"/competitions/{competition_code}/matches", params={
                "status": "FINISHED",
                "limit": 10
            })

            if not response or "matches" not in response:
                return []

            matches = response.get("matches", [])
            competition_name = self.competitions.get(competition_code, "League")

            for match in matches[:5]:
                home = match.get("homeTeam", {}).get("name", "Home")
                away = match.get("awayTeam", {}).get("name", "Away")
                score = match.get("score", {}).get("fullTime", {})
                home_goals = score.get("home", 0)
                away_goals = score.get("away", 0)
                match_date = match.get("utcDate", "")

                result_text = f"{home} {home_goals} - {away_goals} {away}"

                evidence.append(self._create_evidence_dict(
                    title=f"{competition_name} Result: {home} vs {away}",
                    snippet=result_text,
                    url=f"https://www.football-data.org/match/{match.get('id')}",
                    source_date=datetime.fromisoformat(match_date.replace("Z", "+00:00")) if match_date else None,
                    metadata={
                        "api_source": "Football-Data.org",
                        "competition": competition_code,
                        "match_id": match.get("id"),
                        "data_type": "match_result"
                    }
                ))

            return evidence

        except Exception as e:
            logger.error(f"Football-Data match results fetch failed: {e}")
            return []

    def _get_top_scorers(self, query_lower: str) -> List[Dict[str, Any]]:
        """Get top scorers for a competition."""
        evidence = []

        # Detect which competition from query
        competition_code = "PL"  # Default to Premier League
        for code, name in self.competitions.items():
            if name.lower() in query_lower:
                competition_code = code
                break

        try:
            response = self._make_request(f"/competitions/{competition_code}/scorers", params={
                "limit": 10
            })

            if not response or "scorers" not in response:
                logger.warning(f"Top scorers not available for {competition_code}")
                return []

            scorers = response.get("scorers", [])
            competition_name = response.get("competition", {}).get("name", self.competitions.get(competition_code, "League"))
            season = response.get("season", {})

            # Build top scorers summary
            scorers_text = f"Top Scorers - {competition_name} ({season.get('startDate', '')[:4]}/{season.get('endDate', '')[:4]} season):\n"

            for i, scorer in enumerate(scorers[:10], 1):
                player = scorer.get("player", {})
                team = scorer.get("team", {})
                goals = scorer.get("goals", 0)
                assists = scorer.get("assists", 0)
                played = scorer.get("playedMatches", 0)

                player_name = player.get("name", "Unknown")
                team_name = team.get("name", "Unknown")

                scorers_text += f"{i}. {player_name} ({team_name}) - {goals} goals"
                if assists:
                    scorers_text += f", {assists} assists"
                scorers_text += f" in {played} matches\n"

            evidence.append(self._create_evidence_dict(
                title=f"{competition_name} Top Scorers",
                snippet=scorers_text.strip(),
                url=f"https://www.football-data.org/competition/{competition_code}",
                source_date=datetime.utcnow(),
                metadata={
                    "api_source": "Football-Data.org",
                    "competition": competition_code,
                    "data_type": "top_scorers",
                    "season": f"{season.get('startDate', '')[:4]}/{season.get('endDate', '')[:4]}"
                }
            ))

            # Also add individual scorer evidence for players mentioned in query
            for scorer in scorers[:10]:
                player = scorer.get("player", {})
                player_name = player.get("name", "").lower()

                # Check if this player is mentioned in the query
                if any(word in player_name for word in query_lower.split() if len(word) > 3):
                    team = scorer.get("team", {})
                    goals = scorer.get("goals", 0)
                    assists = scorer.get("assists", 0)
                    played = scorer.get("playedMatches", 0)

                    evidence.append(self._create_evidence_dict(
                        title=f"{player.get('name')} - {competition_name} Stats",
                        snippet=f"{player.get('name')} ({team.get('name')}) has scored {goals} goals and provided {assists or 0} assists in {played} matches this season.",
                        url=f"https://www.football-data.org/player/{player.get('id')}",
                        source_date=datetime.utcnow(),
                        metadata={
                            "api_source": "Football-Data.org",
                            "player_id": player.get("id"),
                            "goals": goals,
                            "assists": assists,
                            "data_type": "player_stats"
                        }
                    ))

            return evidence

        except Exception as e:
            logger.error(f"Football-Data top scorers fetch failed: {e}")
            return []

    def _transform_response(self, raw_response: Any) -> List[Dict[str, Any]]:
        """Transform Football-Data.org API response to standardized evidence format."""
        # This is handled by specific methods above
        return []


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
            max_results=5
        )

    def is_relevant_for_domain(self, domain: str, jurisdiction: str) -> bool:
        """WeatherAPI covers Weather globally."""
        return domain in ["Weather", "Climate"]

    def search(self, query: str, domain: str, jurisdiction: str, entities: Optional[List[Dict[str, str]]] = None) -> List[Dict[str, Any]]:
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
                logger.warning(f"WeatherAPI: Could not determine location for query '{query}'")
                return []

            # Determine what type of weather data to fetch
            if any(term in query_lower for term in ["forecast", "tomorrow", "next week", "will it"]):
                evidence.extend(self._get_forecast(location, query))
            elif any(term in query_lower for term in ["yesterday", "last week", "was it", "historical"]):
                evidence.extend(self._get_historical(location, query))
            else:
                # Default: get current conditions
                evidence.extend(self._get_current_weather(location, query))

            return evidence

        except Exception as e:
            logger.error(f"WeatherAPI search failed for '{query}': {e}")
            return []

    def _extract_location(self, query: str, entities: Optional[List[Dict[str, str]]] = None) -> Optional[str]:
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
            import re
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

            evidence.append({
                "title": f"3-Day Weather Forecast for {location_name}",
                "url": f"https://www.weatherapi.com/weather/q/{quote(location)}",
                "snippet": "\n".join(forecast_lines),
                "source": "WeatherAPI.com",
                "date": datetime.now().strftime("%Y-%m-%d"),
                "credibility_score": 0.85,
                "metadata": {
                    "api_source": "WeatherAPI",
                    "data_type": "weather_forecast",
                    "location": location_name,
                    "forecast_days": len(forecast_days)
                }
            })

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

            evidence.append({
                "title": f"Current Weather in {location_name}",
                "url": f"https://www.weatherapi.com/weather/q/{quote(location)}",
                "snippet": snippet,
                "source": "WeatherAPI.com",
                "date": datetime.now().strftime("%Y-%m-%d"),
                "credibility_score": 0.85,
                "metadata": {
                    "api_source": "WeatherAPI",
                    "data_type": "current_weather",
                    "location": location_name,
                    "temperature_c": temp,
                    "condition": condition
                }
            })

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
            from datetime import timedelta

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

            evidence.append({
                "title": f"Historical Weather for {location_name} ({yesterday})",
                "url": f"https://www.weatherapi.com/weather/q/{quote(location)}",
                "snippet": snippet,
                "source": "WeatherAPI.com",
                "date": yesterday,
                "credibility_score": 0.85,
                "metadata": {
                    "api_source": "WeatherAPI",
                    "data_type": "historical_weather",
                    "location": location_name,
                    "date": yesterday
                }
            })

            return evidence

        except Exception as e:
            logger.error(f"WeatherAPI historical fetch failed: {e}")
            return []

    def _transform_response(self, raw_response: Any) -> List[Dict[str, Any]]:
        """Transform WeatherAPI response to standardized evidence format."""
        # Handled by specific methods above
        return []


# ========== GBIF ADAPTER (Global Biodiversity Information Facility) ==========

class GBIFAdapter(GovernmentAPIClient):
    """
    GBIF (Global Biodiversity Information Facility) API Adapter.

    Covers: Animals (species occurrence, taxonomy, biodiversity)
    Jurisdiction: Global
    Free tier: No API key required, rate limit ~10 requests/second
    API key: Not required

    Features:
    - Species occurrence records (observations, specimens)
    - Species taxonomy and classification
    - Biodiversity data from museums, research institutions worldwide
    """

    def __init__(self):
        super().__init__(
            api_name="GBIF",
            base_url="https://api.gbif.org/v1",
            api_key=None,  # No API key required
            cache_ttl=86400 * 7,  # 7 days (species data is stable)
            timeout=15,
            max_results=10
        )

    def is_relevant_for_domain(self, domain: str, jurisdiction: str) -> bool:
        """GBIF covers Animals domain globally."""
        return domain == "Animals"

    def search(self, query: str, domain: str, jurisdiction: str, entities: Optional[List[Dict[str, str]]] = None) -> List[Dict[str, Any]]:
        """
        Search GBIF for species and biodiversity data.

        Args:
            query: Search query (e.g., "African elephant population", "red panda habitat")
            domain: Animals
            jurisdiction: Any (global coverage)
            entities: Optional NER entities

        Returns:
            List of evidence dictionaries
        """
        if not self.is_relevant_for_domain(domain, jurisdiction):
            return []

        query = self._sanitize_query(query)
        evidence = []

        try:
            # Search for species matching the query
            species_evidence = self._search_species(query)
            evidence.extend(species_evidence)

            # Search for occurrence data if we have a species name
            if species_evidence:
                species_key = species_evidence[0].get("metadata", {}).get("species_key")
                if species_key:
                    occurrence_evidence = self._get_occurrence_data(species_key)
                    evidence.extend(occurrence_evidence)

            return evidence[:self.max_results]

        except Exception as e:
            logger.error(f"GBIF search failed for '{query}': {e}")
            return []

    def _search_species(self, query: str) -> List[Dict[str, Any]]:
        """Search for species by name."""
        evidence = []

        try:
            import httpx
            from urllib.parse import quote

            # Search species endpoint
            url = f"{self.base_url}/species/search?q={quote(query)}&limit=5"

            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(url)
                response.raise_for_status()
                data = response.json()

            if not data or "results" not in data:
                return []

            for species in data.get("results", [])[:3]:
                scientific_name = species.get("scientificName", "Unknown species")
                common_name = species.get("vernacularName", "")
                kingdom = species.get("kingdom", "")
                phylum = species.get("phylum", "")
                class_name = species.get("class", "")
                order = species.get("order", "")
                family = species.get("family", "")
                species_key = species.get("key")
                status = species.get("taxonomicStatus", "")

                # Build taxonomy string
                taxonomy_parts = [p for p in [kingdom, phylum, class_name, order, family] if p]
                taxonomy = " > ".join(taxonomy_parts) if taxonomy_parts else "Unknown taxonomy"

                title = common_name if common_name else scientific_name
                if common_name and scientific_name:
                    title = f"{common_name} ({scientific_name})"

                snippet = f"Scientific classification: {taxonomy}. "
                if status:
                    snippet += f"Taxonomic status: {status}. "
                snippet += f"Data from GBIF - Global Biodiversity Information Facility."

                evidence.append(self._create_evidence_dict(
                    title=f"Species: {title}",
                    snippet=snippet,
                    url=f"https://www.gbif.org/species/{species_key}" if species_key else "https://www.gbif.org",
                    source_date=None,
                    metadata={
                        "api_source": "GBIF",
                        "data_type": "species_taxonomy",
                        "species_key": species_key,
                        "scientific_name": scientific_name,
                        "kingdom": kingdom,
                        "family": family
                    }
                ))

            return evidence

        except Exception as e:
            logger.warning(f"GBIF species search failed: {e}")
            return []

    def _get_occurrence_data(self, species_key: int) -> List[Dict[str, Any]]:
        """Get occurrence/observation data for a species."""
        evidence = []

        try:
            import httpx

            # Get occurrence count and country distribution
            url = f"{self.base_url}/occurrence/search?speciesKey={species_key}&limit=0&facet=country&facetLimit=10"

            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(url)
                response.raise_for_status()
                data = response.json()

            count = data.get("count", 0)
            facets = data.get("facets", [])

            if count == 0:
                return []

            # Parse country distribution
            country_counts = []
            for facet in facets:
                if facet.get("field") == "COUNTRY":
                    for item in facet.get("counts", [])[:5]:
                        country_counts.append(f"{item.get('name', 'Unknown')}: {item.get('count', 0):,}")

            snippet = f"Total occurrence records: {count:,}. "
            if country_counts:
                snippet += f"Top countries: {', '.join(country_counts)}."

            evidence.append(self._create_evidence_dict(
                title=f"GBIF Occurrence Data ({count:,} records)",
                snippet=snippet,
                url=f"https://www.gbif.org/species/{species_key}",
                source_date=None,
                metadata={
                    "api_source": "GBIF",
                    "data_type": "occurrence_data",
                    "species_key": species_key,
                    "total_occurrences": count
                }
            ))

            return evidence

        except Exception as e:
            logger.warning(f"GBIF occurrence search failed: {e}")
            return []

    def _transform_response(self, raw_response: Any) -> List[Dict[str, Any]]:
        """Transform GBIF API response to standardized evidence format."""
        # Handled by specific methods above
        return []


class WikipediaAdapter(GovernmentAPIClient):
    """
    Wikipedia REST API Adapter.

    Uses the MediaWiki REST API for reliable, structured data from Wikipedia.
    Excellent for History, Politics, Entertainment, and General knowledge claims.
    """

    def __init__(self, max_results: int = 5):
        super().__init__(
            api_name="Wikipedia",
            base_url="https://en.wikipedia.org/api/rest_v1",
            api_key=None,  # No API key required
            timeout=15,
            max_results=max_results
        )
        # Required: Identify our application per Wikipedia API etiquette
        self.headers["User-Agent"] = "Tru8FactChecker/1.0 (https://tru8.com; contact@tru8.com)"
        self.search_base = "https://en.wikipedia.org/w/api.php"

    def is_relevant_for_domain(self, domain: str, jurisdiction: str) -> bool:
        """Wikipedia covers encyclopedic content across most domains."""
        return domain in [
            "History", "Politics", "Entertainment", "General",
            "Sports", "Science", "Animals", "Climate", "Health"
        ]

    def search(self, query: str, domain: str, jurisdiction: str, entities: Optional[List[Dict[str, str]]] = None) -> List[Dict[str, Any]]:
        """
        Search Wikipedia for relevant articles.

        Strategy:
        1. Use MediaWiki search API to find relevant articles
        2. Fetch page summaries via REST API
        3. Transform to evidence format

        Args:
            query: Search query
            domain: History, Politics, Entertainment, or General
            jurisdiction: Any (global encyclopedia)
            entities: Optional named entities from NER

        Returns:
            List of evidence dictionaries
        """
        if not self.is_relevant_for_domain(domain, jurisdiction):
            return []

        query = self._sanitize_query(query)
        evidence = []

        try:
            # Step 1: Search for relevant articles using MediaWiki API
            # Note: MediaWiki API uses different base URL, so we make direct request
            search_params = {
                "action": "query",
                "list": "search",
                "srsearch": query,
                "srlimit": self.max_results,
                "srprop": "snippet|timestamp|titlesnippet",
                "format": "json",
                "origin": "*"
            }

            # Direct request to MediaWiki API (different from REST API base_url)
            import httpx
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(self.search_base, headers=self.headers, params=search_params)
                response.raise_for_status()
                search_response = response.json()

            if not search_response or "query" not in search_response:
                logger.warning(f"Wikipedia search returned no results for: {query[:50]}...")
                return []

            search_results = search_response.get("query", {}).get("search", [])

            # Step 2: Fetch summaries for each result via REST API
            for result in search_results[:self.max_results]:
                title = result.get("title", "")
                if not title:
                    continue

                # Get page summary via REST API
                try:
                    # URL-encode the title for the REST API
                    encoded_title = title.replace(" ", "_")
                    summary_response = self._make_request(f"/page/summary/{encoded_title}")

                    if summary_response and "extract" in summary_response:
                        # Extract publication date if available
                        pub_date = None
                        if "timestamp" in summary_response:
                            try:
                                pub_date = datetime.fromisoformat(summary_response["timestamp"].replace("Z", "+00:00"))
                            except Exception:
                                pass

                        # Build URL
                        url = summary_response.get("content_urls", {}).get("desktop", {}).get("page")
                        if not url:
                            url = f"https://en.wikipedia.org/wiki/{encoded_title}"

                        evidence.append({
                            "source_name": "Wikipedia",
                            "source_type": "encyclopedia",
                            "title": summary_response.get("title", title),
                            "content": summary_response.get("extract", ""),
                            "url": url,
                            "publication_date": pub_date.isoformat() if pub_date else None,
                            "credibility_score": 0.75,  # Wikipedia is generally reliable but editable
                            "relevance_score": 0.8,
                            "metadata": {
                                "description": summary_response.get("description", ""),
                                "page_id": summary_response.get("pageid"),
                                "last_modified": summary_response.get("timestamp"),
                                "domain": domain
                            }
                        })
                except Exception as e:
                    logger.warning(f"Failed to fetch Wikipedia summary for '{title}': {e}")
                    continue

            logger.info(f"Wikipedia returned {len(evidence)} results for query: {query[:50]}...")

        except Exception as e:
            logger.error(f"Wikipedia search failed: {e}")

        return evidence

    def _transform_response(self, raw_response: Any) -> List[Dict[str, Any]]:
        """Transform Wikipedia API response to standardized evidence format."""
        # Handled by search method above
        return []


# ========== LIBRARY OF CONGRESS ADAPTER (P0) ==========

class LibraryOfCongressAdapter(GovernmentAPIClient):
    """
    Library of Congress API adapter for historical documents and newspapers.

    Provides access to:
    - General LOC collections search
    - Chronicling America (historical newspapers 1789-1963)

    No API key required. Rate limit: polite usage (~10 req/sec).
    """

    def __init__(self, max_results: int = 10):
        super().__init__(
            api_name="Library of Congress",
            base_url="https://www.loc.gov",
            api_key=None,
            cache_ttl=86400 * 7,  # 7 days (historical content is stable)
            timeout=15,
            max_results=max_results
        )
        self.headers["User-Agent"] = "Tru8FactChecker/1.0 (https://tru8.com; contact@tru8.com)"

    def is_relevant_for_domain(self, domain: str, jurisdiction: str) -> bool:
        """Library of Congress covers History, Politics, and General (US focus, global relevance)."""
        return domain in ["History", "Politics", "General"]

    def search(self, query: str, domain: str, jurisdiction: str, entities=None) -> List[Dict[str, Any]]:
        """
        Search Library of Congress collections and Chronicling America newspapers.

        Returns standardized evidence dictionaries.
        """
        evidence = []

        try:
            # Search 1: General LOC collections
            loc_results = self._search_loc_collections(query)
            evidence.extend(loc_results)

            # Search 2: Chronicling America historical newspapers
            newspaper_results = self._search_chronicling_america(query)
            evidence.extend(newspaper_results)

            logger.info(f"Library of Congress returned {len(evidence)} results for query: {query[:50]}...")

        except Exception as e:
            logger.error(f"Library of Congress search failed: {e}")

        return evidence[:self.max_results]

    def _search_loc_collections(self, query: str) -> List[Dict[str, Any]]:
        """Search general LOC collections."""
        evidence = []

        try:
            params = {
                "q": query,
                "fo": "json",
                "c": 5,  # Limit results
                "fa": "original-format:book|original-format:manuscript|original-format:newspaper"
            }

            response = self._make_request("/search/", params=params)

            if not response or "results" not in response:
                return []

            for result in response.get("results", [])[:5]:
                # Skip if no title
                title = result.get("title")
                if not title:
                    continue

                # Extract date
                pub_date = None
                date_str = result.get("date")
                if date_str:
                    try:
                        # LOC dates can be in various formats
                        if len(date_str) == 4:  # Year only
                            pub_date = f"{date_str}-01-01"
                        elif len(date_str) >= 10:
                            pub_date = date_str[:10]
                    except Exception:
                        pass

                # Build URL
                url = result.get("url") or result.get("id")
                if url and not url.startswith("http"):
                    url = f"https://www.loc.gov{url}"

                # Extract description/content
                description = result.get("description", [])
                if isinstance(description, list):
                    description = " ".join(description[:2])

                evidence.append({
                    "source_name": "Library of Congress",
                    "source_type": "archive",
                    "title": title if isinstance(title, str) else title[0] if title else "Unknown",
                    "content": description or result.get("extract", ""),
                    "url": url,
                    "publication_date": pub_date,
                    "credibility_score": 0.95,  # Primary source archive
                    "relevance_score": 0.85,
                    "metadata": {
                        "collection": result.get("partof", []),
                        "format": result.get("original_format", []),
                        "contributor": result.get("contributor", []),
                        "subjects": result.get("subject", [])[:5]
                    }
                })

        except Exception as e:
            logger.warning(f"LOC collections search failed: {e}")

        return evidence

    def _search_chronicling_america(self, query: str) -> List[Dict[str, Any]]:
        """Search Chronicling America historical newspapers (1789-1963) via LOC search API."""
        evidence = []

        try:
            # Use LOC search API with Chronicling America filter
            # (old chroniclingamerica.loc.gov API is deprecated)
            params = {
                "q": query,
                "fo": "json",
                "fa": "partof:chronicling america",
                "c": 5
            }

            response = self._make_request("/search/", params=params)

            if not response or "results" not in response:
                return []

            for result in response.get("results", [])[:5]:
                title = result.get("title", "Historical Newspaper")

                # Handle title as list or string
                if isinstance(title, list):
                    title = title[0] if title else "Historical Newspaper"

                # Parse date
                pub_date = None
                date_str = result.get("date")
                if date_str:
                    try:
                        if isinstance(date_str, list):
                            date_str = date_str[0] if date_str else None
                        if date_str:
                            if len(date_str) == 4:  # Year only
                                pub_date = f"{date_str}-01-01"
                            elif len(date_str) >= 10:
                                pub_date = date_str[:10]
                    except Exception:
                        pass

                # Build URL
                url = result.get("url") or result.get("id", "")
                if url and not url.startswith("http"):
                    url = f"https://www.loc.gov{url}"

                # Extract location info
                location = result.get("location", [])
                if isinstance(location, list):
                    location = location[0] if location else ""

                evidence.append({
                    "source_name": "Chronicling America",
                    "source_type": "newspaper",
                    "title": title,
                    "content": result.get("description", [""])[0] if isinstance(result.get("description"), list) else result.get("description", ""),
                    "url": url,
                    "publication_date": pub_date,
                    "credibility_score": 0.9,  # Historical primary source
                    "relevance_score": 0.8,
                    "metadata": {
                        "location": location,
                        "format": result.get("original_format", []),
                        "subjects": result.get("subject", [])[:5]
                    }
                })

        except Exception as e:
            logger.warning(f"Chronicling America search failed: {e}")

        return evidence

    def _transform_response(self, raw_response: Any) -> List[Dict[str, Any]]:
        """Transform handled by search methods."""
        return []


# ========== SEMANTIC SCHOLAR ADAPTER (P1) ==========

class SemanticScholarAdapter(GovernmentAPIClient):
    """
    Semantic Scholar API adapter for academic paper search.

    Provides access to 200M+ academic papers with citation data.
    No API key required (100 requests/5 minutes).
    """

    def __init__(self, max_results: int = 10):
        super().__init__(
            api_name="Semantic Scholar",
            base_url="https://api.semanticscholar.org/graph/v1",
            api_key=None,
            cache_ttl=86400 * 7,  # 7 days
            timeout=15,
            max_results=max_results
        )
        self.headers["User-Agent"] = "Tru8FactChecker/1.0 (https://tru8.com; contact@tru8.com)"

    def is_relevant_for_domain(self, domain: str, jurisdiction: str) -> bool:
        """Semantic Scholar covers academic research across all knowledge domains."""
        # Academic papers exist for virtually all domains
        return domain in [
            "Science", "Climate", "History", "Health", "General",
            "Politics", "Law", "Demographics", "Animals", "Entertainment"
        ]

    def search(self, query: str, domain: str, jurisdiction: str, entities=None) -> List[Dict[str, Any]]:
        """
        Search Semantic Scholar for academic papers.

        Returns standardized evidence dictionaries.
        """
        evidence = []

        try:
            params = {
                "query": query,
                "limit": self.max_results,
                "fields": "title,abstract,url,year,citationCount,authors,venue,publicationDate"
            }

            response = self._make_request("/paper/search", params=params)

            if not response or "data" not in response:
                logger.warning(f"Semantic Scholar returned no results for: {query[:50]}...")
                return []

            for paper in response.get("data", []):
                if not paper:
                    continue

                title = paper.get("title", "")
                if not title:
                    continue

                # Extract authors
                authors = []
                for author in paper.get("authors", [])[:3]:
                    if author.get("name"):
                        authors.append(author["name"])

                # Parse publication date
                pub_date = paper.get("publicationDate")
                if not pub_date and paper.get("year"):
                    pub_date = f"{paper['year']}-01-01"

                # Calculate credibility based on citations
                citation_count = paper.get("citationCount", 0) or 0
                credibility = min(0.95, 0.75 + (citation_count / 1000) * 0.2)

                evidence.append({
                    "source_name": "Semantic Scholar",
                    "source_type": "academic",
                    "title": title,
                    "content": paper.get("abstract", "") or "",
                    "url": paper.get("url") or f"https://www.semanticscholar.org/paper/{paper.get('paperId', '')}",
                    "publication_date": pub_date,
                    "credibility_score": credibility,
                    "relevance_score": 0.85,
                    "metadata": {
                        "authors": authors,
                        "venue": paper.get("venue", ""),
                        "citation_count": citation_count,
                        "paper_id": paper.get("paperId")
                    }
                })

            logger.info(f"Semantic Scholar returned {len(evidence)} results for query: {query[:50]}...")

        except Exception as e:
            logger.error(f"Semantic Scholar search failed: {e}")

        return evidence

    def _transform_response(self, raw_response: Any) -> List[Dict[str, Any]]:
        """Transform handled by search method."""
        return []


# ========== OPENALEX ADAPTER (P2) ==========

class OpenAlexAdapter(GovernmentAPIClient):
    """
    OpenAlex API adapter for scholarly works.

    Provides access to 250M+ scholarly works from the OpenAlex catalog.
    No API key required (100,000 requests/day with polite pool).
    """

    def __init__(self, max_results: int = 10):
        super().__init__(
            api_name="OpenAlex",
            base_url="https://api.openalex.org",
            api_key=None,
            cache_ttl=86400 * 7,  # 7 days
            timeout=15,
            max_results=max_results
        )
        # OpenAlex requests polite pool identification via email
        self.headers["User-Agent"] = "Tru8FactChecker/1.0 (mailto:contact@tru8.com)"

    def is_relevant_for_domain(self, domain: str, jurisdiction: str) -> bool:
        """OpenAlex covers scholarly works across all knowledge domains."""
        # Scholarly works exist for virtually all domains
        return domain in [
            "Science", "Climate", "History", "Health", "General",
            "Politics", "Law", "Demographics", "Animals", "Entertainment"
        ]

    def search(self, query: str, domain: str, jurisdiction: str, entities=None) -> List[Dict[str, Any]]:
        """
        Search OpenAlex for scholarly works.

        Returns standardized evidence dictionaries.
        """
        evidence = []

        try:
            params = {
                "search": query,
                "per_page": self.max_results,
                "filter": "publication_year:>1900",
                "mailto": "contact@tru8.com"  # Polite pool
            }

            response = self._make_request("/works", params=params)

            if not response or "results" not in response:
                logger.warning(f"OpenAlex returned no results for: {query[:50]}...")
                return []

            for work in response.get("results", []):
                if not work:
                    continue

                title = work.get("title", "")
                if not title:
                    continue

                # Extract authors
                authors = []
                for authorship in work.get("authorships", [])[:3]:
                    author = authorship.get("author", {})
                    if author.get("display_name"):
                        authors.append(author["display_name"])

                # Parse publication date
                pub_date = work.get("publication_date")

                # Calculate credibility based on citations
                citation_count = work.get("cited_by_count", 0) or 0
                credibility = min(0.95, 0.75 + (citation_count / 1000) * 0.2)

                # Get best available URL
                url = work.get("doi")
                if url and not url.startswith("http"):
                    url = f"https://doi.org/{url}"
                if not url:
                    url = work.get("id", "")  # OpenAlex ID URL

                # Reconstruct abstract from inverted index if available
                abstract = ""
                abstract_index = work.get("abstract_inverted_index")
                if abstract_index:
                    try:
                        # OpenAlex uses inverted index for abstract
                        word_positions = []
                        for word, positions in abstract_index.items():
                            for pos in positions:
                                word_positions.append((pos, word))
                        word_positions.sort()
                        abstract = " ".join(word for _, word in word_positions[:100])
                    except Exception:
                        pass

                # Safely extract source name from primary_location
                primary_location = work.get("primary_location") or {}
                source_info = primary_location.get("source") or {}
                source_name = source_info.get("display_name", "") if isinstance(source_info, dict) else ""

                # Safely extract open_access info
                open_access = work.get("open_access") or {}
                is_oa = open_access.get("is_oa", False) if isinstance(open_access, dict) else False

                evidence.append({
                    "source_name": "OpenAlex",
                    "source_type": "academic",
                    "title": title,
                    "content": abstract,
                    "url": url,
                    "publication_date": pub_date,
                    "credibility_score": credibility,
                    "relevance_score": 0.85,
                    "metadata": {
                        "authors": authors,
                        "citation_count": citation_count,
                        "type": work.get("type", ""),
                        "open_access": is_oa,
                        "source": source_name
                    }
                })

            logger.info(f"OpenAlex returned {len(evidence)} results for query: {query[:50]}...")

        except Exception as e:
            logger.error(f"OpenAlex search failed: {e}")

        return evidence

    def _transform_response(self, raw_response: Any) -> List[Dict[str, Any]]:
        """Transform handled by search method."""
        return []


# ========== INTERNET ARCHIVE ADAPTER (P3) ==========

class InternetArchiveAdapter(GovernmentAPIClient):
    """
    Internet Archive API adapter for historical documents and web archives.

    Provides access to:
    - Archive.org collections (texts, audio, video, images)
    - Wayback Machine historical web snapshots

    No API key required. Rate limit: 15 requests/minute per IP.
    """

    def __init__(self, max_results: int = 10):
        super().__init__(
            api_name="Internet Archive",
            base_url="https://archive.org",
            api_key=None,
            cache_ttl=86400 * 7,  # 7 days
            timeout=20,  # Archive can be slow
            max_results=max_results
        )
        self.headers["User-Agent"] = "Tru8FactChecker/1.0 (https://tru8.com; contact@tru8.com)"

    def is_relevant_for_domain(self, domain: str, jurisdiction: str) -> bool:
        """Internet Archive covers historical documents across many domains."""
        return domain in ["History", "General", "Politics", "Entertainment", "Science"]

    def search(self, query: str, domain: str, jurisdiction: str, entities=None) -> List[Dict[str, Any]]:
        """
        Search Internet Archive collections.

        Returns standardized evidence dictionaries.
        """
        evidence = []

        try:
            import httpx

            # Build search query for texts and documents
            params = {
                "q": query,
                "output": "json",
                "rows": self.max_results,
                "fl[]": ["identifier", "title", "description", "date", "creator", "mediatype", "collection"],
                "sort[]": "downloads desc"  # Prioritize popular items
            }

            with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
                response = client.get(
                    f"{self.base_url}/advancedsearch.php",
                    params=params,
                    headers=self.headers
                )
                response.raise_for_status()
                data = response.json()

            if not data or "response" not in data:
                logger.warning(f"Internet Archive returned no results for: {query[:50]}...")
                return []

            docs = data.get("response", {}).get("docs", [])

            for doc in docs:
                if not doc:
                    continue

                title = doc.get("title", "")
                if not title:
                    continue

                # Handle title as list or string
                if isinstance(title, list):
                    title = title[0] if title else ""

                # Parse date
                pub_date = None
                date_str = doc.get("date")
                if date_str:
                    try:
                        if isinstance(date_str, list):
                            date_str = date_str[0]
                        # Various date formats
                        if len(date_str) == 4:  # Year only
                            pub_date = f"{date_str}-01-01"
                        elif len(date_str) >= 10:
                            pub_date = date_str[:10]
                    except Exception:
                        pass

                # Extract description
                description = doc.get("description", "")
                if isinstance(description, list):
                    description = " ".join(description[:2])

                # Build URL
                identifier = doc.get("identifier", "")
                url = f"https://archive.org/details/{identifier}" if identifier else ""

                # Extract creator
                creator = doc.get("creator", [])
                if isinstance(creator, list):
                    creator = creator[:3]
                elif creator:
                    creator = [creator]
                else:
                    creator = []

                # Credibility based on mediatype
                mediatype = doc.get("mediatype", "")
                credibility = 0.85
                if mediatype == "texts":
                    credibility = 0.9
                elif mediatype in ["audio", "video"]:
                    credibility = 0.8

                evidence.append({
                    "source_name": "Internet Archive",
                    "source_type": "archive",
                    "title": title,
                    "content": description[:500] if description else "",
                    "url": url,
                    "publication_date": pub_date,
                    "credibility_score": credibility,
                    "relevance_score": 0.8,
                    "metadata": {
                        "identifier": identifier,
                        "mediatype": mediatype,
                        "creator": creator,
                        "collection": doc.get("collection", [])
                    }
                })

            logger.info(f"Internet Archive returned {len(evidence)} results for query: {query[:50]}...")

        except Exception as e:
            logger.error(f"Internet Archive search failed: {e}")

        return evidence

    def _transform_response(self, raw_response: Any) -> List[Dict[str, Any]]:
        """Transform handled by search method."""
        return []


# ========== ADAPTER INITIALIZATION ==========

def initialize_adapters():
    """
    Initialize all API adapters and register them.

    Call this function at application startup to register all adapters.
    """
    from app.services.government_api_client import get_api_registry
    from app.core.config import settings

    registry = get_api_registry()

    # Register ONS adapter
    registry.register(ONSAdapter())
    logger.info("Registered ONS adapter")

    # Register PubMed adapter
    registry.register(PubMedAdapter())
    logger.info("Registered PubMed adapter")

    # Register Companies House adapter (if API key is configured)
    companies_house_key = os.getenv("COMPANIES_HOUSE_API_KEY")
    if companies_house_key:
        registry.register(CompaniesHouseAdapter())
        logger.info("Registered Companies House adapter")
    else:
        logger.warning("Companies House API key not configured, adapter not registered")

    # Register FRED adapter (Week 2)
    fred_key = os.getenv("FRED_API_KEY")
    if fred_key:
        registry.register(FREDAdapter())
        logger.info("Registered FRED adapter")
    else:
        logger.warning("FRED API key not configured, adapter not registered")

    # Register WHO adapter (Week 2)
    registry.register(WHOAdapter())
    logger.info("Registered WHO adapter")

    # Register NOAA CDO adapter (Global Climate Data)
    if settings.NOAA_API_KEY:
        registry.register(NOAAAdapter())
        logger.info(f"[ADAPTERS] Registered NOAA CDO adapter for Climate (key: {settings.NOAA_API_KEY[:10]}...)")
    else:
        logger.warning("[ADAPTERS] NOAA_API_KEY not configured, NOAA adapter not registered")

    # Register CrossRef adapter (Week 2)
    registry.register(CrossRefAdapter())
    logger.info("Registered CrossRef adapter")

    # Register GOV.UK adapter (Week 2)
    registry.register(GovUKAdapter())
    logger.info("Registered GOV.UK adapter")

    # Register Hansard adapter (Week 2)
    registry.register(HansardAdapter())
    logger.info("Registered Hansard adapter")

    # Register Wikidata adapter (Week 2)
    registry.register(WikidataAdapter())
    logger.info("Registered Wikidata adapter")

    # Register GovInfo adapter (Phase 4/5 integration)
    # Use settings instead of os.getenv() because .env is loaded by pydantic-settings
    if settings.GOVINFO_API_KEY:
        adapter = GovInfoAdapter()
        registry.register(adapter)
        logger.info(f"[ADAPTERS] Registered GovInfo.gov adapter for US legal statutes (key: {settings.GOVINFO_API_KEY[:10]}...)")
        logger.info(f"   Adapter: {adapter.api_name}, relevant for domain=Law, jurisdiction=US")
    else:
        logger.warning("[ADAPTERS] GOVINFO_API_KEY not configured, GovInfo adapter not registered")

    # Register Football-Data.org adapter (Sports Statistics - Real-time)
    # Use settings instead of os.getenv() - .env is loaded by pydantic-settings into settings object
    if settings.FOOTBALL_DATA_API_KEY:
        adapter = FootballDataAdapter()
        registry.register(adapter)
        logger.info(f"[ADAPTERS] Registered Football-Data.org adapter for Sports (key: {settings.FOOTBALL_DATA_API_KEY[:10]}...)")
    else:
        logger.warning("[ADAPTERS] FOOTBALL_DATA_API_KEY not configured, Football-Data adapter not registered")

    # Register Transfermarkt adapter (Sports Statistics - Historical)
    # No API key required - uses free community-hosted API
    registry.register(TransfermarktAdapter())
    logger.info("[ADAPTERS] Registered Transfermarkt adapter for historical sports data (transfers, achievements, career stats)")

    # Register Alpha Vantage adapter (Stocks, Forex, Crypto, News Sentiment)
    if settings.ALPHA_VANTAGE_API_KEY:
        registry.register(AlphaVantageAdapter())
        logger.info(f"[ADAPTERS] Registered Alpha Vantage adapter for Finance (key: {settings.ALPHA_VANTAGE_API_KEY[:10]}...)")
    else:
        logger.warning("[ADAPTERS] ALPHA_VANTAGE_API_KEY not configured, Alpha Vantage adapter not registered")

    # Register Marketaux adapter (Financial News)
    if settings.MARKETAUX_API_KEY:
        registry.register(MarketauxAdapter())
        logger.info(f"[ADAPTERS] Registered Marketaux adapter for Financial News (key: {settings.MARKETAUX_API_KEY[:10]}...)")
    else:
        logger.warning("[ADAPTERS] MARKETAUX_API_KEY not configured, Marketaux adapter not registered")

    # Register FRED adapter (Federal Reserve Economic Data)
    if settings.FRED_API_KEY:
        registry.register(FREDAdapter())
        logger.info(f"[ADAPTERS] Registered FRED adapter for Economics (key: {settings.FRED_API_KEY[:10]}...)")
    else:
        logger.warning("[ADAPTERS] FRED_API_KEY not configured, FRED adapter not registered")

    # Register WeatherAPI adapter (Weather - 1M calls/month free, commercial OK)
    if settings.WEATHER_API_KEY:
        registry.register(WeatherAPIAdapter())
        logger.info(f"[ADAPTERS] Registered WeatherAPI adapter for Weather (key: {settings.WEATHER_API_KEY[:10]}...)")
    else:
        logger.warning("[ADAPTERS] WEATHER_API_KEY not configured, WeatherAPI adapter not registered")

    # Register GBIF adapter (Biodiversity/Species - No API key required, fully open)
    registry.register(GBIFAdapter())
    logger.info("[ADAPTERS] Registered GBIF adapter for Animals/Biodiversity (no key required)")

    # Register Wikipedia adapter (History, Politics, Entertainment, General - No API key required)
    registry.register(WikipediaAdapter())
    logger.info("[ADAPTERS] Registered Wikipedia adapter for History/Politics/Entertainment/General (no key required)")

    # ===== NEW HIGH-QUALITY FREE ADAPTERS (No API keys required) =====

    # Register Library of Congress adapter (History, Politics, General - Primary sources, newspapers)
    registry.register(LibraryOfCongressAdapter())
    logger.info("[ADAPTERS] Registered Library of Congress adapter for History/Politics/General (no key required)")

    # Register Semantic Scholar adapter (Science, History, Health, General - 200M+ academic papers)
    registry.register(SemanticScholarAdapter())
    logger.info("[ADAPTERS] Registered Semantic Scholar adapter for Science/History/Health/General (no key required)")

    # Register OpenAlex adapter (Science, History, Health, General - 250M+ scholarly works)
    registry.register(OpenAlexAdapter())
    logger.info("[ADAPTERS] Registered OpenAlex adapter for Science/History/Health/General (no key required)")

    # Register Internet Archive adapter (History, General - Historical documents, Wayback Machine)
    registry.register(InternetArchiveAdapter())
    logger.info("[ADAPTERS] Registered Internet Archive adapter for History/General (no key required)")

    logger.info(f"API adapter initialization complete. {len(registry.get_all_adapters())} adapters registered.")
