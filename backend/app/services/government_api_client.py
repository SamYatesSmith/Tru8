"""
Government API Client Base Class
Phase 5: Government API Integration

This module provides the base class for all government and institutional API adapters.
Each API (ONS, PubMed, Companies House, etc.) extends this class.
"""

import logging
import httpx
import time
from typing import List, Dict, Optional, Any
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from app.services.cache import get_sync_cache_service, SyncCacheService
from app.services.circuit_breaker import (
    get_circuit_breaker_registry,
    CircuitBreakerError,
)

logger = logging.getLogger(__name__)


class GovernmentAPIClient(ABC):
    """
    Base class for government and institutional API clients.

    All API adapters (ONS, PubMed, Companies House, etc.) extend this class.
    Provides common functionality: caching, rate limiting, error handling.
    """

    def __init__(
        self,
        api_name: str,
        base_url: str,
        api_key: Optional[str] = None,
        cache_ttl: int = 86400,  # 24 hours default
        timeout: int = 10,
        max_results: int = 10,
        max_retries: int = 3,
        priority_tier: int = 1,
        emits_structural_metadata: bool = False,
    ):
        """
        Initialize API client.

        Args:
            api_name: Human-readable API name (e.g., "ONS Economic Statistics")
            base_url: Base URL for API requests
            api_key: Optional API key for authenticated requests
            cache_ttl: Cache time-to-live in seconds (default 24 hours)
            timeout: Request timeout in seconds
            max_results: Maximum number of results to return
            max_retries: Maximum number of retry attempts (default 3)
            priority_tier: Adapter priority (1=specialist, 2=cross-domain academic, 3=general reference)
            emits_structural_metadata: NF-07-v2 self-declaration. Set True when this
                adapter's snippet is structural metadata (taxonomic hierarchy, bill
                stage, observation row, series ID) AND the URL is a canonical
                primary record. Items from such adapters bypass the relevance
                scorer's score=1 exclusion because the scorer is reading the
                metadata snippet, not the URL's content. Default False — search-
                shape adapters whose snippets are content text (paper abstracts,
                article intros, page descriptions) obey the scorer's judgement.
        """
        self.api_name = api_name
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.cache_ttl = cache_ttl
        self.timeout = timeout
        self.max_results = max_results
        self.max_retries = max_retries
        self.priority_tier = priority_tier
        self.emits_structural_metadata = emits_structural_metadata

        # Initialize sync cache (for Celery workers)
        self.cache: SyncCacheService = get_sync_cache_service()

        # Initialize circuit breaker
        self.circuit_breaker = get_circuit_breaker_registry().get_breaker(api_name)

        # HTTP client configuration
        self.headers = {
            "User-Agent": "Tru8 Fact-Checker/1.0 (hello@trueight.com)",
            "Accept": "application/json",
        }

        if self.api_key:
            self._add_auth_header()

    def _add_auth_header(self):
        """Add authentication header. Override in subclasses if needed."""
        self.headers["Authorization"] = f"Bearer {self.api_key}"

    @abstractmethod
    def search(
        self,
        query: str,
        domain: str,
        jurisdiction: str,
        entities: Optional[List[Dict[str, str]]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search the API for evidence related to a claim.

        MUST be implemented by all subclasses.

        Args:
            query: Search query extracted from claim
            domain: Claim domain (Finance, Health, Government, etc.)
            jurisdiction: UK, US, EU, or Global
            entities: Optional list of NER entities from claim, e.g.:
                      [{"text": "Karim Adeyemi", "label": "PERSON"},
                       {"text": "Arsenal", "label": "ORG"}]
                      Adapters can use these for dynamic entity extraction
                      instead of hardcoded lists.

        Returns:
            List of evidence dictionaries with standardized format
        """
        pass

    @abstractmethod
    def _transform_response(self, raw_response: Any) -> List[Dict[str, Any]]:
        """
        Transform API-specific response to standardized evidence format.

        MUST be implemented by all subclasses.

        Args:
            raw_response: Raw API response

        Returns:
            List of evidence dictionaries in standardized format
        """
        pass

    def _make_request(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        method: str = "GET",
    ) -> Optional[Any]:
        """
        Make HTTP request to API with error handling, retries, and circuit breaker.

        Implements:
        - Circuit breaker pattern (fails fast if API is down)
        - Exponential backoff (1s, 2s, 4s delays)
        - Comprehensive error handling

        Args:
            endpoint: API endpoint (will be appended to base_url)
            params: Query parameters
            method: HTTP method (GET, POST)

        Returns:
            Response JSON or None on error
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        # Check circuit breaker before attempting request
        try:
            return self.circuit_breaker.call(
                self._make_request_with_retries, url, params, method
            )
        except CircuitBreakerError as e:
            logger.warning(f"{self.api_name} circuit breaker rejected request: {e}")
            return None

    def _make_request_with_retries(
        self, url: str, params: Optional[Dict[str, Any]], method: str
    ) -> Any:
        """
        Make HTTP request with exponential backoff retries.

        Args:
            url: Full URL to request
            params: Query parameters or JSON body
            method: HTTP method

        Returns:
            Response JSON

        Raises:
            Exception: On all failures after retries exhausted
        """
        last_exception = None

        for attempt in range(self.max_retries):
            try:
                with httpx.Client(
                    timeout=self.timeout, follow_redirects=True
                ) as client:
                    if method == "GET":
                        response = client.get(url, headers=self.headers, params=params)
                    elif method == "POST":
                        response = client.post(url, headers=self.headers, json=params)
                    else:
                        raise ValueError(f"Unsupported HTTP method: {method}")

                    response.raise_for_status()
                    return response.json()

            except httpx.TimeoutException as e:
                last_exception = e
                logger.warning(
                    f"{self.api_name} request timeout (attempt {attempt + 1}/{self.max_retries}): {url}"
                )

            except httpx.HTTPStatusError as e:
                status_code = e.response.status_code
                last_exception = e

                # Don't retry on client errors (4xx) except rate limits
                if 400 <= status_code < 500 and status_code != 429:
                    logger.error(
                        f"{self.api_name} client error {status_code}: {url} (not retrying)"
                    )
                    raise

                logger.warning(
                    f"{self.api_name} HTTP error {status_code} "
                    f"(attempt {attempt + 1}/{self.max_retries}): {url}"
                )

            except httpx.RequestError as e:
                last_exception = e
                logger.warning(
                    f"{self.api_name} request error (attempt {attempt + 1}/{self.max_retries}): {e}"
                )

            except Exception as e:
                last_exception = e
                logger.error(f"{self.api_name} unexpected error: {e}")
                raise

            # Exponential backoff: 1s, 2s, 4s
            if attempt < self.max_retries - 1:
                delay = 2**attempt  # 1, 2, 4 seconds
                logger.debug(f"{self.api_name} retrying in {delay}s...")
                time.sleep(delay)

        # All retries exhausted
        logger.error(
            f"{self.api_name} all {self.max_retries} attempts failed for {url}"
        )
        raise last_exception

    def prepare_query(
        self,
        claim_text: str,
        entities: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        """Shape the inbound claim into the form this adapter's API expects.

        Default returns ``claim_text`` unchanged — adapters that handle natural
        language (OpenAlex, Wikipedia, etc.) need no override. Adapters whose
        APIs need a specific shape (entity name, topic phrase, location+date,
        concept keyword) override this to call helpers in
        ``app.utils.adapter_query_helpers``.

        Called from ``search_with_cache`` *before* the cache lookup, so the
        shaped query forms the cache key — two adapters with different shape
        needs for the same claim no longer share cache namespace.

        Returning an empty string causes the caller to skip the search
        (correct behaviour when a required entity is absent — searching with
        the full sentence produces zero hits and pollutes the cache).
        """
        del entities  # default ignores entities; overrides use them
        return claim_text

    def search_with_cache(
        self,
        query: str,
        domain: str,
        jurisdiction: str,
        entities: Optional[List[Dict[str, str]]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search with caching. Checks cache first, then calls API.

        Args:
            query: Search query
            domain: Claim domain
            jurisdiction: UK, US, EU, or Global
            entities: Optional list of NER entities from claim for dynamic extraction

        Returns:
            List of evidence dictionaries
        """
        # Adapter-specific query shaping. Default is pass-through; overrides
        # may return a focused query or "" to skip the call entirely.
        query = self.prepare_query(query, entities)
        if not query:
            logger.info(
                f"{self.api_name} prepare_query returned empty — skipping API call"
            )
            return []

        # Check cache first
        cached = self.cache.get_cached_api_response_sync(self.api_name, query)
        if cached is not None:
            logger.info(f"{self.api_name} cache HIT for query: {query[:50]}")
            return cached

        # Cache miss - call API
        logger.info(f"{self.api_name} cache MISS - calling API for: {query[:50]}")
        results = self.search(query, domain, jurisdiction, entities)

        # A6: no in-adapter relevance filter. The downstream relevance_scorer
        # does pure topical scoring with full LLM context; literal token
        # overlap here was dropping domain-specific terms that share no
        # surface tokens with the claim (e.g. "Hycean", "sub-Neptune" for a
        # K2-18b biosignature claim).

        # Cache results
        if results:
            self.cache.cache_api_response_sync(
                self.api_name, query, results, self.cache_ttl
            )

        return results

    def _create_evidence_dict(
        self,
        title: str,
        snippet: str,
        url: str,
        source_date: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create standardized evidence dictionary.

        Args:
            title: Evidence title
            snippet: Evidence snippet/summary
            url: Source URL
            source_date: Publication/update date
            metadata: Additional API-specific metadata

        Returns:
            Standardized evidence dictionary
        """
        return {
            "title": title,
            "snippet": snippet,
            "url": url,
            "source": self.api_name,
            "external_source_provider": self.api_name,
            "source_date": source_date.isoformat() if source_date else None,
            "metadata": metadata or {},
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
        }

    # Sentinel domain passed when adapter was added by keyword routing.
    # Bypasses the domain guard so keyword-matched adapters always query.
    KEYWORD_ROUTED = "_keyword_routed"

    def is_relevant_for_domain(self, domain: str, jurisdiction: str) -> bool:
        """
        Check if this API is relevant for the given domain and jurisdiction.

        Override in subclasses to define domain/jurisdiction coverage.

        Args:
            domain: Claim domain (Finance, Health, Government, etc.)
            jurisdiction: UK, US, EU, or Global

        Returns:
            True if this API should be queried for this domain/jurisdiction
        """
        if domain == self.KEYWORD_ROUTED:
            return True
        return True  # Default: query all APIs (subclasses can restrict)

    def _sanitize_query(self, query: str) -> str:
        """
        Sanitize query string for API requests.

        Args:
            query: Raw query string

        Returns:
            Sanitized query string
        """
        # Remove excess whitespace
        query = " ".join(query.split())

        # Limit length to prevent API errors
        max_length = 500
        if len(query) > max_length:
            query = query[:max_length]
            logger.warning(f"Query truncated to {max_length} characters")

        return query

    def _build_targeted_query(
        self,
        query: str,
        entities: Optional[List[Dict[str, str]]] = None,
        max_terms: int = 5,
    ) -> str:
        """Build a targeted API query from entities and claim text.

        Adapters that send queries to external search APIs benefit from
        concise, entity-focused queries rather than raw claim text.

        Strategy:
          1. If entities provided, use ORG/ENTITY/PERSON labels as primary terms.
          2. Fall back to extracting substantive words from query text.
          3. Always returns at least one term (first query word as fallback).

        Subclasses can override to add domain-specific filtering.
        """
        terms: List[str] = []

        # Patterns that indicate numeric/date/quantity entities — not useful
        # as API search terms.  These are claim quantifiers, not topics.
        import re

        _noise_pattern = re.compile(
            r"^[\d£$€%.,/\-\s]+$"  # Pure numbers, currency, percentages
            r"|^\d{4}$"  # Bare years
            r"|^(?:early|late|mid)[\s\-]?\d{4}$"  # "early 2025"
            r"|^\d+(?:\.\d+)?%$"  # "4.2%"
            r"|^[£$€]\d"  # Currency amounts ("$5 billion", "£50 billion")
            r"|^\d+(?:\.\d+)?\s*(?:billion|million|trillion|thousand|bn|mn|m|k)\b",
            re.IGNORECASE,
        )

        # Priority 1: Use provided entities (skip numeric/date/quantity entities)
        if entities:
            for ent in entities:
                text = ent.get("text", "").strip()
                label = ent.get("label", "")
                # NF-15: typed vocab — accept topical/named-thing labels.
                # OTHER is the explicit catch-all for domain concepts.
                if text and label in (
                    "ORG",
                    "PERSON",
                    "LAW",
                    "EVENT",
                    "PRODUCT",
                    "OTHER",
                ):
                    if _noise_pattern.match(text):
                        continue
                    # Strip leading articles from entity text ("the virus" -> "virus")
                    cleaned = re.sub(r"^(?:the|a|an)\s+", "", text, flags=re.IGNORECASE)
                    if len(cleaned) > 2:
                        terms.append(cleaned)

        # Priority 2: Extract key terms from query text
        if not terms:
            _stopwords = {
                "the",
                "a",
                "an",
                "is",
                "are",
                "was",
                "were",
                "be",
                "been",
                "being",
                "have",
                "has",
                "had",
                "do",
                "does",
                "did",
                "will",
                "would",
                "could",
                "should",
                "may",
                "might",
                "shall",
                "can",
                "that",
                "this",
                "these",
                "those",
                "it",
                "its",
                "of",
                "in",
                "to",
                "for",
                "with",
                "on",
                "at",
                "by",
                "from",
                "as",
                "into",
                "than",
                "but",
                "or",
                "and",
                "not",
                "no",
                "so",
                "if",
                "then",
                "about",
                "up",
                "out",
                "more",
                "also",
                "very",
                "just",
                "exceeded",
                "according",
                "said",
                "reported",
                "announced",
                "claimed",
                "suggested",
                "argued",
                "stated",
                "noted",
            }
            words = query.split()
            terms = [
                w
                for w in words
                if w.lower().strip(".,!?'\"()[]") not in _stopwords and len(w) > 2
            ]

        # Cap and join — always return at least something
        if terms:
            targeted = " ".join(terms[:max_terms])
        else:
            targeted = query.split()[0] if query.strip() else query

        logger.debug(
            f"{self.api_name} targeted query: '{targeted}' "
            f"(from: '{query[:60]}...')"
        )
        return targeted

    def _filter_results_by_relevance(
        self,
        results: List[Dict[str, Any]],
        query: str,
        entities: Optional[List[Dict[str, str]]] = None,
        min_overlap: int = 1,
    ) -> List[Dict[str, Any]]:
        """DEPRECATED (A6, 2026-04-22) — no longer called from search_with_cache.

        The literal-token-overlap heuristic implemented here was dropping
        legitimate academic results for any claim whose domain terminology
        didn't share surface tokens with the raw claim (e.g. "Hycean" /
        "sub-Neptune" papers for a K2-18b biosignature claim). Relevance is
        now scored downstream by relevance_scorer.py with full LLM context.

        Retained as a callable for any out-of-tree code that may still
        reference it; do not re-wire into the adapter search path.

        Filter adapter results by entity/term overlap with the claim.

        Removes results whose title+snippet share zero substantive terms
        with the claim's entities or key terms.

        Args:
            results: Evidence dicts from the adapter's search() call.
            query: Original claim text.
            entities: Labelled entities from the claim extraction stage.
            min_overlap: Minimum overlapping terms required to keep.

        Returns:
            Filtered results list (may be shorter than input).
        """
        if not results:
            return results

        # Build reference term set from entities + query
        reference_terms: set = set()
        if entities:
            for ent in entities:
                for word in ent.get("text", "").lower().split():
                    clean = word.strip(".,!?'\"()[]")
                    if len(clean) > 2:
                        reference_terms.add(clean)

        _stopwords = {
            "the",
            "a",
            "an",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "could",
            "should",
            "may",
            "might",
            "shall",
            "can",
            "that",
            "this",
            "it",
            "its",
            "of",
            "in",
            "to",
            "for",
            "with",
            "on",
            "at",
            "by",
            "from",
            "as",
            "than",
            "but",
            "or",
            "and",
            "not",
        }
        for word in query.lower().split():
            clean = word.strip(".,!?'\"()[]")
            if clean not in _stopwords and len(clean) > 2:
                reference_terms.add(clean)

        if not reference_terms:
            return results  # Can't filter without reference terms

        filtered = []
        for item in results:
            title = (item.get("title") or "").lower()
            snippet = (item.get("snippet") or "").lower()
            combined_words = set()
            for w in f"{title} {snippet}".split():
                combined_words.add(w.strip(".,!?'\"()[]"))

            overlap = reference_terms & combined_words
            if len(overlap) >= min_overlap:
                filtered.append(item)
            else:
                logger.info(
                    f"{self.api_name} relevance gate filtered: "
                    f"'{item.get('title', '')[:60]}' "
                    f"(0 term overlap with claim)"
                )

        if len(filtered) < len(results):
            logger.info(
                f"{self.api_name} relevance gate: "
                f"{len(results)} -> {len(filtered)} results"
            )

        return filtered

    def get_api_info(self) -> Dict[str, Any]:
        """
        Get information about this API adapter.

        Returns:
            Dictionary with API metadata
        """
        return {
            "name": self.api_name,
            "base_url": self.base_url,
            "has_api_key": self.api_key is not None,
            "cache_ttl": self.cache_ttl,
            "timeout": self.timeout,
            "max_results": self.max_results,
        }

    def health_check(self) -> bool:
        """
        Check if API is accessible.

        Override in subclasses to implement API-specific health checks.

        Returns:
            True if API is accessible, False otherwise
        """
        try:
            response = self._make_request("", params={})
            return response is not None
        except Exception as e:
            logger.error(f"{self.api_name} health check failed: {e}")
            return False


# ========== API ADAPTER REGISTRY ==========


class APIAdapterRegistry:
    """
    Registry for all government API adapters.

    Usage:
        registry = APIAdapterRegistry()
        registry.register(ONSAdapter())
        registry.register(PubMedAdapter())

        # Get relevant adapters for a claim
        adapters = registry.get_adapters_for_domain("Finance", "UK")
    """

    def __init__(self):
        self.adapters: List[GovernmentAPIClient] = []

    def register(self, adapter: GovernmentAPIClient):
        """Register an API adapter."""
        self.adapters.append(adapter)
        logger.info(f"Registered API adapter: {adapter.api_name}")

    def get_adapters_for_domain(
        self, domain: str, jurisdiction: str
    ) -> List[GovernmentAPIClient]:
        """
        Get all relevant adapters for a domain and jurisdiction.

        Args:
            domain: Claim domain (Finance, Health, Government, etc.)
            jurisdiction: UK, US, EU, or Global

        Returns:
            List of relevant API adapters
        """
        relevant = [
            adapter
            for adapter in self.adapters
            if adapter.is_relevant_for_domain(domain, jurisdiction)
        ]

        logger.info(
            f"Found {len(relevant)} adapters for domain={domain}, "
            f"jurisdiction={jurisdiction}"
        )

        return relevant

    def get_all_adapters(self) -> List[GovernmentAPIClient]:
        """Get all registered adapters."""
        return self.adapters

    def get_adapter_by_name(self, api_name: str) -> Optional[GovernmentAPIClient]:
        """Get adapter by API name."""
        for adapter in self.adapters:
            if adapter.api_name == api_name:
                return adapter
        return None


# Global registry instance
_registry = APIAdapterRegistry()


def get_api_registry() -> APIAdapterRegistry:
    """Get the global API adapter registry."""
    return _registry
