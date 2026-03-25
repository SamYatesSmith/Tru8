import logging
import asyncio
import time
import threading
import re
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import httpx
from urllib.parse import quote_plus
from app.core.config import settings

logger = logging.getLogger(__name__)

# Jurisdiction-to-country mapping for search providers.
# UK → gb (current default), US → us, EU/Global → None (omit filter).
JURISDICTION_TO_COUNTRY: Dict[str, Optional[str]] = {
    "UK": "gb",
    "US": "us",
    "EU": None,
    "Global": None,
}

# CODE RELOAD CHECK: This timestamp proves the module was reloaded
_MODULE_LOAD_TIME = time.time()

# Write to file (works even if logger isn't configured)
import pathlib

_reload_marker = pathlib.Path(__file__).parent.parent.parent / "MODULE_RELOADED.txt"
_reload_marker.write_text(
    f"search.py loaded at {_MODULE_LOAD_TIME}\nRate limiting ACTIVE\n"
)

logger.critical(
    f"search.py MODULE LOADED at {_MODULE_LOAD_TIME} - Rate limiting ACTIVE"
)

# GLOBAL rate limiters to prevent concurrent burst across all concurrent claims
# Using threading.Lock for timestamp coordination (works across event loops)
_brave_lock = threading.Lock()
_brave_last_request_time = 0
_serpapi_lock = threading.Lock()
_serpapi_last_request_time = 0

# Brave circuit breaker — trips on first 429, auto-resets after cooldown
_brave_circuit_lock = threading.Lock()
_brave_circuit_open = False
_brave_circuit_opened_at = 0.0
_BRAVE_CIRCUIT_COOLDOWN = 60.0  # seconds before auto-reset

# Serper.dev rate limiter
_serper_lock = threading.Lock()
_serper_last_request_time = 0


def warmup_search_providers():
    """
    Pre-warm search providers by setting rate limit timestamps.

    This prevents the 10-second "cold start" delay from triggering on the first
    actual fact-check request. The cold start delay was designed to prevent
    API anti-abuse detection, but it was being applied DURING task execution,
    causing the first claim to timeout with 0 sources.

    By setting the timestamps at worker startup, subsequent requests will use
    the normal 2.5s spacing instead of the 10s cold start delay.

    Call this from Celery worker initialization (workers/__init__.py).
    """
    global _brave_lock, _brave_last_request_time, _serpapi_lock, _serpapi_last_request_time, _serper_lock, _serper_last_request_time

    current_time = time.time()

    with _brave_lock:
        if _brave_last_request_time == 0:
            _brave_last_request_time = current_time
            logger.info(f"BRAVE WARMUP: Pre-warmed rate limiter at {current_time:.3f}")

    with _serpapi_lock:
        if _serpapi_last_request_time == 0:
            _serpapi_last_request_time = current_time
            logger.info(
                f"SERPAPI WARMUP: Pre-warmed rate limiter at {current_time:.3f}"
            )

    with _serper_lock:
        if _serper_last_request_time == 0:
            _serper_last_request_time = current_time
            logger.info(f"SERPER WARMUP: Pre-warmed rate limiter at {current_time:.3f}")

    logger.info(
        "[SEARCH] Search providers pre-warmed - cold start delay bypassed for first task"
    )


def _brave_circuit_is_open() -> bool:
    """Check if Brave circuit breaker is open. Auto-resets after cooldown."""
    global _brave_circuit_open, _brave_circuit_opened_at
    with _brave_circuit_lock:
        if not _brave_circuit_open:
            return False
        elapsed = time.time() - _brave_circuit_opened_at
        if elapsed >= _BRAVE_CIRCUIT_COOLDOWN:
            _brave_circuit_open = False
            _brave_circuit_opened_at = 0.0
            logger.info(
                f"BRAVE CIRCUIT BREAKER: Auto-reset after {elapsed:.1f}s cooldown"
            )
            return False
        return True


def _brave_circuit_trip():
    """Trip the Brave circuit breaker on 429 response."""
    global _brave_circuit_open, _brave_circuit_opened_at
    with _brave_circuit_lock:
        _brave_circuit_open = True
        _brave_circuit_opened_at = time.time()
    logger.warning(
        f"BRAVE CIRCUIT BREAKER: TRIPPED — all Brave requests will be skipped "
        f"for {_BRAVE_CIRCUIT_COOLDOWN}s"
    )


