"""
Performance tests for pipeline improvement features.

Measures latency impact of each feature to validate against targets:
- Total pipeline target: <12s p95
- Individual feature budgets defined in FEATURE_ROLLOUT_PLAN.md
"""

import pytest
import time
from typing import List, Dict
import statistics


class TestFeaturePerformance:
    """Measure latency impact of each feature"""

    @pytest.fixture
    def sample_claims(self):
        """Standard set of test claims"""
        return [
            {"text": "The Earth is round and orbits the Sun.", "position": 0},
            {"text": "I think chocolate is the best flavor.", "position": 1},
            {"text": "The stock market will crash by 2030.", "position": 2},
            {"text": "I saw a celebrity at the mall yesterday.", "position": 3},
            {
                "text": "COVID-19 vaccines were approved in December 2020.",
                "position": 4,
            },
        ]

    def benchmark_operation(self, operation, iterations: int = 100) -> Dict[str, float]:
        """Run operation multiple times and return timing statistics"""
        times = []

        for _ in range(iterations):
            start = time.perf_counter()
            operation()
            end = time.perf_counter()
            times.append((end - start) * 1000)  # Convert to ms

        return {
            "mean": statistics.mean(times),
            "median": statistics.median(times),
            "p95": statistics.quantiles(times, n=20)[18],  # 95th percentile
            "min": min(times),
            "max": max(times),
            "iterations": iterations,
        }

    @pytest.mark.performance
    def test_temporal_analysis_overhead(self, sample_claims):
        """
        Test: Temporal context analysis time

        Target: <150ms overhead for 5 claims
        """
        from app.utils.temporal import TemporalAnalyzer

        analyzer = TemporalAnalyzer()

        def operation():
            for claim in sample_claims:
                analyzer.analyze_claim(claim["text"])

        stats = self.benchmark_operation(operation, iterations=100)

        print(f"\n=== Temporal Analysis Performance ===")
        print(f"Mean: {stats['mean']:.2f}ms")
        print(f"Median: {stats['median']:.2f}ms")
        print(f"P95: {stats['p95']:.2f}ms")
        print(f"Target: <150ms (for 5 claims)")

        assert (
            stats["p95"] < 150
        ), f"Temporal analysis p95 {stats['p95']:.2f}ms exceeds 150ms target"

    @pytest.mark.performance
    def test_claim_classification_overhead(self, sample_claims):
        """
        Test: Claim classification time

        Target: <100ms overhead for 5 claims
        """
        from app.utils.legal_claim_detector import LegalClaimDetector

        detector = LegalClaimDetector()

        def operation():
            for claim in sample_claims:
                detector.classify(claim["text"])

        stats = self.benchmark_operation(operation, iterations=100)

        print(f"\n=== Claim Classification Performance ===")
        print(f"Mean: {stats['mean']:.2f}ms")
        print(f"Median: {stats['median']:.2f}ms")
        print(f"P95: {stats['p95']:.2f}ms")
        print(f"Target: <100ms (for 5 claims)")

        assert (
            stats["p95"] < 100
        ), f"Claim classification p95 {stats['p95']:.2f}ms exceeds 100ms target"


@pytest.mark.performance
class TestScalability:
    """Test performance with varying data sizes"""

    def test_classification_scales_linearly(self):
        """Test: Legal claim detection performance scales linearly with claim count"""
        from app.utils.legal_claim_detector import LegalClaimDetector

        detector = LegalClaimDetector()

        claims = [
            "The Earth is round and orbits the Sun.",
            "42 USC 1983 protects civil rights.",
            "The National Historic Preservation Act of 1966 exempts the White House.",
            "A 1952 federal law requires submission.",
            "Water boils at 100 degrees Celsius.",
        ]

        for claim_count in [5, 10, 25, 50]:
            test_claims = (claims * (claim_count // len(claims) + 1))[:claim_count]

            start = time.perf_counter()
            for claim in test_claims:
                detector.classify(claim)
            end = time.perf_counter()

            duration_ms = (end - start) * 1000

            print(f"\nClassification with {claim_count} claims: {duration_ms:.2f}ms")

            # Should be roughly linear (allow some overhead)
            expected_max = claim_count * 3  # 3ms per claim max
            assert duration_ms < expected_max, f"Classification doesn't scale linearly"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "performance", "-s"])
