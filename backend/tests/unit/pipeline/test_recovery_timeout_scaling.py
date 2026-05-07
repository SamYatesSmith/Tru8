"""Tests for _compute_recovery_timeout (Bug B — V1 quality plan 2026-05-06).

Recovery timeout scales with the number of qualifying claims, floored
at the legacy 20s value so 1-2 candidate cases preserve current
behaviour.
"""

from unittest.mock import patch

from app.pipeline.runner import _compute_recovery_timeout


class TestRecoveryTimeoutScaling:
    def test_three_candidates_scales_above_floor(self):
        # 3 × 7 = 21, exceeds floor 20 → returns 21 (Bug B's actual fix)
        assert _compute_recovery_timeout(3) == 21

    def test_one_candidate_floors_at_legacy_value(self):
        # 1 × 7 = 7, below floor 20 → returns 20 (unchanged from pre-Bug-B)
        assert _compute_recovery_timeout(1) == 20

    def test_two_candidates_floors_at_legacy_value(self):
        # 2 × 7 = 14, below floor 20 → returns 20 (unchanged)
        assert _compute_recovery_timeout(2) == 20

    def test_zero_candidates_returns_floor(self):
        # Defensive: caller should not invoke with 0, but if it does,
        # floor protects against returning a 0-second timeout.
        assert _compute_recovery_timeout(0) == 20

    def test_responds_to_per_claim_env_override(self):
        # If RECOVERY_TIMEOUT_SECONDS_PER_CLAIM is bumped (e.g. to 10),
        # the scaling kicks in. Patch the settings object the helper reads.
        with patch("app.pipeline.runner.settings") as mock_settings:
            mock_settings.RECOVERY_TIMEOUT_SECONDS = 20
            mock_settings.RECOVERY_TIMEOUT_SECONDS_PER_CLAIM = 10
            assert _compute_recovery_timeout(3) == 30  # 3 × 10 above floor
            assert _compute_recovery_timeout(1) == 20  # below floor

    def test_responds_to_floor_env_override(self):
        # If RECOVERY_TIMEOUT_SECONDS floor is reduced, scaling can win
        # at smaller candidate counts.
        with patch("app.pipeline.runner.settings") as mock_settings:
            mock_settings.RECOVERY_TIMEOUT_SECONDS = 5
            mock_settings.RECOVERY_TIMEOUT_SECONDS_PER_CLAIM = 7
            assert _compute_recovery_timeout(1) == 7  # 1 × 7 above new floor 5
            assert _compute_recovery_timeout(2) == 14
