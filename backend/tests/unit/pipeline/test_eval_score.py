"""Tests for the MAP-stage evaluation harness (eval_score.py).

Covers:
- Golden check loading and validation
- ClaimMap construction from golden checks
- Scoring logic (correct/incorrect/mixed states)
- Experiment logging format
- Dry-run mode
"""

import json
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

import sys

backend_dir = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(backend_dir))

from scripts.eval_score import (
    load_golden_checks,
    build_claim_map,
    score_claim,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _golden_check(
    claim_id="eval-test",
    claim="Test claim",
    elements=None,
    evidence=None,
    expected_states=None,
):
    """Build a minimal golden check dict."""
    if elements is None:
        elements = [
            {"element_id": "e1", "description": "First element"},
            {"element_id": "e2", "description": "Second element"},
        ]
    if evidence is None:
        evidence = [
            {
                "evidence_id": "ev-001",
                "title": "Test Source",
                "text": "Some evidence text.",
                "snippet": "Some evidence text.",
                "source": "example.com",
                "url": "https://example.com",
                "tier": "primary",
                "evidence_type": "data",
                "content_basis": "full",
            }
        ]
    if expected_states is None:
        expected_states = {"e1": "supported", "e2": "disputed"}
    return {
        "claim_id": claim_id,
        "normalised_claim": claim,
        "elements": elements,
        "evidence": evidence,
        "expected_states": expected_states,
        "rationale": {"e1": "reason 1", "e2": "reason 2"},
    }


# ---------------------------------------------------------------------------
# Golden check loading
# ---------------------------------------------------------------------------


class TestLoadGoldenChecks:
    """Test golden checks file loading and validation."""

    def test_loads_valid_file(self, tmp_path):
        golden = [_golden_check()]
        path = tmp_path / "golden.json"
        path.write_text(json.dumps(golden))

        result = load_golden_checks(path)
        assert len(result) == 1
        assert result[0]["claim_id"] == "eval-test"

    def test_validates_required_fields(self, tmp_path):
        golden = [{"claim_id": "bad"}]  # Missing most fields
        path = tmp_path / "golden.json"
        path.write_text(json.dumps(golden))

        with pytest.raises(AssertionError, match="normalised_claim"):
            load_golden_checks(path)

    def test_validates_expected_states_cover_elements(self, tmp_path):
        golden = [_golden_check(expected_states={"e1": "supported"})]  # Missing e2
        path = tmp_path / "golden.json"
        path.write_text(json.dumps(golden))

        with pytest.raises(AssertionError, match="e2 missing"):
            load_golden_checks(path)

    def test_loads_production_golden_checks(self):
        """Verify the actual golden_checks.json file loads without error."""
        golden_path = backend_dir / "harness" / "golden_checks.json"
        if golden_path.exists():
            checks = load_golden_checks(golden_path)
            assert len(checks) == 20


# ---------------------------------------------------------------------------
# ClaimMap construction
# ---------------------------------------------------------------------------


class TestBuildClaimMap:
    """Test ClaimMap construction from golden check definitions."""

    def test_builds_valid_claim_map(self):
        golden = _golden_check()
        cm = build_claim_map(golden)

        assert cm["claim_id"] == "eval-test"
        assert cm["normalised_claim"] == "Test claim"
        assert len(cm["elements"]) == 2
        assert cm["elements"][0]["element_id"] == "e1"
        assert cm["elements"][0]["evidence_refs"] == []
        assert cm["elements"][0]["state"] is None

    def test_elements_have_empty_refs(self):
        golden = _golden_check()
        cm = build_claim_map(golden)

        for elem in cm["elements"]:
            assert elem["evidence_refs"] == []
            assert elem["state"] is None
            assert elem["uncertainty"] is None

    def test_metadata_is_synthetic(self):
        golden = _golden_check()
        cm = build_claim_map(golden)

        assert cm["metadata"]["decomposition_model"] == "golden-synthetic"
        assert cm["metadata"]["mapping_model"] is None


# ---------------------------------------------------------------------------
# Scoring logic
# ---------------------------------------------------------------------------


class TestScoreClaim:
    """Test the scoring function."""

    def test_perfect_score(self):
        golden = _golden_check(expected_states={"e1": "supported", "e2": "disputed"})
        actual_map = build_claim_map(golden)
        actual_map["elements"][0]["state"] = "supported"
        actual_map["elements"][1]["state"] = "disputed"

        result = score_claim(golden, actual_map)
        assert result["accuracy"] == 1.0
        assert result["correct"] == 2
        assert result["total"] == 2

    def test_zero_score(self):
        golden = _golden_check(expected_states={"e1": "supported", "e2": "disputed"})
        actual_map = build_claim_map(golden)
        actual_map["elements"][0]["state"] = "disputed"  # Wrong
        actual_map["elements"][1]["state"] = "supported"  # Wrong

        result = score_claim(golden, actual_map)
        assert result["accuracy"] == 0.0
        assert result["correct"] == 0

    def test_partial_score(self):
        golden = _golden_check(expected_states={"e1": "supported", "e2": "disputed"})
        actual_map = build_claim_map(golden)
        actual_map["elements"][0]["state"] = "supported"  # Correct
        actual_map["elements"][1]["state"] = "unresolved"  # Wrong

        result = score_claim(golden, actual_map)
        assert result["accuracy"] == 0.5
        assert result["correct"] == 1

    def test_handles_enum_states(self):
        """States from ClaimMapAnalyzer are ElementState enums, not strings."""
        from app.models.claim_map import ElementState

        golden = _golden_check(expected_states={"e1": "supported", "e2": "disputed"})
        actual_map = build_claim_map(golden)
        actual_map["elements"][0]["state"] = ElementState.supported
        actual_map["elements"][1]["state"] = ElementState.disputed

        result = score_claim(golden, actual_map)
        assert result["accuracy"] == 1.0

    def test_element_results_contain_details(self):
        golden = _golden_check(expected_states={"e1": "supported", "e2": "disputed"})
        actual_map = build_claim_map(golden)
        actual_map["elements"][0]["state"] = "supported"
        actual_map["elements"][0]["evidence_refs"] = [
            {"evidence_id": "ev-001", "relationship": "supports", "reasoning": "test"}
        ]
        actual_map["elements"][1]["state"] = "disputed"

        result = score_claim(golden, actual_map)
        assert result["element_results"][0]["evidence_refs_count"] == 1
        assert result["element_results"][0]["correct"] is True
        assert result["element_results"][1]["correct"] is True

    def test_unresolved_state_scoring(self):
        golden = _golden_check(expected_states={"e1": "supported", "e2": "unresolved"})
        actual_map = build_claim_map(golden)
        actual_map["elements"][0]["state"] = "supported"
        actual_map["elements"][1]["state"] = "unresolved"

        result = score_claim(golden, actual_map)
        assert result["accuracy"] == 1.0
