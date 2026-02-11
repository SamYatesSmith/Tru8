"""
Tests for Snippet Fallback Honesty labels in judge.py (PR 1-C).

Verifies that when evidence items are snippet-only (full page extraction failed),
the Judge LLM context includes:
- A per-evidence [SNIPPET ONLY] tag before the Content line
- A global warning block counting snippet-only items
- No marker for full-extract evidence
"""
import pytest
from unittest.mock import patch, MagicMock

from app.pipeline.judge import ClaimJudge


@pytest.fixture
def judge():
    """Create a ClaimJudge instance with minimal config."""
    with patch("app.pipeline.judge.settings") as mock_settings:
        mock_settings.OPENAI_API_KEY = "test"
        mock_settings.GOOGLE_AI_API_KEY = ""
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


def _make_claim(text="Test claim about something"):
    return {"text": text, "position": 0}


def _make_evidence(source="reuters.com", url="https://reuters.com/article",
                   text="Full article text with detailed information",
                   is_snippet_fallback=False, fallback_reason=None,
                   use_metadata=False):
    """Create an evidence dict.

    Args:
        use_metadata: If True, put snippet flags in metadata dict (upstream format).
                      If False, put them as top-level keys.
    """
    ev = {
        "source": source,
        "url": url,
        "text": text,
        "snippet": text,
        "published_date": "2026-01-15",
        "credibility_score": 0.9,
        "metadata": {},
    }
    if use_metadata:
        ev["metadata"]["is_snippet_fallback"] = is_snippet_fallback
        if fallback_reason:
            ev["metadata"]["fallback_reason"] = fallback_reason
    else:
        ev["is_snippet_fallback"] = is_snippet_fallback
        if fallback_reason:
            ev["snippet_fallback_reason"] = fallback_reason
    return ev


class TestSnippetOnlyMarkerInContext:

    def test_snippet_only_marker_present(self, judge):
        """Evidence with is_snippet_fallback=True gets [SNIPPET ONLY] tag."""
        evidence = [
            _make_evidence(
                source="Reuters",
                text="Short snippet text",
                is_snippet_fallback=True,
                fallback_reason="429 Too Many Requests",
            ),
        ]
        context = judge._prepare_judgment_context(
            _make_claim(), evidence
        )
        assert "[SNIPPET ONLY \u2014 full page unavailable: 429]" in context

    def test_snippet_only_marker_appears_before_content(self, judge):
        """The [SNIPPET ONLY] tag appears before the Content: line for that evidence."""
        evidence = [
            _make_evidence(
                source="Reuters",
                text="Short snippet text",
                is_snippet_fallback=True,
                fallback_reason="403 Forbidden",
            ),
        ]
        context = judge._prepare_judgment_context(
            _make_claim(), evidence
        )
        marker = "[SNIPPET ONLY \u2014 full page unavailable: 403]"
        marker_pos = context.index(marker)
        content_pos = context.index("Content: Short snippet text")
        assert marker_pos < content_pos

    def test_reason_classification_timeout(self, judge):
        """Timeout reason is classified correctly."""
        evidence = [
            _make_evidence(is_snippet_fallback=True, fallback_reason="ReadTimeout: connection timed out"),
        ]
        context = judge._prepare_judgment_context(
            _make_claim(), evidence
        )
        assert "full page unavailable: timeout]" in context

    def test_reason_classification_js_required(self, judge):
        """JavaScript-related failures are classified as js_required."""
        evidence = [
            _make_evidence(is_snippet_fallback=True, fallback_reason="JavaScript required to render"),
        ]
        context = judge._prepare_judgment_context(
            _make_claim(), evidence
        )
        assert "full page unavailable: js_required]" in context

    def test_reason_classification_unknown(self, judge):
        """Unrecognized reasons default to 'unknown'."""
        evidence = [
            _make_evidence(is_snippet_fallback=True, fallback_reason="Something weird happened"),
        ]
        context = judge._prepare_judgment_context(
            _make_claim(), evidence
        )
        assert "full page unavailable: unknown]" in context

    def test_reason_missing_defaults_to_unknown(self, judge):
        """Missing reason defaults to 'unknown'."""
        evidence = [
            _make_evidence(is_snippet_fallback=True, fallback_reason=None),
        ]
        context = judge._prepare_judgment_context(
            _make_claim(), evidence
        )
        assert "full page unavailable: unknown]" in context


