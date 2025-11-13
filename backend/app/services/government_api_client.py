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
from datetime import datetime
from app.services.cache import get_sync_cache_service, SyncCacheService
from app.services.circuit_breaker import get_circuit_breaker_registry, CircuitBreakerError

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
        max_retries: int = 3
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
        """
        self.api_name = api_name
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.cache_ttl = cache_ttl
        self.timeout = timeout
        self.max_results = max_results
        self.max_retries = max_retries

        # Initialize sync cache (for Celery workers)
        self.cache: SyncCacheService = get_sync_cache_service()

        # Initialize circuit breaker
        self.circuit_breaker = get_circuit_breaker_registry().get_breaker(api_name)

        # HTTP client configuration
        self.headers = {
            "User-Agent": "Tru8 Fact-Checker/1.0 (contact@tru8.com)",
            "Accept": "application/json"
        }

        if self.api_key:
            self._add_auth_header()

    def _add_auth_header(self):
        """Add authentication header. Override in subclasses if needed."""
        self.headers["Authorization"] = f"Bearer {self.api_key}"

    @abstractmethod
    def search(self, query: str, domain: str, jurisdiction: str) -> List[Dict[str, Any]]:
        """
        Search the API for evidence related to a claim.

        MUST be implemented by all subclasses.

        Args:
            query: Search query extracted from claim
            domain: Claim domain (Finance, Health, Government, etc.)
            jurisdiction: UK, US, EU, or Global

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
        method: str = "GET"
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
                self._make_request_with_retries,
                url,
                params,
                method
            )
        except CircuitBreakerError as e:
            logger.warning(f"{self.api_name} circuit breaker rejected request: {e}")
            return None

    def _make_request_with_retries(
        self,
        url: str,
        params: Optional[Dict[str, Any]],
        method: str
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
                with httpx.Client(timeout=self.timeout) as client:
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
                delay = 2 ** attempt  # 1, 2, 4 seconds
                logger.debug(f"{self.api_name} retrying in {delay}s...")
                time.sleep(delay)

        # All retries exhausted
        logger.error(
            f"{self.api_name} all {self.max_retries} attempts failed for {url}"
        )
        raise last_exception

    def search_with_cache(
        self,
        query: str,
        domain: str,
        jurisdiction: str
    ) -> List[Dict[str, Any]]:
        """
        Search with caching. Checks cache first, then calls API.

        Args:
            query: Search query
            domain: Claim domain
            jurisdiction: UK, US, EU, or Global

        Returns:
            List of evidence dictionaries
        """
        # Check cache first
        cached = self.cache.get_cached_api_response_sync(self.api_name, query)
        if cached is not None:
            logger.info(f"{self.api_name} cache HIT for query: {query[:50]}")
            return cached

        # Cache miss - call API
        logger.info(f"{self.api_name} cache MISS - calling API for: {query[:50]}")
        results = self.search(query, domain, jurisdiction)

        # Cache results
        if results:
            self.cache.cache_api_response_sync(
                self.api_name,
                query,
                results,
                self.cache_ttl
            )

        return results

    def _create_evidence_dict(
        self,
        title: str,
        snippet: str,
        url: str,
        source_date: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None
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
            "credibility_score": 0.95,  # API sources are high credibility
            "source_date": source_date.isoformat() if source_date else None,
            "metadata": metadata or {},
            "retrieved_at": datetime.utcnow().isoformat()
        }

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
            "max_results": self.max_results
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
        self,
        domain: str,
        jurisdiction: str
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
            adapter for adapter in self.adapters
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
