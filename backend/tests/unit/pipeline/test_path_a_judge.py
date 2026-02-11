"""
Tests for PATH_A judge-led pipeline (controlled simplification experiment).

Verifies:
1. PATH_A skips pre-judge abstention — judge always runs
2. PATH_A context uses E-ID format (E1, E2, ...)
3. cited_evidence_ids are resolved to actual evidence items for display
4. Fallback when LLM returns no parseable cited_evidence_ids
5. No evidence is filtered by _select_display_evidence under PATH_A
6. PATH_A system prompt is concise and ID-based
7. _prepare_path_a_context includes all evidence (no truncation to 5)
"""
import pytest
import json
from unittest.mock import patch, MagicMock, AsyncMock

from app.pipeline.judge import ClaimJudge, _select_display_evidence


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def judge():
    """Create a ClaimJudge with PATH_A enabled."""
    with patch("app.pipeline.judge.settings") as mock_settings:
        mock_settings.OPENAI_API_KEY = "test"
        mock_settings.GOOGLE_AI_API_KEY = "test-key"
        mock_settings.JUDGE_MAX_TOKENS = 1000
        mock_settings.JUDGE_TEMPERATURE = 0.3
        mock_settings.EVIDENCE_SNIPPET_LENGTH = 300
        mock_settings.ENABLE_JUDGE_FEW_SHOT = False
        mock_settings.ENABLE_RHETORICAL_CONTEXT = False
        mock_settings.ENABLE_ABSTENTION_LOGIC = True  # Would block, but PATH_A skips it
        mock_settings.ENABLE_PATH_A = True
        mock_settings.MAX_SNIPPET_EVIDENCE_FOR_JUDGE = 2
        mock_settings.MIN_SOURCES_FOR_VERDICT = 2
        mock_settings.MIN_CREDIBILITY_THRESHOLD = 0.60
        mock_settings.MIN_CONSENSUS_STRENGTH = 0.50
        j = ClaimJudge()
        yield j


@pytest.fixture
def judge_no_path_a():
    """Create a ClaimJudge with PATH_A disabled (baseline)."""
    with patch("app.pipeline.judge.settings") as mock_settings:
        mock_settings.OPENAI_API_KEY = "test"
        mock_settings.GOOGLE_AI_API_KEY = "test-key"
        mock_settings.JUDGE_MAX_TOKENS = 1000
        mock_settings.JUDGE_TEMPERATURE = 0.3
        mock_settings.EVIDENCE_SNIPPET_LENGTH = 300
        mock_settings.ENABLE_JUDGE_FEW_SHOT = False
        mock_settings.ENABLE_RHETORICAL_CONTEXT = False
        mock_settings.ENABLE_ABSTENTION_LOGIC = True
        mock_settings.ENABLE_PATH_A = False
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


def _make_evidence(source="reuters.com", url="https://reuters.com/article",
                   text="Full article text with detailed information",
                   llm_score=4, credibility=0.9, date="2026-01-15"):
    return {
        "source": source,
        "url": url,
        "text": text,
        "snippet": text,
        "published_date": date,
        "credibility_score": credibility,
        "llm_relevance_score": llm_score,
        "metadata": {},
    }


def _make_google_response(verdict="supported", confidence=85,
                          cited_ids=None, rationale="Evidence supports."):
    """Build a mock Google AI JSON response."""
    if cited_ids is None:
        cited_ids = ["E1", "E2"]
    body = {
        "verdict": verdict,
        "confidence": confidence,
        "cited_evidence_ids": cited_ids,
        "rationale": rationale,
    }
    return {
        "candidates": [{
            "content": {
                "parts": [{"text": json.dumps(body)}]
            }
        }]
    }


# ---------------------------------------------------------------------------
# Tests: PATH_A context format
# ---------------------------------------------------------------------------

class TestPathAContext:

    def test_context_uses_eid_format(self, judge):
        """Evidence items are numbered E1, E2, ... in PATH_A context."""
        evidence = [
            _make_evidence(source="Reuters"),
            _make_evidence(source="BBC", url="https://bbc.com/news"),
            _make_evidence(source="AP News", url="https://apnews.com/1"),
        ]
        context = judge._prepare_path_a_context(_make_claim(), evidence)

        assert "E1: Reuters" in context
        assert "E2: BBC" in context
        assert "E3: AP News" in context
        assert "Total evidence items: 3" in context

    def test_context_includes_all_evidence(self, judge):
        """PATH_A sends ALL evidence to judge, not just top 5."""
        evidence = [_make_evidence(source=f"Source{i}", url=f"https://s{i}.com")
                    for i in range(12)]
        context = judge._prepare_path_a_context(_make_claim(), evidence)

        assert "E12: Source11" in context
        assert "Total evidence items: 12" in context

    def test_context_includes_advisory_llm_score(self, judge):
        """Advisory LLM score is shown as metadata, not used for filtering."""
        evidence = [_make_evidence(llm_score=4)]
        context = judge._prepare_path_a_context(_make_claim(), evidence)

        assert "LLM relevance: 4/5" in context

    def test_context_handles_none_llm_score(self, judge):
        """Evidence with llm_relevance_score=None omits score line."""
        evidence = [_make_evidence(llm_score=None)]
        context = judge._prepare_path_a_context(_make_claim(), evidence)

        assert "LLM relevance:" not in context

    def test_context_includes_credibility(self, judge):
        """Credibility percentage is shown per evidence item."""
        evidence = [_make_evidence(credibility=0.85)]
        context = judge._prepare_path_a_context(_make_claim(), evidence)

        assert "Credibility: 85%" in context


# ---------------------------------------------------------------------------
# Tests: cited_evidence_ids resolution
# ---------------------------------------------------------------------------

