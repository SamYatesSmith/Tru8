import pytest
from app.utils.source_independence import SourceIndependenceChecker


class TestSourceIndependence:
    """Test source independence checking - detects media ownership clustering"""

    @pytest.fixture
    def checker(self):
        return SourceIndependenceChecker()

    def test_detects_common_ownership(self, checker):
        """Test: Detects when multiple sources share parent company"""
        evidence = [
            {"url": "https://wsj.com/article1", "snippet": "WSJ evidence"},      # News Corp
            {"url": "https://nypost.com/article1", "snippet": "Post evidence"},  # News Corp
            {"url": "https://foxnews.com/article1", "snippet": "Fox evidence"},  # News Corp
            {"url": "https://bbc.com/article1", "snippet": "BBC evidence"}       # BBC
        ]

        result = checker.enrich_evidence(evidence)
        diversity_score, passes = checker.check_diversity(result, threshold=0.6)

        # Assert: 3 of 4 from News Corp = low diversity
        assert diversity_score < 0.6, "Should detect low diversity"
        assert not passes, "Should fail diversity check"

        # Assert: parent_company field added
        assert result[0].get('parent_company') == 'News Corp'
        assert result[1].get('parent_company') == 'News Corp'

    def test_high_diversity_passes(self, checker):
        """Test: High diversity (different owners) passes check"""
        evidence = [
            {"url": "https://bbc.com/article1", "snippet": "BBC"},           # BBC
            {"url": "https://cnn.com/article1", "snippet": "CNN"},           # CNN (Warner Bros)
            {"url": "https://nytimes.com/article1", "snippet": "NYT"},       # NYT Company
            {"url": "https://reuters.com/article1", "snippet": "Reuters"},   # Thomson Reuters
            {"url": "https://apnews.com/article1", "snippet": "AP"}          # Associated Press
        ]

        result = checker.enrich_evidence(evidence)
        diversity_score, passes = checker.check_diversity(result, threshold=0.6)

        assert diversity_score >= 0.6, "Should pass diversity check"
        assert passes

    def test_independence_flag_assignment(self, checker):
        """Test: Assigns independence flags (corporate/independent/state)"""
        evidence = [
            {"url": "https://reuters.com/article1", "snippet": "Reuters"},         # Corporate
            {"url": "https://rt.com/article1", "snippet": "RT"}                    # State-funded
        ]

        result = checker.enrich_evidence(evidence)

        # Assert: Flags assigned
        assert result[0].get('independence_flag') == 'corporate'
        assert result[1].get('independence_flag') == 'state-funded'

    def test_domain_cluster_assignment(self, checker):
        """Test: Groups domains by parent company"""
        evidence = [
            {"url": "https://wsj.com/a", "snippet": "WSJ"},
            {"url": "https://nypost.com/b", "snippet": "Post"},
            {"url": "https://bbc.com/c", "snippet": "BBC"}
        ]

        result = checker.enrich_evidence(evidence)

        # Assert: WSJ and Post share cluster ID
        assert result[0]['domain_cluster_id'] == result[1]['domain_cluster_id']
        # Assert: BBC has different cluster
        assert result[2]['domain_cluster_id'] != result[0]['domain_cluster_id']

    def test_unknown_domain_handling(self, checker):
        """Test: Unknown domains marked as unknown, not penalized"""
        evidence = [
            {"url": "https://unknownsite123.com/article", "snippet": "Unknown source"}
        ]

        result = checker.enrich_evidence(evidence)

        # Assert: Marked as unknown
        assert result[0].get('parent_company') == 'Unknown'
        assert result[0].get('independence_flag') == 'unknown'

        # Assert: Gets cluster ID
        assert 'domain_cluster_id' in result[0]

    def test_edge_case_single_source(self, checker):
        """Test: Single source always passes (no diversity required)"""
        evidence = [
            {"url": "https://bbc.com/article1", "snippet": "Single evidence"}
        ]

        result = checker.enrich_evidence(evidence)
        diversity_score, passes = checker.check_diversity(result, threshold=0.6)

        # Assert: Single source not penalized
        assert passes, "Single source should pass diversity check"

    def test_diversity_metrics_calculation(self, checker):
        """Test: Diversity metrics calculated correctly"""
        evidence = [
            {"url": "https://bbc.com/1", "snippet": "BBC"},
            {"url": "https://reuters.com/1", "snippet": "Reuters"},
            {"url": "https://theguardian.com/1", "snippet": "Guardian"},
        ]

        result = checker.enrich_evidence(evidence)
        metrics = checker.get_diversity_metrics(result)

        assert metrics["unique_parents"] == 3
        assert metrics["diversity_score"] > 0.6  # High diversity
        assert "parent_distribution" in metrics
        assert "independence_distribution" in metrics

    def test_empty_evidence_handling(self, checker):
        """Test: Handles empty evidence list gracefully"""
        metrics = checker.get_diversity_metrics([])

        assert metrics["unique_parents"] == 0
        assert metrics["diversity_score"] == 0
        assert metrics["parent_distribution"] == {}
