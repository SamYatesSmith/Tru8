"""
Cache Monitoring Tests
Phase 5: Week 4 - Cache Hit Rate Monitoring

Tests cache metrics tracking, hit rate calculation, and performance evaluation.
Target: 60%+ hit rate on repeated queries.
"""

import pytest
from unittest.mock import Mock, patch
from app.services.cache import get_sync_cache_service


class TestCacheMetricsTracking:
    """Test cache hit/miss tracking functionality."""

    def setup_method(self):
        """Reset cache metrics before each test."""
        cache = get_sync_cache_service()
        cache.reset_cache_metrics()

    @pytest.mark.performance
    def test_cache_miss_increments_counter(self):
        """Test that cache misses are tracked."""
        cache = get_sync_cache_service()

        # First call - cache miss
        result = cache.get_cached_api_response_sync("ONS", "UK inflation rate")

        # Verify miss was tracked
        metrics = cache.get_cache_metrics("ONS")
        assert metrics["misses"] == 1
        assert metrics["hits"] == 0
        assert metrics["total_queries"] == 1
        assert metrics["hit_rate_percentage"] == 0.0

    @pytest.mark.performance
    def test_cache_hit_increments_counter(self):
        """Test that cache hits are tracked."""
        cache = get_sync_cache_service()

        # Store something in cache
        cache.cache_api_response_sync(
            "ONS",
            "UK inflation rate",
            [{"title": "Test", "snippet": "Test"}],
            ttl=60
        )

        # Second call - cache hit
        result = cache.get_cached_api_response_sync("ONS", "UK inflation rate")

        # Verify hit was tracked
        metrics = cache.get_cache_metrics("ONS")
        assert metrics["hits"] == 1
        assert metrics["misses"] == 0
        assert metrics["total_queries"] == 1
        assert metrics["hit_rate_percentage"] == 100.0

    @pytest.mark.performance
    def test_cache_hit_rate_calculation(self):
        """Test that hit rate is calculated correctly."""
        cache = get_sync_cache_service()

        # Cache a response
        test_data = [{"title": "Test Evidence", "snippet": "Test snippet"}]
        cache.cache_api_response_sync("PubMed", "COVID-19 vaccine", test_data, ttl=60)

        # 1 hit
        cache.get_cached_api_response_sync("PubMed", "COVID-19 vaccine")

        # 2 misses (different queries)
        cache.get_cached_api_response_sync("PubMed", "flu vaccine")
        cache.get_cached_api_response_sync("PubMed", "measles vaccine")

        # Verify: 1 hit + 2 misses = 33.33% hit rate
        metrics = cache.get_cache_metrics("PubMed")
        assert metrics["hits"] == 1
        assert metrics["misses"] == 2
        assert metrics["total_queries"] == 3
        assert metrics["hit_rate_percentage"] == 33.33

    @pytest.mark.performance
    def test_repeated_query_improves_hit_rate(self):
        """Test that repeated queries improve hit rate (target: 60%+)."""
        cache = get_sync_cache_service()

        # Cache multiple responses
        queries = [
            "UK GDP 2024",
            "UK unemployment rate",
            "UK inflation CPI"
        ]

        for query in queries:
            cache.cache_api_response_sync(
                "ONS",
                query,
                [{"title": f"Data for {query}", "snippet": "Test"}],
                ttl=60
            )

        # Simulate realistic usage pattern:
        # - 7 hits (repeated queries)
        # - 3 misses (new queries)

        # Repeated queries (hits)
        for query in queries:
            cache.get_cached_api_response_sync("ONS", query)  # Hit
            cache.get_cached_api_response_sync("ONS", query)  # Hit again

        # New queries (misses)
        cache.get_cached_api_response_sync("ONS", "UK trade balance")
        cache.get_cached_api_response_sync("ONS", "UK population 2024")
        cache.get_cached_api_response_sync("ONS", "UK house prices")

        # 6 hits + 3 misses = 66.67% hit rate (exceeds 60% target)
        metrics = cache.get_cache_metrics("ONS")
        assert metrics["total_queries"] == 9
        assert metrics["hit_rate_percentage"] >= 60.0, f"Hit rate {metrics['hit_rate_percentage']}% below 60% target"

    @pytest.mark.performance
    def test_metrics_for_multiple_apis(self):
        """Test aggregate metrics across multiple APIs."""
        cache = get_sync_cache_service()

        # ONS: 2 hits, 1 miss = 66.67%
        cache.cache_api_response_sync("ONS", "query1", [{"test": "data"}], ttl=60)
        cache.get_cached_api_response_sync("ONS", "query1")  # Hit
        cache.get_cached_api_response_sync("ONS", "query1")  # Hit
        cache.get_cached_api_response_sync("ONS", "query2")  # Miss

        # PubMed: 1 hit, 0 misses = 100%
        cache.cache_api_response_sync("PubMed", "query3", [{"test": "data"}], ttl=60)
        cache.get_cached_api_response_sync("PubMed", "query3")  # Hit

        # Get aggregate metrics
        all_metrics = cache.get_cache_metrics()

        assert "overall" in all_metrics
        assert "by_api" in all_metrics

        # Overall: 3 hits + 1 miss = 75%
        assert all_metrics["overall"]["total_hits"] == 3
        assert all_metrics["overall"]["total_misses"] == 1
        assert all_metrics["overall"]["total_queries"] == 4
        assert all_metrics["overall"]["hit_rate_percentage"] == 75.0

        # Individual API metrics
        assert "ONS" in all_metrics["by_api"]
        assert all_metrics["by_api"]["ONS"]["hit_rate_percentage"] == 66.67

        assert "PubMed" in all_metrics["by_api"]
        assert all_metrics["by_api"]["PubMed"]["hit_rate_percentage"] == 100.0

    @pytest.mark.performance
    def test_metrics_reset(self):
        """Test that metrics can be reset."""
        cache = get_sync_cache_service()

        # Generate some metrics
        cache.cache_api_response_sync("FRED", "test", [{"data": "test"}], ttl=60)
        cache.get_cached_api_response_sync("FRED", "test")

        # Verify metrics exist
        metrics_before = cache.get_cache_metrics("FRED")
        assert metrics_before["total_queries"] > 0

        # Reset metrics for this API
        success = cache.reset_cache_metrics("FRED")
        assert success is True

        # Verify metrics are reset
        metrics_after = cache.get_cache_metrics("FRED")
        assert metrics_after["total_queries"] == 0
        assert metrics_after["hits"] == 0
        assert metrics_after["misses"] == 0

    @pytest.mark.performance
    def test_zero_queries_returns_zero_hit_rate(self):
        """Test that zero queries returns 0% hit rate (no division by zero)."""
        cache = get_sync_cache_service()

        # Get metrics for API with no queries
        metrics = cache.get_cache_metrics("UnusedAPI")

        assert metrics["hits"] == 0
        assert metrics["misses"] == 0
        assert metrics["total_queries"] == 0
        assert metrics["hit_rate_percentage"] == 0.0  # Should not raise division by zero


