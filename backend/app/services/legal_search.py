"""
Legal Statute Search Service

Retrieves statutes from official legal APIs:
- US: GovInfo.gov (primary), Congress.gov (supplementary)
- UK: legislation.gov.uk

Follows three-tier search strategy:
1. Direct citation lookup (fastest, ~1s)
2. Year + keyword search (filtered, ~3-5s)
3. Full-text search (broad, ~5-10s)
"""

import httpx
import re
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta, timezone
from xml.etree import ElementTree as ET

from app.core.config import settings

logger = logging.getLogger(__name__)


class LegalSearchService:
    """
    Search official legal databases for statutes and legislation.

    Features:
    - Direct citation lookup (fastest)
    - Year + keyword search (filtered)
    - Full-text search (broad)
    - Section-level extraction (not full documents)
    - Aggressive caching (statutes rarely change)
    """

    def __init__(self):
        self.govinfo_api_key = getattr(settings, "GOVINFO_API_KEY", None)
        self.congress_api_key = getattr(settings, "CONGRESS_API_KEY", None)
        self.timeout = getattr(settings, "LEGAL_API_TIMEOUT_SECONDS", 10)

        # In-memory cache with TTL
        self.cache = {}
        self.cache_ttl = timedelta(days=getattr(settings, "LEGAL_CACHE_TTL_DAYS", 30))

    async def search_statutes(
        self, claim_text: str, metadata: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Search for statutes across appropriate sources.

        Args:
            claim_text: Original claim text
            metadata: Extracted metadata (year, citation, jurisdiction, act_name)

        Returns:
            List of statute results with text excerpts
        """
        # Check cache first
        cache_key = self._build_cache_key(claim_text, metadata)
        if cache_key in self.cache:
            cached_result, cached_time = self.cache[cache_key]
            if datetime.now(timezone.utc) - cached_time < self.cache_ttl:
                logger.info(f"Legal search cache hit: {cache_key}")
                return cached_result

        results = []
        jurisdiction = metadata.get("jurisdiction")

        try:
            if jurisdiction == "US":
                results = await self._search_us_sources(claim_text, metadata)
            elif jurisdiction == "UK":
                results = await self._search_uk_sources(claim_text, metadata)
            else:
                # Unknown jurisdiction - try both
                logger.warning(f"Unknown jurisdiction, trying all sources")
                us_results = await self._search_us_sources(claim_text, metadata)
                uk_results = await self._search_uk_sources(claim_text, metadata)
                results = us_results + uk_results

            # Cache results
            self.cache[cache_key] = (results, datetime.now(timezone.utc))

            logger.info(
                f"Legal search returned {len(results)} results for: {claim_text[:50]}"
            )
            return results

        except Exception as e:
            logger.error(f"Legal search failed: {e}")
            return []  # Return empty, don't crash pipeline

    async def _search_us_sources(
        self, claim_text: str, metadata: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Search US legal sources (GovInfo + Congress)"""
        results = []

        # Priority 1: Direct citation lookup (if available)
        citations = metadata.get("citations", [])
        for citation in citations:
            if citation.get("type") == "USC":
                citation_results = await self._search_govinfo_by_citation(citation)
                results.extend(citation_results)

        # Prefer the act/bill title (LAW entity, injected by the adapter) over
        # stopword-stripped keywords — the latter produce low-relevance hits.
        act_name = metadata.get("act_name")

        # Priority 2: Year + keyword search (if year available)
        if metadata.get("year") and len(results) < 3:
            year_results = await self._search_govinfo_by_year(
                claim_text, metadata["year"], act_name=act_name
            )
            results.extend(year_results)

        # Priority 3: Broad keyword search (fallback)
        if len(results) < 3:
            keyword_results = await self._search_govinfo_fulltext(
                claim_text, act_name=act_name
            )
            results.extend(keyword_results)

        # Deduplicate by URL
        seen_urls = set()
        unique_results = []
        for result in results:
            if result["url"] not in seen_urls:
                seen_urls.add(result["url"])
                unique_results.append(result)

        return unique_results[:5]  # Top 5 results

    async def _search_govinfo_by_citation(
        self, citation: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """
        Search GovInfo by direct US Code citation.

        Example: 42 USC §1983 → https://api.govinfo.gov/...
        """
        if not self.govinfo_api_key:
            logger.warning("GovInfo API key not configured")
            return []

        try:
            title = citation.get("title")
            section = citation.get("section")

            if not title or not section:
                return []

            # GovInfo API endpoint for US Code
            base_url = "https://api.govinfo.gov/collections/USCODE"

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Search for specific section
                response = await client.get(
                    f"{base_url}/2021/title-{title}/section-{section}",
                    params={"api_key": self.govinfo_api_key},
                    headers={"Accept": "application/json"},
                )

                if response.status_code == 200:
                    data = response.json()
                    return [self._format_govinfo_result(data, citation)]
                else:
                    logger.warning(
                        f"GovInfo citation lookup failed: {response.status_code}"
                    )
                    return []

        except Exception as e:
            logger.error(f"GovInfo citation search error: {e}")
            return []

    async def _search_govinfo_by_year(
        self, claim_text: str, year: str, act_name=None
    ) -> List[Dict[str, Any]]:
        """
        Search GovInfo filtered by year.

        Strategy: Search statutes/bills enacted in specific year
        """
        if not self.govinfo_api_key:
            return []

        try:
            # Prefer the quoted act/bill title; else keyword fallback. The
            # collection filter MUST live in the query string — GovInfo ignores
            # a `collections` body field (and GET returns 400). PLAW = enacted
            # public laws.
            terms = (
                f'"{act_name}"'
                if act_name
                else self._extract_search_keywords(claim_text)
            )
            query = f"{terms} {year} collection:PLAW"

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    "https://api.govinfo.gov/search",
                    params={"api_key": self.govinfo_api_key},
                    json={
                        "query": query,
                        "pageSize": 3,
                        "offsetMark": "*",
                    },
                    headers={"Accept": "application/json"},
                )

                if response.status_code == 200:
                    data = response.json()
                    results = []
                    for item in data.get("results", []):
                        results.append(
                            self._format_govinfo_result(item, {}, act_name=act_name)
                        )
                    return results
                else:
                    logger.warning(
                        f"GovInfo year search failed: {response.status_code}"
                    )
                    return []

        except Exception as e:
            logger.error(f"GovInfo year search error: {e}")
            return []

    async def _search_govinfo_fulltext(
        self, claim_text: str, act_name=None
    ) -> List[Dict[str, Any]]:
        """
        Broad full-text search of GovInfo.

        Fallback when citation and year not available.
        """
        if not self.govinfo_api_key:
            return []

        try:
            terms = (
                f'"{act_name}"'
                if act_name
                else self._extract_search_keywords(claim_text)
            )
            query = f"{terms} collection:PLAW"

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # POST + JSON; collection filter in the query string (the
                # `collections` body field is ignored, which otherwise returns
                # tens of thousands of unranked cross-collection results).
                response = await client.post(
                    "https://api.govinfo.gov/search",
                    params={"api_key": self.govinfo_api_key},
                    json={
                        "query": query,
                        "pageSize": 5,
                        "offsetMark": "*",
                    },
                    headers={"Accept": "application/json"},
                )

                if response.status_code == 200:
                    data = response.json()
                    results = []
                    for item in data.get("results", []):
                        results.append(
                            self._format_govinfo_result(item, {}, act_name=act_name)
                        )
                    return results
                else:
                    logger.warning(
                        f"GovInfo fulltext search failed: {response.status_code}"
                    )
                    return []

        except Exception as e:
            logger.error(f"GovInfo fulltext search error: {e}")
            return []

    async def _search_uk_sources(
        self, claim_text: str, metadata: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Search UK legislation.gov.uk

        No API key required - publicly accessible
        """
        try:
            # Check if we have direct citation
            citations = metadata.get("citations", [])
            for citation in citations:
                if citation.get("type") in ["UKPGA", "UKSI", "ASP"]:
                    # Direct lookup by identifier
                    result = await self._search_uk_by_identifier(citation)
                    if result:
                        return [result]

            # Fallback to search API
            year = metadata.get("year")
            keywords = self._extract_search_keywords(claim_text)

            params = {"text": keywords, "page": 1, "per_page": 5}

            if year:
                params["year"] = year

            async with httpx.AsyncClient(
                timeout=self.timeout, follow_redirects=True
            ) as client:
                response = await client.get(
                    "https://www.legislation.gov.uk/search", params=params
                )

                if response.status_code == 200:
                    # Parse HTML response (legislation.gov.uk returns HTML, not JSON)
                    return self._parse_uk_search_results(response.text)
                else:
                    logger.warning(
                        f"UK legislation search failed: {response.status_code}"
                    )
                    return []

        except Exception as e:
            logger.error(f"UK legislation search error: {e}")
            return []

    async def _search_uk_by_identifier(
        self, citation: Dict[str, str]
    ) -> Optional[Dict[str, Any]]:
        """
        Direct UK legislation lookup by identifier.

        Example: ukpga/2018/12 → https://www.legislation.gov.uk/ukpga/2018/12
        """
        try:
            leg_type = citation.get("type", "").lower()
            year = citation.get("year")
            number = citation.get("number")

            if not all([leg_type, year, number]):
                return None

            url = f"https://www.legislation.gov.uk/{leg_type}/{year}/{number}"

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url + "/data.xml")

                if response.status_code == 200:
                    return self._parse_uk_legislation_xml(response.text, url, citation)
                else:
                    logger.warning(
                        f"UK legislation lookup failed: {response.status_code}"
                    )
                    return None

        except Exception as e:
            logger.error(f"UK identifier lookup error: {e}")
            return None

    def _format_govinfo_result(
        self, item: Dict[str, Any], citation: Dict[str, str], act_name=None
    ) -> Dict[str, Any]:
        """Format GovInfo API response into standard result format.

        GovInfo PLAW titles are OFFICIAL (e.g. "An act to provide for
        reconciliation pursuant to title II of H. Con. Res. 14"), not the
        popular name a claim uses ("Inflation Reduction Act of 2022"). Prepend
        the popular act title so downstream relevance scoring can recognise the
        match — otherwise the correct primary-source statute is filtered out.
        """
        official_title = item.get("title", "US Code Section")
        if act_name and act_name.lower() not in official_title.lower():
            title = f"{act_name} — {official_title}"
        else:
            title = official_title
        return {
            "url": item.get("packageLink") or item.get("detailsLink", ""),
            "title": title,
            "snippet": item.get("summary", "") or title,
            "published_date": item.get("dateIssued"),
            "source": "govinfo.gov",
            "citation": citation.get("full_text", ""),
            "jurisdiction": "US",
        }

    def _parse_uk_legislation_xml(
        self, xml_content: str, url: str, citation: Dict[str, str]
    ) -> Dict[str, Any]:
        """Parse UK legislation XML and extract relevant sections"""
        try:
            root = ET.fromstring(xml_content)

            # Extract title
            title_elem = root.find(
                ".//{http://www.legislation.gov.uk/namespaces/legislation}Title"
            )
            title = title_elem.text if title_elem is not None else "UK Legislation"

            # Extract first section or preamble for snippet
            snippet_elem = root.find(
                ".//{http://www.legislation.gov.uk/namespaces/legislation}Text"
            )
            if snippet_elem is not None and snippet_elem.text:
                snippet = snippet_elem.text[:500]
                if len(snippet_elem.text) > 500:
                    last_space = snippet.rfind(" ")
                    if last_space > 300:
                        snippet = snippet[:last_space]
            else:
                snippet = ""

            return {
                "url": url,
                "title": title,
                "snippet": snippet,
                "published_date": citation.get("year"),
                "source": "legislation.gov.uk",
                "citation": f"{citation.get('type')} {citation.get('year')}/{citation.get('number')}",
                "jurisdiction": "UK",
            }

        except Exception as e:
            logger.error(f"UK XML parsing error: {e}")
            return {
                "url": url,
                "title": f"UK Legislation {citation.get('year')}/{citation.get('number')}",
                "snippet": "",
                "published_date": citation.get("year"),
                "source": "legislation.gov.uk",
                "citation": "",
                "jurisdiction": "UK",
            }

    def _parse_uk_search_results(self, html_content: str) -> List[Dict[str, Any]]:
        """Parse UK legislation search results from HTML"""
        # Simplified parser - in production, use BeautifulSoup or similar
        results = []

        # Basic regex parsing for demonstration
        # In production, use proper HTML parser
        url_pattern = r'href="(/\w+/\d{4}/\d+)"'
        matches = re.findall(url_pattern, html_content)

        for match in matches[:5]:
            url = f"https://www.legislation.gov.uk{match}"
            results.append(
                {
                    "url": url,
                    "title": f"UK Legislation {match}",
                    "snippet": "",
                    "published_date": None,
                    "source": "legislation.gov.uk",
                    "citation": match,
                    "jurisdiction": "UK",
                }
            )

        return results

    def _extract_search_keywords(self, claim_text: str) -> str:
        """Extract relevant search keywords from claim text"""
        # Remove common stopwords and extract key terms
        stopwords = {"a", "an", "the", "is", "are", "was", "were", "that", "this", "it"}

        words = re.findall(r"\b\w+\b", claim_text.lower())
        keywords = [w for w in words if w not in stopwords and len(w) > 3]

        return " ".join(keywords[:10])  # Top 10 keywords

    def _build_cache_key(self, claim_text: str, metadata: Dict[str, Any]) -> str:
        """Build cache key from claim and metadata"""
        jurisdiction = metadata.get("jurisdiction", "unknown")
        year = metadata.get("year", "")
        citations = str(metadata.get("citations", []))

        return f"{jurisdiction}:{year}:{claim_text[:50]}:{citations}"
