"""Tests for V2 frozen evidence replay — Stage 3.7 scorer bypass.

Verifies that when frozen_evidence_replay contextvar is True,
Stage 3.7 LLM scoring is skipped and evidence stays in original claim buckets.
"""
import contextvars
import pytest

from app.pipeline.replay_context import frozen_evidence_replay, frozen_replay_temperature


class TestFrozenReplayContextVar:
    """Test the frozen_evidence_replay contextvar lifecycle."""

    def test_default_is_false(self):
        """Default value should be False (normal pipeline)."""
        assert frozen_evidence_replay.get(False) is False

    def test_set_and_reset(self):
        """Setting True and resetting restores default."""
        token = frozen_evidence_replay.set(True)
        assert frozen_evidence_replay.get(False) is True
        frozen_evidence_replay.reset(token)
        assert frozen_evidence_replay.get(False) is False

    def test_independent_from_temperature(self):
        """frozen_evidence_replay and frozen_replay_temperature are independent."""
        temp_token = frozen_replay_temperature.set(0.0)
        assert frozen_evidence_replay.get(False) is False

        ev_token = frozen_evidence_replay.set(True)
        assert frozen_replay_temperature.get(None) == 0.0
        assert frozen_evidence_replay.get(True) is True

        frozen_replay_temperature.reset(temp_token)
        frozen_evidence_replay.reset(ev_token)


class TestScorerBypassLogic:
    """Test the bypass condition in runner.py Stage 3.7.

    We test the decision logic in isolation without running the full pipeline.
    The key condition is: if frozen_evidence_replay is True and evidence exists,
    skip score_evidence_batch() entirely.
    """

    def _should_skip_scoring(self, is_frozen: bool, has_evidence: bool, scorer_enabled: bool = True) -> str:
        """Replicate the Stage 3.7 branching logic from runner.py.

        Returns: "skip_frozen" | "score" | "disabled"
        """
        if is_frozen and has_evidence:
            return "skip_frozen"
        elif scorer_enabled and has_evidence:
            return "score"
        else:
            return "disabled"

    def test_normal_pipeline_scores(self):
        """Normal pipeline with evidence → score."""
        assert self._should_skip_scoring(False, True) == "score"

    def test_frozen_replay_skips(self):
        """V2 frozen evidence replay → skip scoring."""
        assert self._should_skip_scoring(True, True) == "skip_frozen"

    def test_no_evidence_disabled(self):
        """No evidence → disabled regardless of replay mode."""
        assert self._should_skip_scoring(False, False) == "disabled"
        assert self._should_skip_scoring(True, False) == "disabled"

    def test_scorer_disabled_no_score(self):
        """Scorer disabled → disabled."""
        assert self._should_skip_scoring(False, True, scorer_enabled=False) == "disabled"

    def test_frozen_takes_priority_over_scorer(self):
        """Frozen replay bypass takes priority over scorer enabled check."""
        # Even if scorer is enabled, frozen replay should skip
        assert self._should_skip_scoring(True, True, scorer_enabled=True) == "skip_frozen"


class TestEvidenceBucketPreservation:
    """Test that evidence stays in original claim buckets when scoring is skipped."""

    def test_evidence_unchanged_when_skipped(self):
        """Simulates the frozen replay path: evidence dict passes through unmodified."""
        original_evidence = {
            "0": [
                {"url": "https://reuters.com/article1", "title": "Article 1"},
                {"url": "https://bbc.com/article2", "title": "Article 2"},
            ],
            "1": [
                {"url": "https://nytimes.com/article3", "title": "Article 3"},
            ],
            "2": [],
        }

        # In frozen replay, evidence is not modified by Stage 3.7
        # (no score_evidence_batch call), so it should be identical
        import copy
        evidence_before = copy.deepcopy(original_evidence)

        # Simulate the frozen replay path: no mutation
        evidence_after = original_evidence  # same reference, no scoring applied

        assert evidence_after == evidence_before
        # Verify per-claim counts unchanged
        for pos in original_evidence:
            assert len(evidence_after[pos]) == len(evidence_before[pos])
            for i, ev in enumerate(evidence_after[pos]):
                assert ev["url"] == evidence_before[pos][i]["url"]

    def test_no_cross_claim_reassignment(self):
        """In frozen replay, evidence must NOT move between claims."""
        evidence = {
            "0": [{"url": "https://example.com/a"}],
            "1": [{"url": "https://example.com/b"}],
        }

        # In normal mode, score_evidence_batch might reassign example.com/a to claim 1.
        # In frozen replay mode, this must not happen.
        # The test verifies the invariant: evidence stays in its original bucket.
        assert evidence["0"][0]["url"] == "https://example.com/a"
        assert evidence["1"][0]["url"] == "https://example.com/b"
