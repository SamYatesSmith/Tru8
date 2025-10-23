"""
Simple performance testing script without pytest dependency issues.

Measures latency impact of each pipeline improvement feature.
"""
import time
import statistics
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

# Sample data
SAMPLE_CLAIMS = [
    {"text": "The Earth is round and orbits the Sun.", "position": 0},
    {"text": "I think chocolate is the best flavor.", "position": 1},
    {"text": "The stock market will crash by 2030.", "position": 2},
    {"text": "I saw a celebrity at the mall yesterday.", "position": 3},
    {"text": "COVID-19 vaccines were approved in December 2020.", "position": 4}
]

SAMPLE_EVIDENCE = [
    {
        "source": "BBC",
        "url": "https://bbc.com/news/article1",
        "title": "Scientific Facts About Earth",
        "snippet": "The Earth is a sphere that orbits the Sun. This has been proven by countless observations.",
        "relevance_score": 0.92,
        "credibility_score": 0.9
    },
    {
        "source": "CNN",
        "url": "https://cnn.com/science/earth-facts",
        "title": "Scientific Facts About Earth",
        "snippet": "The Earth is a sphere that orbits the Sun. This has been proven by countless observations.",
        "relevance_score": 0.90,
        "credibility_score": 0.85
    },
    {
        "source": "Reuters",
        "url": "https://reuters.com/science/astronomy",
        "title": "Solar System Structure",
        "snippet": "Planets orbit the Sun in elliptical paths. Earth is the third planet.",
        "relevance_score": 0.88,
        "credibility_score": 0.9
    },
    {
        "source": "The Guardian",
        "url": "https://theguardian.com/science/earth",
        "title": "Earth's Orbital Mechanics",
        "snippet": "Earth completes one orbit around the Sun every 365.25 days.",
        "relevance_score": 0.85,
        "credibility_score": 0.88
    },
    {
        "source": "Snopes",
        "url": "https://snopes.com/fact-check/earth-sun",
        "title": "Fact Check: Earth Orbits Sun",
        "snippet": "True - Earth orbits the Sun, not the other way around.",
        "relevance_score": 0.95,
        "credibility_score": 0.95
    }
]


def benchmark_operation(name, operation, iterations=100, target_ms=None):
    """Run operation multiple times and return timing statistics"""
    print(f"\n{'='*60}")
    print(f"Testing: {name}")
    print(f"{'='*60}")

    times = []

    for i in range(iterations):
        start = time.perf_counter()
        try:
            operation()
        except Exception as e:
            print(f"[ERROR] Error during test: {e}")
            return None
        end = time.perf_counter()
        times.append((end - start) * 1000)  # Convert to ms

    stats = {
        "mean": statistics.mean(times),
        "median": statistics.median(times),
        "p95": statistics.quantiles(times, n=20)[18] if len(times) >= 20 else max(times),
        "min": min(times),
        "max": max(times),
    }

    print(f"Iterations: {iterations}")
    print(f"Mean:      {stats['mean']:.2f}ms")
    print(f"Median:    {stats['median']:.2f}ms")
    print(f"P95:       {stats['p95']:.2f}ms")
    print(f"Min:       {stats['min']:.2f}ms")
    print(f"Max:       {stats['max']:.2f}ms")

    if target_ms:
        print(f"\nTarget:    {target_ms}ms")
        if stats['p95'] <= target_ms:
            print(f"[PASS] P95 {stats['p95']:.2f}ms within target")
        else:
            print(f"[FAIL] P95 {stats['p95']:.2f}ms exceeds target by {stats['p95'] - target_ms:.2f}ms")

    return stats


def test_deduplication():
    """Test deduplication performance"""
    try:
        from app.utils.deduplication import ContentDeduplicator
    except ImportError as e:
        print(f"[SKIP] Skipping deduplication test: {e}")
        return None

    deduplicator = ContentDeduplicator()

    def operation():
        deduplicator.deduplicate(SAMPLE_EVIDENCE.copy())

    return benchmark_operation("Deduplication", operation, iterations=100, target_ms=200)


def test_source_independence():
    """Test source independence checking performance"""
    try:
        from app.utils.source_independence import SourceIndependenceChecker
    except ImportError as e:
        print(f"[SKIP] Skipping source independence test: {e}")
        return None

    checker = SourceIndependenceChecker()

    def operation():
        checker.analyze_evidence(SAMPLE_EVIDENCE.copy())

    return benchmark_operation("Source Independence", operation, iterations=100, target_ms=100)


def test_factcheck_detection():
    """Test fact-check detection performance (without API)"""
    try:
        from app.utils.factcheck import FactCheckDetector
    except ImportError as e:
        print(f"[SKIP] Skipping fact-check test: {e}")
        return None

    detector = FactCheckDetector()

    def operation():
        for evidence in SAMPLE_EVIDENCE:
            detector.detect_factcheck(evidence["url"], evidence["source"])

    return benchmark_operation("Fact-check Detection", operation, iterations=100, target_ms=50)


