import logging
import asyncio
import json
import hashlib
from typing import Any, Optional, Dict, List, Union
from datetime import datetime, timedelta
import redis.asyncio as redis
from app.core.config import settings

logger = logging.getLogger(__name__)

class CacheService:
    """Redis-based caching service for expensive operations"""
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.default_ttl = settings.CACHE_TTL_SECONDS  # From config
        self.key_prefix = "tru8:"
        
        # TTL configurations for different types of data
        self.ttl_config = {
            "search_results": 3600,      # 1 hour
            "evidence_extract": 3600 * 24,  # 1 day
            "claim_extract": 3600 * 6,   # 6 hours
            "embeddings": 3600 * 24 * 7, # 1 week
            "url_content": 3600 * 12,    # 12 hours
            "pipeline_result": 3600 * 24 * 3,  # 3 days
        }
    
    async def initialize(self):
        """Initialize Redis connection"""
        if self.redis_client is None:
            try:
                self.redis_client = redis.from_url(
                    settings.REDIS_URL,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5
                )
                # Test connection
                await self.redis_client.ping()
                logger.info("Cache service initialized")
            except Exception as e:
                logger.error(f"Failed to initialize cache service: {e}")
                self.redis_client = None
    
    def _make_key(self, category: str, identifier: str) -> str:
        """Create a standardized cache key"""
        return f"{self.key_prefix}{category}:{identifier}"
    
    def _hash_content(self, content: Any) -> str:
        """Create a hash from content for cache key"""
        if isinstance(content, dict):
            content_str = json.dumps(content, sort_keys=True)
        else:
            content_str = str(content)
        return hashlib.md5(content_str.encode()).hexdigest()
    
    async def get(self, category: str, identifier: str) -> Optional[Any]:
        """Get cached data"""
        await self.initialize()
        if not self.redis_client:
            return None
        
        try:
            key = self._make_key(category, identifier)
            data = await self.redis_client.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.warning(f"Cache get error for {category}:{identifier}: {e}")
            return None
    
    async def set(self, category: str, identifier: str, data: Any, ttl: Optional[int] = None) -> bool:
        """Set cached data with TTL"""
        await self.initialize()
        if not self.redis_client:
            return False
        
        try:
            key = self._make_key(category, identifier)
            ttl = ttl or self.ttl_config.get(category, self.default_ttl)
            
            serialized_data = json.dumps(data, default=str)  # Handle datetime objects
            await self.redis_client.setex(key, ttl, serialized_data)
            return True
        except Exception as e:
            logger.warning(f"Cache set error for {category}:{identifier}: {e}")
            return False
    
    async def delete(self, category: str, identifier: str) -> bool:
        """Delete cached data"""
        await self.initialize()
        if not self.redis_client:
            return False
        
        try:
            key = self._make_key(category, identifier)
            result = await self.redis_client.delete(key)
            return result > 0
        except Exception as e:
            logger.warning(f"Cache delete error for {category}:{identifier}: {e}")
            return False
    
    async def exists(self, category: str, identifier: str) -> bool:
        """Check if key exists in cache"""
        await self.initialize()
        if not self.redis_client:
            return False
        
        try:
            key = self._make_key(category, identifier)
            result = await self.redis_client.exists(key)
            return result > 0
        except Exception as e:
            logger.warning(f"Cache exists error for {category}:{identifier}: {e}")
            return False
    
    async def get_or_set(self, category: str, identifier: str, 
                        fetch_function, ttl: Optional[int] = None) -> Any:
        """Get from cache or fetch and set if not exists"""
        # Try to get from cache first
        cached_data = await self.get(category, identifier)
        if cached_data is not None:
            return cached_data
        
        # Fetch new data
        try:
            if asyncio.iscoroutinefunction(fetch_function):
                new_data = await fetch_function()
            else:
                new_data = fetch_function()
            
            # Cache the new data
            await self.set(category, identifier, new_data, ttl)
            return new_data
        except Exception as e:
            logger.error(f"Fetch function failed for {category}:{identifier}: {e}")
            return None
    
    # Specialized methods for fact-checking pipeline
    
    async def cache_search_results(self, query: str, provider: str, results: List[Dict]) -> bool:
        """Cache search results"""
        identifier = f"{provider}:{self._hash_content(query)}"
        return await self.set("search_results", identifier, results)
    
    async def get_cached_search_results(self, query: str, provider: str) -> Optional[List[Dict]]:
        """Get cached search results"""
        identifier = f"{provider}:{self._hash_content(query)}"
        return await self.get("search_results", identifier)
    
    async def cache_url_content(self, url: str, content_data: Dict) -> bool:
        """Cache extracted URL content"""
        identifier = self._hash_content(url)
        return await self.set("url_content", identifier, content_data)
    
    async def get_cached_url_content(self, url: str) -> Optional[Dict]:
        """Get cached URL content"""
        identifier = self._hash_content(url)
        return await self.get("url_content", identifier)
    
    async def cache_claim_extraction(self, content: str, model: str, claims: List[Dict]) -> bool:
        """Cache claim extraction results"""
        identifier = f"{model}:{self._hash_content(content)}"
        return await self.set("claim_extract", identifier, claims)
    
    async def get_cached_claim_extraction(self, content: str, model: str) -> Optional[List[Dict]]:
        """Get cached claim extraction"""
        identifier = f"{model}:{self._hash_content(content)}"
        return await self.get("claim_extract", identifier)
    
    async def cache_evidence_extraction(self, claim: str, evidence_data: List[Dict]) -> bool:
        """Cache evidence extraction results"""
        identifier = self._hash_content(claim)
        return await self.set("evidence_extract", identifier, evidence_data)
    
    async def get_cached_evidence_extraction(self, claim: str) -> Optional[List[Dict]]:
        """Get cached evidence extraction"""
        identifier = self._hash_content(claim)
        return await self.get("evidence_extract", identifier)
    
    async def cache_pipeline_result(self, check_id: str, result_data: Dict) -> bool:
        """Cache complete pipeline result"""
        return await self.set("pipeline_result", check_id, result_data)
    
    async def get_cached_pipeline_result(self, check_id: str) -> Optional[Dict]:
        """Get cached pipeline result"""
        return await self.get("pipeline_result", check_id)
    
    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all keys matching a pattern"""
        await self.initialize()
        if not self.redis_client:
            return 0
        
        try:
            key_pattern = f"{self.key_prefix}{pattern}"
            keys = await self.redis_client.keys(key_pattern)
            if keys:
                return await self.redis_client.delete(*keys)
            return 0
        except Exception as e:
            logger.warning(f"Cache invalidate error for pattern {pattern}: {e}")
            return 0
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        await self.initialize()
        if not self.redis_client:
            return {}
        
        try:
            info = await self.redis_client.info("memory")
            keyspace = await self.redis_client.info("keyspace")
            
            # Count keys by category
            categories = {}
            for category in self.ttl_config.keys():
                pattern = f"{self.key_prefix}{category}:*"
                keys = await self.redis_client.keys(pattern)
                categories[category] = len(keys)
            
            return {
                "memory_used": info.get("used_memory_human"),
                "total_keys": sum(categories.values()),
                "categories": categories,
                "keyspace_info": keyspace
            }
        except Exception as e:
            logger.error(f"Cache stats error: {e}")
            return {}
    
    async def cleanup(self):
        """Cleanup cache connections"""
        if self.redis_client:
            await self.redis_client.close()

    # ========== NEW METHODS FOR API CACHING (Phase 5: Government API Integration) ==========

    async def get_cached_api_response(
        self,
        api_name: str,
        query: str
    ) -> Optional[List[Dict]]:
        """
        Retrieve cached API response.

        Args:
            api_name: "ONS Economic Statistics", "PubMed", etc.
            query: Search query

        Returns:
            Cached response or None
        """
        query_hash = self._hash_content(query)
        identifier = f"{api_name}:{query_hash}"
        return await self.get("api_response", identifier)

    async def cache_api_response(
        self,
        api_name: str,
        query: str,
        response: List[Dict],
        ttl: int = 86400  # 24 hours
    ) -> bool:
        """Cache API response"""
        query_hash = self._hash_content(query)
        identifier = f"{api_name}:{query_hash}"
        return await self.set("api_response", identifier, response, ttl)

# Convenient decorator for caching function results
def cache_result(category: str, ttl: Optional[int] = None):
    """Decorator to cache function results"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            cache_service = await get_cache_service()
            
            # Create cache key from function name and arguments
            cache_key_data = {
                "func": func.__name__,
                "args": args,
                "kwargs": kwargs
            }
            identifier = cache_service._hash_content(cache_key_data)
            
            # Try to get from cache
            cached_result = await cache_service.get(category, identifier)
            if cached_result is not None:
                logger.debug(f"Cache hit for {func.__name__}")
                return cached_result
            
            # Execute function and cache result
            logger.debug(f"Cache miss for {func.__name__}")
            result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
            await cache_service.set(category, identifier, result, ttl)
            return result
        
        return wrapper
    return decorator

