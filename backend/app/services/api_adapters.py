"""
Government API Adapters
Phase 5: Government API Integration

Concrete implementations of API adapters for:
- ONS Economic Statistics (UK) - Finance, Demographics
- FRED (US) - Finance
- Companies House (UK) - Government
- PubMed (US/Global) - Health, Science
- WHO (Global) - Health
- Met Office (UK) - Climate
- CrossRef (Global) - Science
- GovUK Content (UK) - Government
- Hansard (UK) - Law, Parliament
- Wikidata (Global) - General
- GovInfo.gov (US) - Law, Federal Statutes

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
        """PubMed covers Health and Science globally."""
        return domain in ["Health", "Science"]

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


# ========== MET OFFICE ADAPTER (UK Weather/Climate) ==========

class MetOfficeAdapter(GovernmentAPIClient):
    """
    Met Office DataPoint API Adapter.

    Covers: Climate
    Jurisdiction: UK
    Free tier: 5,000 requests/day
    API key: Required
    """

    def __init__(self):
        api_key = os.getenv("MET_OFFICE_API_KEY")

        super().__init__(
            api_name="Met Office",
            base_url="http://datapoint.metoffice.gov.uk/public/data",
            api_key=api_key,
            cache_ttl=3600,  # 1 hour (weather data changes frequently)
            timeout=10,
            max_results=10
        )

        # Met Office uses API key as query parameter
        if self.api_key:
            del self.headers["Authorization"]

    def is_relevant_for_domain(self, domain: str, jurisdiction: str) -> bool:
        """Met Office covers Climate for UK."""
        return domain == "Climate" and jurisdiction in ["UK", "Global"]

    def search(self, query: str, domain: str, jurisdiction: str, entities: Optional[List[Dict[str, str]]] = None) -> List[Dict[str, Any]]:
        """
        Search Met Office for UK weather/climate data.

        Args:
            query: Search query (e.g., "temperature forecast")
            domain: Climate
            jurisdiction: UK

        Returns:
            List of evidence dictionaries
        """
        if not self.is_relevant_for_domain(domain, jurisdiction):
            return []

        if not self.api_key:
            logger.warning("Met Office API key not configured, skipping")
            return []

        # Met Office API is limited - return general climate info
        # Full implementation would query specific forecasts/observations
        return self._create_placeholder_evidence()

    def _create_placeholder_evidence(self) -> List[Dict[str, Any]]:
        """Create placeholder evidence for Met Office (API has limited search)."""
        evidence = self._create_evidence_dict(
            title="Met Office Weather and Climate Data",
            snippet="UK weather forecasts, observations, and climate data from the Met Office. Visit the site for specific data.",
            url="https://www.metoffice.gov.uk/",
            source_date=datetime.utcnow(),
            metadata={"api_source": "Met Office", "note": "Limited search capability"}
        )
        return [evidence]

    def _transform_response(self, raw_response: Any) -> List[Dict[str, Any]]:
        """Met Office API returns XML - simplified for MVP."""
        return self._create_placeholder_evidence()


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
        """CrossRef covers Science globally."""
        return domain == "Science"

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
        """GOV.UK covers Government for UK."""
        return domain in ["Government", "General"] and jurisdiction in ["UK", "Global"]

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
        """Wikidata covers General globally."""
        return domain == "General"

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
        GovInfo covers Law domain for US jurisdiction.

        Args:
            domain: Domain classification (Law, Finance, Health, etc.)
            jurisdiction: US, UK, EU, Global

        Returns:
            True if this adapter can handle the domain/jurisdiction
        """
        return domain == "Law" and jurisdiction == "US"

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
            from app.utils.claim_classifier import ClaimClassifier
            classifier = ClaimClassifier()
            classification = classifier.classify(query)

            # Only proceed if classified as legal
            if classification.get("claim_type") != "legal":
                logger.info(f"GovInfo: Query not classified as legal, skipping: {query[:50]}")
                return []

            legal_metadata = classification.get("metadata", {})

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

    # Register Met Office adapter (Week 2)
    met_office_key = os.getenv("MET_OFFICE_API_KEY")
    if met_office_key:
        registry.register(MetOfficeAdapter())
        logger.info("Registered Met Office adapter")
    else:
        logger.warning("Met Office API key not configured, adapter not registered")

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

    logger.info(f"API adapter initialization complete. {len(registry.get_all_adapters())} adapters registered.")
