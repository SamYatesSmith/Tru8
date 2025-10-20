import pytest
from unittest.mock import AsyncMock, patch
from app.services.factcheck_api import FactCheckAPI


class TestFactCheckAPI:
    """Test Google Fact Check Explorer API integration"""

    @pytest.fixture
    def api(self):
        return FactCheckAPI()

    def test_normalize_verdict_true(self, api):
        """Test: Normalizes 'true' ratings to SUPPORTED"""
        test_cases = ['True', 'Correct', 'Accurate', 'Verified', 'Confirmed', 'Mostly True']
        for rating in test_cases:
            normalized = api._normalize_verdict(rating)
            assert normalized == 'SUPPORTED', f"Failed for: {rating}"

    def test_normalize_verdict_false(self, api):
        """Test: Normalizes 'false' ratings to CONTRADICTED"""
        test_cases = ['False', 'Incorrect', 'Wrong', 'Debunked', 'Pants on Fire', 'Misleading']
        for rating in test_cases:
            normalized = api._normalize_verdict(rating)
            assert normalized == 'CONTRADICTED', f"Failed for: {rating}"

    def test_normalize_verdict_uncertain(self, api):
        """Test: Normalizes mixed ratings to UNCERTAIN"""
        test_cases = ['Mixture', 'Half True', 'Unproven', 'Needs Context', 'Mostly False']
        for rating in test_cases:
            normalized = api._normalize_verdict(rating)
            assert normalized == 'UNCERTAIN', f"Failed for: {rating}"

    def test_normalize_verdict_unknown(self, api):
        """Test: Unknown ratings default to UNCERTAIN"""
        unknown_rating = 'Unknown Rating Format XYZ'
        normalized = api._normalize_verdict(unknown_rating)
        assert normalized == 'UNCERTAIN'

    def test_convert_to_evidence(self, api):
        """Test: Converts fact-check to evidence format"""
        fact_check = {
            'publisher': 'Snopes',
            'url': 'https://snopes.com/fact-check/example',
            'title': 'Fact Check: Example Claim',
            'rating': 'False',
            'review_date': '2024-01-15'
        }

        evidence = api.convert_to_evidence(fact_check, "Example claim")

        assert evidence['source'] == 'Snopes'
        assert evidence['is_factcheck'] == True
        assert evidence['credibility_score'] == 0.95  # High credibility for fact-checks
        assert evidence['factcheck_rating'] == 'False'
        assert evidence['source_type'] == 'factcheck'

    def test_cache_stats(self, api):
        """Test: Cache stats calculation"""
        stats = api.get_cache_stats()

        assert 'cache_size' in stats
        assert 'cache_ttl_hours' in stats
        assert stats['cache_ttl_hours'] == 24

    def test_clear_cache(self, api):
        """Test: Cache clearing"""
        # Add something to cache
        api.cache['test_key'] = ('test_value', 'test_time')
        assert len(api.cache) == 1

        # Clear cache
        api.clear_cache()
        assert len(api.cache) == 0

    def test_parse_fact_check(self, api):
        """Test: Fact-check parsing"""
        claim = {
            'text': 'Example claim text',
            'claimDate': '2024-01-01',
            'claimant': 'John Doe'
        }

        review = {
            'publisher': {'name': 'FactCheck.org', 'site': 'factcheck.org'},
            'url': 'https://factcheck.org/example',
            'title': 'Fact Check Title',
            'textualRating': 'False',
            'reviewDate': '2024-01-15',
            'languageCode': 'en'
        }

        result = api._parse_fact_check(claim, review)

        assert result is not None
        assert result['claim_text'] == 'Example claim text'
        assert result['publisher'] == 'FactCheck.org'
        assert result['rating'] == 'False'
        assert result['normalized_verdict'] == 'CONTRADICTED'
