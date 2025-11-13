"""
Government API Adapters
Phase 5: Government API Integration

Concrete implementations of API adapters for:
- ONS Economic Statistics (UK)
- PubMed (US/Global)
- Companies House (UK)

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

    def search(self, query: str, domain: str, jurisdiction: str) -> List[Dict[str, Any]]:
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

    def search(self, query: str, domain: str, jurisdiction: str) -> List[Dict[str, Any]]:
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

    def search(self, query: str, domain: str, jurisdiction: str) -> List[Dict[str, Any]]:
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

    def search(self, query: str, domain: str, jurisdiction: str) -> List[Dict[str, Any]]:
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

    def search(self, query: str, domain: str, jurisdiction: str) -> List[Dict[str, Any]]:
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

    def search(self, query: str, domain: str, jurisdiction: str) -> List[Dict[str, Any]]:
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

    def search(self, query: str, domain: str, jurisdiction: str) -> List[Dict[str, Any]]:
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

    def search(self, query: str, domain: str, jurisdiction: str) -> List[Dict[str, Any]]:
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

    def search(self, query: str, domain: str, jurisdiction: str) -> List[Dict[str, Any]]:
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

    def search(self, query: str, domain: str, jurisdiction: str) -> List[Dict[str, Any]]:
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


# ========== ADAPTER INITIALIZATION ==========

def initialize_adapters():
    """
    Initialize all API adapters and register them.

    Call this function at application startup to register all adapters.
    """
    from app.services.government_api_client import get_api_registry

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

    logger.info(f"API adapter initialization complete. {len(registry.get_all_adapters())} adapters registered.")
