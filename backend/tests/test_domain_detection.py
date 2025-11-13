"""
Unit Tests for Domain Detection
Phase 5: Government API Integration

Tests for ClaimClassifier.detect_domain() method.
Validates 82-87% routing accuracy as per plan.
"""

import pytest
from app.utils.claim_classifier import ClaimClassifier


@pytest.fixture
def classifier():
    """Create ClaimClassifier instance for tests."""
    return ClaimClassifier()


class TestDomainDetection:
    """Test suite for domain detection functionality."""

    # ========== FINANCE DOMAIN ==========

    def test_finance_domain_uk_unemployment(self, classifier):
        """Test Finance domain detection for UK unemployment claim."""
        claim = "UK unemployment is 5.2%"
        result = classifier.detect_domain(claim)

        assert result["domain"] == "Finance"
        assert result["jurisdiction"] == "UK"
        assert result["domain_confidence"] >= 0.5
        assert "unemployment" in [e.lower() for e in result["key_entities"]]

    def test_finance_domain_gdp_growth(self, classifier):
        """Test Finance domain detection for GDP claim."""
        claim = "GDP growth reached 2.1% in Q4"
        result = classifier.detect_domain(claim)

        assert result["domain"] == "Finance"
        assert result["domain_confidence"] >= 0.5

    def test_finance_domain_inflation(self, classifier):
        """Test Finance domain detection for inflation claim."""
        claim = "Inflation is at 3.2% according to the ONS"
        result = classifier.detect_domain(claim)

        assert result["domain"] == "Finance"
        assert result["jurisdiction"] == "UK"  # ONS is UK entity
        assert "ons" in [e.lower() for e in result["key_entities"]]

    def test_finance_domain_us_fed(self, classifier):
        """Test Finance domain with US Federal Reserve."""
        claim = "The Federal Reserve raised interest rates by 0.25%"
        result = classifier.detect_domain(claim)

        assert result["domain"] == "Finance"
        assert result["jurisdiction"] == "US"
        assert "federal reserve" in [e.lower() for e in result["key_entities"]]

    # ========== HEALTH DOMAIN ==========

    def test_health_domain_nhs(self, classifier):
        """Test Health domain detection for NHS claim."""
        claim = "The NHS reported 1000 new COVID cases yesterday"
        result = classifier.detect_domain(claim)

        assert result["domain"] == "Health"
        assert result["jurisdiction"] == "UK"
        assert "nhs" in [e.lower() for e in result["key_entities"]]

    def test_health_domain_who(self, classifier):
        """Test Health domain detection for WHO claim."""
        claim = "WHO declared COVID-19 a pandemic"
        result = classifier.detect_domain(claim)

        assert result["domain"] == "Health"
        assert result["jurisdiction"] == "Global"
        assert "who" in [e.lower() for e in result["key_entities"]]

    def test_health_domain_vaccine(self, classifier):
        """Test Health domain for vaccine claim."""
        claim = "COVID vaccine is 95% effective according to clinical trials"
        result = classifier.detect_domain(claim)

        assert result["domain"] == "Health"

    def test_health_domain_medical_treatment(self, classifier):
        """Test Health domain for medical treatment claim."""
        claim = "New cancer treatment shows promising results in hospital trials"
        result = classifier.detect_domain(claim)

        assert result["domain"] == "Health"

    # ========== GOVERNMENT DOMAIN ==========

    def test_government_domain_parliament(self, classifier):
        """Test Government domain for UK Parliament claim."""
        claim = "UK Parliament passed new legislation on climate change"
        result = classifier.detect_domain(claim)

        assert result["domain"] == "Government"
        assert result["jurisdiction"] == "UK"

    def test_government_domain_companies_house(self, classifier):
        """Test Government domain for Companies House claim."""
        claim = "Companies House registered 500000 new businesses in 2024"
        result = classifier.detect_domain(claim)

        assert result["domain"] == "Government"
        assert result["jurisdiction"] == "UK"
        assert "companies house" in [e.lower() for e in result["key_entities"]]

    def test_government_domain_policy(self, classifier):
        """Test Government domain for policy claim."""
        claim = "Government announced new policy on immigration"
        result = classifier.detect_domain(claim)

        assert result["domain"] == "Government"

    # ========== CLIMATE DOMAIN ==========

    def test_climate_domain_temperature(self, classifier):
        """Test Climate domain for temperature claim."""
        claim = "Global temperature increased by 1.5 degrees Celsius"
        result = classifier.detect_domain(claim)

        assert result["domain"] == "Climate"

    def test_climate_domain_met_office(self, classifier):
        """Test Climate domain with Met Office."""
        claim = "Met Office forecasts record temperatures this summer"
        result = classifier.detect_domain(claim)

        assert result["domain"] == "Climate"
        assert result["jurisdiction"] == "UK"

    # ========== SCIENCE DOMAIN ==========

    def test_science_domain_research(self, classifier):
        """Test Science domain for research claim."""
        claim = "Study published in Nature shows breakthrough in quantum computing"
        result = classifier.detect_domain(claim)

        assert result["domain"] == "Science"

    def test_science_domain_pubmed(self, classifier):
        """Test Science domain with PubMed."""
        claim = "PubMed database contains over 30 million research articles"
        result = classifier.detect_domain(claim)

        assert result["domain"] == "Science"

    # ========== DEMOGRAPHICS DOMAIN ==========

    def test_demographics_domain_census(self, classifier):
        """Test Demographics domain for census claim."""
        claim = "UK Census shows population growth of 6.3% since 2011"
        result = classifier.detect_domain(claim)

        assert result["domain"] == "Demographics"
        assert result["jurisdiction"] == "UK"

    def test_demographics_domain_population(self, classifier):
        """Test Demographics domain for population claim."""
        claim = "Population of London reached 9 million in 2024"
        result = classifier.detect_domain(claim)

        assert result["domain"] == "Demographics"

    # ========== LAW DOMAIN ==========

    def test_law_domain_legislation(self, classifier):
        """Test Law domain for legislation claim."""
        claim = "Section 230 of Communications Decency Act protects online platforms"
        result = classifier.detect_domain(claim)

        assert result["domain"] == "Law"
        assert result["jurisdiction"] == "US"

    def test_law_domain_court(self, classifier):
        """Test Law domain for court claim."""
        claim = "Supreme Court ruled on landmark case"
        result = classifier.detect_domain(claim)

        assert result["domain"] == "Law"

    # ========== GENERAL DOMAIN (FALLBACK) ==========

    def test_general_domain_ambiguous(self, classifier):
        """Test General domain for ambiguous claim."""
        claim = "The weather is nice today"
        result = classifier.detect_domain(claim)

        # This is not a verifiable claim, should default to General
        assert result["domain"] == "General"
        assert result["domain_confidence"] <= 0.5

    def test_general_domain_opinion(self, classifier):
        """Test General domain for opinion claim."""
        claim = "The movie was excellent"
        result = classifier.detect_domain(claim)

        assert result["domain"] == "General"

    # ========== MULTI-DOMAIN CLAIMS ==========

    def test_multi_domain_health_finance(self, classifier):
        """Test multi-domain claim (Health + Finance)."""
        claim = "NHS spending on mental health increased by 10%"
        result = classifier.detect_domain(claim)

        # Should pick the HIGHEST scoring domain
        assert result["domain"] in ["Health", "Finance", "Government"]
        # Multi-domain claims are expected to have lower confidence
        # This is a known limitation (13-18% routing error rate)

    def test_multi_domain_climate_government(self, classifier):
        """Test multi-domain claim (Climate + Government)."""
        claim = "Government spending on climate research doubled"
        result = classifier.detect_domain(claim)

        assert result["domain"] in ["Climate", "Government", "Finance"]

    # ========== JURISDICTION DETECTION ==========

    def test_jurisdiction_uk_explicit(self, classifier):
        """Test UK jurisdiction detection."""
        claim = "UK unemployment rate is 4.2%"
        result = classifier.detect_domain(claim)

        assert result["jurisdiction"] == "UK"

    def test_jurisdiction_us_explicit(self, classifier):
        """Test US jurisdiction detection."""
        claim = "US inflation reached 3.5%"
        result = classifier.detect_domain(claim)

        assert result["jurisdiction"] == "US"

    def test_jurisdiction_global_implicit(self, classifier):
        """Test Global jurisdiction for claims without specific location."""
        claim = "Climate change is accelerating"
        result = classifier.detect_domain(claim)

        assert result["jurisdiction"] == "Global"

    def test_jurisdiction_eu_detection(self, classifier):
        """Test EU jurisdiction detection."""
        claim = "European Union passed GDPR legislation"
        result = classifier.detect_domain(claim)

        assert result["jurisdiction"] == "EU"

    # ========== ENTITY EXTRACTION ==========

    def test_entity_extraction_organizations(self, classifier):
        """Test that key organizations are extracted."""
        claim = "The NHS and WHO collaborated on vaccine distribution"
        result = classifier.detect_domain(claim)

        entities_lower = [e.lower() for e in result["key_entities"]]
        assert "nhs" in entities_lower
        assert "who" in entities_lower

    def test_entity_extraction_numbers(self, classifier):
        """Test that numbers and percentages are captured."""
        claim = "GDP grew by 2.1% in Q4"
        result = classifier.detect_domain(claim)

        # Should have percentage entities
        assert len(result["key_entities"]) > 0

    # ========== CONFIDENCE SCORING ==========

    def test_high_confidence_single_domain(self, classifier):
        """Test that single-domain claims have high confidence."""
        claim = "The Federal Reserve raised interest rates by 0.25%"
        result = classifier.detect_domain(claim)

        assert result["domain"] == "Finance"
        assert result["domain_confidence"] >= 0.7  # High confidence

    def test_low_confidence_ambiguous(self, classifier):
        """Test that ambiguous claims have low confidence."""
        claim = "Things are getting better"
        result = classifier.detect_domain(claim)

        assert result["domain_confidence"] < 0.5  # Low confidence

    # ========== EDGE CASES ==========

    def test_empty_claim(self, classifier):
        """Test handling of empty claim."""
        claim = ""
        result = classifier.detect_domain(claim)

        assert result["domain"] == "General"
        assert result["domain_confidence"] == 0.0

    def test_very_long_claim(self, classifier):
        """Test handling of very long claim."""
        claim = "UK unemployment " * 100  # 200+ words
        result = classifier.detect_domain(claim)

        assert result["domain"] == "Finance"
        # Should still work despite length

    def test_special_characters(self, classifier):
        """Test handling of special characters."""
        claim = "GDP growth is 2.1% (up from 1.5%!!!) according to ONS"
        result = classifier.detect_domain(claim)

        assert result["domain"] == "Finance"
        assert result["jurisdiction"] == "UK"

    def test_case_insensitivity(self, classifier):
        """Test that detection is case-insensitive."""
        claim1 = "NHS reported 1000 cases"
        claim2 = "nhs reported 1000 cases"

        result1 = classifier.detect_domain(claim1)
        result2 = classifier.detect_domain(claim2)

        assert result1["domain"] == result2["domain"]
        assert result1["jurisdiction"] == result2["jurisdiction"]


