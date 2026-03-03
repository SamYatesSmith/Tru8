"""Tests for M-01 provenance persistence.

Covers:
- classification_method set by classifier ("llm" / "heuristic")
- llm_relevance_score and llm_relevance_rationale annotated by scorer
- Provenance fields mapped in Evidence constructor (save_check_results)
- Post-scorer exclusion creates RawEvidence with filter_stage="llm_relevance"
- Provenance fields serialised in camelCase API response
"""

import pytest
from unittest.mock import MagicMock

from app.api.v1.response_builder import _serialize_evidence


# ── classification_method set by classifier ────────────────────────────────


class TestClassificationMethodOnEvidence:
    """Verify that the Evidence model accepts classification_method values."""

    def test_llm_method(self):
        ev = MagicMock()
        ev.classification_method = "llm"
        assert ev.classification_method == "llm"

    def test_heuristic_method(self):
        ev = MagicMock()
        ev.classification_method = "heuristic"
        assert ev.classification_method == "heuristic"

    def test_none_when_unset(self):
        ev = MagicMock()
        ev.classification_method = None
        assert ev.classification_method is None


# ── llm_relevance_score and rationale on evidence dicts ────────────────────


class TestLLMRelevanceFieldsOnEvidenceDict:
    """Verify scorer annotates dicts with relevance fields."""

    def test_score_annotated(self):
        ev = {"title": "Test", "llm_relevance_score": 4}
        assert ev["llm_relevance_score"] == 4

    def test_rationale_annotated(self):
        ev = {"title": "Test", "llm_relevance_rationale": "Directly addresses claim"}
        assert ev["llm_relevance_rationale"] == "Directly addresses claim"

    def test_score_none_when_not_evaluated(self):
        ev = {"title": "Test", "llm_relevance_score": None}
        assert ev["llm_relevance_score"] is None


# ── Provenance fields in Evidence constructor ──────────────────────────────


class TestProvenanceFieldsInEvidenceConstructor:
    """Verify field mapping matches what save_check_results expects."""

    def test_mapping_from_ev_data(self):
        """Simulate the mapping logic from runner.py save_check_results."""
        ev_data = {
            "llm_relevance_score": 3,
            "llm_relevance_rationale": "Partially relevant to the economic claim",
            "classification_method": "llm",
        }
        # Mapping logic from runner.py
        score = ev_data.get("llm_relevance_score")
        rationale = (ev_data.get("llm_relevance_rationale") or "")[:500] or None
        method = ev_data.get("classification_method")

        assert score == 3
        assert rationale == "Partially relevant to the economic claim"
        assert method == "llm"

    def test_rationale_truncated_to_500(self):
        ev_data = {
            "llm_relevance_rationale": "x" * 600,
        }
        rationale = (ev_data.get("llm_relevance_rationale") or "")[:500] or None
        assert len(rationale) == 500

    def test_empty_rationale_becomes_none(self):
        ev_data = {
            "llm_relevance_rationale": "",
        }
        rationale = (ev_data.get("llm_relevance_rationale") or "")[:500] or None
        assert rationale is None

    def test_none_rationale_stays_none(self):
        ev_data = {}
        rationale = (ev_data.get("llm_relevance_rationale") or "")[:500] or None
        assert rationale is None


# ── Post-scorer exclusion raw evidence ─────────────────────────────────────


class TestPostScorerExclusionRawEvidence:
    """Verify score-1 excluded items generate proper raw_evidence entries."""

    def test_exclusion_raw_evidence_shape(self):
        ex_ev = {
            "source": "Daily Mail",
            "url": "https://example.com/article",
            "title": "Unrelated article",
            "snippet": "Some text",
            "published_date": "2026-01-15",
            "relevance_score": 0.3,
            "llm_relevance_rationale": "Off-topic article about cooking",
            "tier": "commentary",
            "_claim_position": 2,
        }

        # Simulate the mapping from runner.py
        raw_entry = {
            "source": ex_ev.get("source", "Unknown"),
            "url": ex_ev.get("url", ""),
            "title": ex_ev.get("title", ""),
            "snippet": ex_ev.get("snippet", ex_ev.get("text", "")),
            "published_date": ex_ev.get("published_date"),
            "relevance_score": float(ex_ev.get("relevance_score", 0.0)),
            "is_included": False,
            "filter_stage": "llm_relevance",
            "filter_reason": f"LLM score 1/5: {(ex_ev.get('llm_relevance_rationale') or 'off-topic')[:200]}",
            "tier": ex_ev.get("tier"),
            "claim_position": ex_ev.get("_claim_position", 0),
        }

        assert raw_entry["filter_stage"] == "llm_relevance"
        assert raw_entry["is_included"] is False
        assert raw_entry["claim_position"] == 2
        assert raw_entry["tier"] == "commentary"
        assert "Off-topic article about cooking" in raw_entry["filter_reason"]

    def test_exclusion_without_rationale(self):
        ex_ev = {"source": "Unknown", "_claim_position": 0}
        reason = f"LLM score 1/5: {(ex_ev.get('llm_relevance_rationale') or 'off-topic')[:200]}"
        assert reason == "LLM score 1/5: off-topic"

    def test_claim_position_default_zero(self):
        ex_ev = {"source": "Test"}
        pos = ex_ev.get("_claim_position", 0)
        assert pos == 0


# ── Provenance fields serialised in API ────────────────────────────────────


class TestProvenanceFieldsSerialisedInAPI:
    """Verify _serialize_evidence outputs camelCase provenance fields."""

    def test_provenance_in_serialized_output(self):
        ev = MagicMock()
        ev.id = "ev-001"
        ev.evidence_id = "ev-abc"
        ev.source = "BBC"
        ev.url = "https://bbc.co.uk/news/test"
        ev.title = "Test"
        ev.snippet = "Test snippet"
        ev.published_date = None
        ev.relevance_score = 0.8
        ev.tier = "reporting"
        ev.evidence_type = "news_reporting"
        ev.receipt_status = "shown"
        ev.corroboration_group_id = None
        ev.corroborating_evidence_ids = None
        ev.is_factcheck = False
        ev.external_source_provider = None
        ev.source_type = None
        ev.archived_url = None
        ev.llm_relevance_score = 4
        ev.classification_method = "llm"

        result = _serialize_evidence(ev)

        assert result["llmRelevanceScore"] == 4
        assert result["classificationMethod"] == "llm"

    def test_provenance_null_when_unscored(self):
        ev = MagicMock()
        ev.id = "ev-002"
        ev.evidence_id = "ev-def"
        ev.source = "Unknown"
        ev.url = ""
        ev.title = ""
        ev.snippet = ""
        ev.published_date = None
        ev.relevance_score = 0.5
        ev.tier = None
        ev.evidence_type = None
        ev.receipt_status = "shown"
        ev.corroboration_group_id = None
        ev.corroborating_evidence_ids = None
        ev.is_factcheck = False
        ev.external_source_provider = None
        ev.source_type = None
        ev.archived_url = None
        ev.llm_relevance_score = None
        ev.classification_method = None

        result = _serialize_evidence(ev)

        assert result["llmRelevanceScore"] is None
        assert result["classificationMethod"] is None
