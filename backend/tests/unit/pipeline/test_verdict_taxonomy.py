"""
Tests for Verdict Taxonomy Consistency (PR 1-E).

Verifies:
1) All outputs use strict 3-way verdict: supported / contradicted / uncertain
2) When verdict is "uncertain", uncertainty_reason is one of the valid enum values
3) Abstention verdicts (insufficient_evidence, conflicting_expert_opinion, outdated_claim)
   are mapped to verdict="uncertain" + appropriate uncertainty_reason
4) Processing errors produce verdict="uncertain" + reason="processing_error"
5) "supported" and "contradicted" never carry uncertainty_reason
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from app.pipeline.judge import ClaimJudge, JudgmentResult


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def judge():
    """Create a ClaimJudge instance with minimal config."""
    with patch("app.pipeline.judge.settings") as mock_settings:
        mock_settings.OPENAI_API_KEY = "test"
        mock_settings.GOOGLE_AI_API_KEY = "test-key"
        mock_settings.JUDGE_MAX_TOKENS = 1000
        mock_settings.JUDGE_TEMPERATURE = 0.3
        mock_settings.EVIDENCE_SNIPPET_LENGTH = 400
        mock_settings.ENABLE_JUDGE_FEW_SHOT = False
        mock_settings.ENABLE_RHETORICAL_CONTEXT = False
        mock_settings.ENABLE_ABSTENTION_LOGIC = True
        mock_settings.MAX_SNIPPET_EVIDENCE_FOR_JUDGE = 2
        mock_settings.MIN_SOURCES_FOR_VERDICT = 2
        mock_settings.MIN_CREDIBILITY_THRESHOLD = 0.60
        mock_settings.MIN_CONSENSUS_STRENGTH = 0.50
        j = ClaimJudge()
        yield j


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_claim(text="Test claim about something"):
    return {"text": text, "position": 0}


def _make_signals(**overrides):
    base = {
        "overall_verdict": "uncertain",
        "confidence": 0.5,
        "supporting_count": 0,
        "contradicting_count": 0,
        "total_evidence": 0,
        "max_entailment": 0.0,
        "max_contradiction": 0.0,
        "evidence_quality": "low",
    }
    base.update(overrides)
    return base


def _make_evidence(source="reuters.com", url="https://reuters.com/article",
                   text="Full article text with detailed information",
                   credibility_score=0.9):
    return {
        "source": source,
        "url": url,
        "text": text,
        "snippet": text,
        "published_date": "2026-01-15",
        "credibility_score": credibility_score,
        "metadata": {},
    }


# ---------------------------------------------------------------------------
# A) _normalize_verdict unit tests
# ---------------------------------------------------------------------------

class TestNormalizeVerdict:

    def test_supported_passes_through(self):
        v, r = ClaimJudge._normalize_verdict("supported")
        assert v == "supported"
        assert r is None

    def test_contradicted_passes_through(self):
        v, r = ClaimJudge._normalize_verdict("contradicted")
        assert v == "contradicted"
        assert r is None

    def test_uncertain_passes_through(self):
        v, r = ClaimJudge._normalize_verdict("uncertain")
        assert v == "uncertain"
        assert r is None

    def test_uncertain_preserves_reason(self):
        v, r = ClaimJudge._normalize_verdict("uncertain", "low_quality_sources")
        assert v == "uncertain"
        assert r == "low_quality_sources"

    def test_insufficient_evidence_maps(self):
        v, r = ClaimJudge._normalize_verdict("insufficient_evidence")
        assert v == "uncertain"
        assert r == "insufficient_evidence"

    def test_conflicting_expert_opinion_maps(self):
        v, r = ClaimJudge._normalize_verdict("conflicting_expert_opinion")
        assert v == "uncertain"
        assert r == "conflicting_expert_opinion"

    def test_outdated_claim_maps(self):
        v, r = ClaimJudge._normalize_verdict("outdated_claim")
        assert v == "uncertain"
        assert r == "outdated_evidence"

    def test_outdated_shorthand_maps(self):
        v, r = ClaimJudge._normalize_verdict("outdated")
        assert v == "uncertain"
        assert r == "outdated_evidence"

    def test_unknown_verdict_maps_to_processing_error(self):
        v, r = ClaimJudge._normalize_verdict("some_random_verdict")
        assert v == "uncertain"
        assert r == "processing_error"

    def test_case_insensitive(self):
        v, r = ClaimJudge._normalize_verdict("Supported")
        assert v == "supported"
        assert r is None

    def test_whitespace_stripped(self):
        v, r = ClaimJudge._normalize_verdict("  contradicted  ")
        assert v == "contradicted"
        assert r is None


# ---------------------------------------------------------------------------
# B) Abstention paths in judge_claim → 3-way verdict + uncertainty_reason
# ---------------------------------------------------------------------------

class TestAbstentionMapsToUncertain:

    @pytest.mark.asyncio
    async def test_insufficient_evidence_abstention(self, judge):
        """Too few sources → verdict=uncertain, reason=insufficient_evidence, confidence=0."""
        claim = _make_claim()
        # Only 1 evidence item → below MIN_SOURCES_FOR_VERDICT=2
        evidence = [_make_evidence()]
        signals = _make_signals()

        with patch.object(judge, "initialize", new_callable=AsyncMock):
            judge.cache_service = None
            result = await judge.judge_claim(claim, evidence)

        assert result.verdict == "uncertain"
        assert result.uncertainty_reason == "insufficient_evidence"
        assert result.confidence == 0.0

    @pytest.mark.asyncio
    async def test_conflicting_expert_opinion_abstention(self, judge):
        """Conflicting expert opinion → verdict=uncertain, reason=conflicting_expert_opinion."""
        claim = _make_claim()
        evidence = [
            _make_evidence(source="reuters.com", url="https://reuters.com/1"),
            _make_evidence(source="bbc.com", url="https://bbc.com/1"),
        ]
        signals = _make_signals()

        # Mock _should_abstain to return conflicting_expert_opinion
        with patch.object(judge, "_should_abstain",
                          return_value=("conflicting_expert_opinion",
                                        "High-credibility sources disagree.", 0.3)), \
             patch.object(judge, "initialize", new_callable=AsyncMock):
            judge.cache_service = None
            result = await judge.judge_claim(claim, evidence)

        assert result.verdict == "uncertain"
        assert result.uncertainty_reason == "conflicting_expert_opinion"
        assert result.confidence <= 45

    @pytest.mark.asyncio
    async def test_outdated_claim_abstention(self, judge):
        """Outdated claim → verdict=uncertain, reason=outdated_evidence."""
        claim = _make_claim()
        evidence = [
            _make_evidence(source="reuters.com", url="https://reuters.com/1"),
            _make_evidence(source="bbc.com", url="https://bbc.com/1"),
        ]
        signals = _make_signals()

        with patch.object(judge, "_should_abstain",
                          return_value=("outdated_claim",
                                        "Claim may have been accurate historically.", 0.4)), \
             patch.object(judge, "initialize", new_callable=AsyncMock):
            judge.cache_service = None
            result = await judge.judge_claim(claim, evidence)

        assert result.verdict == "uncertain"
        assert result.uncertainty_reason == "outdated_evidence"
        assert result.confidence <= 45


# ---------------------------------------------------------------------------
# C) Processing error → uncertainty_reason="processing_error"
# ---------------------------------------------------------------------------

class TestProcessingErrorReason:

    @pytest.mark.asyncio
    async def test_llm_failure_produces_processing_error(self, judge):
        """LLM exception → fallback with reason=processing_error."""
        claim = _make_claim()
        evidence = [
            _make_evidence(source="reuters.com", url="https://reuters.com/1"),
            _make_evidence(source="bbc.com", url="https://bbc.com/1"),
        ]
        signals = _make_signals()

        # Disable abstention so we reach LLM path, then make LLM fail
        with patch("app.pipeline.judge.settings") as mock_settings:
            mock_settings.OPENAI_API_KEY = "test"
            mock_settings.GOOGLE_AI_API_KEY = "test-key"
            mock_settings.JUDGE_MAX_TOKENS = 1000
            mock_settings.JUDGE_TEMPERATURE = 0.3
            mock_settings.EVIDENCE_SNIPPET_LENGTH = 400
            mock_settings.ENABLE_JUDGE_FEW_SHOT = False
            mock_settings.ENABLE_RHETORICAL_CONTEXT = False
            mock_settings.ENABLE_ABSTENTION_LOGIC = False
            mock_settings.MIN_SOURCES_FOR_VERDICT = 2
            mock_settings.MIN_CREDIBILITY_THRESHOLD = 0.60
            mock_settings.MIN_CONSENSUS_STRENGTH = 0.50
            mock_settings.MAX_SNIPPET_EVIDENCE_FOR_JUDGE = 2

            judge2 = ClaimJudge()

            with patch.object(judge2, "_judge_with_google", new_callable=AsyncMock,
                              side_effect=Exception("API timeout")), \
                 patch.object(judge2, "_judge_with_openai", new_callable=AsyncMock,
                              side_effect=Exception("API timeout")), \
                 patch.object(judge2, "initialize", new_callable=AsyncMock):
                judge2.cache_service = None
                result = await judge2.judge_claim(claim, evidence)

        assert result.verdict == "uncertain"
        assert result.uncertainty_reason == "processing_error"


# ---------------------------------------------------------------------------
# D) Supported/contradicted verdicts have NO uncertainty_reason
# ---------------------------------------------------------------------------

class TestNonUncertainNoReason:

    @pytest.mark.asyncio
    async def test_supported_has_no_uncertainty_reason(self, judge):
        """Supported verdict must not carry uncertainty_reason."""
        claim = _make_claim()
        evidence = [
            _make_evidence(source="reuters.com", url="https://reuters.com/1"),
            _make_evidence(source="bbc.com", url="https://bbc.com/1"),
        ]
        signals = _make_signals(overall_verdict="supported", confidence=0.85)

        with patch.object(judge, "_judge_with_google", new_callable=AsyncMock,
                          return_value={"verdict": "supported", "confidence": 85,
                                        "rationale": "Reuters confirms this."}), \
             patch.object(judge, "initialize", new_callable=AsyncMock), \
             patch("app.pipeline.judge.settings") as ms:
            # Disable abstention for this test
            ms.ENABLE_ABSTENTION_LOGIC = False
            ms.ENABLE_RHETORICAL_CONTEXT = False
            ms.ENABLE_JUDGE_FEW_SHOT = False
            ms.EVIDENCE_SNIPPET_LENGTH = 400
            ms.MAX_SNIPPET_EVIDENCE_FOR_JUDGE = 2
            judge.cache_service = None
            result = await judge.judge_claim(claim, evidence)

        assert result.verdict == "supported"
        assert result.uncertainty_reason is None
        # to_dict should not include uncertainty_reason
        d = result.to_dict()
        assert "uncertainty_reason" not in d

    @pytest.mark.asyncio
    async def test_contradicted_has_no_uncertainty_reason(self, judge):
        """Contradicted verdict must not carry uncertainty_reason."""
        claim = _make_claim()
        evidence = [
            _make_evidence(source="reuters.com", url="https://reuters.com/1"),
            _make_evidence(source="bbc.com", url="https://bbc.com/1"),
        ]
        signals = _make_signals(overall_verdict="contradicted", confidence=0.80)

        with patch.object(judge, "_judge_with_google", new_callable=AsyncMock,
                          return_value={"verdict": "contradicted", "confidence": 80,
                                        "rationale": "Reuters contradicts this."}), \
             patch.object(judge, "initialize", new_callable=AsyncMock), \
             patch("app.pipeline.judge.settings") as ms:
            ms.ENABLE_ABSTENTION_LOGIC = False
            ms.ENABLE_RHETORICAL_CONTEXT = False
            ms.ENABLE_JUDGE_FEW_SHOT = False
            ms.EVIDENCE_SNIPPET_LENGTH = 400
            ms.MAX_SNIPPET_EVIDENCE_FOR_JUDGE = 2
            judge.cache_service = None
            result = await judge.judge_claim(claim, evidence)

        assert result.verdict == "contradicted"
        assert result.uncertainty_reason is None
        d = result.to_dict()
        assert "uncertainty_reason" not in d


# ---------------------------------------------------------------------------
# E) JudgmentResult.to_dict includes/excludes uncertainty fields correctly
# ---------------------------------------------------------------------------

class TestJudgmentResultDict:

    def test_uncertain_with_reason_in_dict(self):
        """to_dict includes uncertainty_reason when verdict=uncertain + reason set."""
        r = JudgmentResult(
            claim_text="test", verdict="uncertain", confidence=30,
            rationale="Insufficient sources.", supporting_evidence=[], evidence_summary={},
            uncertainty_reason="insufficient_evidence",
            uncertainty_details="Only 1 source found.",
        )
        d = r.to_dict()
        assert d["verdict"] == "uncertain"
        assert d["uncertainty_reason"] == "insufficient_evidence"
        assert d["uncertainty_details"] == "Only 1 source found."

    def test_uncertain_without_reason_in_dict(self):
        """to_dict omits uncertainty_reason when not set."""
        r = JudgmentResult(
            claim_text="test", verdict="uncertain", confidence=30,
            rationale="Mixed evidence.", supporting_evidence=[], evidence_summary={},
        )
        d = r.to_dict()
        assert d["verdict"] == "uncertain"
        assert "uncertainty_reason" not in d

    def test_supported_never_includes_reason(self):
        """to_dict never includes uncertainty_reason for supported."""
        r = JudgmentResult(
            claim_text="test", verdict="supported", confidence=85,
            rationale="Confirmed.", supporting_evidence=[], evidence_summary={},
            uncertainty_reason="should_be_ignored",
        )
        d = r.to_dict()
        assert "uncertainty_reason" not in d

    def test_contradicted_never_includes_reason(self):
        """to_dict never includes uncertainty_reason for contradicted."""
        r = JudgmentResult(
            claim_text="test", verdict="contradicted", confidence=80,
            rationale="Denied.", supporting_evidence=[], evidence_summary={},
            uncertainty_reason="should_be_ignored",
        )
        d = r.to_dict()
        assert "uncertainty_reason" not in d


# ---------------------------------------------------------------------------
# F) Valid constants
# ---------------------------------------------------------------------------

class TestVerdictConstants:

    def test_valid_verdicts(self):
        assert ClaimJudge.VALID_VERDICTS == {"supported", "contradicted", "uncertain"}

    def test_valid_uncertainty_reasons(self):
        expected = {
            "insufficient_evidence",
            "conflicting_expert_opinion",
            "outdated_evidence",
            "low_quality_sources",
            "off_topic_evidence",
            "processing_error",
        }
        assert ClaimJudge.VALID_UNCERTAINTY_REASONS == expected
