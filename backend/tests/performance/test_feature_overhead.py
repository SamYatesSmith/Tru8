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
            {"text": "COVID-19 vaccines were approved in December 2020.", "position": 4}
        ]

    @pytest.fixture
    def sample_evidence(self):
        """Standard set of evidence for testing"""
        return [
            {
                "source": "BBC",
                "url": "https://bbc.com/news/article1",
                "title": "Scientific Facts About Earth",
                "snippet": "The Earth is a sphere that orbits the Sun. This has been proven by countless observations.",
                "published_date": "2024-01-15",
                "relevance_score": 0.92,
                "credibility_score": 0.9
            },
            {
                "source": "CNN",
                "url": "https://cnn.com/science/earth-facts",
                "title": "Scientific Facts About Earth",  # Duplicate title
                "snippet": "The Earth is a sphere that orbits the Sun. This has been proven by countless observations.",  # Duplicate
                "published_date": "2024-01-16",
                "relevance_score": 0.90,
                "credibility_score": 0.85
            },
            {
                "source": "Reuters",
                "url": "https://reuters.com/science/astronomy",
                "title": "Solar System Structure",
                "snippet": "Planets orbit the Sun in elliptical paths. Earth is the third planet.",
                "published_date": "2024-02-20",
                "relevance_score": 0.88,
                "credibility_score": 0.9
            },
            {
                "source": "The Guardian",
                "url": "https://theguardian.com/science/earth",
                "title": "Earth's Orbital Mechanics",
                "snippet": "Earth completes one orbit around the Sun every 365.25 days.",
                "published_date": "2023-12-10",
                "relevance_score": 0.85,
                "credibility_score": 0.88
            },
            {
                "source": "Snopes",
                "url": "https://snopes.com/fact-check/earth-sun",
                "title": "Fact Check: Earth Orbits Sun",
                "snippet": "True - Earth orbits the Sun, not the other way around.",
                "published_date": "2024-03-05",
                "relevance_score": 0.95,
                "credibility_score": 0.95
            }
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
            "iterations": iterations
        }

    @pytest.mark.performance
    def test_deduplication_overhead(self, sample_evidence):
        """
        Test: Deduplication processing time

        Target: <200ms overhead
        """
        from app.utils.deduplication import ContentDeduplicator

        deduplicator = ContentDeduplicator()

        def operation():
            deduplicator.deduplicate(sample_evidence.copy())

        stats = self.benchmark_operation(operation, iterations=100)

        print(f"\n=== Deduplication Performance ===")
        print(f"Mean: {stats['mean']:.2f}ms")
        print(f"Median: {stats['median']:.2f}ms")
        print(f"P95: {stats['p95']:.2f}ms")
        print(f"Target: <200ms")

        assert stats['p95'] < 200, f"Deduplication p95 {stats['p95']:.2f}ms exceeds 200ms target"

    @pytest.mark.performance
    def test_source_independence_overhead(self, sample_evidence):
        """
        Test: Source independence checking time

        Target: <100ms overhead
        """
        from app.utils.source_independence import SourceIndependenceChecker

        checker = SourceIndependenceChecker()

        def operation():
            checker.analyze_evidence(sample_evidence.copy())

        stats = self.benchmark_operation(operation, iterations=100)

        print(f"\n=== Source Independence Performance ===")
        print(f"Mean: {stats['mean']:.2f}ms")
        print(f"Median: {stats['median']:.2f}ms")
        print(f"P95: {stats['p95']:.2f}ms")
        print(f"Target: <100ms")

        assert stats['p95'] < 100, f"Source independence p95 {stats['p95']:.2f}ms exceeds 100ms target"

    @pytest.mark.performance
    def test_factcheck_detection_overhead(self, sample_evidence):
        """
        Test: Fact-check detection time (without API calls)

        Target: <50ms overhead for detection only
        Note: API calls add ~500ms but are async and cached
        """
        from app.utils.factcheck import FactCheckDetector

        detector = FactCheckDetector()

        def operation():
            for evidence in sample_evidence:
                detector.detect_factcheck(evidence["url"], evidence["source"])

        stats = self.benchmark_operation(operation, iterations=100)

        print(f"\n=== Fact-check Detection Performance ===")
        print(f"Mean: {stats['mean']:.2f}ms")
        print(f"Median: {stats['median']:.2f}ms")
        print(f"P95: {stats['p95']:.2f}ms")
        print(f"Target: <50ms (detection only)")

        assert stats['p95'] < 50, f"Fact-check detection p95 {stats['p95']:.2f}ms exceeds 50ms target"

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

        assert stats['p95'] < 150, f"Temporal analysis p95 {stats['p95']:.2f}ms exceeds 150ms target"

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

        assert stats['p95'] < 100, f"Claim classification p95 {stats['p95']:.2f}ms exceeds 100ms target"

    @pytest.mark.performance
    def test_explainability_overhead(self, sample_claims, sample_evidence):
        """
        Test: Explainability generation time

        Target: <200ms overhead
        """
        from app.utils.explainability import ExplainabilityEnhancer

        explainer = ExplainabilityEnhancer()

        claim = sample_claims[0]
        signals = {
            "supporting_count": 4,
            "contradicting_count": 0,
            "neutral_count": 1
        }
        judgment = {
            "verdict": "supported",
            "confidence": 90,
            "rationale": "Multiple reliable sources confirm the claim"
        }

        def operation():
            # Decision trail
            explainer.create_decision_trail(claim, sample_evidence, signals, judgment)

            # Confidence breakdown
            explainer.create_confidence_breakdown(judgment, sample_evidence, signals)

            # Uncertainty explanation (if needed)
            explainer.create_uncertainty_explanation("supported", signals, sample_evidence)

        stats = self.benchmark_operation(operation, iterations=100)

        print(f"\n=== Explainability Performance ===")
        print(f"Mean: {stats['mean']:.2f}ms")
        print(f"Median: {stats['median']:.2f}ms")
        print(f"P95: {stats['p95']:.2f}ms")
        print(f"Target: <200ms")

        assert stats['p95'] < 200, f"Explainability p95 {stats['p95']:.2f}ms exceeds 200ms target"

    @pytest.mark.performance
    def test_domain_capping_overhead(self, sample_evidence):
        """
        Test: Domain capping time

        Target: <50ms overhead
        """
        from app.pipeline.retrieve import apply_domain_cap

        # Create evidence with multiple items per domain
        evidence_with_dupes = sample_evidence * 3  # 15 items

        def operation():
            apply_domain_cap(evidence_with_dupes.copy(), max_per_domain=3)

        stats = self.benchmark_operation(operation, iterations=100)

        print(f"\n=== Domain Capping Performance ===")
        print(f"Mean: {stats['mean']:.2f}ms")
        print(f"Median: {stats['median']:.2f}ms")
        print(f"P95: {stats['p95']:.2f}ms")
        print(f"Target: <50ms")

        assert stats['p95'] < 50, f"Domain capping p95 {stats['p95']:.2f}ms exceeds 50ms target"

    @pytest.mark.performance
    def test_combined_overhead(self, sample_claims, sample_evidence):
        """
        Test: Combined overhead of all features

        Target: <1300ms total overhead
        """
        from app.utils.deduplication import ContentDeduplicator
        from app.utils.source_independence import SourceIndependenceChecker
        from app.utils.factcheck import FactCheckDetector
        from app.utils.temporal import TemporalAnalyzer
        from app.utils.legal_claim_detector import LegalClaimDetector
        from app.utils.explainability import ExplainabilityEnhancer
        from app.pipeline.retrieve import apply_domain_cap

        # Initialize all utilities
        deduplicator = ContentDeduplicator()
        independence_checker = SourceIndependenceChecker()
        factcheck_detector = FactCheckDetector()
        temporal_analyzer = TemporalAnalyzer()
        detector = LegalClaimDetector()
        explainer = ExplainabilityEnhancer()

        def operation():
            # Simulate full pipeline with all features

            # 1. Legal claim detection and temporal analysis (extract stage)
            for claim in sample_claims:
                detector.classify(claim["text"])
                temporal_analyzer.analyze_claim(claim["text"])

            # 2. Evidence processing (retrieve stage)
            evidence = sample_evidence.copy()

            # Deduplication
            evidence = deduplicator.deduplicate(evidence)

            # Source independence
            independence_checker.analyze_evidence(evidence)

            # Fact-check detection (without API call)
            for ev in evidence:
                factcheck_detector.detect_factcheck(ev["url"], ev["source"])

            # Domain capping
            evidence = apply_domain_cap(evidence, max_per_domain=3)

            # 3. Explainability (judge stage)
            signals = {"supporting_count": 3, "contradicting_count": 0, "neutral_count": 1}
            judgment = {"verdict": "supported", "confidence": 85, "rationale": "Strong evidence"}

            explainer.create_decision_trail(sample_claims[0], evidence, signals, judgment)
            explainer.create_confidence_breakdown(judgment, evidence, signals)

        stats = self.benchmark_operation(operation, iterations=50)  # Fewer iterations for combined test

        print(f"\n=== COMBINED OVERHEAD (All Features) ===")
        print(f"Mean: {stats['mean']:.2f}ms")
        print(f"Median: {stats['median']:.2f}ms")
        print(f"P95: {stats['p95']:.2f}ms")
        print(f"Target: <1300ms")
        print(f"\nBreakdown estimate:")
        print(f"  Deduplication:        ~200ms")
        print(f"  Source independence:  ~100ms")
        print(f"  Fact-check detection:  ~50ms")
        print(f"  Temporal analysis:    ~150ms")
        print(f"  Classification:       ~100ms")
        print(f"  Explainability:       ~200ms")
        print(f"  Domain capping:        ~50ms")
        print(f"  Misc overhead:        ~450ms")
        print(f"  Total budget:        1300ms")

        assert stats['p95'] < 1300, f"Combined overhead p95 {stats['p95']:.2f}ms exceeds 1300ms target"

    @pytest.mark.performance
    def test_memory_footprint(self, sample_claims, sample_evidence):
        """
        Test: Memory usage of all utilities

        Ensures no memory leaks or excessive allocations
        """
        import tracemalloc

        from app.utils.deduplication import ContentDeduplicator
        from app.utils.source_independence import SourceIndependenceChecker
        from app.utils.temporal import TemporalAnalyzer
        from app.utils.legal_claim_detector import LegalClaimDetector
        from app.utils.explainability import ExplainabilityEnhancer

        tracemalloc.start()

        # Snapshot before
        snapshot_before = tracemalloc.take_snapshot()

        # Process 100 iterations
        for _ in range(100):
            deduplicator = ContentDeduplicator()
            independence = SourceIndependenceChecker()
            temporal = TemporalAnalyzer()
            detector = LegalClaimDetector()
            explainer = ExplainabilityEnhancer()

            # Do some work
            deduplicator.deduplicate(sample_evidence.copy())
            independence.analyze_evidence(sample_evidence.copy())
            temporal.analyze_claim(sample_claims[0]["text"])
            classifier.classify(sample_claims[0]["text"])

            signals = {"supporting_count": 3, "contradicting_count": 0}
            judgment = {"verdict": "supported", "confidence": 85}
            explainer.create_decision_trail(sample_claims[0], sample_evidence, signals, judgment)

        # Snapshot after
        snapshot_after = tracemalloc.take_snapshot()

        # Calculate difference
        top_stats = snapshot_after.compare_to(snapshot_before, 'lineno')

        total_diff = sum(stat.size_diff for stat in top_stats)
        total_diff_mb = total_diff / (1024 * 1024)

        print(f"\n=== Memory Footprint ===")
        print(f"Total memory increase: {total_diff_mb:.2f} MB")
        print(f"Per iteration: {total_diff_mb / 100:.4f} MB")

        tracemalloc.stop()

        # Should not leak more than 10MB over 100 iterations
        assert total_diff_mb < 10, f"Memory increase {total_diff_mb:.2f}MB exceeds 10MB threshold"


