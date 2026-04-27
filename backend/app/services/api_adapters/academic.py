"""
Academic Research API Adapters

Adapters for academic research and scholarly works:
- CrossRef (research metadata)
- Semantic Scholar (academic papers)
- OpenAlex (scholarly works)
"""

import logging
import time
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from app.services.government_api_client import GovernmentAPIClient

logger = logging.getLogger(__name__)


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
            max_results=3,  # Cap at 3: CrossRef supplements web search, not displaces it
        )

        # CrossRef requests User-Agent with contact email
        self.headers.update(
            {
                "User-Agent": "Tru8FactChecker/1.0 (https://tru8.com; mailto:hello@trueight.com)"
            }
        )

    def is_relevant_for_domain(self, domain: str, jurisdiction: str) -> bool:
        """
        CrossRef covers academic papers - only relevant for research-heavy domains.

        NOT relevant for:
        - Politics (current news, not academic papers)
        - Law (legal news, not legal scholarship)
        - Business/Entertainment (company news, not research)

        Academic papers rarely help verify current news claims about meetings,
        deals, statements, or events.
        """
        return domain in [
            "Science",
            "Climate",
            "Health",
            # Removed: Politics, Law, History, Demographics, Animals
            # These are better served by news sources for current events
        ]

    def search(
        self,
        query: str,
        domain: str,
        jurisdiction: str,
        entities: Optional[List[Dict[str, str]]] = None,
    ) -> List[Dict[str, Any]]:
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

        current_year = datetime.now(timezone.utc).year
        min_year = current_year - 2

        params = {
            "query": query,
            "rows": self.max_results,
            "sort": "relevance",
            "select": "title,author,published-print,DOI,publisher,abstract",
            "filter": f"from-pub-date:{min_year}",
        }

        try:
            response = self._make_request("/works", params=params)

            if not response or "message" not in response:
                logger.warning(f"CrossRef returned empty response for: {query}")
                return []

            return self._transform_response(response["message"])

        except Exception as e:
            # A8b: recoverable, caller treats [] as no CrossRef evidence
            logger.warning(f"CrossRef search failed for '{query}': {e}")
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
                        source_date = datetime(
                            date_parts[0], date_parts[1], date_parts[2]
                        )
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
                    "authors": (
                        ", ".join(author_names)
                        if author_names
                        else "Authors not listed"
                    ),
                }

                evidence = self._create_evidence_dict(
                    title=title,
                    snippet=snippet,
                    url=url,
                    source_date=source_date,
                    metadata=metadata,
                )

                evidence_list.append(evidence)

            except Exception as e:
                logger.warning(f"Failed to parse CrossRef item: {e}")
                continue

        logger.info(f"CrossRef returned {len(evidence_list)} evidence items")
        return evidence_list


# ========== SEMANTIC SCHOLAR ADAPTER (P1) ==========


