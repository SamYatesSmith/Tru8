"""Tests for _compute_recovery_timeout (Bug B — V1 quality plan 2026-05-06).

Recovery timeout scales with the number of qualifying claims, floored at
RECOVERY_TIMEOUT_SECONDS so low-candidate cases get a workable budget.

2026-07-22: floor raised 20s → 35s. The §4d starvation trigger routes
intact single-claim checks into recovery, where retrieve (≈13s incl.
enrichment) + classify + score + map overran the legacy 20s floor and the
in-flight mapping call was cancelled with its inputs fully paid for
(E323-8862: killed 5.4s into mapping, 0 elements recovered). Same bug
class Bug B fixed for 4+ claims, recurring at n=1.
"""

from unittest.mock import patch

from app.pipeline.runner import _compute_recovery_timeout


class TestRecoveryTimeoutScaling:
    def test_six_candidates_scales_above_floor(self):
        # 6 × 7 = 42, exceeds floor 35 → returns 42 (Bug B's actual fix)
        assert _compute_recovery_timeout(6) == 42

    def test_one_candidate_floors_at_full_chain_budget(self):
        # 1 × 7 = 7, below floor 35 → returns 35 (2026-07-22 floor:
        # E323-8862's chain needed ~26s; 20s discarded completed work)
        assert _compute_recovery_timeout(1) == 35

    def test_two_candidates_floors_at_full_chain_budget(self):
        # 2 × 7 = 14, below floor 35 → returns 35
        assert _compute_recovery_timeout(2) == 35

    def test_zero_candidates_returns_floor(self):
        # Defensive: caller should not invoke with 0, but if it does,
        # floor protects against returning a 0-second timeout.
        assert _compute_recovery_timeout(0) == 35

    def test_responds_to_per_claim_env_override(self):
        # If RECOVERY_TIMEOUT_SECONDS_PER_CLAIM is bumped (e.g. to 10),
        # the scaling kicks in. Patch the settings object the helper reads.
        with patch("app.pipeline.runner.settings") as mock_settings:
            mock_settings.RECOVERY_TIMEOUT_SECONDS = 35
            mock_settings.RECOVERY_TIMEOUT_SECONDS_PER_CLAIM = 10
            assert _compute_recovery_timeout(4) == 40  # 4 × 10 above floor
            assert _compute_recovery_timeout(1) == 35  # below floor

    def test_responds_to_floor_env_override(self):
        # If RECOVERY_TIMEOUT_SECONDS floor is reduced (rollback lever),
        # scaling can win at smaller candidate counts.
        with patch("app.pipeline.runner.settings") as mock_settings:
            mock_settings.RECOVERY_TIMEOUT_SECONDS = 5
            mock_settings.RECOVERY_TIMEOUT_SECONDS_PER_CLAIM = 7
            assert _compute_recovery_timeout(1) == 7  # 1 × 7 above new floor 5
            assert _compute_recovery_timeout(2) == 14
