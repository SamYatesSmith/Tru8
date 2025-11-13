"""
Test fixes for opinion recognition and legal routing.

Tests cover:
1. Opinion recognition with expanded patterns
2. Legal claim routing using classification metadata
"""
import pytest
from app.utils.claim_classifier import ClaimClassifier


class TestOpinionRecognition:
    """Test expanded opinion recognition patterns"""

    def setup_method(self):
        self.classifier = ClaimClassifier()

    def test_opinion_is_considered_pattern(self):
        """Test 'is considered' pattern catches subjective judgments"""
        claim = "The demolition of the East Wing is considered one of the most substantial alterations."
        result = self.classifier.classify(claim)

        assert result["claim_type"] == "opinion", f"Expected 'opinion' but got '{result['claim_type']}'"
        assert result["is_verifiable"] is False
        assert "opinion" in result["reason"].lower()

    def test_opinion_one_of_the_most_pattern(self):
        """Test 'one of the most' pattern catches comparative rankings"""
        claim = "This is one of the most important events in history."
        result = self.classifier.classify(claim)

        assert result["claim_type"] == "opinion"
        assert result["is_verifiable"] is False

    def test_opinion_most_substantial_pattern(self):
        """Test superlative judgments are caught"""
        claim = "The change was most substantial in modern history."
        result = self.classifier.classify(claim)

        assert result["claim_type"] == "opinion"
        assert result["is_verifiable"] is False

    def test_opinion_regarded_as_pattern(self):
        """Test 'regarded as' subjective judgment"""
        claim = "The policy is regarded as the most effective approach."
        result = self.classifier.classify(claim)

        assert result["claim_type"] == "opinion"
        assert result["is_verifiable"] is False

    def test_opinion_arguably_pattern(self):
        """Test hedging words indicate opinion"""
        claim = "This was arguably the best decision ever made."
        result = self.classifier.classify(claim)

        assert result["claim_type"] == "opinion"
        assert result["is_verifiable"] is False

    def test_factual_claim_still_verifiable(self):
        """Ensure factual claims are still classified correctly"""
        claim = "The National Historic Preservation Act was passed in 1966."
        result = self.classifier.classify(claim)

        # This should be legal, not opinion
        assert result["claim_type"] in ["legal", "factual"]
        assert result["is_verifiable"] is True


class TestLegalClaimClassification:
    """Test legal claim classification and metadata extraction"""

    def setup_method(self):
        self.classifier = ClaimClassifier()

    def test_legal_claim_1966_act(self):
        """Test legal claim with year and act"""
        claim = "The National Historic Preservation Act of 1966 exempts the White House from its provisions."
        result = self.classifier.classify(claim)

        assert result["claim_type"] == "legal", f"Expected 'legal' but got '{result['claim_type']}'"
        assert result["is_verifiable"] is True

        # Check metadata extraction
        metadata = result.get("metadata", {})
        assert metadata["year"] == "1966", f"Expected year 1966 but got {metadata.get('year')}"
        assert metadata["jurisdiction"] in ["US", None], f"Expected US jurisdiction but got {metadata.get('jurisdiction')}"

    def test_legal_claim_1952_federal_law(self):
        """Test legal claim with year and 'federal law'"""
        claim = "A 1952 federal law requires the administration to submit plans to the National Capital Planning Commission."
        result = self.classifier.classify(claim)

        assert result["claim_type"] == "legal"
        assert result["is_verifiable"] is True

        metadata = result.get("metadata", {})
        assert metadata["year"] == "1952"
        assert metadata["jurisdiction"] == "US"

    def test_legal_claim_usc_citation(self):
        """Test legal claim with US Code citation"""
        claim = "Under 42 USC 1983, individuals can sue state officials for constitutional violations."
        result = self.classifier.classify(claim)

        assert result["claim_type"] == "legal"
        assert result["is_verifiable"] is True

        metadata = result.get("metadata", {})
        assert len(metadata["citations"]) > 0
        assert metadata["citations"][0]["type"] == "USC"
        assert metadata["citations"][0]["title"] == "42"
        assert metadata["citations"][0]["section"] == "1983"

    def test_non_legal_claim(self):
        """Test that non-legal claims are not classified as legal"""
        claim = "The company delivered 1.3 million vehicles in 2022."
        result = self.classifier.classify(claim)

        assert result["claim_type"] == "factual"
        assert result["is_verifiable"] is True


class TestLegalRoutingLogic:
    """Test that legal claims are routed correctly"""

    def test_legal_claim_has_metadata(self):
        """Verify legal claims have required fields for routing"""
        classifier = ClaimClassifier()
        claim_text = "The National Historic Preservation Act of 1966 exempts the White House."

        result = classifier.classify(claim_text)

        # Verify all required fields for routing are present
        assert result["claim_type"] == "legal"
        assert "metadata" in result
        assert "jurisdiction" in result["metadata"]
        assert result["metadata"]["jurisdiction"] is not None

    def test_legal_metadata_has_year(self):
        """Verify legal metadata includes year for API queries"""
        classifier = ClaimClassifier()
        claim_text = "A 1952 federal law requires submission of plans."

        result = classifier.classify(claim_text)

        assert result["claim_type"] == "legal"
        assert result["metadata"]["year"] == "1952"
        # Year can be used to construct targeted API queries


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
