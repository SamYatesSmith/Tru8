"""
Unit tests for Consensus & Abstention Logic

Phase 3 - Week 8: Abstention Logic
Tests abstention triggers and minimum requirements.
"""

import pytest
from app.pipeline.judge import ClaimJudge
from app.core.config import settings


class TestAbstentionLogic:
    """Test suite for abstention logic in ClaimJudge"""

    def setup_method(self):
        """Create fresh judge instance for each test"""
        self.judge = ClaimJudge()

    # ========== ABSTENTION TRIGGER TESTS ==========

    def test_abstains_with_too_few_sources(self):
        """Should abstain when fewer than MIN_SOURCES_FOR_VERDICT sources"""
        # Only 1 source - below MIN_SOURCES_FOR_VERDICT (default: 2)
        evidence = [
            {'id': '1', 'credibility_score': 0.9, 'url': 'test1.com'}
        ]

        result = self.judge._should_abstain(evidence)

        assert result is not None
        verdict, reason, consensus = result
        assert verdict == "insufficient_evidence"
        assert "Only 1 source(s) found" in reason
        assert f"Need at least {settings.MIN_SOURCES_FOR_VERDICT}" in reason

    def test_proceeds_with_sufficient_sources(self):
        """Should NOT abstain when MIN_SOURCES_FOR_VERDICT requirement met"""
        evidence = [
            {'id': '1', 'credibility_score': 0.9, 'url': 'test1.com'},
            {'id': '2', 'credibility_score': 0.85, 'url': 'test2.com'},
            {'id': '3', 'credibility_score': 0.8, 'url': 'test3.com'}
        ]

        result = self.judge._should_abstain(evidence)

        # Should not abstain - sufficient high-cred sources
        assert result is None

    def test_abstains_with_no_high_credibility_sources(self):
        """Should abstain when all sources below MIN_CREDIBILITY_THRESHOLD"""
        # All sources below 0.60 threshold (0.50, 0.55, 0.59)
        evidence = [
            {'id': '1', 'credibility_score': 0.50, 'url': 'a.com'},
            {'id': '2', 'credibility_score': 0.55, 'url': 'b.com'},
            {'id': '3', 'credibility_score': 0.59, 'url': 'c.com'}
        ]

        result = self.judge._should_abstain(evidence)

        assert result is not None
        verdict, reason, consensus = result
        assert verdict == "insufficient_evidence"
        assert "No high-credibility sources" in reason
        assert str(int(settings.MIN_CREDIBILITY_THRESHOLD * 100)) in reason

    def test_proceeds_with_high_credibility_sources(self):
        """Should NOT abstain when at least one source >= MIN_CREDIBILITY_THRESHOLD"""
        evidence = [
            {'id': '1', 'credibility_score': 0.9, 'url': 'reuters.com'},  # High credibility
            {'id': '2', 'credibility_score': 0.65, 'url': 'blog.com'},
            {'id': '3', 'credibility_score': 0.6, 'url': 'news.com'}
        ]

        result = self.judge._should_abstain(evidence)

        # Should not abstain - has high credibility source
        assert result is None

    # ========== INTEGRATION TESTS ==========

    def test_no_abstention_with_strong_evidence(self):
        """Should NOT abstain when all requirements met"""
        # 3+ sources, high credibility
        evidence = [
            {'id': '1', 'credibility_score': 0.9, 'url': 'reuters.com'},
            {'id': '2', 'credibility_score': 0.85, 'url': 'bbc.co.uk'},
            {'id': '3', 'credibility_score': 0.8, 'url': 'ap.org'}
        ]

        result = self.judge._should_abstain(evidence)

        # Should NOT abstain - all requirements met
        assert result is None

    def test_abstention_priority_order(self):
        """Test that abstention checks happen in priority order"""
        # Too few sources (should trigger first check)
        evidence = [
            {'id': '1', 'credibility_score': 0.2, 'url': 'test.com'}  # Also low credibility
        ]

        result = self.judge._should_abstain(evidence)

        # Should fail on source count, not credibility
        assert result is not None
        verdict, reason, _ = result
        assert verdict == "insufficient_evidence"
        assert "Only 1 source(s)" in reason

    def test_consensus_check_only_after_quality_checks(self):
        """Test that credibility is checked after source count passes"""
        # Enough sources, but all below 0.60 credibility threshold
        evidence = [
            {'id': '1', 'credibility_score': 0.50, 'url': 'a.com'},
            {'id': '2', 'credibility_score': 0.55, 'url': 'b.com'},
            {'id': '3', 'credibility_score': 0.59, 'url': 'c.com'}
        ]

        result = self.judge._should_abstain(evidence)

        # Should fail on credibility
        assert result is not None
        verdict, _, _ = result
        assert verdict == "insufficient_evidence"  # Failed quality check

    # ========== EDGE CASES ==========

    def test_handles_missing_credibility_score(self):
        """Should handle evidence missing credibility_score gracefully"""
        evidence = [
            {'id': '1', 'url': 'test1.com'},  # Missing credibility_score (defaults to 0.6)
            {'id': '2', 'credibility_score': 0.9, 'url': 'test2.com'},
            {'id': '3', 'credibility_score': 0.85, 'url': 'test3.com'}
        ]

        # Should not crash, should use default 0.6 for missing credibility
        result = self.judge._should_abstain(evidence)
        # Either outcome is valid - key is it doesn't crash
        assert result is None or isinstance(result, tuple)

    def test_handles_missing_evidence_id(self):
        """Should handle evidence missing ID gracefully"""
        evidence = [
            {'credibility_score': 0.9, 'url': 'test1.com'},  # Missing id
            {'credibility_score': 0.85, 'url': 'test2.com'},
            {'credibility_score': 0.8, 'url': 'test3.com'}
        ]

        # Should not crash
        result = self.judge._should_abstain(evidence)
        assert result is None  # All high-cred, should pass


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
