import pytest
from app.utils.deduplication import EvidenceDeduplicator


class TestDeduplication:
    """Test evidence deduplication - eliminates duplicates and syndicated content"""

    @pytest.fixture
    def deduplicator(self):
        return EvidenceDeduplicator()

    def test_exact_duplicate_removal(self, deduplicator):
        """Test: Exact duplicate snippets removed"""
        evidence = [
            {"url": "https://site1.com/a", "snippet": "Climate change is affecting polar bears."},
            {"url": "https://site2.com/b", "snippet": "Climate change is affecting polar bears."},
            {"url": "https://site3.com/c", "snippet": "Different evidence entirely."}
        ]

        result, stats = deduplicator.deduplicate(evidence)

        assert len(result) == 2, "Expected 2 unique evidence items"
        assert stats['duplicates_removed'] == 1

    def test_high_similarity_removal(self, deduplicator):
        """Test: Near-duplicates (>85% similar) removed"""
        evidence = [
            {"url": "https://site1.com/a", "snippet": "The stock market rose by 5% today."},
            {"url": "https://site2.com/b", "snippet": "The stock market increased by 5% today."},  # Very similar
            {"url": "https://site3.com/c", "snippet": "Unemployment rates fell to 3%."}  # Different
        ]

        result, stats = deduplicator.deduplicate(evidence)

        assert len(result) == 2, "Expected high-similarity duplicate removed"
        assert stats['duplicates_removed'] >= 1

    def test_preserves_highest_credibility(self, deduplicator):
        """Test: When deduplicating, keeps highest credibility source"""
        evidence = [
            {"url": "https://highcred.com/a", "snippet": "The study found X.", "credibility_score": 0.9, "final_score": 0.9},
            {"url": "https://lowcred.com/b", "snippet": "The study found X.", "credibility_score": 0.5, "final_score": 0.5}
        ]

        result, stats = deduplicator.deduplicate(evidence)

        assert len(result) == 1
        # Should keep the first one (higher score, comes first in sorted list)
        assert result[0]['credibility_score'] == 0.9, "Should keep higher credibility source"

    def test_no_removal_when_all_unique(self, deduplicator):
        """Test: No changes when all evidence unique"""
        evidence = [
            {"url": "https://site1.com/a", "snippet": "Evidence A about topic 1."},
            {"url": "https://site2.com/b", "snippet": "Evidence B about topic 2."},
            {"url": "https://site3.com/c", "snippet": "Evidence C about topic 3."}
        ]

        result, stats = deduplicator.deduplicate(evidence)

        assert len(result) == 3
        assert stats['duplicates_removed'] == 0

    def test_content_hash_storage(self, deduplicator):
        """Test: Content hashes stored for future comparison"""
        evidence = [
            {"url": "https://site1.com/a", "snippet": "Test snippet for hashing."}
        ]

        result, stats = deduplicator.deduplicate(evidence)

        # Assert: Hash added to evidence
        assert 'content_hash' in result[0]
        assert len(result[0]['content_hash']) == 32  # MD5 hex length

    def test_syndicated_content_detection(self, deduplicator):
        """Test: Syndicated content (same text, different URL) marked"""
        evidence = [
            {"url": "https://original.com/a", "snippet": "BREAKING: Major event occurred today."},
            {"url": "https://syndicated.com/b", "snippet": "BREAKING: Major event occurred today."}
        ]

        result, stats = deduplicator.deduplicate(evidence)

        # Should keep only one
        assert len(result) == 1
        # First one kept, should NOT be marked as syndicated
        assert result[0].get('is_syndicated') == False

    def test_hash_normalization(self, deduplicator):
        """Test: Hash normalization handles case and whitespace"""
        text1 = "The Quick Brown Fox"
        text2 = "THE QUICK  BROWN   FOX"  # Different case, extra spaces

        hash1 = deduplicator._hash_content(text1)
        hash2 = deduplicator._hash_content(text2)

        assert hash1 == hash2, "Hashes should match after normalization"

    def test_hash_normalization_punctuation(self, deduplicator):
        """Test: Hash normalization removes punctuation"""
        text1 = "Hello, world!"
        text2 = "Hello world"

        hash1 = deduplicator._hash_content(text1)
        hash2 = deduplicator._hash_content(text2)

        assert hash1 == hash2, "Hashes should match after punctuation removal"

    def test_empty_evidence_list(self, deduplicator):
        """Test: Handles empty evidence list gracefully"""
        result, stats = deduplicator.deduplicate([])

        assert result == []
        assert stats['duplicates_removed'] == 0

    def test_single_evidence_item(self, deduplicator):
        """Test: Single item returns unchanged"""
        evidence = [{"url": "https://site.com", "snippet": "Single item"}]

        result, stats = deduplicator.deduplicate(evidence)

        assert len(result) == 1
        assert stats['duplicates_removed'] == 0

    def test_dedup_metrics_calculation(self, deduplicator):
        """Test: Dedup metrics calculated correctly"""
        metrics = deduplicator.get_dedup_metrics(original_count=10, final_count=7)

        assert metrics['duplicates_found'] == 3
        assert metrics['dedup_percentage'] == 30.0
        assert metrics['efficiency_gain'] == 0.3

    def test_dedup_metrics_no_duplicates(self, deduplicator):
        """Test: Metrics correct when no duplicates"""
        metrics = deduplicator.get_dedup_metrics(original_count=5, final_count=5)

        assert metrics['duplicates_found'] == 0
        assert metrics['dedup_percentage'] == 0.0
        assert metrics['efficiency_gain'] == 0.0