class SearchResult:
    """Standardized search result format"""

    def __init__(
        self,
        title: str,
        url: str,
        snippet: str,
        published_date: Optional[str] = None,
        source: Optional[str] = None,
    ):
        from app.utils.url_utils import extract_domain

        self.title = title
        self.url = url
        self.snippet = snippet
        self.published_date = published_date
        self.source = source or extract_domain(url, fallback="Unknown Source")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "published_date": self.published_date,
            "source": self.source,
        }


class BaseSearchProvider:
    """Base class for search providers"""

    def __init__(self):
        self.timeout = 10
        self.max_results = 10

    async def search(self, query: str, **kwargs) -> List[SearchResult]:
        """Search for query and return standardized results"""
        raise NotImplementedError


class BraveSearchProvider(BaseSearchProvider):
    """Brave Search API implementation"""

    def __init__(self):
        super().__init__()
        self.api_key = settings.BRAVE_API_KEY
        self.base_url = "https://api.search.brave.com/res/v1/web/search"
        # Request spacing to prevent concurrent requests (Brave rejects concurrent calls)
        # Using 2.5s spacing ensures each request completes before next starts
        self.request_spacing = 2.5  # seconds between requests

        # Persistent HTTP client for connection reuse
        # Prevents Brave from seeing each request as a "new client"
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create persistent HTTP client"""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
            logger.info("BRAVE: Created persistent HTTP client for connection reuse")
        return self._client

    async def close(self):
        """Close the persistent HTTP client"""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
            logger.info("BRAVE: Closed persistent HTTP client")

    async def search(self, query: str, **kwargs) -> List[SearchResult]:
        """Search using Brave Search API"""
        logger.info(
            f"[BRAVE DEBUG] search called, api_key present: {bool(self.api_key)}, api_key length: {len(self.api_key) if self.api_key else 0}"
        )
        if not self.api_key:
            logger.warning("Brave API key not configured")
            return []

        # Circuit breaker: skip Brave entirely if recently rate-limited
        if _brave_circuit_is_open():
            logger.info(
                f"BRAVE CIRCUIT BREAKER: OPEN — skipping query '{query[:60]}...'"
            )
            return []

        # RATE LIMITING: Use threading.Lock for timestamp coordination
        # Works across different event loops (Celery tasks)
        global _brave_lock, _brave_last_request_time

        # Acquire lock, calculate wait time, reserve slot, release immediately
        with _brave_lock:
            current_time = time.time()
            time_since_last = current_time - _brave_last_request_time

            # Cold start detection: First request after worker startup
            if _brave_last_request_time == 0:
                # Apply warm-up delay to prevent anti-abuse detection
                wait_time = 3.0  # 3 second warm-up (reduced from 10s to avoid claim timeout pressure)
                logger.info(
                    f"BRAVE COLD START: First request since worker startup - applying 3s warm-up delay"
                )
            elif time_since_last < self.request_spacing:
                wait_time = self.request_spacing - time_since_last
            else:
                wait_time = 0

            # Reserve this time slot by updating timestamp
            _brave_last_request_time = current_time + wait_time

        # Wait OUTSIDE the lock (doesn't block other tasks from checking)
        if wait_time > 0:
            logger.info(
                f"BRAVE RATE LIMIT: Waiting {wait_time:.3f}s (last request was {time_since_last:.3f}s ago)"
            )
            await asyncio.sleep(wait_time)
        else:
            logger.info(
                f"BRAVE RATE LIMIT: No wait needed (last request was {time_since_last:.3f}s ago)"
            )

        # Make the request (naturally serialized by timestamp reservation)
        return await self._execute_search(query, **kwargs)

    async def _execute_search(self, query: str, **kwargs) -> List[SearchResult]:
        """Execute the actual search request with exponential backoff retry on 429 errors"""
        # Freshness parameter: pd (past day), pw (past week), pm (past month), py (past year), 2y (2 years)
        # Use passed freshness or default to 2y
        freshness = kwargs.get("freshness", "2y")

        country_code = kwargs.get("country", "gb")
        params = {
            "q": query,
            "count": min(kwargs.get("max_results", self.max_results), 20),
            "freshness": freshness,
            "text_decorations": False,
            "search_lang": "en",
            "safesearch": "moderate",
            "extra_snippets": True,  # Get up to 5 snippets for better context (Pro plans only, ignored otherwise)
        }
        if country_code is not None:
            params["country"] = country_code.upper()  # Brave uses uppercase: GB, US

        if freshness != "2y":
            logger.info(
                f"BRAVE FRESHNESS: Using '{freshness}' for time-sensitive claim"
            )

        # Retry configuration
        max_retries = 3
        retry_delays = [5.0, 10.0, 20.0]  # Exponential backoff: 5s, 10s, 20s

        for attempt in range(max_retries):
            try:
                # Use persistent client instead of creating new one each time
                client = await self._get_client()
                response = await client.get(
                    self.base_url,
                    headers={
                        "Accept": "application/json",
                        "Accept-Encoding": "gzip",
                        "X-Subscription-Token": self.api_key,
                    },
                    params=params,
                )

                response.raise_for_status()
                data = response.json()

                # Success - break out of retry loop
                if attempt > 0:
                    logger.info(
                        f"BRAVE RETRY SUCCESS: Request succeeded on attempt {attempt + 1}"
                    )
                break

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    # Trip circuit breaker on first 429 — don't waste time retrying
                    _brave_circuit_trip()
                    logger.warning(
                        f"BRAVE 429: Circuit breaker tripped on query '{query[:60]}...' — "
                        f"falling through to next provider immediately"
                    )
                    return []
                else:
                    # Non-429 HTTP error - don't retry
                    raise
            except httpx.TimeoutException:
                logger.error(
                    f"BRAVE TIMEOUT | Query: '{query[:60]}...' | Attempt {attempt + 1}/{max_retries}"
                )
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delays[attempt])
                    continue
                else:
                    return []
            except Exception as e:
                # Unexpected error - don't retry
                logger.error(
                    f"BRAVE ERROR | Error: {type(e).__name__}: {e} | Query: '{query[:60]}...'"
                )
                return []

        # Process successful response (only reached if retry loop succeeded)
        try:
            # DIAGNOSTIC: Log Brave search results
            raw_results = data.get("web", {}).get("results", [])
            logger.info(
                f"BRAVE SEARCH | Query: '{query[:60]}...' | Results: {len(raw_results)}"
            )

            results = []
            for item in data.get("web", {}).get("results", []):
                # Extract published date if available
                published_date = None
                if "published_date" in item:
                    published_date = item["published_date"]
                elif "age" in item:
                    # Convert relative age to approximate date
                    published_date = self._parse_relative_date(item["age"])

                # Extract source name from Brave's profile data
                source = item.get("profile", {}).get("name")
                # Filter out invalid source values
                if source in ["", "http:", "https:", None]:
                    source = None  # Will fallback to domain extraction

                result = SearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    snippet=item.get("description", ""),
                    published_date=published_date,
                    source=source,
                )
                results.append(result)

            logger.info(f"Brave search returned {len(results)} results for: {query}")
            return results
        except Exception as e:
            logger.error(
                f"BRAVE PARSE ERROR | Error processing response: {type(e).__name__}: {e}"
            )
            return []

    def _parse_relative_date(self, age_str: str) -> Optional[str]:
        """Convert relative age to approximate ISO date"""
        try:
            # Simple parsing for "X days ago", "X weeks ago", etc.
            if "day" in age_str:
                days = int(age_str.split()[0])
                date = datetime.now() - timedelta(days=days)
            elif "week" in age_str:
                weeks = int(age_str.split()[0])
                date = datetime.now() - timedelta(weeks=weeks)
            elif "month" in age_str:
                months = int(age_str.split()[0])
                date = datetime.now() - timedelta(days=months * 30)
            else:
                return None

            return date.isoformat()[:10]  # YYYY-MM-DD format
        except:
            return None


class SerpAPIProvider(BaseSearchProvider):
    """SerpAPI Google Search implementation"""

    # Mapping from Brave freshness to Google tbs parameter
    FRESHNESS_TO_TBS = {
        "pd": "qdr:d",  # past day
        "pw": "qdr:w",  # past week
        "pm": "qdr:m",  # past month
        "py": "qdr:y",  # past year
        "2y": "qdr:y2",  # 2 years (default)
    }

    def __init__(self):
        super().__init__()
        self.api_key = settings.SERP_API_KEY
        self.base_url = "https://serpapi.com/search"
        # Request spacing to prevent concurrent requests
        # Using same spacing as Brave for consistency
        self.request_spacing = 2.5  # seconds between requests

        # Persistent HTTP client for connection reuse
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create persistent HTTP client"""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
            logger.info("SERPAPI: Created persistent HTTP client for connection reuse")
        return self._client

    async def close(self):
        """Close the persistent HTTP client"""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
            logger.info("SERPAPI: Closed persistent HTTP client")

    async def search(self, query: str, **kwargs) -> List[SearchResult]:
        """Search using SerpAPI Google Search"""
        if not self.api_key:
            logger.warning("SerpAPI key not configured")
            return []

        # RATE LIMITING: Use threading.Lock for timestamp coordination
        # Works across different event loops (Celery tasks)
        global _serpapi_lock, _serpapi_last_request_time

        # Acquire lock, calculate wait time, reserve slot, release immediately
        with _serpapi_lock:
            current_time = time.time()
            time_since_last = current_time - _serpapi_last_request_time

            # Cold start detection: First request after worker startup
            if _serpapi_last_request_time == 0:
                # Apply warm-up delay to prevent anti-abuse detection
                wait_time = 10.0  # 10 second warm-up
                logger.info(
                    f"SERPAPI COLD START: First request since worker startup - applying 10s warm-up delay"
                )
            elif time_since_last < self.request_spacing:
                wait_time = self.request_spacing - time_since_last
            else:
                wait_time = 0

            # Reserve this time slot by updating timestamp
            _serpapi_last_request_time = current_time + wait_time

        # Wait OUTSIDE the lock (doesn't block other tasks from checking)
        if wait_time > 0:
            logger.info(
                f"SERPAPI RATE LIMIT: Waiting {wait_time:.3f}s (last request was {time_since_last:.3f}s ago)"
            )
            await asyncio.sleep(wait_time)
        else:
            logger.info(
                f"SERPAPI RATE LIMIT: No wait needed (last request was {time_since_last:.3f}s ago)"
            )

        # Make the request (naturally serialized by timestamp reservation)
        return await self._execute_search(query, **kwargs)

    async def _execute_search(self, query: str, **kwargs) -> List[SearchResult]:
        """Execute the actual search request (called within rate limit lock)"""
        try:
            # Map freshness parameter to Google tbs format
            freshness = kwargs.get("freshness", "2y")
            tbs_value = self.FRESHNESS_TO_TBS.get(freshness, "qdr:y2")

            country_code = kwargs.get("country", "gb")
            params = {
                "q": query,
                "engine": "google",
                "api_key": self.api_key,
                "num": min(kwargs.get("max_results", self.max_results), 20),
                "hl": "en",
                "tbs": tbs_value,
            }
            if country_code is not None:
                params["gl"] = country_code.lower()

            # Use persistent client instead of creating new one each time
            client = await self._get_client()
            response = await client.get(self.base_url, params=params)
            response.raise_for_status()
            data = response.json()

            # DIAGNOSTIC: Log SerpAPI search results
            raw_results = data.get("organic_results", [])
            logger.info(
                f"SERPAPI SEARCH | Query: '{query[:60]}...' | Results: {len(raw_results)}"
            )

            results = []
            for item in data.get("organic_results", []):
                # Extract date from various fields
                published_date = None
                if "date" in item:
                    published_date = item["date"]
                elif "displayed_date" in item:
                    published_date = item["displayed_date"]

                # Extract source properly from displayed_link (e.g., "example.com/path" -> "example.com")
                displayed_link = item.get("displayed_link", "")
                source = None
                if displayed_link and "/" in displayed_link:
                    # Remove protocol and get domain (e.g., "https://example.com" -> "example.com")
                    source = (
                        displayed_link.split("//")[-1].split("/")[0]
                        if "//" in displayed_link
                        else displayed_link.split("/")[0]
                    )

                result = SearchResult(
                    title=item.get("title", ""),
                    url=item.get("link", ""),
                    snippet=item.get("snippet", ""),
                    published_date=published_date,
                    source=source,
                )
                results.append(result)

            logger.info(f"SerpAPI returned {len(results)} results for: {query}")
            return results

        except httpx.TimeoutException:
            logger.error(f"SERPAPI TIMEOUT | Query: '{query[:60]}...'")
            return []
        except httpx.HTTPStatusError as e:
            # Enhanced logging for rate limit debugging
            status = e.response.status_code
            headers = e.response.headers

            # Log basic error
            logger.error(
                f"SERPAPI HTTP ERROR | Status: {status} | Query: '{query[:60]}...'"
            )

            # Log rate limit headers if present (especially important for 429 errors)
            if status == 429:
                retry_after = headers.get("Retry-After", "not provided")
                rate_limit = headers.get(
                    "X-RateLimit-Limit", headers.get("RateLimit-Limit", "not provided")
                )
                rate_remaining = headers.get(
                    "X-RateLimit-Remaining",
                    headers.get("RateLimit-Remaining", "not provided"),
                )
                rate_reset = headers.get(
                    "X-RateLimit-Reset", headers.get("RateLimit-Reset", "not provided")
                )

                logger.error(
                    f"SERPAPI RATE LIMIT | Retry-After: {retry_after} | Limit: {rate_limit} | Remaining: {rate_remaining} | Reset: {rate_reset}"
                )

                # Log session context for cold-start debugging
                global _serpapi_last_request_time
                time_since_worker_start = time.time() - _MODULE_LOAD_TIME
                logger.error(
                    f"SERPAPI SESSION | Worker uptime: {time_since_worker_start:.1f}s | Last request was: {time.time() - _serpapi_last_request_time:.1f}s ago"
                )

            return []
        except Exception as e:
            logger.error(
                f"SERPAPI ERROR | Error: {type(e).__name__}: {e} | Query: '{query[:60]}...'"
            )
            return []