class TestCitedEvidenceResolution:

    def test_resolve_valid_ids(self, judge):
        """E1, E3 resolve to indices 0, 2."""
        evidence = [
            _make_evidence(source="A"),
            _make_evidence(source="B"),
            _make_evidence(source="C"),
        ]
        resolved = ClaimJudge._resolve_cited_evidence(["E1", "E3"], evidence)

        assert len(resolved) == 2
        assert resolved[0]["source"] == "A"
        assert resolved[1]["source"] == "C"

    def test_resolve_deduplicates(self, judge):
        """Duplicate IDs are resolved only once."""
        evidence = [_make_evidence(source="A"), _make_evidence(source="B")]
        resolved = ClaimJudge._resolve_cited_evidence(["E1", "E1", "E2"], evidence)

        assert len(resolved) == 2

    def test_resolve_ignores_invalid_ids(self, judge):
        """Invalid IDs (out of range, malformed) are skipped."""
        evidence = [_make_evidence(source="A")]
        resolved = ClaimJudge._resolve_cited_evidence(
            ["E1", "E99", "garbage", "E0"], evidence
        )

        assert len(resolved) == 1
        assert resolved[0]["source"] == "A"

    def test_resolve_empty_list(self, judge):
        """Empty cited_ids → empty result."""
        evidence = [_make_evidence(source="A")]
        resolved = ClaimJudge._resolve_cited_evidence([], evidence)

        assert resolved == []


# ---------------------------------------------------------------------------
# Tests: PATH_A judge_claim flow
# ---------------------------------------------------------------------------

class TestPathAJudgeClaim:

    @pytest.mark.asyncio
    async def test_skips_abstention(self, judge):
        """PATH_A never abstains — judge runs even with 0 evidence."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = _make_google_response(
            verdict="uncertain", confidence=20, cited_ids=[],
            rationale="No evidence found."
        )

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            result = await judge.judge_claim(
                _make_claim(), evidence=[], max_display_items=3
            )

        # Under baseline (PATH_A=False), 0 evidence would abstain.
        # Under PATH_A, judge always runs.
        assert result.verdict == "uncertain"
        assert result.confidence == 20

    @pytest.mark.asyncio
    async def test_abstention_fires_without_path_a(self, judge_no_path_a):
        """Baseline: abstention blocks judgment with 0 evidence."""
        result = await judge_no_path_a.judge_claim(
            _make_claim(), evidence=[], max_display_items=3
        )

        assert result.verdict == "uncertain"
        assert result.confidence == 0.0  # Abstention confidence

    @pytest.mark.asyncio
    async def test_display_uses_cited_evidence(self, judge):
        """Display evidence comes from cited_evidence_ids, not _select_display_evidence."""
        evidence = [
            _make_evidence(source="Reuters", llm_score=5),
            _make_evidence(source="BBC", url="https://bbc.com", llm_score=2),
            _make_evidence(source="AP News", url="https://ap.com", llm_score=4),
        ]

        # LLM cites E2 (BBC, low score) and E3 (AP) — NOT the highest-scored E1
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = _make_google_response(
            verdict="supported", confidence=80,
            cited_ids=["E2", "E3"],
            rationale="BBC (E2) and AP News (E3) confirm."
        )

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            result = await judge.judge_claim(
                _make_claim(), evidence, max_display_items=3
            )

        # Display should be BBC + AP (cited), NOT Reuters (highest score)
        display_sources = [e["source"] for e in result.supporting_evidence]
        assert "BBC" in display_sources
        assert "AP News" in display_sources
        # Reuters was NOT cited, so it should NOT be in display
        assert "Reuters" not in display_sources

    @pytest.mark.asyncio
    async def test_fallback_on_no_cited_ids(self, judge):
        """When LLM returns no cited_evidence_ids, fall back to top by score."""
        evidence = [
            _make_evidence(source="Reuters", llm_score=5),
            _make_evidence(source="Low", url="https://low.com", llm_score=1),
        ]

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = _make_google_response(
            verdict="supported", confidence=70,
            cited_ids=[],  # No citations
            rationale="Evidence supports."
        )

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            result = await judge.judge_claim(
                _make_claim(), evidence, max_display_items=3
            )

        # Fallback: should show something (top by score)
        assert len(result.supporting_evidence) > 0


# ---------------------------------------------------------------------------
# Tests: PATH_A system prompt
# ---------------------------------------------------------------------------

class TestPathASystemPrompt:

    def test_prompt_mentions_eid_format(self, judge):
        """PATH_A system prompt instructs the LLM to use E-IDs."""
        assert "E1" in judge.path_a_system_prompt
        assert "cited_evidence_ids" in judge.path_a_system_prompt

    def test_prompt_is_concise(self, judge):
        """PATH_A prompt is significantly shorter than the default."""
        assert len(judge.path_a_system_prompt) < len(judge.system_prompt) / 2

    def test_prompt_expects_json(self, judge):
        """PATH_A prompt asks for JSON response."""
        assert "JSON" in judge.path_a_system_prompt


# ---------------------------------------------------------------------------
# Tests: evidence_summary includes PATH_A metadata
# ---------------------------------------------------------------------------

class TestPathAMetadata:

    @pytest.mark.asyncio
    async def test_result_includes_path_a_flag(self, judge):
        """JudgmentResult.evidence_summary includes path_a=True."""
        evidence = [_make_evidence()]

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = _make_google_response(
            cited_ids=["E1"]
        )

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            result = await judge.judge_claim(
                _make_claim(), evidence, max_display_items=3
            )

        result_dict = result.to_dict()
        assert result_dict["evidence_summary"].get("path_a") is True
        assert "cited_ids" in result_dict["evidence_summary"]