def test_temporal_analysis():
    """Test temporal analysis performance"""
    try:
        from app.utils.temporal import TemporalAnalyzer
    except ImportError as e:
        print(f"[SKIP] Skipping temporal analysis test: {e}")
        return None

    analyzer = TemporalAnalyzer()

    def operation():
        for claim in SAMPLE_CLAIMS:
            analyzer.analyze_claim(claim["text"])

    return benchmark_operation("Temporal Analysis (5 claims)", operation, iterations=100, target_ms=150)


def test_claim_classification():
    """Test claim classification performance"""
    try:
        from app.utils.claim_classifier import ClaimClassifier
    except ImportError as e:
        print(f"[SKIP] Skipping claim classification test: {e}")
        return None

    classifier = ClaimClassifier()

    def operation():
        for claim in SAMPLE_CLAIMS:
            classifier.classify(claim["text"])

    return benchmark_operation("Claim Classification (5 claims)", operation, iterations=100, target_ms=100)


def test_explainability():
    """Test explainability generation performance"""
    try:
        from app.utils.explainability import ExplainabilityEnhancer
    except ImportError as e:
        print(f"[SKIP] Skipping explainability test: {e}")
        return None

    explainer = ExplainabilityEnhancer()

    claim = SAMPLE_CLAIMS[0]
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
        explainer.create_decision_trail(claim, SAMPLE_EVIDENCE, signals, judgment)
        explainer.create_confidence_breakdown(judgment, SAMPLE_EVIDENCE, signals)
        explainer.create_uncertainty_explanation("supported", signals, SAMPLE_EVIDENCE)

    return benchmark_operation("Explainability", operation, iterations=100, target_ms=200)


def test_combined_overhead():
    """Test combined overhead of all features"""
    print(f"\n{'='*60}")
    print("Testing: COMBINED OVERHEAD (All Features)")
    print(f"{'='*60}")

    try:
        from app.utils.deduplication import ContentDeduplicator
        from app.utils.source_independence import SourceIndependenceChecker
        from app.utils.factcheck import FactCheckDetector
        from app.utils.temporal import TemporalAnalyzer
        from app.utils.claim_classifier import ClaimClassifier
        from app.utils.explainability import ExplainabilityEnhancer
    except ImportError as e:
        print(f"[SKIP] Cannot run combined test: {e}")
        return None

    # Initialize utilities
    deduplicator = ContentDeduplicator()
    independence_checker = SourceIndependenceChecker()
    factcheck_detector = FactCheckDetector()
    temporal_analyzer = TemporalAnalyzer()
    classifier = ClaimClassifier()
    explainer = ExplainabilityEnhancer()

    def operation():
        # Simulate full pipeline

        # 1. Claim processing
        for claim in SAMPLE_CLAIMS:
            classifier.classify(claim["text"])
            temporal_analyzer.analyze_claim(claim["text"])

        # 2. Evidence processing
        evidence = SAMPLE_EVIDENCE.copy()
        evidence = deduplicator.deduplicate(evidence)
        independence_checker.analyze_evidence(evidence)

        for ev in evidence:
            factcheck_detector.detect_factcheck(ev["url"], ev["source"])

        # 3. Explainability
        signals = {"supporting_count": 3, "contradicting_count": 0, "neutral_count": 1}
        judgment = {"verdict": "supported", "confidence": 85, "rationale": "Strong evidence"}

        explainer.create_decision_trail(SAMPLE_CLAIMS[0], evidence, signals, judgment)
        explainer.create_confidence_breakdown(judgment, evidence, signals)

    return benchmark_operation("Combined Overhead", operation, iterations=50, target_ms=1300)


def main():
    """Run all performance tests"""
    print("\n" + "="*60)
    print("PIPELINE IMPROVEMENTS PERFORMANCE TEST SUITE")
    print("="*60)
    print("\nTarget: Total overhead <1300ms (baseline 10s -> target 11.3s)")
    print("Individual feature targets defined in FEATURE_ROLLOUT_PLAN.md")

    results = {}

    # Run individual tests
    results['deduplication'] = test_deduplication()
    results['source_independence'] = test_source_independence()
    results['factcheck'] = test_factcheck_detection()
    results['temporal'] = test_temporal_analysis()
    results['classification'] = test_claim_classification()
    results['explainability'] = test_explainability()

    # Run combined test
    results['combined'] = test_combined_overhead()

    # Summary
    print("\n" + "="*60)
    print("PERFORMANCE TEST SUMMARY")
    print("="*60)

    successful_tests = sum(1 for r in results.values() if r is not None)
    total_tests = len(results)

    print(f"\nTests run: {successful_tests}/{total_tests}")

    if results['combined']:
        print(f"\nCOMBINED OVERHEAD: {results['combined']['p95']:.2f}ms (target: <1300ms)")

        if results['combined']['p95'] <= 1300:
            print("[PASS] ALL FEATURES within performance target!")
        else:
            print(f"[WARN] Exceeds target by {results['combined']['p95'] - 1300:.2f}ms")

    print("\nBreakdown:")
    for name, result in results.items():
        if result and name != 'combined':
            print(f"  {name:20s}: {result['p95']:6.2f}ms (p95)")

    print("\n" + "="*60)


if __name__ == "__main__":
    main()