class TestAccuracyBenchmark:
    """
    Benchmark tests to validate 82-87% routing accuracy.

    These tests use a predefined set of claims with known correct domains.
    """

    BENCHMARK_CLAIMS = [
        # Format: (claim, expected_domain, expected_jurisdiction)
        ("UK unemployment is 5.2%", "Finance", "UK"),
        ("NHS reported 1000 COVID cases", "Health", "UK"),
        ("WHO declared pandemic", "Health", "Global"),
        ("Companies House registered 500000 businesses", "Government", "UK"),
        ("GDP growth is 2.1%", "Finance", "UK"),
        ("Met Office forecasts record temperatures", "Climate", "UK"),
        ("PubMed contains 30 million articles", "Science", "Global"),
        ("UK Census shows population growth", "Demographics", "UK"),
        ("Federal Reserve raised interest rates", "Finance", "US"),
        ("Supreme Court ruled on landmark case", "Law", "US"),
    ]

    def test_routing_accuracy_benchmark(self, classifier):
        """
        Test routing accuracy across benchmark claims.

        Target: 82-87% accuracy (8-9 out of 10 correct)
        """
        correct = 0
        total = len(self.BENCHMARK_CLAIMS)

        for claim, expected_domain, expected_jurisdiction in self.BENCHMARK_CLAIMS:
            result = classifier.detect_domain(claim)

            if result["domain"] == expected_domain and result["jurisdiction"] == expected_jurisdiction:
                correct += 1
            else:
                print(f"MISS: '{claim}' -> Got {result['domain']}/{result['jurisdiction']}, "
                      f"Expected {expected_domain}/{expected_jurisdiction}")

        accuracy = correct / total

        print(f"\nRouting Accuracy: {accuracy:.1%} ({correct}/{total})")

        # Assert 80%+ accuracy (allowing for some variance)
        assert accuracy >= 0.80, f"Routing accuracy {accuracy:.1%} below 80% threshold"


# ========== PERFORMANCE TESTS ==========

class TestPerformance:
    """Test domain detection performance."""

    def test_detection_speed(self, classifier):
        """Test that domain detection is fast (<50ms as per plan)."""
        import time

        claim = "UK unemployment is 5.2%"

        start = time.time()
        for _ in range(10):
            classifier.detect_domain(claim)
        end = time.time()

        avg_time_ms = (end - start) / 10 * 1000

        print(f"\nAverage detection time: {avg_time_ms:.2f}ms")

        # Should be under 50ms per plan (allowing 100ms for CI environments)
        assert avg_time_ms < 100, f"Detection took {avg_time_ms:.2f}ms (target <100ms)"

    def test_lazy_loading(self, classifier):
        """Test that spaCy loads lazily."""
        # Before first call, nlp should be None
        if not hasattr(classifier, '_spacy_loaded'):
            assert classifier.nlp is None

        # After first call, nlp should be loaded
        classifier.detect_domain("Test claim")
        assert classifier.nlp is not None