# Global cache service instance
_cache_service = None

async def get_cache_service() -> CacheService:
    """Get singleton cache service instance"""
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService()
        await _cache_service.initialize()
    return _cache_service


# ========== SYNCHRONOUS CACHE SERVICE FOR CELERY (Phase 5) ==========

class SyncCacheService:
    """
    Synchronous cache service for Celery workers.
    Avoids event loop issues in worker threads.
    """

    def __init__(self):
        import redis as sync_redis
        try:
            self.redis = sync_redis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=5
            )
            logger.info("Sync cache service initialized")
        except Exception as e:
            logger.error(f"Failed to initialize sync cache: {e}")
            self.redis = None

        # Cache hit/miss tracking (stored in Redis)
        self.metrics_key_prefix = "tru8:cache_metrics:"

    def _hash_content(self, content: Any) -> str:
        """Create a hash from content for cache key"""
        if isinstance(content, dict):
            content_str = json.dumps(content, sort_keys=True)
        else:
            content_str = str(content)
        return hashlib.md5(content_str.encode()).hexdigest()

    def get_cached_api_response_sync(self, api_name: str, query: str) -> Optional[List[Dict]]:
        """Synchronous version: Get cached API response"""
        if not self.redis:
            return None

        try:
            query_hash = self._hash_content(query)
            cache_key = f"tru8:api_response:{api_name}:{query_hash}"
            cached = self.redis.get(cache_key)

            # Track cache hit/miss metrics
            if cached:
                self._increment_metric(api_name, "hits")
            else:
                self._increment_metric(api_name, "misses")

            return json.loads(cached) if cached else None
        except Exception as e:
            logger.error(f"Sync cache retrieval error: {e}")
            return None

    def cache_api_response_sync(
        self,
        api_name: str,
        query: str,
        response: List[Dict],
        ttl: int = 86400
    ) -> bool:
        """Synchronous version: Cache API response"""
        if not self.redis:
            return False

        try:
            query_hash = self._hash_content(query)
            cache_key = f"tru8:api_response:{api_name}:{query_hash}"
            self.redis.setex(cache_key, ttl, json.dumps(response, default=str))
            return True
        except Exception as e:
            logger.error(f"Sync cache storage error: {e}")
            return False

    def _increment_metric(self, api_name: str, metric_type: str) -> None:
        """
        Increment cache metric counter.

        Args:
            api_name: API adapter name
            metric_type: "hits" or "misses"
        """
        if not self.redis:
            return

        try:
            metric_key = f"{self.metrics_key_prefix}{api_name}:{metric_type}"
            self.redis.incr(metric_key)
            # Set expiry of 7 days for metrics
            self.redis.expire(metric_key, 86400 * 7)
        except Exception as e:
            logger.debug(f"Failed to increment metric {metric_type} for {api_name}: {e}")

    def get_cache_metrics(self, api_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get cache hit/miss statistics.

        Args:
            api_name: Optional - get metrics for specific API, or all APIs if None

        Returns:
            Dictionary with cache metrics including hit rate percentage
        """
        if not self.redis:
            return {"error": "Redis not available"}

        try:
            if api_name:
                # Get metrics for specific API
                hits_key = f"{self.metrics_key_prefix}{api_name}:hits"
                misses_key = f"{self.metrics_key_prefix}{api_name}:misses"

                hits = int(self.redis.get(hits_key) or 0)
                misses = int(self.redis.get(misses_key) or 0)
                total = hits + misses

                hit_rate = (hits / total * 100) if total > 0 else 0

                return {
                    "api_name": api_name,
                    "hits": hits,
                    "misses": misses,
                    "total_queries": total,
                    "hit_rate_percentage": round(hit_rate, 2)
                }
            else:
                # Get metrics for all APIs
                all_metrics = {}
                total_hits = 0
                total_misses = 0

                # Find all metric keys
                pattern = f"{self.metrics_key_prefix}*:hits"
                keys = self.redis.keys(pattern)

                for hits_key in keys:
                    # Extract API name from key
                    api = hits_key.replace(f"{self.metrics_key_prefix}", "").replace(":hits", "")
                    misses_key = f"{self.metrics_key_prefix}{api}:misses"

                    hits = int(self.redis.get(hits_key) or 0)
                    misses = int(self.redis.get(misses_key) or 0)
                    total = hits + misses

                    hit_rate = (hits / total * 100) if total > 0 else 0

                    all_metrics[api] = {
                        "hits": hits,
                        "misses": misses,
                        "total_queries": total,
                        "hit_rate_percentage": round(hit_rate, 2)
                    }

                    total_hits += hits
                    total_misses += misses

                # Calculate overall hit rate
                grand_total = total_hits + total_misses
                overall_hit_rate = (total_hits / grand_total * 100) if grand_total > 0 else 0

                return {
                    "overall": {
                        "total_hits": total_hits,
                        "total_misses": total_misses,
                        "total_queries": grand_total,
                        "hit_rate_percentage": round(overall_hit_rate, 2)
                    },
                    "by_api": all_metrics
                }
        except Exception as e:
            logger.error(f"Failed to get cache metrics: {e}")
            return {"error": str(e)}

    def reset_cache_metrics(self, api_name: Optional[str] = None) -> bool:
        """
        Reset cache metrics (useful for testing).

        Args:
            api_name: Optional - reset metrics for specific API, or all if None

        Returns:
            True if successful
        """
        if not self.redis:
            return False

        try:
            if api_name:
                hits_key = f"{self.metrics_key_prefix}{api_name}:hits"
                misses_key = f"{self.metrics_key_prefix}{api_name}:misses"
                self.redis.delete(hits_key, misses_key)
            else:
                pattern = f"{self.metrics_key_prefix}*"
                keys = self.redis.keys(pattern)
                if keys:
                    self.redis.delete(*keys)
            return True
        except Exception as e:
            logger.error(f"Failed to reset cache metrics: {e}")
            return False


def get_sync_cache_service() -> SyncCacheService:
    """Create sync cache service for Celery context"""
    return SyncCacheService()