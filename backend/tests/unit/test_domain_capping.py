import pytest
from app.utils.domain_capping import DomainCapper


class TestDomainCapping:
    """Test domain capping utility - prevents single-source dominance"""

    @pytest.fixture
    def capper(self):
        return DomainCapper(max_per_domain=3, max_domain_ratio=0.4)

    @pytest.fixture
    def evidence_list(self):
        """10 evidence items, 5 from bbc.com (50% - should be capped to 40%)"""
        return [
            {"url": "https://bbc.com/article1", "snippet": "BBC evidence 1", "final_score": 0.95},
            {"url": "https://bbc.com/article2", "snippet": "BBC evidence 2", "final_score": 0.90},
            {"url": "https://bbc.com/article3", "snippet": "BBC evidence 3", "final_score": 0.85},
            {"url": "https://bbc.com/article4", "snippet": "BBC evidence 4", "final_score": 0.80},
            {"url": "https://bbc.com/article5", "snippet": "BBC evidence 5", "final_score": 0.75},
            {"url": "https://cnn.com/article1", "snippet": "CNN evidence 1", "final_score": 0.88},
            {"url": "https://reuters.com/article1", "snippet": "Reuters evidence", "final_score": 0.87},
            {"url": "https://apnews.com/article1", "snippet": "AP evidence", "final_score": 0.86},
            {"url": "https://nytimes.com/article1", "snippet": "NYT evidence", "final_score": 0.84},
            {"url": "https://theguardian.com/article1", "snippet": "Guardian evidence", "final_score": 0.83}
        ]

    def test_apply_caps_reduces_dominant_domain(self, capper, evidence_list):
        """Test: Dominant domain (50%) reduced to max 40%"""
        result = capper.apply_caps(evidence_list, target_count=10)

        # Count BBC evidence in result
        bbc_count = sum(1 for ev in result if 'bbc.com' in ev['url'])

        # Assert: Max 40% (4 out of 10)
        assert bbc_count <= 4, f"Expected ≤4 BBC evidence, got {bbc_count}"

        # Assert: Total count unchanged
        assert len(result) == 10

    def test_apply_caps_preserves_quality_ranking(self, capper, evidence_list):
        """Test: Capping keeps highest-quality evidence from each domain"""
        result = capper.apply_caps(evidence_list, target_count=10)

        # Find which BBC articles made it through
        bbc_survivors = [ev for ev in result if 'bbc.com' in ev['url']]

        # Assert: Top BBC articles by score survived
        assert len(bbc_survivors) <= 4
        for survivor in bbc_survivors:
            assert survivor['final_score'] >= 0.75  # High-quality evidence

    def test_no_capping_when_already_diverse(self, capper):
        """Test: No changes when all domains already below threshold"""
        diverse_evidence = [
            {"url": "https://bbc.com/article1", "snippet": "BBC", "final_score": 0.9},
            {"url": "https://cnn.com/article1", "snippet": "CNN", "final_score": 0.85},
            {"url": "https://reuters.com/article1", "snippet": "Reuters", "final_score": 0.8},
            {"url": "https://apnews.com/article1", "snippet": "AP", "final_score": 0.75},
            {"url": "https://nytimes.com/article1", "snippet": "NYT", "final_score": 0.7}
        ]

        result = capper.apply_caps(diverse_evidence, target_count=5)

        # Assert: All evidence preserved
        assert len(result) == 5
        assert result == diverse_evidence

    def test_edge_case_small_evidence_set(self, capper):
        """Test: Handles small evidence sets (< target_count)"""
        small_evidence = [
            {"url": "https://bbc.com/article1", "snippet": "BBC 1", "final_score": 0.9},
            {"url": "https://bbc.com/article2", "snippet": "BBC 2", "final_score": 0.8}
        ]

        result = capper.apply_caps(small_evidence, target_count=5)

        # Assert: Both preserved (too few to cap)
        assert len(result) == 2

    def test_edge_case_single_domain(self, capper):
        """Test: Handles case where all evidence from one domain"""
        single_domain = [
            {"url": "https://bbc.com/article1", "snippet": "BBC 1", "final_score": 0.95},
            {"url": "https://bbc.com/article2", "snippet": "BBC 2", "final_score": 0.90},
            {"url": "https://bbc.com/article3", "snippet": "BBC 3", "final_score": 0.85},
            {"url": "https://bbc.com/article4", "snippet": "BBC 4", "final_score": 0.80},
            {"url": "https://bbc.com/article5", "snippet": "BBC 5", "final_score": 0.75}
        ]

        result = capper.apply_caps(single_domain, target_count=5)

        # Assert: Capped to max_per_domain (3)
        assert len(result) == 3
        # Assert: Top 3 by quality
        assert result[0]['final_score'] == 0.95
        assert result[1]['final_score'] == 0.90
        assert result[2]['final_score'] == 0.85

    def test_diversity_metrics_calculation(self, capper):
        """Test: Diversity metrics calculated correctly"""
        evidence = [
            {"url": "https://bbc.com/1"},
            {"url": "https://reuters.com/1"},
            {"url": "https://theguardian.com/1"},
        ]

        metrics = capper.get_diversity_metrics(evidence)

        assert metrics["unique_domains"] == 3
        assert metrics["max_domain_ratio"] == pytest.approx(0.33, abs=0.01)
        assert metrics["diversity_score"] > 0.6  # High diversity
        assert "domain_distribution" in metrics

    def test_diversity_metrics_empty_evidence(self, capper):
        """Test: Handles empty evidence list gracefully"""
        metrics = capper.get_diversity_metrics([])

        assert metrics["unique_domains"] == 0
        assert metrics["max_domain_ratio"] == 0
        assert metrics["diversity_score"] == 0
        assert metrics["domain_distribution"] == {}

    def test_extract_domain_removes_www(self, capper):
        """Test: www. prefix is correctly removed"""
        domain = capper._extract_domain("https://www.bbc.com/news/article")
        assert domain == "bbc.com"

    def test_extract_domain_handles_subdomains(self, capper):
        """Test: Subdomains are preserved but www is removed"""
        domain = capper._extract_domain("https://news.bbc.co.uk/article")
        assert domain == "news.bbc.co.uk"

    def test_extract_domain_invalid_url(self, capper):
        """Test: Invalid URLs return 'unknown' without crashing"""
        domain = capper._extract_domain("not-a-valid-url")
        assert domain == "unknown"
