"""
Legal Claim Detector Tests

Tests legal claim detection and statute metadata extraction.
Simplified from full claim classification - only tests legal detection.
"""

import pytest
from app.utils.legal_claim_detector import LegalClaimDetector


class TestLegalClaimDetector:
    """Test legal claim detection and metadata extraction"""

    @pytest.fixture
    def detector(self):
        return LegalClaimDetector()

    # ============ Basic Detection Tests ============

    def test_factual_claim_not_legal(self, detector):
        """Test: Non-legal factual claims are classified as factual"""
        test_cases = [
            "Biden is the president of the United States",
            "Water boils at 100 degrees Celsius",
            "The population of Tokyo is 14 million",
            "Shakespeare wrote Hamlet in 1600"
        ]

        for claim in test_cases:
            result = detector.classify(claim)
            assert result["claim_type"] == "factual", f"Failed for: {claim}"
            assert result["is_legal"] == False

    def test_is_legal_flag(self, detector):
        """Test: is_legal flag correctly identifies legal claims"""
        legal_claim = "42 USC 1983 protects civil rights"
        non_legal_claim = "The sky is blue"

        legal_result = detector.classify(legal_claim)
        non_legal_result = detector.classify(non_legal_claim)

        assert legal_result["is_legal"] == True
        assert non_legal_result["is_legal"] == False

    # ============ Legal Claim Tests ============

    def test_legal_detection_usc_citations(self, detector):
        """Test: Detects US Code citations"""
        test_cases = [
            "42 USC 1983 protects civil rights",
            "The law is codified in 42 U.S.C. 1983",
            "Under 18 USC 1001, lying to federal agents is illegal",
        ]

        for claim in test_cases:
            result = detector.classify(claim)
            assert result["claim_type"] == "legal", f"Failed to detect legal claim: {claim}"
            assert result["is_legal"] == True
            assert "metadata" in result

    def test_legal_detection_uk_legislation(self, detector):
        """Test: Detects UK legislation citations"""
        test_cases = [
            "ukpga 2010/15 defines the requirements",
            "Under uksi 2020/1234, businesses must comply",
        ]

        for claim in test_cases:
            result = detector.classify(claim)
            assert result["claim_type"] == "legal", f"Failed to detect UK legal claim: {claim}"
            assert result["is_legal"] == True

    def test_legal_detection_public_law(self, detector):
        """Test: Detects Public Law citations"""
        test_cases = [
            "Public Law 117-58 allocated $1 trillion for infrastructure",
            "Pub. L. 117-58 was signed in November 2021",
        ]

        for claim in test_cases:
            result = detector.classify(claim)
            assert result["claim_type"] == "legal", f"Failed to detect Public Law: {claim}"
            assert result["is_legal"] == True

    def test_legal_detection_bill_references(self, detector):
        """Test: Detects bill references"""
        test_cases = [
            "H.R. 1234 was introduced in Congress",
            "S. 456 is currently in committee",
        ]

        for claim in test_cases:
            result = detector.classify(claim)
            assert result["claim_type"] == "legal", f"Failed to detect bill reference: {claim}"
            assert result["is_legal"] == True

    def test_legal_detection_year_law_pattern(self, detector):
        """Test: Detects year + law patterns"""
        test_cases = [
            "The 1952 federal law created the National Capital Planning Commission",
            "A 2010 statute requires environmental reviews",
        ]

        for claim in test_cases:
            result = detector.classify(claim)
            assert result["claim_type"] == "legal", f"Failed to detect year+law pattern: {claim}"
            assert result["is_legal"] == True

    def test_legal_detection_general_legal_language(self, detector):
        """Test: Detects general legal references"""
        test_cases = [
            "According to the law, this is required",
            "The statute requires annual reporting",
            "This is illegal under federal law",
        ]

        for claim in test_cases:
            result = detector.classify(claim)
            assert result["claim_type"] == "legal", f"Failed to detect legal language: {claim}"
            assert result["is_legal"] == True

    # ============ Metadata Extraction Tests ============

    def test_legal_metadata_extraction_usc(self, detector):
        """Test: Extracts USC citation metadata"""
        claim = "42 USC 1983 protects civil rights"
        result = detector.classify(claim)

        assert result["claim_type"] == "legal"
        assert "metadata" in result
        assert len(result["metadata"]["citations"]) > 0
        citation = result["metadata"]["citations"][0]
        assert citation["type"] == "USC"
        assert citation["title"] == "42"
        assert citation["section"] == "1983"
        assert result["metadata"]["jurisdiction"] == "US"
        assert result["metadata"]["statute_type"] == "federal"

    def test_legal_metadata_extraction_uk(self, detector):
        """Test: Extracts UK legislation metadata"""
        claim = "ukpga 2010/15 defines the requirements"
        result = detector.classify(claim)

        assert result["claim_type"] == "legal"
        assert result["metadata"]["jurisdiction"] == "UK"
        assert result["metadata"]["year"] == "2010"

    def test_legal_metadata_extraction_public_law(self, detector):
        """Test: Extracts Public Law metadata"""
        claim = "Public Law 117-58 allocated infrastructure funding"
        result = detector.classify(claim)

        assert result["claim_type"] == "legal"
        assert len(result["metadata"]["citations"]) > 0
        citation = result["metadata"]["citations"][0]
        assert citation["type"] == "Public Law"
        assert citation["congress"] == "117"
        assert citation["number"] == "58"

    def test_legal_metadata_extraction_bill(self, detector):
        """Test: Extracts bill reference metadata"""
        claim = "H.R. 1234 was introduced in Congress"
        result = detector.classify(claim)

        assert result["claim_type"] == "legal"
        assert len(result["metadata"]["citations"]) > 0
        citation = result["metadata"]["citations"][0]
        assert citation["type"] == "Bill"
        assert citation["chamber"] == "House"
        assert citation["number"] == "1234"

    def test_legal_jurisdiction_detection_us(self, detector):
        """Test: Correctly detects US jurisdiction"""
        test_cases = [
            ("Congress passed the law", "US"),
            ("The federal statute requires it", "US"),
        ]

        for claim, expected_jurisdiction in test_cases:
            result = detector.classify(claim)
            if result["is_legal"]:
                assert result["metadata"]["jurisdiction"] == expected_jurisdiction

    def test_legal_jurisdiction_detection_uk(self, detector):
        """Test: Correctly detects UK jurisdiction"""
        test_cases = [
            ("Parliament enacted the legislation", "UK"),
            ("The British law requires it", "UK"),
            ("Westminster approved the statute", "UK")
        ]

        for claim, expected_jurisdiction in test_cases:
            result = detector.classify(claim)
            if result["is_legal"]:
                assert result["metadata"]["jurisdiction"] == expected_jurisdiction

    def test_legal_multiple_citations(self, detector):
        """Test: Handles claims with multiple legal citations"""
        claim = "42 USC 1983 and 18 USC 1001 both apply to this case"
        result = detector.classify(claim)

        assert result["claim_type"] == "legal"
        assert result["is_legal"] == True
        assert len(result["metadata"]["citations"]) >= 2

    def test_legal_confidence_scores(self, detector):
        """Test: Legal claims have appropriate confidence scores"""
        test_cases = [
            "42 USC 1983 protects civil rights",
            "The 1952 federal law created the commission",
        ]

        for claim in test_cases:
            result = detector.classify(claim)
            assert result["confidence"] >= 0.8, f"Low confidence for: {claim}"

    def test_case_insensitivity(self, detector):
        """Test: Detection is case-insensitive"""
        test_cases = [
            "42 usc 1983 protects civil rights",
            "42 USC 1983 PROTECTS CIVIL RIGHTS",
            "UKPGA 2010/15 defines requirements"
        ]

        for claim in test_cases:
            result = detector.classify(claim)
            assert result["is_legal"] == True, f"Failed for: {claim}"

    def test_reason_field_present(self, detector):
        """Test: All results include reason field"""
        test_claims = [
            "42 USC 1983 protects civil rights",
            "The sky is blue"
        ]

        for claim in test_claims:
            result = detector.classify(claim)
            assert "reason" in result
            assert isinstance(result["reason"], str)
            assert len(result["reason"]) > 0
