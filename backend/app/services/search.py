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

# CODE RELOAD CHECK: This timestamp proves the module was reloaded
_MODULE_LOAD_TIME = time.time()

# Write to file (works even if logger isn't configured)
import pathlib
_reload_marker = pathlib.Path(__file__).parent.parent.parent / "MODULE_RELOADED.txt"
_reload_marker.write_text(f"search.py loaded at {_MODULE_LOAD_TIME}\nRate limiting ACTIVE\n")

logger.critical(f"search.py MODULE LOADED at {_MODULE_LOAD_TIME} - Rate limiting ACTIVE")

# GLOBAL rate limiters to prevent concurrent burst across all concurrent claims
# Using threading.Lock for timestamp coordination (works across event loops)
_brave_lock = threading.Lock()
_brave_last_request_time = 0
_serpapi_lock = threading.Lock()
_serpapi_last_request_time = 0

class SearchResult:
    """Standardized search result format"""
    def __init__(self, title: str, url: str, snippet: str,
                 published_date: Optional[str] = None, source: Optional[str] = None):
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
            "source": self.source
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
        if not self.api_key:
            logger.warning("Brave API key not configured")
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
                wait_time = 10.0  # 10 second warm-up
                logger.info(f"BRAVE COLD START: First request since worker startup - applying 10s warm-up delay")
            elif time_since_last < self.request_spacing:
                wait_time = self.request_spacing - time_since_last
            else:
                wait_time = 0

            # Reserve this time slot by updating timestamp
            _brave_last_request_time = current_time + wait_time

        # Wait OUTSIDE the lock (doesn't block other tasks from checking)
        if wait_time > 0:
            logger.info(f"BRAVE RATE LIMIT: Waiting {wait_time:.3f}s (last request was {time_since_last:.3f}s ago)")
            await asyncio.sleep(wait_time)
        else:
            logger.info(f"BRAVE RATE LIMIT: No wait needed (last request was {time_since_last:.3f}s ago)")

        # Make the request (naturally serialized by timestamp reservation)
        return await self._execute_search(query, **kwargs)

    async def _execute_search(self, query: str, **kwargs) -> List[SearchResult]:
        """Execute the actual search request with exponential backoff retry on 429 errors"""
        # Filter for recent content (last 2 years as per project requirements)
        params = {
            "q": query,
            "count": min(kwargs.get("max_results", self.max_results), 20),
            "freshness": "2y",  # Last 2 years
            "text_decorations": False,
            "search_lang": "en",
            "country": "GB",  # UK focus for Tru8
            "safesearch": "moderate",
            "extra_snippets": True  # Get up to 5 snippets for better context (Pro plans only, ignored otherwise)
        }

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
                        "X-Subscription-Token": self.api_key
                    },
                    params=params
                )

                response.raise_for_status()
                data = response.json()

                # Success - break out of retry loop
                if attempt > 0:
                    logger.info(f"BRAVE RETRY SUCCESS: Request succeeded on attempt {attempt + 1}")
                break

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    # Rate limit error - retry with exponential backoff
                    if attempt < max_retries - 1:
                        # Extract retry delay from Retry-After header if present
                        retry_after = e.response.headers.get('Retry-After')
                        if retry_after and retry_after.isdigit():
                            delay = float(retry_after)
                        else:
                            delay = retry_delays[attempt]

                        logger.warning(
                            f"BRAVE RETRY: 429 on attempt {attempt + 1}/{max_retries}. "
                            f"Retrying after {delay}s..."
                        )
                        await asyncio.sleep(delay)
                        continue
                    else:
                        # Final attempt failed - log and raise
                        logger.error(
                            f"BRAVE RETRY FAILED: All {max_retries} attempts exhausted with 429 errors"
                        )
                        raise
                else:
                    # Non-429 HTTP error - don't retry
                    raise
            except httpx.TimeoutException:
                logger.error(f"BRAVE TIMEOUT | Query: '{query[:60]}...' | Attempt {attempt + 1}/{max_retries}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delays[attempt])
                    continue
                else:
                    return []
            except Exception as e:
                # Unexpected error - don't retry
                logger.error(f"BRAVE ERROR | Error: {type(e).__name__}: {e} | Query: '{query[:60]}...'")
                return []

        # Process successful response (only reached if retry loop succeeded)
        try:
            # DIAGNOSTIC: Log Brave search results
            raw_results = data.get("web", {}).get("results", [])
            logger.info(f"BRAVE SEARCH | Query: '{query[:60]}...' | Results: {len(raw_results)}")

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
                if source in ['', 'http:', 'https:', None]:
                    source = None  # Will fallback to domain extraction

                result = SearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    snippet=item.get("description", ""),
                    published_date=published_date,
                    source=source
                )
                results.append(result)

            logger.info(f"Brave search returned {len(results)} results for: {query}")
            return results
        except Exception as e:
            logger.error(f"BRAVE PARSE ERROR | Error processing response: {type(e).__name__}: {e}")
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
                date = datetime.now() - timedelta(days=months*30)
            else:
                return None
            
            return date.isoformat()[:10]  # YYYY-MM-DD format
        except:
            return None