@pytest.mark.performance
class TestScalability:
    """Test performance with varying data sizes"""

    def test_deduplication_scales_linearly(self):
        """Test: Deduplication performance scales linearly with evidence count"""
        from app.utils.deduplication import ContentDeduplicator

        deduplicator = ContentDeduplicator()

        evidence_template = {
            "source": "Source",
            "url": "https://example.com/article",
            "title": "Article Title",
            "snippet": "Article content here",
            "relevance_score": 0.8
        }

        for size in [10, 50, 100, 200]:
            evidence = [
                {**evidence_template, "url": f"https://example.com/article{i}"}
                for i in range(size)
            ]

            start = time.perf_counter()
            deduplicator.deduplicate(evidence)
            end = time.perf_counter()

            duration_ms = (end - start) * 1000

            print(f"\nDeduplication with {size} items: {duration_ms:.2f}ms")

            # Should be roughly linear (allow some overhead)
            expected_max = size * 2  # 2ms per item max
            assert duration_ms < expected_max, f"Deduplication doesn't scale linearly"

    def test_classification_scales_linearly(self):
        """Test: Legal claim detection performance scales linearly with claim count"""
        from app.utils.legal_claim_detector import LegalClaimDetector

        detector = LegalClaimDetector()

        claims = [
            "The Earth is round and orbits the Sun.",
            "42 USC 1983 protects civil rights.",
            "The National Historic Preservation Act of 1966 exempts the White House.",
            "A 1952 federal law requires submission.",
            "Water boils at 100 degrees Celsius."
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
