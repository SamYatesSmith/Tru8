"""
Tests for Evidence Recency/Staleness Enforcement (PR 1-D).

Verifies:
1) _assess_staleness correctly identifies time-sensitive claims with stale evidence
2) Confidence is capped and verdict biased to "uncertain" when evidence is predominantly stale
3) combined_score changes when recency differs (via _apply_credibility_weighting)
4) Deterministic under frozen evidence replay (same input = same output)
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock, AsyncMock

from app.pipeline.judge import ClaimJudge
from app.pipeline.retrieve import EvidenceRetriever


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
        mock_settings.ENABLE_ABSTENTION_LOGIC = False
        mock_settings.MAX_SNIPPET_EVIDENCE_FOR_JUDGE = 2
        mock_settings.MIN_SOURCES_FOR_VERDICT = 2
        mock_settings.MIN_CREDIBILITY_THRESHOLD = 0.60
        mock_settings.MIN_CONSENSUS_STRENGTH = 0.50
        j = ClaimJudge()
        yield j


@pytest.fixture
def retriever():
    """Minimal EvidenceRetriever for testing _apply_credibility_weighting."""
    with patch("app.pipeline.retrieve.SearchService"), \
         patch("app.pipeline.retrieve.EvidenceExtractor"), \
         patch("app.pipeline.retrieve.get_api_registry") as mock_registry:
        mock_registry.return_value = MagicMock()
        ret = EvidenceRetriever()
        yield ret


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_evidence(source="reuters.com", url="https://reuters.com/article",
                   published_date="2026-01-15", is_stale=False, age_days=30,
                   max_age_days=365):
    """Create an evidence dict with optional staleness metadata."""
    meta = {}
    if is_stale or age_days > max_age_days:
        meta["staleness_check"] = {
            "is_stale": True,
            "age_days": age_days,
            "max_age_days": max_age_days,
        }
    elif published_date:
        meta["staleness_check"] = {
            "is_stale": False,
            "age_days": age_days,
            "max_age_days": max_age_days,
        }
    return {
        "source": source,
        "url": url,
        "text": "Some evidence text about the topic",
        "snippet": "Some evidence text about the topic",
        "published_date": published_date,
        "credibility_score": 0.9,
        "metadata": meta,
    }


def _make_undated_evidence(source="example.com", url="https://example.com/page"):
    """Evidence with no published_date."""
    return {
        "source": source,
        "url": url,
        "text": "Some evidence text",
        "snippet": "Some evidence text",
        "published_date": None,
        "credibility_score": 0.7,
        "metadata": {},
    }


def _time_sensitive_claim(temporal_window="current_month"):
    return {
        "text": "The latest jobs report shows 200,000 new jobs",
        "position": 0,
        "temporal_window": temporal_window,
    }


def _timeless_claim():
    return {
        "text": "The speed of light is approximately 299,792 km/s",
        "position": 0,
        "temporal_window": "timeless",
        "claim_type": "timeless_fact",
    }


# ---------------------------------------------------------------------------
# A) _assess_staleness tests
# ---------------------------------------------------------------------------

class TestAssessStaleness:

    def test_time_sensitive_mostly_stale(self, judge):
        """Majority stale evidence → should_cap=True."""
        claim = _time_sensitive_claim("current_week")
        evidence = [
            _make_evidence(is_stale=True, age_days=400),
            _make_evidence(source="bbc.com", url="https://bbc.com/1", is_stale=True, age_days=500),
            _make_evidence(source="ap.com", url="https://ap.com/1", is_stale=False, age_days=5),
        ]
        result = judge._assess_staleness(claim, evidence)
        assert result["is_time_sensitive"] is True
        assert result["stale_count"] == 2
        assert result["should_cap"] is True

    def test_time_sensitive_mostly_fresh(self, judge):
        """Majority fresh evidence → should_cap=False."""
        claim = _time_sensitive_claim("current_month")
        evidence = [
            _make_evidence(is_stale=False, age_days=10),
            _make_evidence(source="bbc.com", url="https://bbc.com/1", is_stale=False, age_days=15),
            _make_evidence(source="ap.com", url="https://ap.com/1", is_stale=True, age_days=400),
        ]
        result = judge._assess_staleness(claim, evidence)
        assert result["stale_count"] == 1
        assert result["should_cap"] is False

    def test_timeless_claim_no_cap(self, judge):
        """Timeless claim → never capped regardless of dates."""
        claim = _timeless_claim()
        evidence = [
            _make_evidence(is_stale=True, age_days=1000),
            _make_evidence(source="bbc.com", url="https://bbc.com/1", is_stale=True, age_days=900),
        ]
        result = judge._assess_staleness(claim, evidence)
        assert result["is_time_sensitive"] is False
        assert result["should_cap"] is False

    def test_undated_evidence_counts(self, judge):
        """Undated evidence counts toward problematic threshold."""
        claim = _time_sensitive_claim("current_day")
        evidence = [
            _make_undated_evidence("a.com", "https://a.com/1"),
            _make_undated_evidence("b.com", "https://b.com/2"),
            _make_evidence(source="c.com", url="https://c.com/3", is_stale=False, age_days=1),
        ]
        result = judge._assess_staleness(claim, evidence)
        assert result["undated_count"] == 2
        assert result["should_cap"] is True

    def test_no_temporal_window_not_time_sensitive(self, judge):
        """Claim without temporal_window → not time-sensitive → no cap."""
        claim = {"text": "Something happened", "position": 0, "temporal_window": "any"}
        evidence = [
            _make_evidence(is_stale=True, age_days=999),
            _make_evidence(source="b.com", url="https://b.com/1", is_stale=True, age_days=888),
        ]
        result = judge._assess_staleness(claim, evidence)
        assert result["is_time_sensitive"] is False
        assert result["should_cap"] is False

    def test_empty_evidence(self, judge):
        """Empty evidence → no cap."""
        claim = _time_sensitive_claim()
        result = judge._assess_staleness(claim, [])
        assert result["should_cap"] is False

    def test_assesses_top_5_only(self, judge):
        """Only the top 5 evidence items are assessed."""
        claim = _time_sensitive_claim()
        # 6 fresh items to ensure top 5 are all fresh
        evidence = [_make_evidence(source=f"fresh{i}.com", url=f"https://fresh{i}.com/1",
                                   is_stale=False, age_days=5) for i in range(6)]
        # Add stale items beyond position 5
        evidence += [_make_evidence(source=f"stale{i}.com", url=f"https://stale{i}.com/1",
                                    is_stale=True, age_days=400) for i in range(5)]
        result = judge._assess_staleness(claim, evidence)
        # Top 5 are all fresh → no cap
        assert result["total"] == 5
        assert result["stale_count"] == 0
        assert result["should_cap"] is False


# ---------------------------------------------------------------------------
# B) Confidence cap + verdict override in judge_claim
# ---------------------------------------------------------------------------

class TestStalenessConfidenceCap:

    @pytest.mark.asyncio
    async def test_confidence_capped_when_stale(self, judge):
        """LLM says 85% supported, but evidence is stale → capped to 45, verdict=uncertain."""
        claim = _time_sensitive_claim("current_week")
        evidence = [
            _make_evidence(is_stale=True, age_days=400),
            _make_evidence(source="bbc.com", url="https://bbc.com/1", is_stale=True, age_days=500),
        ]
        signals = {"overall_verdict": "supported", "confidence": 0.85}

        # Mock LLM to return high-confidence supported
        with patch.object(judge, "_judge_with_google", new_callable=AsyncMock,
                          return_value={"verdict": "supported", "confidence": 85,
                                        "rationale": "Reuters confirms this."}), \
             patch.object(judge, "initialize", new_callable=AsyncMock):
            judge.cache_service = None
            result = await judge.judge_claim(claim, evidence)

        assert result.verdict == "uncertain"
        assert result.confidence <= 45

    @pytest.mark.asyncio
    async def test_no_cap_when_fresh(self, judge):
        """Fresh evidence → LLM confidence passes through unchanged."""
        claim = _time_sensitive_claim("current_month")
        evidence = [
            _make_evidence(is_stale=False, age_days=10),
            _make_evidence(source="bbc.com", url="https://bbc.com/1", is_stale=False, age_days=15),
        ]
        signals = {"overall_verdict": "supported", "confidence": 0.85}

        with patch.object(judge, "_judge_with_google", new_callable=AsyncMock,
                          return_value={"verdict": "supported", "confidence": 85,
                                        "rationale": "Reuters confirms this."}), \
             patch.object(judge, "initialize", new_callable=AsyncMock):
            judge.cache_service = None
            result = await judge.judge_claim(claim, evidence)

        assert result.verdict == "supported"
        assert result.confidence == 85

    @pytest.mark.asyncio
    async def test_uncertain_verdict_not_overridden(self, judge):
        """LLM already says uncertain → staleness cap applies to confidence only."""
        claim = _time_sensitive_claim("current_week")
        evidence = [
            _make_evidence(is_stale=True, age_days=400),
            _make_evidence(source="b.com", url="https://b.com/1", is_stale=True, age_days=500),
        ]
        signals = {"overall_verdict": "uncertain", "confidence": 0.6}

        with patch.object(judge, "_judge_with_google", new_callable=AsyncMock,
                          return_value={"verdict": "uncertain", "confidence": 60,
                                        "rationale": "Insufficient evidence."}), \
             patch.object(judge, "initialize", new_callable=AsyncMock):
            judge.cache_service = None
            result = await judge.judge_claim(claim, evidence)

        # Verdict stays uncertain, confidence still capped
        assert result.verdict == "uncertain"
        assert result.confidence <= 45

    @pytest.mark.asyncio
    async def test_timeless_claim_no_cap(self, judge):
        """Timeless claims never get capped."""
        claim = _timeless_claim()
        evidence = [
            _make_evidence(is_stale=True, age_days=1000),
            _make_evidence(source="b.com", url="https://b.com/1", is_stale=True, age_days=900),
        ]
        signals = {"overall_verdict": "supported", "confidence": 0.9}

        with patch.object(judge, "_judge_with_google", new_callable=AsyncMock,
                          return_value={"verdict": "supported", "confidence": 90,
                                        "rationale": "Confirmed."}), \
             patch.object(judge, "initialize", new_callable=AsyncMock):
            judge.cache_service = None
            result = await judge.judge_claim(claim, evidence)

        assert result.verdict == "supported"
        assert result.confidence == 90


# ---------------------------------------------------------------------------
# C) combined_score changes with recency (retrieve.py)
# ---------------------------------------------------------------------------

FIXED_NOW = datetime(2026, 6, 15, tzinfo=timezone.utc)


def _patch_now():
    return patch("app.pipeline.retrieve.datetime", wraps=datetime,
                 **{"now": MagicMock(return_value=FIXED_NOW)})


class TestRecencyAffectsCombinedScore:

    def test_recent_evidence_scores_higher(self, retriever):
        """Same source, recent date → higher final_score than old date."""
        recent_ev = {
            "source": "reuters.com",
            "url": "https://reuters.com/recent",
            "text": "Recent evidence about the topic with fresh data",
            "published_date": "2026-01-15",
            "combined_score": 0.8,
        }
        old_ev = {
            "source": "bbc.com",
            "url": "https://bbc.com/old",
            "text": "Older evidence about the same topic from years ago",
            "published_date": "2020-01-15",
            "combined_score": 0.8,
        }
        claim = {"text": "test", "position": 0}

        with _patch_now():
            result = retriever._apply_credibility_weighting(
                [recent_ev, old_ev], claim, track_raw_evidence=False
            )

        weighted = result if isinstance(result, list) else result[0]
        # Recent should have recency_score=1.0, old should have 0.80
        assert len(weighted) == 2, f"Expected 2 items, got {len(weighted)}"
        assert weighted[0]["recency_score"] > weighted[1]["recency_score"]
        assert weighted[0]["final_score"] > weighted[1]["final_score"]

    def test_undated_gets_default_recency(self, retriever):
        """Evidence without published_date gets recency_score=0.80."""
        ev = {
            "source": "reuters.com",
            "url": "https://reuters.com/undated",
            "text": "Test",
            "published_date": None,
            "combined_score": 0.8,
        }
        claim = {"text": "test", "position": 0}

        result = retriever._apply_credibility_weighting(
            [ev], claim, track_raw_evidence=False
        )
        weighted = result if isinstance(result, list) else result[0]
        assert weighted[0]["recency_score"] == 0.80


# ---------------------------------------------------------------------------
# D) Determinism under frozen evidence replay
# ---------------------------------------------------------------------------

class TestDeterminismUnderFrozenReplay:

    def test_assess_staleness_deterministic(self, judge):
        """Same input always produces same staleness assessment."""
        claim = _time_sensitive_claim("current_week")
        evidence = [
            _make_evidence(is_stale=True, age_days=400),
            _make_evidence(source="b.com", url="https://b.com/1", is_stale=False, age_days=5),
            _make_undated_evidence("c.com", "https://c.com/1"),
        ]
        result1 = judge._assess_staleness(claim, evidence)
        result2 = judge._assess_staleness(claim, evidence)
        assert result1 == result2

    def test_recency_score_deterministic(self, retriever):
        """Same published_date always produces same recency_score."""
        with _patch_now():
            s1 = retriever._get_recency_score("2024-06-15")
            s2 = retriever._get_recency_score("2024-06-15")
        assert s1 == s2

    def test_weighting_deterministic(self, retriever):
        """Same evidence list through _apply_credibility_weighting is deterministic."""
        evidence = [
            {"source": "reuters.com", "url": "https://reuters.com/1",
             "text": "Text", "published_date": "2026-01-15", "combined_score": 0.8},
            {"source": "bbc.com", "url": "https://bbc.com/1",
             "text": "Text", "published_date": "2024-03-10", "combined_score": 0.7},
        ]
        claim = {"text": "test", "position": 0}

        import copy
        with _patch_now():
            r1 = retriever._apply_credibility_weighting(
                copy.deepcopy(evidence), claim, track_raw_evidence=False
            )
            r2 = retriever._apply_credibility_weighting(
                copy.deepcopy(evidence), claim, track_raw_evidence=False
            )

        w1 = r1 if isinstance(r1, list) else r1[0]
        w2 = r2 if isinstance(r2, list) else r2[0]
        for i in range(len(w1)):
            assert w1[i]["final_score"] == w2[i]["final_score"]
            assert w1[i]["recency_score"] == w2[i]["recency_score"]
