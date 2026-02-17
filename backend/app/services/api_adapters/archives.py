"""
Archive and Historical Document API Adapters.

Contains adapters for:
- Wikipedia: MediaWiki REST API for encyclopedic content
- Library of Congress: Historical documents and Chronicling America newspapers
- Internet Archive: Archive.org collections and Wayback Machine
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

from app.services.government_api_client import GovernmentAPIClient

logger = logging.getLogger(__name__)


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
            timeout=5,  # Reduced from 15s - prevents blocking claim timeout (45s)
            max_results=max_results,
            max_retries=2,  # Reduced from 3 - total now: 5 + 1 + 5 = 11s max
        )
        # Required: Identify our application per Wikipedia API etiquette
        self.headers["User-Agent"] = (
            "Tru8FactChecker/1.0 (https://tru8.com; contact@tru8.com)"
        )
        self.search_base = "https://en.wikipedia.org/w/api.php"

    def is_relevant_for_domain(self, domain: str, jurisdiction: str) -> bool:
        """Wikipedia covers encyclopedic content across most domains."""
        return domain in [
            "History",
            "Politics",
            "Entertainment",
            "General",
            "Sports",
            "Science",
            "Animals",
            "Climate",
            "Health",
        ]

    def search(
        self,
        query: str,
        domain: str,
        jurisdiction: str,
        entities: Optional[List[Dict[str, str]]] = None,
    ) -> List[Dict[str, Any]]:
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
                "origin": "*",
            }

            # Direct request to MediaWiki API (different from REST API base_url)
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(
                    self.search_base, headers=self.headers, params=search_params
                )
                response.raise_for_status()
                search_response = response.json()

            if not search_response or "query" not in search_response:
                logger.warning(
                    f"Wikipedia search returned no results for: {query[:50]}..."
                )
                return []

            search_results = search_response.get("query", {}).get("search", [])

            # Step 2: Fetch summaries for each result via REST API
            for result in search_results[: self.max_results]:
                title = result.get("title", "")
                if not title:
                    continue

                # Get page summary via REST API
                try:
                    # URL-encode the title for the REST API
                    encoded_title = title.replace(" ", "_")
                    summary_response = self._make_request(
                        f"/page/summary/{encoded_title}"
                    )

                    if summary_response and "extract" in summary_response:
                        # Extract publication date if available
                        pub_date = None
                        if "timestamp" in summary_response:
                            try:
                                pub_date = datetime.fromisoformat(
                                    summary_response["timestamp"].replace("Z", "+00:00")
                                )
                            except Exception:
                                pass

                        # Build URL
                        url = (
                            summary_response.get("content_urls", {})
                            .get("desktop", {})
                            .get("page")
                        )
                        if not url:
                            url = f"https://en.wikipedia.org/wiki/{encoded_title}"

                        evidence.append(
                            {
                                "source": "Wikipedia",
                                "source_type": "encyclopedia",
                                "title": summary_response.get("title", title),
                                "snippet": summary_response.get("extract", ""),
                                "url": url,
                                "source_date": (
                                    pub_date.isoformat() if pub_date else None
                                ),
                                "relevance_score": 0.8,
                                "external_source_provider": "Wikipedia",
                                "metadata": {
                                    "description": summary_response.get(
                                        "description", ""
                                    ),
                                    "page_id": summary_response.get("pageid"),
                                    "last_modified": summary_response.get("timestamp"),
                                    "domain": domain,
                                },
                            }
                        )
                except Exception as e:
                    logger.warning(
                        f"Failed to fetch Wikipedia summary for '{title}': {e}"
                    )
                    continue

            logger.info(
                f"Wikipedia returned {len(evidence)} results for query: {query[:50]}..."
            )

        except Exception as e:
            logger.error(f"Wikipedia search failed: {e}")

        return evidence

    def _transform_response(self, raw_response: Any) -> List[Dict[str, Any]]:
        """Transform Wikipedia API response to standardized evidence format."""
        # Handled by search method above
        return []


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
            timeout=5,  # Reduced from 15s - was causing 48s total with retries, exceeding 45s claim timeout
            max_results=max_results,
            max_retries=2,  # Reduced from 3 - total now: 5 + 1 + 5 = 11s max vs previous 48s
        )
        self.headers["User-Agent"] = (
            "Tru8FactChecker/1.0 (https://tru8.com; contact@tru8.com)"
        )

    def is_relevant_for_domain(self, domain: str, jurisdiction: str) -> bool:
        """Library of Congress covers History, Politics, and General (US focus, global relevance)."""
        return domain in ["History", "Politics", "General"]

    def search(
        self, query: str, domain: str, jurisdiction: str, entities=None
    ) -> List[Dict[str, Any]]:
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

            logger.info(
                f"Library of Congress returned {len(evidence)} results for query: {query[:50]}..."
            )

        except Exception as e:
            logger.error(f"Library of Congress search failed: {e}")

        return evidence[: self.max_results]

    def _search_loc_collections(self, query: str) -> List[Dict[str, Any]]:
        """Search general LOC collections."""
        evidence = []

        try:
            params = {
                "q": query,
                "fo": "json",
                "c": 5,  # Limit results
                "fa": "original-format:book|original-format:manuscript|original-format:newspaper",
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

                evidence.append(
                    {
                        "source": "Library of Congress",
                        "source_type": "archive",
                        "title": (
                            title
                            if isinstance(title, str)
                            else title[0] if title else "Unknown"
                        ),
                        "snippet": description or result.get("extract", ""),
                        "url": url,
                        "source_date": pub_date,
                        "relevance_score": 0.85,
                        "external_source_provider": "Library of Congress",
                        "metadata": {
                            "collection": result.get("partof", []),
                            "format": result.get("original_format", []),
                            "contributor": result.get("contributor", []),
                            "subjects": result.get("subject", [])[:5],
                        },
                    }
                )

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
                "c": 5,
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

                evidence.append(
                    {
                        "source": "Chronicling America",
                        "source_type": "newspaper",
                        "title": title,
                        "snippet": (
                            result.get("description", [""])[0]
                            if isinstance(result.get("description"), list)
                            else result.get("description", "")
                        ),
                        "url": url,
                        "source_date": pub_date,
                        "relevance_score": 0.8,
                        "external_source_provider": "Chronicling America",
                        "metadata": {
                            "location": location,
                            "format": result.get("original_format", []),
                            "subjects": result.get("subject", [])[:5],
                        },
                    }
                )

        except Exception as e:
            logger.warning(f"Chronicling America search failed: {e}")

        return evidence

    def _transform_response(self, raw_response: Any) -> List[Dict[str, Any]]:
        """Transform handled by search methods."""
        return []


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
            timeout=5,  # Reduced from 20s - was causing 63s total with retries, exceeding 45s claim timeout
            max_results=max_results,
            max_retries=2,  # Reduced from 3 - total now: 5 + 1 + 5 = 11s max
        )
        self.headers["User-Agent"] = (
            "Tru8FactChecker/1.0 (https://tru8.com; contact@tru8.com)"
        )

    def is_relevant_for_domain(self, domain: str, jurisdiction: str) -> bool:
        """Internet Archive covers historical documents across many domains."""
        return domain in ["History", "General", "Politics", "Entertainment", "Science"]

    def search(
        self, query: str, domain: str, jurisdiction: str, entities=None
    ) -> List[Dict[str, Any]]:
        """
        Search Internet Archive collections.

        Returns standardized evidence dictionaries.
        """
        evidence = []

        try:
            # Build search query for texts and documents
            params = {
                "q": query,
                "output": "json",
                "rows": self.max_results,
                "fl[]": [
                    "identifier",
                    "title",
                    "description",
                    "date",
                    "creator",
                    "mediatype",
                    "collection",
                ],
                "sort[]": "downloads desc",  # Prioritize popular items
            }

            with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
                response = client.get(
                    f"{self.base_url}/advancedsearch.php",
                    params=params,
                    headers=self.headers,
                )
                response.raise_for_status()
                data = response.json()

            if not data or "response" not in data:
                logger.warning(
                    f"Internet Archive returned no results for: {query[:50]}..."
                )
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

                mediatype = doc.get("mediatype", "")

                evidence.append(
                    {
                        "source": "Internet Archive",
                        "source_type": "archive",
                        "title": title,
                        "snippet": description[:500] if description else "",
                        "url": url,
                        "source_date": pub_date,
                        "relevance_score": 0.8,
                        "external_source_provider": "Internet Archive",
                        "metadata": {
                            "identifier": identifier,
                            "mediatype": mediatype,
                            "creator": creator,
                            "collection": doc.get("collection", []),
                        },
                    }
                )

            logger.info(
                f"Internet Archive returned {len(evidence)} results for query: {query[:50]}..."
            )

        except Exception as e:
            logger.error(f"Internet Archive search failed: {e}")

        return evidence

    def _transform_response(self, raw_response: Any) -> List[Dict[str, Any]]:
        """Transform handled by search method."""
        return []
