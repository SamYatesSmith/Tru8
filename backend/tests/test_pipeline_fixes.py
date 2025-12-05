"""
Test fixes for legal claim detection and routing.

Tests cover:
1. Legal claim detection using LegalClaimDetector
2. Legal claim routing using classification metadata

Note: Opinion recognition tests removed - LLM extraction handles this.
"""
import pytest
from app.utils.legal_claim_detector import LegalClaimDetector


class TestLegalClaimClassification:
    """Test legal claim classification and metadata extraction"""

    def setup_method(self):
        self.detector = LegalClaimDetector()

    def test_legal_claim_1966_act(self):
        """Test legal claim with year and act"""
        claim = "The National Historic Preservation Act of 1966 exempts the White House from its provisions."
        result = self.detector.classify(claim)

        assert result["claim_type"] == "legal", f"Expected 'legal' but got '{result['claim_type']}'"
        assert result["is_legal"] is True

        # Check metadata extraction
        metadata = result.get("metadata", {})
        assert metadata["year"] == "1966", f"Expected year 1966 but got {metadata.get('year')}"
        assert metadata["jurisdiction"] in ["US", None], f"Expected US jurisdiction but got {metadata.get('jurisdiction')}"

    def test_legal_claim_1952_federal_law(self):
        """Test legal claim with year and 'federal law'"""
        claim = "A 1952 federal law requires the administration to submit plans to the National Capital Planning Commission."
        result = self.detector.classify(claim)

        assert result["claim_type"] == "legal"
        assert result["is_legal"] is True

        metadata = result.get("metadata", {})
        assert metadata["year"] == "1952"
        assert metadata["jurisdiction"] == "US"

    def test_legal_claim_usc_citation(self):
        """Test legal claim with US Code citation"""
        claim = "Under 42 USC 1983, individuals can sue state officials for constitutional violations."
        result = self.detector.classify(claim)

        assert result["claim_type"] == "legal"
        assert result["is_legal"] is True

        metadata = result.get("metadata", {})
        assert len(metadata["citations"]) > 0
        assert metadata["citations"][0]["type"] == "USC"
        assert metadata["citations"][0]["title"] == "42"
        assert metadata["citations"][0]["section"] == "1983"

    def test_non_legal_claim(self):
        """Test that non-legal claims are not classified as legal"""
        claim = "The company delivered 1.3 million vehicles in 2022."
        result = self.detector.classify(claim)

        assert result["claim_type"] == "factual"
        assert result["is_legal"] is False


class TestLegalRoutingLogic:
    """Test that legal claims are routed correctly"""

    def test_legal_claim_has_metadata(self):
        """Verify legal claims have required fields for routing"""
        detector = LegalClaimDetector()
        claim_text = "The National Historic Preservation Act of 1966 exempts the White House."

        result = detector.classify(claim_text)

        # Verify all required fields for routing are present
        assert result["claim_type"] == "legal"
        assert result["is_legal"] is True
        assert "metadata" in result
        assert "jurisdiction" in result["metadata"]
        assert result["metadata"]["jurisdiction"] is not None

    def test_legal_metadata_has_year(self):
        """Verify legal metadata includes year for API queries"""
        detector = LegalClaimDetector()
        claim_text = "A 1952 federal law requires submission of plans."

        result = detector.classify(claim_text)

        assert result["claim_type"] == "legal"
        assert result["is_legal"] is True
        assert result["metadata"]["year"] == "1952"
        # Year can be used to construct targeted API queries


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
