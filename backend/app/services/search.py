import logging
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import httpx
from urllib.parse import quote_plus
from app.core.config import settings

logger = logging.getLogger(__name__)

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
    
    async def search(self, query: str, **kwargs) -> List[SearchResult]:
        """Search using Brave Search API"""
        if not self.api_key:
            logger.warning("Brave API key not configured")
            return []
        
        try:
            # Filter for recent content (last 2 years as per project requirements)
            params = {
                "q": query,
                "count": min(kwargs.get("max_results", self.max_results), 20),
                "freshness": "2y",  # Last 2 years
                "text_decorations": False,
                "search_lang": "en",
                "country": "GB",  # UK focus for Tru8
                "safesearch": "moderate"
            }
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
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
                
        except httpx.TimeoutException:
            logger.error("Brave search timeout")
            return []
        except httpx.HTTPStatusError as e:
            logger.error(f"Brave search HTTP error {e.response.status_code}: {e}")
            return []
        except Exception as e:
            logger.error(f"Brave search error: {e}")
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
    
    async def search(self, query: str, **kwargs) -> List[SearchResult]:
        """Search using SerpAPI Google Search"""
        if not self.api_key:
            logger.warning("SerpAPI key not configured")
            return []
        
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
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(self.base_url, params=params)
                response.raise_for_status()
                data = response.json()
                
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
            logger.error("SerpAPI timeout")
            return []
        except httpx.HTTPStatusError as e:
            logger.error(f"SerpAPI HTTP error {e.response.status_code}: {e}")
            return []
        except Exception as e:
            logger.error(f"SerpAPI error: {e}")
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
        
        # Try providers in order until we get results
        for provider in self.providers:
            try:
                results = await provider.search(query, max_results=max_results)
                if results:
                    # Filter for credible sources
                    filtered_results = self._filter_credible_sources(results)
                    logger.info(f"Found {len(filtered_results)} credible sources for claim")
                    return filtered_results[:max_results]
            except Exception as e:
                logger.error(f"Provider {provider.__class__.__name__} failed: {e}")
                continue
        
        logger.warning(f"No search results found for claim: {claim[:50]}...")
        return []
    
    def _optimize_query_for_factcheck(self, claim: str) -> str:
        """Optimize search query for better fact-checking results"""
        # Extract key terms and add fact-checking keywords
        query = claim

        # Add fact-checking terms to improve result quality
        factcheck_terms = [
            "study", "research", "report", "data", "statistics",
            "official", "government", "university", "peer reviewed"
        ]

        # Remove question words and make it more search-friendly
        query = query.replace("?", "").replace("!", "")

        # Exclude fact-check meta-content sites to prefer primary sources
        # Use negative keywords to filter out fact-checking articles about other claims
        exclude_terms = [
            "-site:snopes.com",
            "-site:factcheck.org",
            "-site:politifact.com",
            "-\"fact check\"",
            "-\"fact-check\""
        ]
        query += " " + " ".join(exclude_terms)

        # Limit query length for API limits
        if len(query) > 250:
            words = query.split()
            query = " ".join(words[:35])  # First 35 words including exclusions

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