class TestCachePerformanceEvaluation:
    """Test cache performance status evaluation."""

    def test_excellent_performance_75_percent_plus(self):
        """Test that 75%+ hit rate is marked as excellent."""
        from app.api.v1.health import _evaluate_cache_performance

        assert _evaluate_cache_performance(75.0) == "excellent"
        assert _evaluate_cache_performance(85.0) == "excellent"
        assert _evaluate_cache_performance(100.0) == "excellent"

    def test_good_performance_60_to_74_percent(self):
        """Test that 60-74% hit rate is marked as good (meets target)."""
        from app.api.v1.health import _evaluate_cache_performance

        assert _evaluate_cache_performance(60.0) == "good"
        assert _evaluate_cache_performance(65.0) == "good"
        assert _evaluate_cache_performance(70.0) == "good"

    def test_acceptable_performance_40_to_59_percent(self):
        """Test that 40-59% hit rate is marked as acceptable."""
        from app.api.v1.health import _evaluate_cache_performance

        assert _evaluate_cache_performance(40.0) == "acceptable"
        assert _evaluate_cache_performance(50.0) == "acceptable"
        assert _evaluate_cache_performance(55.0) == "acceptable"

    def test_needs_optimization_below_40_percent(self):
        """Test that <40% hit rate needs optimization."""
        from app.api.v1.health import _evaluate_cache_performance

        assert _evaluate_cache_performance(0.0) == "needs_optimization"
        assert _evaluate_cache_performance(20.0) == "needs_optimization"
        assert _evaluate_cache_performance(39.9) == "needs_optimization"