class SerpAPIProvider(BaseSearchProvider):
    """SerpAPI Google Search implementation"""

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
                logger.info(f"SERPAPI COLD START: First request since worker startup - applying 10s warm-up delay")
            elif time_since_last < self.request_spacing:
                wait_time = self.request_spacing - time_since_last
            else:
                wait_time = 0

            # Reserve this time slot by updating timestamp
            _serpapi_last_request_time = current_time + wait_time

        # Wait OUTSIDE the lock (doesn't block other tasks from checking)
        if wait_time > 0:
            logger.info(f"SERPAPI RATE LIMIT: Waiting {wait_time:.3f}s (last request was {time_since_last:.3f}s ago)")
            await asyncio.sleep(wait_time)
        else:
            logger.info(f"SERPAPI RATE LIMIT: No wait needed (last request was {time_since_last:.3f}s ago)")

        # Make the request (naturally serialized by timestamp reservation)
        return await self._execute_search(query, **kwargs)

    async def _execute_search(self, query: str, **kwargs) -> List[SearchResult]:
        """Execute the actual search request (called within rate limit lock)"""
        try:
            params = {
                "q": query,
                "engine": "google",
                "api_key": self.api_key,
                "num": min(kwargs.get("max_results", self.max_results), 20),
                "gl": "gb",  # UK geolocation
                "hl": "en",  # English language
                "tbs": "qdr:y2"  # Last 2 years
            }

            # Use persistent client instead of creating new one each time
            client = await self._get_client()
            response = await client.get(self.base_url, params=params)
            response.raise_for_status()
            data = response.json()

            # DIAGNOSTIC: Log SerpAPI search results
            raw_results = data.get("organic_results", [])
            logger.info(f"SERPAPI SEARCH | Query: '{query[:60]}...' | Results: {len(raw_results)}")

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
                    source = displayed_link.split("//")[-1].split("/")[0] if "//" in displayed_link else displayed_link.split("/")[0]

                result = SearchResult(
                    title=item.get("title", ""),
                    url=item.get("link", ""),
                    snippet=item.get("snippet", ""),
                    published_date=published_date,
                    source=source
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
            logger.error(f"SERPAPI HTTP ERROR | Status: {status} | Query: '{query[:60]}...'")

            # Log rate limit headers if present (especially important for 429 errors)
            if status == 429:
                retry_after = headers.get('Retry-After', 'not provided')
                rate_limit = headers.get('X-RateLimit-Limit', headers.get('RateLimit-Limit', 'not provided'))
                rate_remaining = headers.get('X-RateLimit-Remaining', headers.get('RateLimit-Remaining', 'not provided'))
                rate_reset = headers.get('X-RateLimit-Reset', headers.get('RateLimit-Reset', 'not provided'))

                logger.error(f"SERPAPI RATE LIMIT | Retry-After: {retry_after} | Limit: {rate_limit} | Remaining: {rate_remaining} | Reset: {rate_reset}")

                # Log session context for cold-start debugging
                global _serpapi_last_request_time
                time_since_worker_start = time.time() - _MODULE_LOAD_TIME
                logger.error(f"SERPAPI SESSION | Worker uptime: {time_since_worker_start:.1f}s | Last request was: {time.time() - _serpapi_last_request_time:.1f}s ago")

            return []
        except Exception as e:
            logger.error(f"SERPAPI ERROR | Error: {type(e).__name__}: {e} | Query: '{query[:60]}...'")
            return []

class SearchService:
    """Main search service with provider fallback"""
    
    def __init__(self):
        self.providers = []
        
        # Initialize available providers
        if settings.BRAVE_API_KEY:
            self.providers.append(BraveSearchProvider())
        if settings.SERP_API_KEY:
            self.providers.append(SerpAPIProvider())
        
        if not self.providers:
            logger.warning("No search providers configured")
    
    async def search_for_evidence(self, claim: str, max_results: int = 10) -> List[SearchResult]:
        """Search for evidence supporting/contradicting a claim"""
        # Optimize search query for fact-checking
        query = self._optimize_query_for_factcheck(claim)

        # DIAGNOSTIC: Log search initiation
        logger.info(f"SEARCH INITIATED | Claim: '{claim[:60]}...' | Query: '{query[:80]}...' | Max: {max_results}")
        logger.info(f"Providers available: {[p.__class__.__name__ for p in self.providers]}")

        # Try providers in order until we get results
        for i, provider in enumerate(self.providers):
            provider_name = provider.__class__.__name__
            try:
                logger.info(f"Trying provider {i+1}/{len(self.providers)}: {provider_name}")
                results = await provider.search(query, max_results=max_results)

                if results:
                    # Filter for credible sources
                    filtered_results = self._filter_credible_sources(results)
                    logger.info(f"{provider_name} SUCCESS: {len(results)} raw results -> {len(filtered_results)} after filtering")
                    return filtered_results[:max_results]
                else:
                    logger.warning(f"{provider_name} returned 0 results, trying next provider...")
            except Exception as e:
                logger.error(f"{provider_name} FAILED: {e}, trying next provider...")
                continue

        logger.warning(f"ALL PROVIDERS FAILED for claim: {claim[:50]}...")
        return []
    
    def _optimize_query_for_factcheck(self, claim: str) -> str:
        """Optimize search query for better fact-checking results"""
        query = claim

        # STEP 1: Strip procedural negative phrases (unverifiable)
        # These phrases describe actions NOT taken, which are nearly impossible to verify
        negative_patterns = [
            r'\s+without\s+\w+ing\b.*',  # "without consulting...", "without notifying..."
            r'\s+failed to\s+\w+\b.*',   # "failed to notify...", "failed to consult..."
            r'\s+did not\s+\w+\b.*',     # "did not consider...", "did not consult..."
            r'\s+didn\'?t\s+\w+\b.*',    # "didn't notify...", "didn't consult..."
            r'\s+never\s+\w+ed\b.*',     # "never consulted...", "never notified..."
            r'\s+refused to\s+\w+\b.*',  # "refused to consult...", "refused to notify..."
        ]

        original_query = query
        for pattern in negative_patterns:
            query = re.sub(pattern, '', query, flags=re.IGNORECASE)

        # Log if we stripped procedural negatives
        if query != original_query:
            logger.info(f"QUERY OPTIMIZATION: Stripped procedural negatives")
            logger.info(f"   Original: {original_query[:100]}...")
            logger.info(f"   Optimized: {query[:100]}...")

        # STEP 2: Remove filler words that don't help search
        filler_words = ['claimed', 'stated', 'said', 'allegedly', 'reportedly', 'according to']
        for word in filler_words:
            query = re.sub(r'\b' + re.escape(word) + r'\b', '', query, flags=re.IGNORECASE)

        # STEP 3: Remove question marks and exclamation marks
        query = query.replace("?", "").replace("!", "")

        # STEP 4: Clean up extra whitespace
        query = re.sub(r'\s+', ' ', query).strip()

        # STEP 5: Add credibility-boosting terms (helps surface official sources)
        # Note: Only add if query is short enough
        boost_terms = []
        if len(query) < 150:
            boost_terms = ["official", "report"]

        # STEP 6: Exclude fact-check meta-content sites to prefer primary sources
        exclude_terms = [
            "-site:snopes.com",
            "-site:factcheck.org",
            "-site:politifact.com",
            "-\"fact check\"",
            "-\"fact-check\""
        ]

        # Combine all parts
        if boost_terms:
            query = f"{query} {' '.join(boost_terms)}"
        query += " " + " ".join(exclude_terms)

        # STEP 7: Limit query length for API limits
        if len(query) > 250:
            words = query.split()
            # Keep core claim + exclusions (exclude terms are at the end)
            core_words = [w for w in words if not w.startswith('-')][:25]
            exclude_words = [w for w in words if w.startswith('-')]
            query = " ".join(core_words + exclude_words)

        return query.strip()
    
    def _filter_credible_sources(self, results: List[SearchResult]) -> List[SearchResult]:
        """Filter for more credible sources"""
        # List of generally credible domains (can be expanded)
        credible_domains = {
            'bbc.co.uk', 'bbc.com',
            'reuters.com',
            'ap.org', 'apnews.com',
            'nature.com',
            'science.org',
            'gov.uk', 'gov',
            'who.int',
            'nhs.uk',
            'guardian.com', 'theguardian.com',
            'telegraph.co.uk',
            'independent.co.uk',
            'economist.com',
            'ft.com', 'financial-times.com'
        }
        
        # Academic domains pattern
        academic_patterns = ['.edu', '.ac.uk', '.org']
        
        filtered = []
        for result in results:
            domain = result.source.lower()
            
            # Check if domain is in credible list or matches academic pattern
            is_credible = (
                any(cred_domain in domain for cred_domain in credible_domains) or
                any(pattern in domain for pattern in academic_patterns)
            )
            
            if is_credible:
                filtered.append(result)
            else:
                # Still include non-credible sources but mark them
                result.credibility_score = 0.5  # Lower credibility
                filtered.append(result)
        
        return filtered