class SemanticScholarAdapter(GovernmentAPIClient):
    """
    Semantic Scholar API adapter for academic paper search.

    Provides access to 200M+ academic papers with citation data.
    No API key required (100 requests/5 minutes).
    """

    def __init__(self):
        super().__init__(
            api_name="Semantic Scholar",
            base_url="https://api.semanticscholar.org/graph/v1",
            api_key=None,
            cache_ttl=86400 * 7,  # 7 days
            timeout=15,
            max_results=3,  # Cap at 3: academic papers supplement web search
            priority_tier=2,  # Cross-domain academic
        )
        self.headers["User-Agent"] = (
            "Tru8FactChecker/1.0 (https://tru8.com; hello@trueight.com)"
        )

    def is_relevant_for_domain(self, domain: str, jurisdiction: str) -> bool:
        """
        Semantic Scholar covers academic papers - only for research-heavy domains.

        NOT relevant for current news verification (Politics, Entertainment, Business).
        Academic papers rarely help verify claims about recent events, meetings, or deals.
        """
        return domain in [
            "Science",
            "Climate",
            "Health",
            # Removed: Politics, Law, History, Demographics, Animals, Entertainment, General
        ]

    def search(
        self, query: str, domain: str, jurisdiction: str, entities=None
    ) -> List[Dict[str, Any]]:
        """
        Search Semantic Scholar for academic papers.

        Returns standardized evidence dictionaries.
        """
        evidence = []

        try:
            import httpx
            from urllib.parse import quote

            # Build targeted query from entities (avoids sending full claim text)
            targeted_query = self._build_targeted_query(query, entities)

            # Build search URL with fields
            fields = "paperId,title,abstract,url,year,authors,citationCount,publicationDate,venue"
            current_year = datetime.now(timezone.utc).year
            min_year = current_year - 2
            url = f"{self.base_url}/paper/search?query={quote(targeted_query)}&limit={self.max_results}&fields={fields}&year={min_year}-{current_year}"

            # A3: retry on 429 with Retry-After honoured. Semantic Scholar
            # rate-limits aggressively; the first call of every check was
            # previously failing with no retry (Sentry PYTHON-FASTAPI-B).
            data = None
            with httpx.Client(timeout=self.timeout, headers=self.headers) as client:
                for attempt in range(3):
                    response = client.get(url)
                    if response.status_code == 429 and attempt < 2:
                        wait = float(response.headers.get("retry-after", 2**attempt))
                        logger.info(
                            f"Semantic Scholar 429, backing off {wait}s "
                            f"(attempt {attempt + 1}/3)"
                        )
                        time.sleep(min(wait, 10))
                        continue
                    response.raise_for_status()
                    data = response.json()
                    break

            if not data or "data" not in data:
                return []

            for paper in data.get("data", []):
                title = paper.get("title")
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

                citation_count = paper.get("citationCount", 0) or 0

                # A7: if no abstract is available, synthesise a snippet from
                # metadata so the retrieve-stage converter doesn't silently
                # drop the item for an empty snippet. Keeps the paper reachable
                # by the downstream LLM scorer + mapper.
                snippet = paper.get("abstract", "") or ""
                if not snippet.strip():
                    fallback_parts = []
                    venue = paper.get("venue", "")
                    if venue:
                        fallback_parts.append(f"Published in {venue}")
                    if authors:
                        fallback_parts.append(f"Authors: {', '.join(authors)}")
                    if paper.get("year"):
                        fallback_parts.append(f"Year: {paper['year']}")
                    if citation_count:
                        fallback_parts.append(f"Citations: {citation_count}")
                    if fallback_parts:
                        snippet = ". ".join(fallback_parts) + "."

                evidence.append(
                    {
                        "source": "Semantic Scholar",
                        "source_type": "academic",
                        "title": title,
                        "snippet": snippet,
                        "url": paper.get("url")
                        or f"https://www.semanticscholar.org/paper/{paper.get('paperId', '')}",
                        "source_date": pub_date,
                        "external_source_provider": "Semantic Scholar",
                        "metadata": {
                            "authors": authors,
                            "venue": paper.get("venue", ""),
                            "citation_count": citation_count,
                            "paper_id": paper.get("paperId"),
                        },
                    }
                )

            logger.info(
                f"Semantic Scholar returned {len(evidence)} results for query: {query[:50]}..."
            )

        except Exception as e:
            # A8b: recoverable, caller continues with whatever evidence accumulated
            logger.warning(f"Semantic Scholar search failed: {e}")

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

    def __init__(self):
        super().__init__(
            api_name="OpenAlex",
            base_url="https://api.openalex.org",
            api_key=None,
            cache_ttl=86400 * 7,  # 7 days
            timeout=15,
            max_results=3,  # Cap at 3: academic papers supplement web search
            priority_tier=2,  # Cross-domain academic
        )
        # OpenAlex requests polite pool identification via email
        self.headers["User-Agent"] = "Tru8FactChecker/1.0 (mailto:hello@trueight.com)"

    def is_relevant_for_domain(self, domain: str, jurisdiction: str) -> bool:
        """
        OpenAlex covers scholarly works - only for research-heavy domains.

        NOT relevant for current news verification (Politics, Entertainment, Business).
        Scholarly papers rarely help verify claims about recent events, meetings, or deals.
        """
        return domain in [
            "Science",
            "Climate",
            "Health",
            # Removed: Politics, Law, History, Demographics, Animals, Entertainment, General
        ]

    def search(
        self, query: str, domain: str, jurisdiction: str, entities=None
    ) -> List[Dict[str, Any]]:
        """
        Search OpenAlex for scholarly works.

        Returns standardized evidence dictionaries.
        """
        evidence = []

        try:
            import httpx
            from urllib.parse import quote

            # Build search URL with mailto for polite pool
            current_year = datetime.now(timezone.utc).year
            min_year = current_year - 2
            url = f"{self.base_url}/works?search={quote(query)}&per-page={self.max_results}&mailto=hello@trueight.com&filter=from_publication_date:{min_year}-01-01"

            # A3: retry on 429 with Retry-After honoured. Same pattern as
            # Semantic Scholar — both adapters bypassed the base client's
            # 429 retry logic by building their own inline httpx client.
            data = None
            with httpx.Client(timeout=self.timeout, headers=self.headers) as client:
                for attempt in range(3):
                    response = client.get(url)
                    if response.status_code == 429 and attempt < 2:
                        wait = float(response.headers.get("retry-after", 2**attempt))
                        logger.info(
                            f"OpenAlex 429, backing off {wait}s "
                            f"(attempt {attempt + 1}/3)"
                        )
                        time.sleep(min(wait, 10))
                        continue
                    response.raise_for_status()
                    data = response.json()
                    break

            if not data or "results" not in data:
                return []

            for work in data.get("results", []):
                title = work.get("title")
                if not title:
                    continue

                # Extract authors
                authors = []
                for authorship in work.get("authorships", [])[:3]:
                    author = authorship.get("author", {})
                    if author and author.get("display_name"):
                        authors.append(author["display_name"])

                # Parse publication date
                pub_date = work.get("publication_date")
                if not pub_date and work.get("publication_year"):
                    pub_date = f"{work['publication_year']}-01-01"

                citation_count = work.get("cited_by_count", 0) or 0

                # Get URL
                url = work.get("doi")
                if url:
                    url = f"https://doi.org/{url.replace('https://doi.org/', '')}"
                else:
                    url = work.get("id", "https://openalex.org")

                # Reconstruct abstract from inverted index
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
                source_name = (
                    source_info.get("display_name", "")
                    if isinstance(source_info, dict)
                    else ""
                )

                # Safely extract open_access info
                open_access = work.get("open_access") or {}
                is_oa = (
                    open_access.get("is_oa", False)
                    if isinstance(open_access, dict)
                    else False
                )

                # A7: if the inverted-index reconstruction produced nothing
                # (common for older papers or certain venues), synthesise a
                # snippet from available metadata rather than let the
                # retrieve-stage converter silently drop the item.
                if not abstract.strip():
                    fallback_parts = []
                    if source_name:
                        fallback_parts.append(f"Published in {source_name}")
                    if authors:
                        fallback_parts.append(f"Authors: {', '.join(authors)}")
                    if work.get("publication_year"):
                        fallback_parts.append(f"Year: {work['publication_year']}")
                    if citation_count:
                        fallback_parts.append(f"Citations: {citation_count}")
                    if fallback_parts:
                        abstract = ". ".join(fallback_parts) + "."

                evidence.append(
                    {
                        "source": "OpenAlex",
                        "source_type": "academic",
                        "title": title,
                        "snippet": abstract,
                        "url": url,
                        "source_date": pub_date,
                        "external_source_provider": "OpenAlex",
                        "metadata": {
                            "authors": authors,
                            "citation_count": citation_count,
                            "type": work.get("type", ""),
                            "open_access": is_oa,
                            "journal_source": source_name,
                        },
                    }
                )

            logger.info(
                f"OpenAlex returned {len(evidence)} results for query: {query[:50]}..."
            )

        except Exception as e:
            # A8b: recoverable, caller continues with whatever evidence accumulated
            logger.warning(f"OpenAlex search failed: {e}")

        return evidence

    def _transform_response(self, raw_response: Any) -> List[Dict[str, Any]]:
        """Transform handled by search method."""
        return []
