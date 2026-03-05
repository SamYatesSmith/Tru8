"""Tests for the mapping quality audit suite (Track N).

Covers:
- Case extraction: schema, evidence fields, mapper window, stratified sampling
- Judgment templates: pre-population, validation, failure mode values
- Summary aggregation: frequency table, window splits, accuracy, dominant mode
- Golden case promotion: expected outputs, data preservation
- Regression comparison: state match/mismatch, ref match/mismatch, summary accuracy
"""

import json
import pytest
from pathlib import Path
from typing import Any, Dict, List

import sys

backend_dir = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(backend_dir))

from scripts.audit_extract import (
    build_case_file,
    build_judgment_template,
    score_claim_for_audit,
    stratified_sample,
)
from scripts.audit_review import (
    build_failure_mode_table,
    build_summary,
    compute_accuracy,
    identify_dominant_mode,
    is_judgment_complete,
    promote_to_golden,
    validate_judgment,
    _build_expected_from_judgment,
)
from scripts.audit_regress import (
    collect_regressions,
    compare_refs,
    compare_states,
    compute_regression_summary,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_claim(
    claim_id: str = "test-001",
    n_elements: int = 2,
    n_evidence: int = 3,
    has_disputed: bool = False,
) -> Dict[str, Any]:
    """Build a synthetic claim dict for testing."""
    elements = [
        {"element_id": f"e{i}", "description": f"Element {i}"}
        for i in range(1, n_elements + 1)
    ]

    evidence = [
        {
            "evidence_id": f"ev-{i:03d}",
            "title": f"Evidence {i}",
            "snippet": f"Snippet for evidence {i}. " * 20,  # ~400 chars
            "text": f"Full text for evidence {i}. " * 50,
            "source": f"source{i}.com",
            "url": f"https://source{i}.com/article",
            "tier": "primary" if i == 1 else "reporting",
            "evidence_type": "data" if i == 1 else "news_reporting",
            "relevance_score": 0.9 - (i * 0.1),
            "llm_relevance_score": 5 - i,
            "classification_method": "llm",
        }
        for i in range(1, n_evidence + 1)
    ]

    # Build original_claim_map
    cm_elements = []
    for i, elem in enumerate(elements, start=1):
        refs = [
            {
                "evidence_id": ev["evidence_id"],
                "relationship": "supports",
                "reasoning": f"Supports element {i}",
            }
            for ev in evidence[:2]
        ]
        state = "disputed" if (has_disputed and i == 1) else "supported"
        cm_elements.append(
            {
                **elem,
                "evidence_refs": refs,
                "state": state,
                "uncertainty": None,
            }
        )

    return {
        "claim_id": claim_id,
        "check_id": f"check-{claim_id}",
        "position": 0,
        "normalised_claim": f"Test claim {claim_id}",
        "elements": elements,
        "evidence": evidence,
        "original_claim_map": {
            "claim_id": claim_id,
            "normalised_claim": f"Test claim {claim_id}",
            "claim_type": "empirical",
            "elements": cm_elements,
            "orientation": None,
            "metadata": {
                "decomposition_model": "test-model",
                "mapping_model": "gemini-2.5-flash-lite",
                "element_count": n_elements,
                "completed_at": "2026-03-01T12:00:00Z",
            },
        },
    }


def _make_judgment(
    case_id: str = "case-001",
    n_refs: int = 2,
    n_states: int = 2,
    complete: bool = True,
    ref_failures: List[Dict[str, Any]] = None,
    state_failures: List[Dict[str, Any]] = None,
    missing_refs: List[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build a synthetic judgment dict for testing."""
    ref_judgments = []
    for i in range(n_refs):
        rj = {
            "element_id": f"e{(i // 2) + 1}",
            "evidence_id": f"ev-{i+1:03d}",
            "mapper_relationship": "supports",
            "mapper_reasoning": f"Reasoning for ref {i}",
            "correct": True if complete else None,
            "expected_relationship": None,
            "failure_mode": None,
            "window_sufficient": None,
            "notes": "",
        }
        ref_judgments.append(rj)

    # Apply ref failures
    if ref_failures:
        for fail in ref_failures:
            idx = fail.get("index", 0)
            if idx < len(ref_judgments):
                ref_judgments[idx]["correct"] = False
                ref_judgments[idx]["failure_mode"] = fail.get("mode", "A")
                ref_judgments[idx]["window_sufficient"] = fail.get("ws", True)
                if fail.get("expected_rel"):
                    ref_judgments[idx]["expected_relationship"] = fail["expected_rel"]

    state_judgments = []
    for i in range(n_states):
        sj = {
            "element_id": f"e{i+1}",
            "mapper_state": "supported",
            "correct": True if complete else None,
            "expected_state": None,
            "failure_mode": None,
            "notes": "",
        }
        state_judgments.append(sj)

    # Apply state failures
    if state_failures:
        for fail in state_failures:
            idx = fail.get("index", 0)
            if idx < len(state_judgments):
                state_judgments[idx]["correct"] = False
                state_judgments[idx]["failure_mode"] = fail.get("mode", "D")
                state_judgments[idx]["expected_state"] = fail.get(
                    "expected", "disputed"
                )

    return {
        "case_id": case_id,
        "reviewed_at": "2026-03-04T10:30:00Z" if complete else None,
        "ref_judgments": ref_judgments,
        "missing_refs": missing_refs or [],
        "state_judgments": state_judgments,
    }


# ---------------------------------------------------------------------------
# Case extraction tests
# ---------------------------------------------------------------------------


class TestCaseExtraction:
    """Tests for audit case file construction."""

    def test_case_schema_has_required_fields(self):
        claim = _make_claim()
        case = build_case_file(claim, case_number=1)

        assert "case_id" in case
        assert "source" in case
        assert "claim" in case
        assert "evidence" in case
        assert "mapper_output" in case

        assert case["case_id"] == "case-001"
        assert "check_id" in case["source"]
        assert "claim_id" in case["source"]
        assert "extracted_at" in case["source"]
        assert "normalised_claim" in case["claim"]
        assert "elements" in case["claim"]
        assert "model" in case["mapper_output"]
        assert "prompt_hash" in case["mapper_output"]
        assert "elements" in case["mapper_output"]

    def test_case_evidence_has_full_text_and_window(self):
        claim = _make_claim(n_evidence=2)
        case = build_case_file(claim, case_number=1)

        for ev in case["evidence"]:
            assert "full_text" in ev
            assert "mapper_window" in ev
            assert len(ev["full_text"]) > 0
            assert len(ev["mapper_window"]) > 0

    def test_case_mapper_window_is_1000_chars(self):
        claim = _make_claim(n_evidence=1)
        # Make sure evidence text is longer than 1000 chars
        claim["evidence"][0]["snippet"] = "A" * 2000
        case = build_case_file(claim, case_number=1, snippet_length=1000)

        ev = case["evidence"][0]
        assert len(ev["mapper_window"]) == 1000
        assert len(ev["full_text"]) == 2000

    def test_stratified_sampling_prefers_disputed(self):
        claims = [
            _make_claim("c1", has_disputed=False),
            _make_claim("c2", has_disputed=True),
            _make_claim("c3", has_disputed=False),
        ]

        selected = stratified_sample(claims, n=1)
        assert len(selected) == 1
        assert selected[0]["claim_id"] == "c2"

    def test_stratified_sampling_prefers_complex(self):
        simple = _make_claim("c1", n_elements=1, n_evidence=2)
        complex_ = _make_claim("c2", n_elements=4, n_evidence=8)
        medium = _make_claim("c3", n_elements=3, n_evidence=3)

        selected = stratified_sample([simple, complex_, medium], n=2)
        ids = [c["claim_id"] for c in selected]
        # complex_ should be first (score: +1 elements +1 evidence = 2)
        assert ids[0] == "c2"


# ---------------------------------------------------------------------------
# Judgment schema tests
# ---------------------------------------------------------------------------


class TestJudgmentTemplates:
    """Tests for judgment template construction and validation."""

    def test_judgment_template_prepopulated(self):
        claim = _make_claim(n_elements=2, n_evidence=3)
        case = build_case_file(claim, case_number=1)
        judgment = build_judgment_template(case)

        assert judgment["case_id"] == "case-001"
        assert judgment["reviewed_at"] is None

        # Ref judgments: pre-populated with mapper assignments
        for rj in judgment["ref_judgments"]:
            assert rj["mapper_relationship"] is not None
            assert rj["correct"] is None  # Not yet reviewed
            assert rj["failure_mode"] is None

        # State judgments: pre-populated with mapper states
        for sj in judgment["state_judgments"]:
            assert sj["mapper_state"] is not None
            assert sj["correct"] is None
            assert sj["failure_mode"] is None

        # Missing refs: empty
        assert judgment["missing_refs"] == []

    def test_judgment_validation_catches_incomplete(self):
        judgment = _make_judgment(complete=False)
        errors = validate_judgment(judgment)
        assert len(errors) > 0
        assert any("null" in e for e in errors)

    def test_judgment_validation_catches_missing_failure_mode(self):
        judgment = _make_judgment(
            complete=True,
            ref_failures=[{"index": 0, "mode": None, "ws": True}],
        )
        # Manually set correct=False without failure_mode
        judgment["ref_judgments"][0]["correct"] = False
        judgment["ref_judgments"][0]["failure_mode"] = None
        errors = validate_judgment(judgment)
        assert any("failure_mode" in e for e in errors)

    def test_judgment_failure_modes_are_valid(self):
        # Valid modes: A, B, C, D — anything else should fail validation
        judgment = _make_judgment(
            complete=True,
            ref_failures=[{"index": 0, "mode": "X", "ws": True}],
        )
        errors = validate_judgment(judgment)
        assert any("invalid failure_mode" in e for e in errors)


# ---------------------------------------------------------------------------
# Summary aggregation tests
# ---------------------------------------------------------------------------


class TestSummaryAggregation:
    """Tests for failure mode summary computation."""

    def test_summary_counts_failure_modes(self):
        judgments = [
            _make_judgment(
                ref_failures=[
                    {"index": 0, "mode": "A", "ws": True},
                    {"index": 1, "mode": "B", "ws": False},
                ],
            ),
        ]
        table = build_failure_mode_table(judgments)
        assert table["A_missed_contradiction"]["window_sufficient"] == 1
        assert table["B_phantom_support"]["window_insufficient"] == 1

    def test_summary_splits_by_window(self):
        judgments = [
            _make_judgment(
                n_refs=4,
                ref_failures=[
                    {"index": 0, "mode": "A", "ws": True},
                    {"index": 1, "mode": "A", "ws": False},
                    {"index": 2, "mode": "A", "ws": False},
                ],
            ),
        ]
        table = build_failure_mode_table(judgments)
        a = table["A_missed_contradiction"]
        assert a["window_sufficient"] == 1
        assert a["window_insufficient"] == 2

    def test_summary_computes_accuracy(self):
        judgment = _make_judgment(
            n_refs=4,
            n_states=2,
            ref_failures=[{"index": 0, "mode": "A", "ws": True}],
            state_failures=[{"index": 0, "mode": "D", "expected": "disputed"}],
        )
        accuracy = compute_accuracy([judgment])
        # 3/4 refs correct = 0.75
        assert accuracy["relationship_correct_pct"] == 0.75
        # 1/2 states correct = 0.5
        assert accuracy["state_correct_pct"] == 0.5

    def test_summary_identifies_dominant_mode(self):
        table = {
            "A_missed_contradiction": {
                "window_sufficient": 2,
                "window_insufficient": 7,
            },
            "B_phantom_support": {"window_sufficient": 4, "window_insufficient": 1},
            "C_misattributed_scope": {"window_sufficient": 1, "window_insufficient": 0},
            "D_state_inflation": {"window_sufficient": 3, "window_insufficient": 0},
        }
        mode, cause, signal = identify_dominant_mode(table)
        assert mode == "A_missed_contradiction"  # 9 total, highest
        assert cause == "window_insufficient"  # 7 > 2
        assert "input pipeline" in signal.lower() or "Fix input" in signal

    def test_summary_generates_decision_signal(self):
        # Window-sufficient dominant: model issue
        table_ws = {
            "A_missed_contradiction": {
                "window_sufficient": 0,
                "window_insufficient": 0,
            },
            "B_phantom_support": {"window_sufficient": 10, "window_insufficient": 2},
            "C_misattributed_scope": {"window_sufficient": 0, "window_insufficient": 0},
            "D_state_inflation": {"window_sufficient": 0, "window_insufficient": 0},
        }
        _, cause_ws, signal_ws = identify_dominant_mode(table_ws)
        assert cause_ws == "window_sufficient"
        assert "model" in signal_ws.lower()

        # Window-insufficient dominant: input issue
        table_wi = {
            "A_missed_contradiction": {
                "window_sufficient": 1,
                "window_insufficient": 8,
            },
            "B_phantom_support": {"window_sufficient": 0, "window_insufficient": 0},
            "C_misattributed_scope": {"window_sufficient": 0, "window_insufficient": 0},
            "D_state_inflation": {"window_sufficient": 0, "window_insufficient": 0},
        }
        _, cause_wi, signal_wi = identify_dominant_mode(table_wi)
        assert cause_wi == "window_insufficient"
        assert "input" in signal_wi.lower()


# ---------------------------------------------------------------------------
# Golden case tests
# ---------------------------------------------------------------------------


class TestGoldenCases:
    """Tests for golden case promotion."""

    def test_golden_case_has_expected_outputs(self):
        judgment = _make_judgment(
            n_refs=2,
            n_states=2,
            complete=True,
            state_failures=[{"index": 1, "mode": "D", "expected": "disputed"}],
        )
        expected = _build_expected_from_judgment(judgment)

        assert len(expected) == 2
        # All elements should have expected_state
        for elem in expected:
            assert "expected_state" in elem
            assert "expected_refs" in elem

    def test_golden_case_preserves_case_data(self):
        claim = _make_claim()
        case = build_case_file(claim, case_number=1)
        judgment = _make_judgment(n_refs=2, n_states=2, complete=True)

        expected = _build_expected_from_judgment(judgment)
        golden = {**case, "expected": {"elements": expected}}

        # Original case data should be preserved
        assert golden["case_id"] == case["case_id"]
        assert golden["claim"] == case["claim"]
        assert golden["evidence"] == case["evidence"]
        assert golden["mapper_output"] == case["mapper_output"]
        # Expected should be present
        assert "expected" in golden
        assert "elements" in golden["expected"]


# ---------------------------------------------------------------------------
# Regression comparison tests
# ---------------------------------------------------------------------------


class TestRegressionComparison:
    """Tests for regression result comparison logic."""

    def _make_golden(
        self,
        expected_states: Dict[str, str],
        expected_refs: Dict[str, List[Dict[str, str]]],
    ) -> Dict[str, Any]:
        elements = []
        for eid, state in expected_states.items():
            elem = {
                "element_id": eid,
                "expected_state": state,
                "expected_refs": expected_refs.get(eid, []),
            }
            elements.append(elem)
        return {"expected": {"elements": elements}}

    def test_regression_detects_state_match(self):
        golden = self._make_golden(
            expected_states={"e1": "supported", "e2": "disputed"},
            expected_refs={},
        )
        actual = [
            {"element_id": "e1", "state": "supported", "evidence_refs": []},
            {"element_id": "e2", "state": "disputed", "evidence_refs": []},
        ]
        results = compare_states(golden, actual)
        assert all(r["match"] for r in results)

    def test_regression_detects_state_mismatch(self):
        golden = self._make_golden(
            expected_states={"e1": "supported", "e2": "disputed"},
            expected_refs={},
        )
        actual = [
            {"element_id": "e1", "state": "supported", "evidence_refs": []},
            {"element_id": "e2", "state": "supported", "evidence_refs": []},
        ]
        results = compare_states(golden, actual)
        assert results[0]["match"] is True
        assert results[1]["match"] is False

    def test_regression_detects_ref_match(self):
        golden = self._make_golden(
            expected_states={"e1": "supported"},
            expected_refs={
                "e1": [{"evidence_id": "ev-001", "expected_relationship": "supports"}],
            },
        )
        actual = [
            {
                "element_id": "e1",
                "state": "supported",
                "evidence_refs": [
                    {"evidence_id": "ev-001", "relationship": "supports"},
                ],
            },
        ]
        results = compare_refs(golden, actual)
        assert len(results) == 1
        assert results[0]["match"] is True

    def test_regression_detects_ref_mismatch(self):
        golden = self._make_golden(
            expected_states={"e1": "disputed"},
            expected_refs={
                "e1": [
                    {"evidence_id": "ev-001", "expected_relationship": "challenges"}
                ],
            },
        )
        actual = [
            {
                "element_id": "e1",
                "state": "disputed",
                "evidence_refs": [
                    {"evidence_id": "ev-001", "relationship": "supports"},
                ],
            },
        ]
        results = compare_refs(golden, actual)
        assert len(results) == 1
        assert results[0]["match"] is False
        assert results[0]["expected_rel"] == "challenges"
        assert results[0]["actual_rel"] == "supports"

    def test_regression_summary_accuracy(self):
        case_results = [
            {
                "case_id": "case-001",
                "state_results": [
                    {
                        "element_id": "e1",
                        "expected": "supported",
                        "actual": "supported",
                        "match": True,
                    },
                    {
                        "element_id": "e2",
                        "expected": "disputed",
                        "actual": "supported",
                        "match": False,
                    },
                ],
                "ref_results": [
                    {
                        "element_id": "e1",
                        "evidence_id": "ev-001",
                        "expected_rel": "supports",
                        "actual_rel": "supports",
                        "match": True,
                    },
                    {
                        "element_id": "e1",
                        "evidence_id": "ev-002",
                        "expected_rel": "challenges",
                        "actual_rel": "context",
                        "match": False,
                    },
                    {
                        "element_id": "e2",
                        "evidence_id": "ev-001",
                        "expected_rel": "supports",
                        "actual_rel": "supports",
                        "match": True,
                    },
                ],
                "regressions": ["e2: state mismatch"],
            },
        ]
        summary = compute_regression_summary(case_results)
        assert summary["cases_tested"] == 1
        assert summary["state_accuracy"] == 0.5  # 1/2
        assert summary["ref_accuracy"] == 0.67  # 2/3 rounded
        assert summary["regressions"] == 1
