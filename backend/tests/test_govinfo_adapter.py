"""
Tests for GovInfo.gov API Adapter (Phase 4/5 Integration)

Verifies that US legal statute claims correctly route to GovInfo.gov API
through the Phase 5 adapter system.
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from app.services.api_adapters import GovInfoAdapter
from app.utils.legal_claim_detector import LegalClaimDetector


class TestGovInfoAdapter:
    """Test GovInfoAdapter routing and integration"""

    def setup_method(self):
        """Setup test fixtures"""
        self.adapter = GovInfoAdapter()
        self.detector = LegalClaimDetector()

    def test_adapter_domain_matching_law_us(self):
        """Test adapter matches Law domain with US jurisdiction"""
        assert self.adapter.is_relevant_for_domain("Law", "US") is True

    def test_adapter_rejects_law_uk(self):
        """Test adapter rejects Law domain with UK jurisdiction"""
        assert self.adapter.is_relevant_for_domain("Law", "UK") is False

    def test_adapter_rejects_other_domains(self):
        """Test adapter rejects non-Law domains"""
        assert self.adapter.is_relevant_for_domain("Finance", "US") is False
        assert self.adapter.is_relevant_for_domain("Health", "US") is False
        assert self.adapter.is_relevant_for_domain("Government", "US") is False

    def test_legal_claim_classification_1966_act(self):
        """Test legal claim with 'Act of YYYY' format is classified correctly"""
        claim = "The National Historic Preservation Act of 1966 exempts the White House from its provisions."

        result = self.detector.classify(claim)

        assert result["claim_type"] == "legal", f"Expected 'legal' but got '{result['claim_type']}'"
        assert result["is_legal"] is True

        metadata = result.get("metadata", {})
        assert metadata["year"] == "1966", f"Expected year 1966 but got {metadata.get('year')}"
        assert metadata["jurisdiction"] in ["US", None]

    def test_legal_claim_classification_1952_federal_law(self):
        """Test legal claim with 'YYYY federal law' format"""
        claim = "A 1952 federal law requires the administration to submit new construction plans."

        result = self.detector.classify(claim)

        assert result["claim_type"] == "legal"
        metadata = result.get("metadata", {})
        assert metadata["year"] == "1952"
        assert metadata["jurisdiction"] == "US"

    @patch('app.services.api_adapters.LegalSearchService')
    def test_adapter_search_calls_legal_service(self, mock_legal_service_class):
        """Test adapter search() method calls LegalSearchService correctly"""
        # Setup mock
        mock_service = Mock()
        mock_legal_service_class.return_value = mock_service

        # Mock async search_statutes to return mock results
        async def mock_search_statutes(query, metadata):
            return [
                {
                    "title": "National Historic Preservation Act - Section 107",
                    "text": "The White House, Capitol, and Supreme Court are exempt...",
                    "url": "https://api.govinfo.gov/...",
                    "source_date": "1966-10-15",
                    "citation": "54 USC 306107",
                    "jurisdiction": "US"
                }
            ]

        mock_service.search_statutes = mock_search_statutes

        # Create adapter with mocked service
        adapter = GovInfoAdapter()
        adapter.legal_service = mock_service

        # Test search
        claim = "The National Historic Preservation Act of 1966 exempts the White House."
        results = adapter.search(claim, "Law", "US")

        # Verify results were transformed correctly
        assert len(results) > 0
        assert results[0]["credibility_score"] == 0.95  # Legal statutes get high credibility
        assert results[0]["external_source_provider"] == "GovInfo.gov"

    def test_adapter_skips_non_legal_claims(self):
        """Test adapter returns empty for non-legal claims"""
        # This is a factual claim, not a legal one
        claim = "The unemployment rate increased to 5.2% in January 2024."

        results = self.adapter.search(claim, "Law", "US")

        # Should return empty because claim is not classified as legal
        assert len(results) == 0

    def test_adapter_skips_wrong_jurisdiction(self):
        """Test adapter returns empty for wrong jurisdiction"""
        claim = "The National Historic Preservation Act of 1966 exempts the White House."

        # Try to search with UK jurisdiction (should be rejected)
        results = self.adapter.search(claim, "Law", "UK")

        assert len(results) == 0


class TestGovInfoIntegration:
    """Test end-to-end integration of GovInfo adapter"""

    def test_legal_claim_gets_legal_classification(self):
        """Test that legal claims are classified correctly for routing"""
        from app.utils.legal_claim_detector import LegalClaimDetector

        detector = LegalClaimDetector()
        claim = "The National Historic Preservation Act of 1966 exempts the White House."

        # Classify claim - this is what retrieve.py checks FIRST
        classification = detector.classify(claim)
        assert classification["claim_type"] == "legal"
        assert classification["is_legal"] is True

        # Extract legal metadata (year, jurisdiction, etc.)
        metadata = classification.get("metadata", {})
        assert metadata.get("year") == "1966"
        assert metadata.get("jurisdiction") in ["US", None]

        # NOTE: Domain detection is handled by article_classification at extraction time,
        # but retrieve.py checks claim_type=="legal" FIRST,
        # so legal claims still route correctly to Law domain adapters.

    def test_multiple_legal_patterns(self):
        """Test various legal claim patterns"""
        detector = LegalClaimDetector()

        test_claims = [
            ("The National Historic Preservation Act of 1966 exempts the White House", "legal"),
            ("A 1952 federal law requires submission to NCPC", "legal"),
            ("Section 230 of the Communications Decency Act protects platforms", "legal"),
            ("42 USC 1983 allows citizens to sue state officials", "legal"),
            ("The statute requires environmental review", "legal"),
        ]

        for claim_text, expected_type in test_claims:
            result = detector.classify(claim_text)
            assert result["claim_type"] == expected_type, \
                f"Claim '{claim_text[:50]}...' expected {expected_type}, got {result['claim_type']}"


class TestGovInfoAdapterRegistry:
    """Test that GovInfo adapter is properly registered"""

    def test_adapter_registered_when_api_key_present(self):
        """Test adapter is registered when GOVINFO_API_KEY is configured"""
        from app.services.government_api_client import get_api_registry
        import os

        # Only test if API key is configured
        if not os.getenv("GOVINFO_API_KEY"):
            pytest.skip("GOVINFO_API_KEY not configured")

        registry = get_api_registry()
        adapters = registry.get_adapters_for_domain("Law", "US")

        # Should find at least one adapter (GovInfo)
        adapter_names = [adapter.api_name for adapter in adapters]
        assert "GovInfo.gov" in adapter_names, \
            f"GovInfo.gov not found in registered adapters: {adapter_names}"

    def test_adapter_matches_law_us_jurisdiction(self):
        """Test that GovInfo adapter is returned for Law/US queries"""
        from app.services.government_api_client import get_api_registry
        import os

        if not os.getenv("GOVINFO_API_KEY"):
            pytest.skip("GOVINFO_API_KEY not configured")

        registry = get_api_registry()
        adapters = registry.get_adapters_for_domain("Law", "US")

        # Find GovInfo adapter
        govinfo_adapter = next(
            (a for a in adapters if a.api_name == "GovInfo.gov"),
            None
        )

        assert govinfo_adapter is not None, "GovInfo adapter should be registered for Law/US"
        assert govinfo_adapter.is_relevant_for_domain("Law", "US") is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