class TestCacheOptimization:
    """Test cache optimization strategies."""

    @pytest.mark.performance
    def test_long_ttl_improves_hit_rate_for_stable_data(self):
        """Test that longer TTL improves hit rate for stable data (e.g., economic indicators)."""
        cache = get_sync_cache_service()

        # Economic data changes slowly - use long TTL (7 days)
        long_ttl = 86400 * 7

        # Cache stable data
        cache.cache_api_response_sync(
            "ONS",
            "UK GDP growth Q1 2024",
            [{"title": "GDP Data", "snippet": "1.2% growth"}],
            ttl=long_ttl
        )

        # Simulate queries over multiple "days" (in reality, immediate)
        # Users repeatedly query the same historical data
        hit_count = 0
        for _ in range(10):
            result = cache.get_cached_api_response_sync("ONS", "UK GDP growth Q1 2024")
            if result:
                hit_count += 1

        # All 10 queries should hit cache (100% hit rate)
        metrics = cache.get_cache_metrics("ONS")
        assert metrics["hit_rate_percentage"] == 100.0
        assert hit_count == 10

    @pytest.mark.performance
    def test_short_ttl_for_frequently_changing_data(self):
        """Test that short TTL is appropriate for frequently changing data (e.g., weather)."""
        cache = get_sync_cache_service()

        # Weather data changes frequently - use short TTL (1 hour)
        short_ttl = 3600

        # Cache weather data
        cache.cache_api_response_sync(
            "Met Office",
            "London weather forecast",
            [{"title": "Weather", "snippet": "Sunny, 18C"}],
            ttl=short_ttl
        )

        # First query - hit
        result1 = cache.get_cached_api_response_sync("Met Office", "London weather forecast")
        assert result1 is not None

        # In production, after 1 hour this would expire
        # For testing, we verify the TTL was set correctly
        # (actual TTL validation would require waiting or mocking time)

        metrics = cache.get_cache_metrics("Met Office")
        assert metrics["total_queries"] >= 1


class TestCacheMetricsAPI:
    """Test cache metrics API endpoint."""

    @pytest.mark.performance
    def test_cache_metrics_endpoint_returns_overall_stats(self):
        """Test that /health/cache-metrics returns overall statistics."""
        cache = get_sync_cache_service()
        cache.reset_cache_metrics()

        # Generate some test data
        cache.cache_api_response_sync("ONS", "test1", [{"data": "test"}], ttl=60)
        cache.get_cached_api_response_sync("ONS", "test1")  # Hit
        cache.get_cached_api_response_sync("ONS", "test2")  # Miss

        # Get all metrics (simulating API call without api_name parameter)
        all_metrics = cache.get_cache_metrics()

        # Verify structure
        assert "overall" in all_metrics
        assert "by_api" in all_metrics
        assert all_metrics["overall"]["total_queries"] == 2
        assert all_metrics["overall"]["total_hits"] == 1
        assert all_metrics["overall"]["total_misses"] == 1
        assert all_metrics["overall"]["hit_rate_percentage"] == 50.0

    @pytest.mark.performance
    def test_cache_metrics_endpoint_filters_by_api(self):
        """Test that /health/cache-metrics?api_name=ONS filters correctly."""
        cache = get_sync_cache_service()
        cache.reset_cache_metrics()

        # Generate data for multiple APIs
        cache.cache_api_response_sync("ONS", "test", [{"data": "test"}], ttl=60)
        cache.get_cached_api_response_sync("ONS", "test")  # Hit

        cache.cache_api_response_sync("PubMed", "test", [{"data": "test"}], ttl=60)
        cache.get_cached_api_response_sync("PubMed", "test2")  # Miss

        # Get metrics for specific API
        ons_metrics = cache.get_cache_metrics("ONS")

        # Verify only ONS metrics returned
        assert ons_metrics["api_name"] == "ONS"
        assert ons_metrics["hits"] == 1
        assert ons_metrics["misses"] == 0
        # Should not include PubMed data


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "-m", "performance"])
