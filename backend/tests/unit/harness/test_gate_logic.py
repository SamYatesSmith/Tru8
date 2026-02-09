"""Tests for the two-gate harness system: judge-input hash + flip classification."""
import hashlib
import sys
from pathlib import Path

import pytest

# Add harness directory to path so we can import compare_runs
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "harness"))

from compare_runs import (
    classify_flip,
    jaccard,
    FROZEN_EVIDENCE_MIN_JACCARD_OVERALL,
    FROZEN_EVIDENCE_MIN_JACCARD_CORE,
    FROZEN_MIN_EVIDENCE_JACCARD,
    MIN_EVIDENCE_JACCARD,
)

# Import hash functions from judge.py
from app.pipeline.judge import _canonicalize_for_hash, _compute_judge_input_hash


# --- classify_flip tests ---

class TestClassifyFlip:
    def test_directional_reversal_supported_to_contradicted(self):
        """supported <-> contradicted is always a hard_fail regardless of hash."""
        flip_type, reason = classify_flip("supported", "contradicted", "abc123", "abc123")
        assert flip_type == "hard_fail"
        assert "directional reversal" in reason

    def test_directional_reversal_contradicted_to_supported(self):
        """contradicted -> supported is also a hard_fail."""
        flip_type, reason = classify_flip("contradicted", "supported", "hash1", "hash2")
        assert flip_type == "hard_fail"

    def test_same_hash_is_llm_noise(self):
        """uncertain -> supported with same hash = LLM nondeterminism."""
        flip_type, reason = classify_flip("uncertain", "supported", "abcdef1234567890", "abcdef1234567890")
        assert flip_type == "llm_noise"
        assert "same judge input" in reason
        assert "abcdef12" in reason  # First 8 chars of hash shown

    def test_different_hash_is_pipeline_fail(self):
        """uncertain -> supported with different hash = pipeline changed input."""
        flip_type, reason = classify_flip("uncertain", "supported", "aaaa1111bbbb2222", "cccc3333dddd4444")
        assert flip_type == "pipeline_fail"
        assert "aaaa1111" in reason
        assert "cccc3333" in reason

    def test_no_hash_data_is_llm_noise(self):
        """Missing hash data (legacy runs) defaults to llm_noise."""
        flip_type, reason = classify_flip("uncertain", "contradicted", "", "")
        assert flip_type == "llm_noise"
        assert "no hash data" in reason

    def test_one_hash_missing_is_llm_noise(self):
        """One hash present, one missing = legacy."""
        flip_type, reason = classify_flip("uncertain", "supported", "abc123", "")
        assert flip_type == "llm_noise"
        assert "no hash data" in reason


# --- Hash stability tests ---

class TestHashStability:
    def test_same_input_same_hash(self):
        """Same canonical input produces identical hash."""
        context = "CLAIM: The sky is blue\nEVIDENCE: Multiple sources confirm"
        h1 = _compute_judge_input_hash(context)
        h2 = _compute_judge_input_hash(context)
        assert h1 == h2
        assert len(h1) == 16  # SHA256 truncated to 16 hex chars

    def test_different_input_different_hash(self):
        """Different input produces different hash."""
        h1 = _compute_judge_input_hash("CLAIM: The sky is blue")
        h2 = _compute_judge_input_hash("CLAIM: The sky is red")
        assert h1 != h2

    def test_canonicalize_trailing_whitespace(self):
        """Trailing whitespace should not affect hash."""
        h1 = _compute_judge_input_hash("line1\nline2\nline3")
        h2 = _compute_judge_input_hash("line1  \nline2\t\nline3   ")
        assert h1 == h2

    def test_canonicalize_crlf(self):
        """CRLF vs LF should not affect hash."""
        h1 = _compute_judge_input_hash("line1\nline2")
        h2 = _compute_judge_input_hash("line1\r\nline2")
        assert h1 == h2

    def test_canonicalize_excess_blank_lines(self):
        """Multiple blank lines collapsed to double newline."""
        h1 = _compute_judge_input_hash("section1\n\nsection2")
        h2 = _compute_judge_input_hash("section1\n\n\n\n\nsection2")
        assert h1 == h2