class TestSnippetOnlyMarkerFromMetadata:

    def test_reads_from_metadata(self, judge):
        """Evidence with is_snippet_fallback in metadata (upstream format) gets marker."""
        evidence = [
            _make_evidence(
                source="BBC",
                text="Snippet from BBC",
                is_snippet_fallback=True,
                fallback_reason="timeout",
                use_metadata=True,
            ),
        ]
        context = judge._prepare_judgment_context(
            _make_claim(), evidence
        )
        assert "[SNIPPET ONLY \u2014 full page unavailable: timeout]" in context

    def test_reads_fallback_reason_from_metadata(self, judge):
        """fallback_reason in metadata is read correctly."""
        evidence = [
            _make_evidence(
                is_snippet_fallback=True,
                fallback_reason="403 Forbidden",
                use_metadata=True,
            ),
        ]
        context = judge._prepare_judgment_context(
            _make_claim(), evidence
        )
        assert "full page unavailable: 403]" in context


class TestNoMarkerForFullExtract:

    def test_no_marker_when_full_extract(self, judge):
        """Evidence without snippet fallback flags has no [SNIPPET ONLY] tag."""
        evidence = [
            _make_evidence(
                source="Reuters",
                text="Full article with lots of detailed information about the topic",
                is_snippet_fallback=False,
            ),
        ]
        context = judge._prepare_judgment_context(
            _make_claim(), evidence
        )
        assert "[SNIPPET ONLY" not in context

    def test_no_marker_when_no_flags(self, judge):
        """Evidence with no snippet flags at all has no marker."""
        evidence = [{
            "source": "reuters.com",
            "url": "https://reuters.com/article",
            "text": "Full content",
            "snippet": "Full content",
            "published_date": "2026-01-15",
            "metadata": {},
        }]
        context = judge._prepare_judgment_context(
            _make_claim(), evidence
        )
        assert "[SNIPPET ONLY" not in context


class TestSnippetOnlyWarningBlock:

    def test_warning_block_present(self, judge):
        """When snippet-only evidence exists, warning block is in context."""
        evidence = [
            _make_evidence(is_snippet_fallback=True, fallback_reason="429"),
            _make_evidence(source="bbc.com", url="https://bbc.com/news", is_snippet_fallback=False),
        ]
        context = judge._prepare_judgment_context(
            _make_claim(), evidence
        )
        assert "SNIPPET-ONLY EVIDENCE WARNING" in context
        assert "1 of 2 evidence items are snippets" in context

    def test_warning_block_absent_when_no_snippets(self, judge):
        """When no snippet-only evidence, warning block is absent."""
        evidence = [
            _make_evidence(is_snippet_fallback=False),
            _make_evidence(source="bbc.com", url="https://bbc.com/news", is_snippet_fallback=False),
        ]
        context = judge._prepare_judgment_context(
            _make_claim(), evidence
        )
        assert "SNIPPET-ONLY EVIDENCE WARNING" not in context

    def test_warning_block_counts_multiple(self, judge):
        """Warning block correctly counts multiple snippet-only items."""
        evidence = [
            _make_evidence(source="a.com", url="https://a.com/1", is_snippet_fallback=True, fallback_reason="403"),
            _make_evidence(source="b.com", url="https://b.com/2", is_snippet_fallback=True, fallback_reason="timeout"),
            _make_evidence(source="c.com", url="https://c.com/3", is_snippet_fallback=False),
        ]
        context = judge._prepare_judgment_context(
            _make_claim(), evidence
        )
        assert "2 of 3 evidence items are snippets" in context
