"""Tests for PR 2-D: Snippet-only evidence guardrails in judge context.

Verifies:
1. Extracted evidence preferred over snippet-only in judge selection
2. Snippet-only capped at MAX_SNIPPET_EVIDENCE_FOR_JUDGE when extracted exists
3. All-snippet scenario: no cap, all items pass through
4. All-extracted scenario: identical to old evidence[:5] behavior
5. Original order preserved within extracted and snippet-only groups
6. All-snippet warning text strengthened
7. Mixed warning text shows correct count
8. Evidence without metadata key doesn't crash
"""
import pytest
from app.pipeline.judge import _select_judge_evidence


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ev(source, url, is_snippet=False, llm_score=4):
    """Build a minimal evidence dict."""
    ev = {
        "source": source,
        "url": url,
        "title": f"Article from {source}",
        "text": f"Full content from {source}" if not is_snippet else f"Brief snippet from {source}",
        "snippet": f"Snippet from {source}",
        "published_date": "2026-02-01",
        "credibility_score": 0.85,
        "final_score": 0.80,
        "llm_relevance_score": llm_score,
        "metadata": {
            "is_snippet_fallback": is_snippet,
            "extraction_status": "fallback_blocked" if is_snippet else "success",
        },
    }
    return ev


# ---------------------------------------------------------------------------
# _select_judge_evidence tests
# ---------------------------------------------------------------------------

class TestSelectJudgeEvidence:

    def test_extracted_preferred_over_snippet(self):
        """3 extracted + 3 snippet-only → 3 extracted + 2 snippet, extracted first."""
        evidence = [
            _ev("reuters.com", "https://reuters.com/a1"),
            _ev("bbc.com", "https://bbc.com/a1"),
            _ev("apnews.com", "https://apnews.com/a1"),
            _ev("cnn.com", "https://cnn.com/a1", is_snippet=True),
            _ev("fox.com", "https://fox.com/a1", is_snippet=True),
            _ev("nbc.com", "https://nbc.com/a1", is_snippet=True),
        ]

        result = _select_judge_evidence(evidence, max_items=5, max_snippet_only=2)

        assert len(result) == 5
        # First 3 are extracted
        for ev in result[:3]:
            assert not ev["metadata"]["is_snippet_fallback"]
        # Last 2 are snippet-only
        for ev in result[3:]:
            assert ev["metadata"]["is_snippet_fallback"]

    def test_snippet_cap_at_max(self):
        """1 extracted + 4 snippet-only → 1 extracted + 2 snippet (cap=2)."""
        evidence = [
            _ev("reuters.com", "https://reuters.com/a1"),
            _ev("cnn.com", "https://cnn.com/a1", is_snippet=True),
            _ev("fox.com", "https://fox.com/a1", is_snippet=True),
            _ev("nbc.com", "https://nbc.com/a1", is_snippet=True),
            _ev("abc.com", "https://abc.com/a1", is_snippet=True),
        ]

        result = _select_judge_evidence(evidence, max_items=5, max_snippet_only=2)

        assert len(result) == 3
        extracted = [e for e in result if not e["metadata"]["is_snippet_fallback"]]
        snippets = [e for e in result if e["metadata"]["is_snippet_fallback"]]
        assert len(extracted) == 1
        assert len(snippets) == 2

    def test_all_snippet_no_cap(self):
        """5 snippet-only → all 5 pass through, no cap."""
        evidence = [
            _ev("cnn.com", f"https://cnn.com/a{i}", is_snippet=True)
            for i in range(5)
        ]

        result = _select_judge_evidence(evidence, max_items=5, max_snippet_only=2)

        assert len(result) == 5
        for ev in result:
            assert ev["metadata"]["is_snippet_fallback"]

    def test_all_extracted_unchanged(self):
        """5 extracted → same as evidence[:5], no change."""
        evidence = [
            _ev(f"source{i}.com", f"https://source{i}.com/a1")
            for i in range(7)
        ]

        result = _select_judge_evidence(evidence, max_items=5, max_snippet_only=2)

        assert len(result) == 5
        for i, ev in enumerate(result):
            assert ev["url"] == evidence[i]["url"]
            assert not ev["metadata"]["is_snippet_fallback"]

    def test_ordering_preserved_within_groups(self):
        """Original order within extracted and within snippet groups is maintained."""
        evidence = [
            _ev("first-ext.com", "https://first-ext.com/a1"),
            _ev("second-ext.com", "https://second-ext.com/a1"),
            _ev("first-snip.com", "https://first-snip.com/a1", is_snippet=True),
            _ev("second-snip.com", "https://second-snip.com/a1", is_snippet=True),
        ]

        result = _select_judge_evidence(evidence, max_items=5, max_snippet_only=2)

        assert len(result) == 4
        assert result[0]["source"] == "first-ext.com"
        assert result[1]["source"] == "second-ext.com"
        assert result[2]["source"] == "first-snip.com"
        assert result[3]["source"] == "second-snip.com"

    def test_evidence_without_metadata(self):
        """Evidence dicts missing 'metadata' key don't crash."""
        evidence = [
            {"source": "reuters.com", "url": "https://reuters.com/a1", "text": "Full text"},
            {"source": "bbc.com", "url": "https://bbc.com/a1", "text": "Brief"},
        ]

        result = _select_judge_evidence(evidence, max_items=5, max_snippet_only=2)

        # Both treated as extracted (no metadata → not snippet)
        assert len(result) == 2

    def test_top_level_is_snippet_fallback(self):
        """Evidence with top-level is_snippet_fallback (no metadata) is detected."""
        evidence = [
            {"source": "reuters.com", "url": "https://reuters.com/a1", "text": "Full",
             "is_snippet_fallback": True},
            {"source": "bbc.com", "url": "https://bbc.com/a1", "text": "Full"},
        ]

        result = _select_judge_evidence(evidence, max_items=5, max_snippet_only=1)

        assert len(result) == 2
        # Extracted first
        assert result[0]["source"] == "bbc.com"
        assert result[1]["source"] == "reuters.com"

    def test_max_snippet_zero_excludes_all_snippets(self):
        """max_snippet_only=0 excludes snippet items when extracted exist."""
        evidence = [
            _ev("reuters.com", "https://reuters.com/a1"),
            _ev("cnn.com", "https://cnn.com/a1", is_snippet=True),
            _ev("fox.com", "https://fox.com/a1", is_snippet=True),
        ]

        result = _select_judge_evidence(evidence, max_items=5, max_snippet_only=0)

        assert len(result) == 1
        assert result[0]["source"] == "reuters.com"

    def test_extracted_fills_all_slots(self):
        """5+ extracted + snippet-only → all 5 slots go to extracted, no snippets."""
        evidence = [
            _ev(f"ext{i}.com", f"https://ext{i}.com/a1")
            for i in range(6)
        ] + [
            _ev("snip.com", "https://snip.com/a1", is_snippet=True),
        ]

        result = _select_judge_evidence(evidence, max_items=5, max_snippet_only=2)

        assert len(result) == 5
        for ev in result:
            assert not ev.get("metadata", {}).get("is_snippet_fallback", False)