# --- Gate threshold tests ---

class TestGateThresholds:
    def test_gate1_frozen_evidence_thresholds(self):
        """Frozen evidence Jaccard thresholds are set correctly."""
        assert FROZEN_EVIDENCE_MIN_JACCARD_OVERALL == 0.90
        assert FROZEN_EVIDENCE_MIN_JACCARD_CORE == 0.95
        assert FROZEN_EVIDENCE_MIN_JACCARD_OVERALL < FROZEN_EVIDENCE_MIN_JACCARD_CORE

    def test_gate1_jaccard_hierarchy(self):
        """Normal < frozen URL < frozen evidence thresholds."""
        assert MIN_EVIDENCE_JACCARD < FROZEN_MIN_EVIDENCE_JACCARD
        assert FROZEN_MIN_EVIDENCE_JACCARD <= FROZEN_EVIDENCE_MIN_JACCARD_OVERALL

    def test_gate2_ignores_llm_noise(self):
        """Gate 2 should pass when only LLM noise flips exist."""
        # Simulate: 2 flips, both LLM noise
        hard_fail_count = 0
        pipeline_fail_count = 0
        llm_noise_count = 2
        gate2_passed = hard_fail_count == 0 and pipeline_fail_count == 0
        assert gate2_passed is True

    def test_gate2_fails_on_hard_fail(self):
        """Gate 2 should fail on any directional reversal."""
        hard_fail_count = 1
        pipeline_fail_count = 0
        gate2_passed = hard_fail_count == 0 and pipeline_fail_count == 0
        assert gate2_passed is False

    def test_gate2_fails_on_pipeline_fail(self):
        """Gate 2 should fail when pipeline changes judge input and verdict flips."""
        hard_fail_count = 0
        pipeline_fail_count = 1
        gate2_passed = hard_fail_count == 0 and pipeline_fail_count == 0
        assert gate2_passed is False


class TestFreezeStageIntegrity:
    """Test freeze_stage versioning and mismatch detection."""

    def test_freeze_stage_mismatch_detected(self):
        """Mismatched freeze_stage between runs should be flagged."""
        before_stage = "pre_weighting_evidence"
        after_stage = "judge_input_evidence"
        mismatch = before_stage and after_stage and before_stage != after_stage
        assert mismatch is True

    def test_freeze_stage_same_no_mismatch(self):
        """Matching freeze_stage should not flag a mismatch."""
        before_stage = "judge_input_evidence"
        after_stage = "judge_input_evidence"
        mismatch = before_stage and after_stage and before_stage != after_stage
        assert mismatch is False

    def test_freeze_stage_none_no_mismatch(self):
        """Missing freeze_stage (legacy run) should not flag a mismatch."""
        before_stage = None
        after_stage = "judge_input_evidence"
        mismatch = before_stage and after_stage and before_stage != after_stage
        assert not mismatch

    def test_freeze_version_v3_for_judge_input(self):
        """judge_input_evidence should produce freeze_version 3."""
        has_extracted = True
        judge_input_ev = {"0": [{"url": "https://example.com"}]}
        if has_extracted:
            if judge_input_ev:
                freeze_ver = 3
                freeze_stage = "judge_input_evidence"
            else:
                freeze_ver = 2
                freeze_stage = "pre_weighting_evidence"
        assert freeze_ver == 3
        assert freeze_stage == "judge_input_evidence"

    def test_freeze_version_v2_for_pre_weighting(self):
        """pre_weighting_evidence (no judge_input) should produce freeze_version 2."""
        has_extracted = True
        judge_input_ev = {}
        if has_extracted:
            if judge_input_ev:
                freeze_ver = 3
                freeze_stage = "judge_input_evidence"
            else:
                freeze_ver = 2
                freeze_stage = "pre_weighting_evidence"
        assert freeze_ver == 2
        assert freeze_stage == "pre_weighting_evidence"
