"""
Health API Adapters

Adapters for health and medical data:
- PubMed (NCBI biomedical literature)
- WHO (World Health Organization)
"""

import logging
import os
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Optional
from datetime import datetime

import httpx

from app.core.config import settings
from app.services.government_api_client import GovernmentAPIClient

logger = logging.getLogger(__name__)


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
            max_results=10,
        )

        # PubMed uses API key as query parameter, not header
        if self.api_key:
            del self.headers["Authorization"]

    def is_relevant_for_domain(self, domain: str, jurisdiction: str) -> bool:
        """PubMed covers biomedical and life sciences globally.

        Note: Climate removed (Fix 2) - PubMed is a biomedical database.
        Climate claims should use NOAA CDO, WeatherAPI, and climate-specific APIs.
        """
        return domain in ["Health", "Science", "Animals"]

    def search(
        self,
        query: str,
        domain: str,
        jurisdiction: str,
        entities: Optional[List[Dict[str, str]]] = None,
    ) -> List[Dict[str, Any]]:
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

        targeted_query = self._build_targeted_query(query, entities)

        # Step 1: Search for article IDs
        # A2: tool + email are NCBI politeness params. Without them NCBI silently
        # throttles unidentified callers by returning HTTP 200 with empty body.
        search_params = {
            "db": "pubmed",
            "term": targeted_query,
            "retmax": self.max_results,
            "retmode": "json",
            "sort": "relevance",
            "tool": "tru8",
            "email": settings.NCBI_CONTACT_EMAIL,
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
            # A2: efetch returns XML, not JSON. Use adapter-local _fetch_xml
            # helper to avoid the base client's response.json() call which
            # crashes on XML payloads. tool + email = NCBI politeness params.
            fetch_params = {
                "db": "pubmed",
                "id": ",".join(id_list),
                "retmode": "xml",
                "tool": "tru8",
                "email": settings.NCBI_CONTACT_EMAIL,
            }

            if self.api_key:
                fetch_params["api_key"] = self.api_key

            fetch_response = self._fetch_xml("efetch.fcgi", fetch_params)

            if not fetch_response:
                logger.warning(f"PubMed fetch failed for IDs: {id_list}")
                return []

            return self._transform_response({"ids": id_list, "xml": fetch_response})

        except Exception as e:
            logger.error(f"PubMed search failed for '{query}': {e}")
            return []

    def _fetch_xml(self, endpoint: str, params: Dict[str, Any]) -> Optional[str]:
        """Fetch raw XML from NCBI.

        A2: PubMed's efetch endpoint returns XML, not JSON. The base client's
        _make_request → _make_request_with_retries always calls response.json()
        which crashes on XML payloads (seen in Sentry as PYTHON-FASTAPI-1F/1G/1H/
        1J/1P, "Expecting value: line 1 column 1 (char 0)"). Adapter-local helper
        avoids changing the base client's shape (10+ adapters depend on JSON).

        Logs at warning level because failure is recoverable (caller returns []).
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        try:
            with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
                response = client.get(url, headers=self.headers, params=params)
                response.raise_for_status()
                return response.text
        except Exception as e:
            logger.warning(f"PubMed XML fetch failed ({endpoint}): {e}")
            return None

    def _transform_response(self, raw_response: Any) -> List[Dict[str, Any]]:
        """
        Transform PubMed XML response to standardized evidence format.

        Parses XML to extract title, abstract, authors, and publication date.
        """
        evidence_list = []
        xml_data = raw_response.get("xml", "")

        if not xml_data:
            logger.warning("PubMed returned empty XML response")
            return []

        try:
            # Parse XML response
            root = ET.fromstring(xml_data)

            # Iterate through each article
            for article in root.findall(".//PubmedArticle"):
                try:
                    # Extract PMID
                    pmid_elem = article.find(".//PMID")
                    pmid = pmid_elem.text if pmid_elem is not None else "unknown"

                    # Extract title
                    title_elem = article.find(".//ArticleTitle")
                    title = (
                        title_elem.text
                        if title_elem is not None
                        else f"PubMed Article {pmid}"
                    )

                    # Extract abstract (may have multiple AbstractText elements)
                    abstract_parts = []
                    for abstract_text in article.findall(".//AbstractText"):
                        if abstract_text.text:
                            abstract_parts.append(abstract_text.text)

                    abstract = (
                        " ".join(abstract_parts)
                        if abstract_parts
                        else "No abstract available."
                    )
                    # Use longer snippet for peer-reviewed research (captures methodology + findings)
                    snippet = (
                        abstract[:600] + "..." if len(abstract) > 600 else abstract
                    )

                    # Extract publication date
                    pub_date_elem = article.find(".//PubDate")
                    source_date = None
                    if pub_date_elem is not None:
                        year_elem = pub_date_elem.find("Year")
                        month_elem = pub_date_elem.find("Month")

                        if year_elem is not None:
                            try:
                                year = int(year_elem.text)
                                month = 1

                                # Try to parse month
                                if month_elem is not None:
                                    month_text = month_elem.text
                                    month_map = {
                                        "Jan": 1,
                                        "Feb": 2,
                                        "Mar": 3,
                                        "Apr": 4,
                                        "May": 5,
                                        "Jun": 6,
                                        "Jul": 7,
                                        "Aug": 8,
                                        "Sep": 9,
                                        "Oct": 10,
                                        "Nov": 11,
                                        "Dec": 12,
                                    }
                                    month = month_map.get(
                                        month_text,
                                        int(month_text) if month_text.isdigit() else 1,
                                    )

                                source_date = datetime(year, month, 1)
                            except (ValueError, TypeError):
                                pass

                    # Extract authors (first 3)
                    authors = []
                    for author in article.findall(".//Author")[:3]:
                        last_name = author.findtext("LastName", "")
                        fore_name = author.findtext("ForeName", "")
                        if last_name:
                            authors.append(f"{fore_name} {last_name}".strip())

                    authors_str = (
                        ", ".join(authors) if authors else "Authors not listed"
                    )

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
                            "authors": authors_str,
                        },
                    )

                    evidence_list.append(evidence)

                except Exception as e:
                    logger.warning(f"Failed to parse PubMed article: {e}")
                    continue

        except ET.ParseError as e:
            logger.error(f"Failed to parse PubMed XML: {e}")
            # Fallback: Use IDs if XML parsing fails
            for pmid in raw_response.get("ids", []):
                evidence_list.append(
                    self._create_evidence_dict(
                        title=f"PubMed Article {pmid}",
                        snippet="Medical research article from PubMed database.",
                        url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                        source_date=None,
                        metadata={"pmid": pmid, "api_source": "PubMed"},
                    )
                )

        logger.info(f"PubMed returned {len(evidence_list)} evidence items")
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
            max_results=10,
            emits_structural_metadata=True,  # NF-07-v2: indicator data, structural
        )

    def is_relevant_for_domain(self, domain: str, jurisdiction: str) -> bool:
        """WHO covers Health globally."""
        return domain == "Health"

    def search(
        self,
        query: str,
        domain: str,
        jurisdiction: str,
        entities: Optional[List[Dict[str, str]]] = None,
    ) -> List[Dict[str, Any]]:
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

        targeted_query = self._build_targeted_query(query, entities)

        # Search indicators
        try:
            # First, search for relevant indicators
            indicator_response = self._make_request("/Indicator")

            if not indicator_response or "value" not in indicator_response:
                logger.warning("WHO returned empty indicator response")
                return []

            # Filter indicators by query terms
            query_lower = targeted_query.lower()
            matching_indicators = [
                ind
                for ind in indicator_response.get("value", [])
                if query_lower in ind.get("IndicatorName", "").lower()
            ][: self.max_results]

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
                title = indicator.get(
                    "IndicatorName", f"WHO Indicator {indicator_code}"
                )
                description = indicator.get("Definition", "")

                url = f"https://www.who.int/data/gho/data/indicators/indicator-details/GHO/{indicator_code}"

                snippet = (
                    description[:300]
                    if description
                    else f"WHO health indicator: {title}"
                )

                metadata = {
                    "api_source": "WHO",
                    "indicator_code": indicator_code,
                    "language": indicator.get("Language", "EN"),
                }

                evidence = self._create_evidence_dict(
                    title=title,
                    snippet=snippet,
                    url=url,
                    source_date=None,
                    metadata=metadata,
                )

                evidence_list.append(evidence)

            except Exception as e:
                logger.warning(f"Failed to parse WHO indicator: {e}")
                continue

        logger.info(f"WHO returned {len(evidence_list)} evidence items")
        return evidence_list