class SerperProvider(BaseSearchProvider):
    """Serper.dev Google Search implementation (high-throughput secondary provider)"""

    # Reuse same freshness-to-tbs mapping as SerpAPI
    FRESHNESS_TO_TBS = {
        "pd": "qdr:d",  # past day
        "pw": "qdr:w",  # past week
        "pm": "qdr:m",  # past month
        "py": "qdr:y",  # past year
        "2y": "qdr:y2",  # 2 years (default)
    }

    def __init__(self):
        super().__init__()
        self.api_key = settings.SERPER_API_KEY
        self.base_url = "https://google.serper.dev/search"
        self.request_spacing = 0.1  # 300 req/sec API limit

        # Persistent HTTP client for connection reuse
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create persistent HTTP client"""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
            logger.info("SERPER: Created persistent HTTP client for connection reuse")
        return self._client

    async def close(self):
        """Close the persistent HTTP client"""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
            logger.info("SERPER: Closed persistent HTTP client")

    async def search(self, query: str, **kwargs) -> List[SearchResult]:
        """Search using Serper.dev Google Search"""
        if not self.api_key:
            logger.warning("Serper API key not configured")
            return []

        # RATE LIMITING
        global _serper_lock, _serper_last_request_time

        with _serper_lock:
            current_time = time.time()
            time_since_last = current_time - _serper_last_request_time

            if time_since_last < self.request_spacing:
                wait_time = self.request_spacing - time_since_last
            else:
                wait_time = 0

            _serper_last_request_time = current_time + wait_time

        if wait_time > 0:
            await asyncio.sleep(wait_time)

        return await self._execute_search(query, **kwargs)

    async def _execute_search(self, query: str, **kwargs) -> List[SearchResult]:
        """Execute the actual search request"""
        try:
            freshness = kwargs.get("freshness", "2y")
            tbs_value = self.FRESHNESS_TO_TBS.get(freshness, "qdr:y2")

            country_code = kwargs.get("country", "gb")
            payload = {
                "q": query,
                "num": min(kwargs.get("max_results", self.max_results), 20),
                "hl": "en",
                "tbs": tbs_value,
            }
            if country_code is not None:
                payload["gl"] = country_code.lower()

            client = await self._get_client()
            response = await client.post(
                self.base_url,
                headers={
                    "X-API-KEY": self.api_key,
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

            raw_results = data.get("organic", [])
            logger.info(
                f"SERPER SEARCH | Query: '{query[:60]}...' | Results: {len(raw_results)}"
            )

            results = []
            for item in raw_results:
                published_date = item.get("date")

                result = SearchResult(
                    title=item.get("title", ""),
                    url=item.get("link", ""),
                    snippet=item.get("snippet", ""),
                    published_date=published_date,
                )
                results.append(result)

            logger.info(f"Serper returned {len(results)} results for: {query}")
            return results

        except httpx.TimeoutException:
            logger.error(f"SERPER TIMEOUT | Query: '{query[:60]}...'")
            return []
        except httpx.HTTPStatusError as e:
            logger.error(
                f"SERPER HTTP ERROR | Status: {e.response.status_code} | "
                f"Query: '{query[:60]}...'"
            )
            return []
        except Exception as e:
            logger.error(
                f"SERPER ERROR | Error: {type(e).__name__}: {e} | Query: '{query[:60]}...'"
            )
            return []


class SearchService:
    """Main search service with provider fallback"""

    def __init__(self):
        self.providers = []

        # Initialize available providers: Serper (primary) > Brave (secondary) > SerpAPI (tertiary)
        if settings.SERPER_API_KEY:
            self.providers.append(SerperProvider())
        if settings.BRAVE_API_KEY:
            self.providers.append(BraveSearchProvider())
        if settings.SERP_API_KEY:
            self.providers.append(SerpAPIProvider())

        if not self.providers:
            logger.warning("No search providers configured")

    async def search_for_evidence(
        self,
        claim: str,
        max_results: int = 10,
        freshness: str = None,
        country: Optional[str] = "gb",
    ) -> List[SearchResult]:
        """Search for evidence supporting/contradicting a claim

        Args:
            claim: The claim text to search for
            max_results: Maximum number of results to return
            freshness: Brave freshness filter - pd (day), pw (week), pm (month), py (year), 2y (default)
            country: 2-letter country code for geo-localisation, or None to omit filter
        """
        # Optimize search query for fact-checking
        query = self._optimize_query_for_factcheck(claim)

        # DIAGNOSTIC: Log search initiation with full query details
        freshness_str = f" | Freshness: {freshness}" if freshness else ""
        country_str = f" | Country: {country}" if country else " | Country: (none)"
        has_exclusions = "-site:" in query
        logger.info(
            f"SEARCH INITIATED | Claim: '{claim[:60]}...' | Max: {max_results}{freshness_str}{country_str}"
        )
        logger.info(f"SEARCH QUERY: '{query}'")
        logger.info(
            f"Providers available: {[p.__class__.__name__ for p in self.providers]}"
        )

        # Try providers in order until we get results
        results = await self._try_providers(
            query, max_results, freshness, country=country
        )

        if results:
            return results

        # FALLBACK: If 0 results with exclusions, retry without exclusions
        if has_exclusions:
            simple_query = self._get_query_without_exclusions(query)
            logger.warning(
                f"0 RESULTS FALLBACK: Retrying without exclusions | New query: '{simple_query}'"
            )

            results = await self._try_providers(
                simple_query, max_results, freshness, country=country
            )

            if results:
                logger.info(
                    f"FALLBACK SUCCESS: Got {len(results)} results without exclusions"
                )
                return results

        logger.warning(f"ALL PROVIDERS FAILED for claim: {claim[:50]}...")
        return []

    async def _try_providers(
        self,
        query: str,
        max_results: int,
        freshness: str = None,
        country: Optional[str] = "gb",
    ) -> List[SearchResult]:
        """Try each search provider in order until we get results"""
        for i, provider in enumerate(self.providers):
            provider_name = provider.__class__.__name__
            try:
                logger.info(
                    f"Trying provider {i+1}/{len(self.providers)}: {provider_name}"
                )
                search_kwargs = {"max_results": max_results}
                if freshness:
                    search_kwargs["freshness"] = freshness
                if country is not None:
                    search_kwargs["country"] = country
                results = await provider.search(query, **search_kwargs)

                if results:
                    logger.info(f"{provider_name} SUCCESS: {len(results)} results")
                    return results[:max_results]
                else:
                    logger.warning(
                        f"{provider_name} returned 0 results | Query: '{query[:80]}...'"
                    )
            except Exception as e:
                logger.error(f"{provider_name} FAILED: {e}, trying next provider...")
                continue

        return []

    def _get_query_without_exclusions(self, query: str) -> str:
        """Remove exclusion terms (-site:, -"term") from query for fallback"""
        words = query.split()
        # Keep only non-exclusion words
        clean_words = [w for w in words if not w.startswith("-")]
        return " ".join(clean_words).strip()

    def _optimize_query_for_factcheck(self, claim: str) -> str:
        """Optimize search query for better fact-checking results"""
        query = claim

        # STEP 1: Strip procedural negative phrases (unverifiable)
        # These phrases describe actions NOT taken, which are nearly impossible to verify
        negative_patterns = [
            r"\s+without\s+\w+ing\b.*",  # "without consulting...", "without notifying..."
            r"\s+failed to\s+\w+\b.*",  # "failed to notify...", "failed to consult..."
            r"\s+did not\s+\w+\b.*",  # "did not consider...", "did not consult..."
            r"\s+didn\'?t\s+\w+\b.*",  # "didn't notify...", "didn't consult..."
            r"\s+never\s+\w+ed\b.*",  # "never consulted...", "never notified..."
            r"\s+refused to\s+\w+\b.*",  # "refused to consult...", "refused to notify..."
        ]

        original_query = query
        for pattern in negative_patterns:
            query = re.sub(pattern, "", query, flags=re.IGNORECASE)

        # Log if we stripped procedural negatives
        if query != original_query:
            logger.info(f"QUERY OPTIMIZATION: Stripped procedural negatives")
            logger.info(f"   Original: {original_query[:100]}...")
            logger.info(f"   Optimized: {query[:100]}...")

        # STEP 2: Remove filler words that don't help search
        filler_words = [
            "claimed",
            "stated",
            "said",
            "allegedly",
            "reportedly",
            "according to",
        ]
        for word in filler_words:
            query = re.sub(
                r"\b" + re.escape(word) + r"\b", "", query, flags=re.IGNORECASE
            )

        # STEP 3: Remove question marks and exclamation marks
        query = query.replace("?", "").replace("!", "")

        # STEP 4: Clean up extra whitespace
        query = re.sub(r"\s+", " ", query).strip()

        # STEP 5: Add exclusions ONLY if not already present (avoid duplicates from query_formulation.py)
        # These exclusions may already be in the query from upstream processing
        exclude_terms = [
            "-site:snopes.com",
            "-site:factcheck.org",
            "-site:politifact.com",
            "-site:wikipedia.org",  # Reference encyclopedia, not evidence - wastes search slots
        ]

        # Only add exclusions that aren't already present
        for term in exclude_terms:
            if term not in query:
                query += " " + term

        # STEP 6: Limit query length for API limits - PRIORITIZE CLAIM KEYWORDS
        if len(query) > 250:
            words = query.split()
            # Separate claim words from exclusions
            core_words = [w for w in words if not w.startswith("-")]
            exclude_words = [w for w in words if w.startswith("-")]

            # Dedupe exclusions (keep unique only)
            exclude_words = list(dict.fromkeys(exclude_words))

            # PRIORITIZE: Keep as many claim words as possible, limit exclusions to 3
            max_exclusions = 3
            truncated_excludes = exclude_words[:max_exclusions]

            # Calculate remaining space for claim words
            exclude_chars = sum(len(w) + 1 for w in truncated_excludes)
            remaining_chars = 250 - exclude_chars

            # Keep claim words up to the remaining character limit
            kept_words = []
            char_count = 0
            for w in core_words:
                if char_count + len(w) + 1 <= remaining_chars:
                    kept_words.append(w)
                    char_count += len(w) + 1
                else:
                    break

            query = " ".join(kept_words + truncated_excludes)
            logger.debug(
                f"QUERY TRUNCATED: {len(core_words)} words -> {len(kept_words)} words, {len(exclude_words)} exclusions -> {len(truncated_excludes)}"
            )

        return query.strip()
