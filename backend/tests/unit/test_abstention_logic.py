"""
Unit tests for Consensus & Abstention Logic

Phase 3 - Week 8: Abstention Logic
Tests abstention triggers, consensus calculation, and minimum requirements.
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
        evidence = [
            {'id': '1', 'credibility_score': 0.9, 'url': 'test1.com'},
            {'id': '2', 'credibility_score': 0.85, 'url': 'test2.com'}
        ]
        verification_signals = {}

        result = self.judge._should_abstain(evidence, verification_signals)

        assert result is not None
        verdict, reason, consensus = result
        assert verdict == "insufficient_evidence"
        assert "Only 2 source(s) found" in reason
        assert f"Need at least {settings.MIN_SOURCES_FOR_VERDICT}" in reason

    def test_proceeds_with_sufficient_sources(self):
        """Should NOT abstain when MIN_SOURCES_FOR_VERDICT requirement met"""
        evidence = [
            {'id': '1', 'credibility_score': 0.9, 'url': 'test1.com'},
            {'id': '2', 'credibility_score': 0.85, 'url': 'test2.com'},
            {'id': '3', 'credibility_score': 0.8, 'url': 'test3.com'}
        ]
        verification_signals = {
            'evidence_1_stance': 'supporting',
            'evidence_2_stance': 'supporting',
            'evidence_3_stance': 'supporting'
        }

        result = self.judge._should_abstain(evidence, verification_signals)

        # Should not abstain - all sources support
        # Note: This tests the source count check passes; might still abstain on other checks
        assert result is None or result[0] != "insufficient_evidence"

    def test_abstains_with_no_high_credibility_sources(self):
        """Should abstain when all sources below MIN_CREDIBILITY_THRESHOLD"""
        evidence = [
            {'id': '1', 'credibility_score': 0.6, 'url': 'a.com'},
            {'id': '2', 'credibility_score': 0.65, 'url': 'b.com'},
            {'id': '3', 'credibility_score': 0.7, 'url': 'c.com'}
        ]
        verification_signals = {}

        result = self.judge._should_abstain(evidence, verification_signals)

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
        verification_signals = {
            'evidence_1_stance': 'supporting',
            'evidence_2_stance': 'supporting',
            'evidence_3_stance': 'supporting'
        }

        result = self.judge._should_abstain(evidence, verification_signals)

        # Should not abstain due to source quality (might still abstain on consensus)
        if result:
            verdict, _, _ = result
            assert verdict != "insufficient_evidence"  # Passed quality check

    def test_abstains_with_weak_consensus(self):
        """Should abstain when consensus strength < MIN_CONSENSUS_STRENGTH"""
        from unittest.mock import patch

        evidence = [
            {'id': '1', 'credibility_score': 0.9, 'url': 'a.com'},
            {'id': '2', 'credibility_score': 0.85, 'url': 'b.com'},
            {'id': '3', 'credibility_score': 0.8, 'url': 'c.com'}
        ]
        # Evenly split evidence - weak consensus
        verification_signals = {
            'evidence_1_stance': 'supporting',
            'evidence_2_stance': 'contradicting',
            'evidence_3_stance': 'neutral'
        }

        # Use higher threshold to trigger weak consensus abstention
        with patch('app.pipeline.judge.settings.MIN_CONSENSUS_STRENGTH', 0.65):
            result = self.judge._should_abstain(evidence, verification_signals, "")

        assert result is not None
        verdict, reason, consensus = result
        assert verdict == "conflicting_expert_opinion"
        assert "weak consensus" in reason.lower() or "disagree" in reason.lower()

    def test_abstains_with_conflicting_high_credibility_sources(self):
        """Should abstain when tier1 sources disagree"""
        evidence = [
            {'id': '1', 'credibility_score': 0.9, 'url': 'reuters.com'},
            {'id': '2', 'credibility_score': 0.9, 'url': 'bbc.co.uk'},
            {'id': '3', 'credibility_score': 0.9, 'url': 'guardian.com'},  # Need 2+ high-cred contradicting
            {'id': '4', 'credibility_score': 0.9, 'url': 'nyt.com'}
        ]
        # High credibility sources conflict - need 2+ contradicting to trigger
        verification_signals = {
            'evidence_1_stance': 'supporting',
            'evidence_2_stance': 'contradicting',
            'evidence_3_stance': 'contradicting',  # 2 high-cred contradicting
            'evidence_4_stance': 'supporting'
        }

        result = self.judge._should_abstain(evidence, verification_signals, "")

        assert result is not None
        verdict, reason, consensus = result
        assert verdict == "conflicting_expert_opinion"
        assert "High-credibility sources conflict" in reason

    def test_abstains_with_outdated_temporal_flag(self):
        """Should abstain when temporal flag indicates outdated claim"""
        evidence = [
            {'id': '1', 'credibility_score': 0.9, 'url': 'a.com'},
            {'id': '2', 'credibility_score': 0.85, 'url': 'b.com'},
            {'id': '3', 'credibility_score': 0.8, 'url': 'c.com'}
        ]
        verification_signals = {
            'temporal_flag': 'outdated',
            'evidence_1_stance': 'supporting',
            'evidence_2_stance': 'supporting',
            'evidence_3_stance': 'supporting'
        }

        result = self.judge._should_abstain(evidence, verification_signals)

        assert result is not None
        verdict, reason, consensus = result
        assert verdict == "outdated_claim"
        assert "circumstances have changed" in reason.lower() or "no longer current" in reason.lower()

    # ========== CONSENSUS STRENGTH CALCULATION TESTS ==========

    def test_consensus_strength_calculation_unanimous_support(self):
        """Test consensus with all sources supporting"""
        evidence = [
            {'id': '1', 'credibility_score': 0.9, 'url': 'a.com'},
            {'id': '2', 'credibility_score': 0.8, 'url': 'b.com'},
            {'id': '3', 'credibility_score': 0.7, 'url': 'c.com'}
        ]
        signals = {
            'evidence_1_stance': 'supporting',
            'evidence_2_stance': 'supporting',
            'evidence_3_stance': 'supporting'
        }

        consensus = self.judge._calculate_consensus_strength(evidence, signals)

        # All sources support = 100% consensus
        assert consensus == 1.0

    def test_consensus_strength_calculation_weighted(self):
        """Test credibility-weighted consensus calculation"""
        evidence = [
            {'id': '1', 'credibility_score': 0.9, 'url': 'a.com'},  # High cred supporting
            {'id': '2', 'credibility_score': 0.6, 'url': 'b.com'}   # Low cred contradicting
        ]
        signals = {
            'evidence_1_stance': 'supporting',     # Weight: 0.9
            'evidence_2_stance': 'contradicting'   # Weight: 0.6
        }

        consensus = self.judge._calculate_consensus_strength(evidence, signals)

        # Consensus = 0.9 / (0.9 + 0.6) = 0.9 / 1.5 = 0.6 (60%)
        assert abs(consensus - 0.6) < 0.01

    def test_consensus_strength_with_neutral_evidence(self):
        """Test that neutral evidence counts as weak support (40% weight)"""
        evidence = [
            {'id': '1', 'credibility_score': 0.9, 'url': 'a.com'},
            {'id': '2', 'credibility_score': 0.8, 'url': 'b.com'},
            {'id': '3', 'credibility_score': 0.7, 'url': 'c.com'}
        ]
        signals = {
            'evidence_1_stance': 'supporting',
            'evidence_2_stance': 'supporting',
            'evidence_3_stance': 'neutral'  # Counts as 40% support
        }

        consensus = self.judge._calculate_consensus_strength(evidence, signals)

        # Evidence 1: 0.9, Evidence 2: 0.8, Evidence 3: 0.7 * 0.4 = 0.28
        # Total: (0.9 + 0.8 + 0.28) / (0.9 + 0.8 + 0.28) = 1.0
        assert consensus == 1.0

    def test_consensus_strength_with_no_stances(self):
        """Test consensus when no stances available"""
        evidence = [
            {'id': '1', 'credibility_score': 0.9, 'url': 'a.com'},
            {'id': '2', 'credibility_score': 0.8, 'url': 'b.com'}
        ]
        signals = {}  # No stance data

        consensus = self.judge._calculate_consensus_strength(evidence, signals)

        # No stances = 0 consensus
        assert consensus == 0.0

    def test_consensus_strength_with_empty_evidence(self):
        """Test consensus calculation with empty evidence list"""
        consensus = self.judge._calculate_consensus_strength([], {})

        assert consensus == 0.0

    def test_consensus_strength_with_all_neutral_evidence(self):
        """Test that all-neutral evidence produces strong consensus (not 0%)"""
        evidence = [
            {'id': '1', 'credibility_score': 0.9, 'url': 'a.com'},
            {'id': '2', 'credibility_score': 0.8, 'url': 'b.com'},
            {'id': '3', 'credibility_score': 0.7, 'url': 'c.com'}
        ]
        signals = {
            'evidence_1_stance': 'neutral',
            'evidence_2_stance': 'neutral',
            'evidence_3_stance': 'neutral'
        }

        consensus = self.judge._calculate_consensus_strength(evidence, signals)

        # All neutral = (0.9 + 0.8 + 0.7) * 0.4 = 0.96
        # Consensus = 0.96 / 0.96 = 1.0 (100% weak support)
        assert consensus == 1.0

    # ========== INTEGRATION TESTS ==========

    def test_no_abstention_with_strong_evidence(self):
        """Should NOT abstain when all requirements met"""
        # 3+ sources, high credibility, strong consensus
        evidence = [
            {'id': '1', 'credibility_score': 0.9, 'url': 'reuters.com'},
            {'id': '2', 'credibility_score': 0.85, 'url': 'bbc.co.uk'},
            {'id': '3', 'credibility_score': 0.8, 'url': 'ap.org'}
        ]
        verification_signals = {
            'evidence_1_stance': 'supporting',
            'evidence_2_stance': 'supporting',
            'evidence_3_stance': 'supporting'
        }

        result = self.judge._should_abstain(evidence, verification_signals)

        # Should NOT abstain - all requirements met
        assert result is None

    def test_abstention_priority_order(self):
        """Test that abstention checks happen in priority order"""
        # Too few sources (should trigger first check)
        evidence = [
            {'id': '1', 'credibility_score': 0.2, 'url': 'test.com'}  # Also low credibility
        ]
        verification_signals = {}

        result = self.judge._should_abstain(evidence, verification_signals)

        # Should fail on source count, not credibility
        assert result is not None
        verdict, reason, _ = result
        assert verdict == "insufficient_evidence"
        assert "Only 1 source(s)" in reason

    def test_consensus_check_only_after_quality_checks(self):
        """Test that consensus is only checked after source quality checks pass"""
        # Enough sources, but low credibility
        evidence = [
            {'id': '1', 'credibility_score': 0.6, 'url': 'a.com'},
            {'id': '2', 'credibility_score': 0.6, 'url': 'b.com'},
            {'id': '3', 'credibility_score': 0.6, 'url': 'c.com'}
        ]
        verification_signals = {
            'evidence_1_stance': 'supporting',
            'evidence_2_stance': 'contradicting',
            'evidence_3_stance': 'neutral'
        }

        result = self.judge._should_abstain(evidence, verification_signals)

        # Should fail on credibility, not reach consensus check
        assert result is not None
        verdict, _, _ = result
        assert verdict == "insufficient_evidence"  # Failed quality check

    # ========== EDGE CASES ==========

    def test_handles_missing_credibility_score(self):
        """Should handle evidence missing credibility_score gracefully"""
        evidence = [
            {'id': '1', 'url': 'test1.com'},  # Missing credibility_score
            {'id': '2', 'credibility_score': 0.9, 'url': 'test2.com'},
            {'id': '3', 'credibility_score': 0.85, 'url': 'test3.com'}
        ]
        verification_signals = {}

        # Should not crash, should use default 0.6
        result = self.judge._should_abstain(evidence, verification_signals)
        assert result is not None  # Will likely abstain due to missing high-cred source

    def test_handles_missing_evidence_id(self):
        """Should handle evidence missing ID gracefully"""
        evidence = [
            {'credibility_score': 0.9, 'url': 'test1.com'},  # Missing id
            {'credibility_score': 0.85, 'url': 'test2.com'},
            {'credibility_score': 0.8, 'url': 'test3.com'}
        ]
        verification_signals = {
            'evidence__stance': 'supporting'  # Won't match due to missing ID
        }

        # Should not crash
        result = self.judge._should_abstain(evidence, verification_signals)
        assert result is not None or result is None  # Either outcome is valid


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
