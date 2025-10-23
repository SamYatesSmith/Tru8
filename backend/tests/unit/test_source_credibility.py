"""
Unit tests for Source Credibility Service

Phase 3 - Week 9: Domain Credibility Framework
Tests tier matching, risk assessment, wildcard patterns, and edge cases.
"""

import pytest
from app.services.source_credibility import SourceCredibilityService, get_credibility_service


class TestSourceCredibilityService:
    """Test suite for SourceCredibilityService"""

    def setup_method(self):
        """Create fresh service instance for each test"""
        self.service = SourceCredibilityService()
        self.service.clear_cache()  # Ensure clean state

    # ========== TIER MATCHING TESTS ==========

    def test_matches_academic_domain(self):
        """Should match academic institutions"""
        result = self.service.get_credibility("MIT", "https://mit.edu/article")

        assert result['tier'] == 'academic'
        assert result['credibility'] == 1.0
        assert result['risk_flags'] == []
        assert result['auto_exclude'] is False

    def test_matches_wildcard_edu_pattern(self):
        """Should match *.edu wildcard pattern"""
        result = self.service.get_credibility("Stanford", "https://stanford.edu/research")

        assert result['tier'] == 'academic'
        assert result['credibility'] == 1.0

    def test_matches_wildcard_ac_uk_pattern(self):
        """Should match *.ac.uk wildcard pattern"""
        result = self.service.get_credibility("Oxford", "https://ox.ac.uk/news")

        assert result['tier'] == 'academic'
        assert result['credibility'] == 1.0

    def test_matches_government_domain(self):
        """Should match government sources"""
        result = self.service.get_credibility("CDC", "https://cdc.gov/health")

        assert result['tier'] == 'government'
        assert result['credibility'] == 0.85

    def test_matches_wildcard_gov_pattern(self):
        """Should match *.gov wildcard pattern"""
        result = self.service.get_credibility("EPA", "https://epa.gov/climate")

        assert result['tier'] == 'government'
        assert result['credibility'] == 0.85

    def test_matches_scientific_journal(self):
        """Should match scientific journals"""
        result = self.service.get_credibility("Nature", "https://nature.com/articles/123")

        assert result['tier'] == 'scientific'
        assert result['credibility'] == 0.95

    def test_matches_news_tier1(self):
        """Should match tier 1 news agencies"""
        result = self.service.get_credibility("BBC", "https://bbc.co.uk/news/123")

        assert result['tier'] == 'news_tier1'
        assert result['credibility'] == 0.9

    def test_matches_news_tier2(self):
        """Should match tier 2 news outlets"""
        result = self.service.get_credibility("Guardian", "https://theguardian.com/politics")

        assert result['tier'] == 'news_tier2'
        assert result['credibility'] == 0.8

    def test_matches_reference_source(self):
        """Should match reference sources like Wikipedia"""
        result = self.service.get_credibility("Wikipedia", "https://wikipedia.org/wiki/Test")

        assert result['tier'] == 'reference'
        assert result['credibility'] == 0.85

    def test_matches_factcheck_organization(self):
        """Should match fact-checking organizations"""
        result = self.service.get_credibility("Snopes", "https://snopes.com/fact-check/test")

        assert result['tier'] == 'factcheck'
        assert result['credibility'] == 0.95

    def test_matches_legal_domain(self):
        """Should match legal and court system sources"""
        result = self.service.get_credibility("US Supreme Court", "https://supremecourt.gov/opinions/123")

        assert result['tier'] == 'legal'
        assert result['credibility'] == 0.9
        assert result['risk_flags'] == []
        assert result['auto_exclude'] is False

    def test_matches_legal_database(self):
        """Should match legal database sources"""
        result = self.service.get_credibility("BAILII", "https://bailii.org/uk/cases/123")

        assert result['tier'] == 'legal'
        assert result['credibility'] == 0.9

    def test_matches_uk_judiciary(self):
        """Should match UK court system"""
        result = self.service.get_credibility("UK Judiciary", "https://judiciary.uk/judgments")

        assert result['tier'] == 'legal'
        assert result['credibility'] == 0.9

    def test_matches_technical_standards(self):
        """Should match technical standards bodies"""
        result = self.service.get_credibility("IETF", "https://ietf.org/rfc/rfc9000.txt")

        assert result['tier'] == 'technical'
        assert result['credibility'] == 0.88
        assert result['risk_flags'] == []
        assert result['auto_exclude'] is False

    def test_matches_w3c_standards(self):
        """Should match W3C standards"""
        result = self.service.get_credibility("W3C", "https://w3.org/TR/html5")

        assert result['tier'] == 'technical'
        assert result['credibility'] == 0.88

    def test_matches_technical_documentation(self):
        """Should match official technical documentation"""
        result = self.service.get_credibility("MDN", "https://developer.mozilla.org/docs/Web/API")

        assert result['tier'] == 'technical'
        assert result['credibility'] == 0.88

    def test_matches_professional_body(self):
        """Should match professional associations"""
        result = self.service.get_credibility("IEEE", "https://ieee.org/standards/123")

        assert result['tier'] == 'professional'
        assert result['credibility'] == 0.85
        assert result['risk_flags'] == []
        assert result['auto_exclude'] is False

    def test_matches_medical_professional_body(self):
        """Should match medical professional associations"""
        result = self.service.get_credibility("AMA", "https://ama-assn.org/guidelines/ethics")

        assert result['tier'] == 'professional'
        assert result['credibility'] == 0.85

    def test_matches_uk_professional_body(self):
        """Should match UK professional bodies"""
        result = self.service.get_credibility("BMA", "https://bma.org.uk/advice/policy")

        assert result['tier'] == 'professional'
        assert result['credibility'] == 0.85

    def test_matches_financial_regulatory(self):
        """Should match financial regulatory bodies"""
        result = self.service.get_credibility("SEC", "https://sec.gov/edgar/123")

        assert result['tier'] == 'financial'
        assert result['credibility'] == 0.82
        assert result['risk_flags'] == []
        assert result['auto_exclude'] is False

    def test_matches_financial_data_provider(self):
        """Should match financial data providers"""
        result = self.service.get_credibility("Bloomberg", "https://bloomberg.com/markets/stocks")

        assert result['tier'] == 'financial'
        assert result['credibility'] == 0.82

    def test_matches_central_bank(self):
        """Should match central banks"""
        result = self.service.get_credibility("Federal Reserve", "https://federalreserve.gov/policy")

        assert result['tier'] == 'financial'
        assert result['credibility'] == 0.82

    # ========== BLACKLIST & RISK TESTS ==========

    def test_blacklist_low_credibility(self):
        """Should assign low credibility to blacklisted sources"""
        result = self.service.get_credibility("InfoWars", "https://infowars.com/article")

        assert result['tier'] == 'blacklist'
        assert result['credibility'] == 0.2
        assert 'conspiracy_theories' in result['risk_flags']
        assert result['auto_exclude'] is False  # Track but don't exclude

    def test_state_media_flagged(self):
        """Should flag state-sponsored media"""
        result = self.service.get_credibility("RT", "https://rt.com/news/123")

        assert result['tier'] == 'state_media'
        assert result['credibility'] == 0.5
        assert 'state_sponsored' in result['risk_flags']
        assert 'propaganda_concerns' in result['risk_flags']

    def test_satire_auto_excluded(self):
        """Should auto-exclude satirical sources"""
        result = self.service.get_credibility("The Onion", "https://theonion.com/funny")

        assert result['tier'] == 'satire'
        assert result['credibility'] == 0.0
        assert result['auto_exclude'] is True
        assert 'satire' in result['risk_flags']

    def test_should_exclude_satire(self):
        """Should return True for satirical sources"""
        assert self.service.should_exclude("https://theonion.com/article") is True
        assert self.service.should_exclude("https://bbc.co.uk/news") is False

    def test_tabloid_moderate_credibility(self):
        """Should assign moderate credibility to tabloids"""
        result = self.service.get_credibility("Daily Mail", "https://dailymail.co.uk/news")

        assert result['tier'] == 'tabloid'
        assert result['credibility'] == 0.55
        assert 'sensationalism' in result['risk_flags']

    # ========== RISK ASSESSMENT TESTS ==========

    def test_risk_assessment_high_risk(self):
        """Should classify blacklisted sources as high risk"""
        risk = self.service.get_risk_assessment("https://infowars.com/article")

        assert risk['risk_level'] == 'high'
        assert risk['should_flag_to_user'] is True
        assert 'misinformation' in risk['warning_message'].lower()

    def test_risk_assessment_medium_risk(self):
        """Should classify state media as medium risk"""
        risk = self.service.get_risk_assessment("https://rt.com/news")

        assert risk['risk_level'] == 'medium'
        assert risk['should_flag_to_user'] is True
        assert 'editorial independence' in risk['warning_message'].lower()

    def test_risk_assessment_low_risk(self):
        """Should classify tabloids as low risk"""
        risk = self.service.get_risk_assessment("https://dailymail.co.uk/news")

        assert risk['risk_level'] == 'low'
        assert risk['should_flag_to_user'] is False

    def test_risk_assessment_no_risk(self):
        """Should classify tier 1 sources as no risk"""
        risk = self.service.get_risk_assessment("https://bbc.co.uk/news")

        assert risk['risk_level'] == 'none'
        assert risk['should_flag_to_user'] is False
        assert risk['warning_message'] is None

    # ========== FALLBACK & EDGE CASES ==========

    def test_general_fallback_for_unknown_domain(self):
        """Should fallback to general tier for unknown domains"""
        result = self.service.get_credibility("Unknown Blog", "https://randomblog.com/post")

        assert result['tier'] == 'general'
        assert result['credibility'] == 0.6
        assert result['risk_flags'] == []
        assert result['auto_exclude'] is False

    def test_invalid_url_handling(self):
        """Should handle invalid URLs gracefully"""
        result = self.service.get_credibility("Test", "not-a-url")

        assert result['tier'] == 'general'
        assert result['credibility'] == 0.6

    def test_empty_url_handling(self):
        """Should handle empty URLs gracefully"""
        result = self.service.get_credibility("Test", "")

        assert result['tier'] == 'general'

    def test_case_insensitive_matching(self):
        """Should match domains case-insensitively"""
        result1 = self.service.get_credibility("BBC", "https://BBC.CO.UK/news")
        result2 = self.service.get_credibility("BBC", "https://bbc.co.uk/news")

        assert result1['tier'] == result2['tier']
        assert result1['credibility'] == result2['credibility']

    # ========== CACHING TESTS ==========

    def test_caching_same_domain(self):
        """Should cache credibility info for same domain"""
        # First call
        result1 = self.service.get_credibility("BBC", "https://bbc.co.uk/news/article1")

        # Second call with different path - should use cache
        result2 = self.service.get_credibility("BBC", "https://bbc.co.uk/news/article2")

        assert result1 == result2

    def test_clear_cache(self):
        """Should clear cache when requested"""
        self.service.get_credibility("BBC", "https://bbc.co.uk/news")
        assert len(self.service._domain_cache) > 0

        self.service.clear_cache()
        assert len(self.service._domain_cache) == 0

    # ========== UTILITY METHODS ==========

    def test_get_tier_summary(self):
        """Should return domain counts per tier"""
        summary = self.service.get_tier_summary()

        assert 'academic' in summary
        assert 'government' in summary
        assert 'news_tier1' in summary
        assert 'legal' in summary
        assert 'technical' in summary
        assert 'professional' in summary
        assert 'financial' in summary
        assert summary['academic'] > 0  # Has domains
        assert summary['legal'] > 0  # Has domains
        assert summary['technical'] > 0  # Has domains
        assert summary['professional'] > 0  # Has domains
        assert summary['financial'] > 0  # Has domains
        assert summary['general'] == 0  # No domains (fallback tier)

    def test_get_credibility_breakdown(self):
        """Should return complete credibility breakdown"""
        breakdown = self.service.get_credibility_breakdown("https://rt.com/news")

        assert 'url' in breakdown
        assert 'tier' in breakdown
        assert 'credibility_score' in breakdown
        assert 'risk_level' in breakdown
        assert 'risk_flags' in breakdown
        assert 'should_flag' in breakdown
        assert breakdown['tier'] == 'state_media'
        assert breakdown['should_flag'] is True

    # ========== WILDCARD PATTERN EDGE CASES ==========

    def test_wildcard_does_not_match_subdomain(self):
        """Wildcard *.edu should not match subdomain.example.com"""
        result = self.service.get_credibility("Test", "https://edu.example.com/page")

        # Should NOT match academic tier (*.edu expects .edu TLD)
        assert result['tier'] != 'academic'

    def test_exact_match_takes_precedence(self):
        """Exact domain match should be found over wildcard"""
        # mit.edu is listed explicitly AND matches *.edu
        result = self.service.get_credibility("MIT", "https://mit.edu/article")

        assert result['tier'] == 'academic'
        assert 'mit.edu' in str(result['reasoning']).lower() or 'academic' in str(result['reasoning']).lower()

    # ========== SINGLETON INSTANCE TEST ==========

    def test_get_credibility_service_singleton(self):
        """Should return singleton instance"""
        service1 = get_credibility_service()
        service2 = get_credibility_service()

        assert service1 is service2  # Same instance


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