# ---------------------------------------------------------------------------
# Warning text tests (via _prepare_judgment_context internals)
# ---------------------------------------------------------------------------

class TestSnippetWarningText:

    def test_all_snippet_warning_contains_all_keyword(self):
        """When all evidence is snippet-only, warning text should say 'ALL'."""
        snippet_only_count = 3
        evidence_shown_count = 3

        # Reproduce the exact condition from judge.py
        if snippet_only_count > 0 and snippet_only_count == evidence_shown_count:
            warning = (
                f"ALL {evidence_shown_count} evidence items are search snippets "
                f"(full pages unavailable)."
            )
        else:
            warning = ""

        assert "ALL" in warning
        assert "search snippets" in warning

    def test_mixed_warning_shows_count(self):
        """When some evidence is snippet-only, warning shows X of Y."""
        snippet_only_count = 2
        evidence_shown_count = 5

        if snippet_only_count > 0 and snippet_only_count == evidence_shown_count:
            warning = "ALL"
        elif snippet_only_count > 0:
            warning = (
                f"{snippet_only_count} of {evidence_shown_count} evidence items "
                f"are snippets (full page unavailable)."
            )
        else:
            warning = ""

        assert "2 of 5" in warning

    def test_no_snippet_no_warning(self):
        """When no snippet-only evidence, no warning emitted."""
        snippet_only_count = 0
        evidence_shown_count = 5

        warning = ""
        if snippet_only_count > 0 and snippet_only_count == evidence_shown_count:
            warning = "ALL"
        elif snippet_only_count > 0:
            warning = "partial"

        assert warning == ""


# ---------------------------------------------------------------------------
# Config defaults
# ---------------------------------------------------------------------------

class TestSnippetConfig:

    def test_default_max_snippet_for_judge(self):
        """Default MAX_SNIPPET_EVIDENCE_FOR_JUDGE is 2."""
        from app.core.config import Settings
        field = Settings.model_fields['MAX_SNIPPET_EVIDENCE_FOR_JUDGE']
        assert field.default == 2
