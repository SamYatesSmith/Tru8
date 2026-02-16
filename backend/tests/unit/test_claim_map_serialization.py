"""
Regression tests for ClaimMap serialization contract.

Verifies that the API response shape matches frontend TypeScript expectations.
These tests prevent the snake_case/camelCase mismatch that caused the UI
to fail rendering ClaimMap data (element.evidenceRefs was undefined).

Root cause: backend TypedDict uses snake_case, frontend expects camelCase.
Fix: _claim_map_to_camel_case() converter in checks.py.
"""

import pytest
from app.api.v1.checks import _claim_map_to_camel_case


class TestClaimMapCamelCaseConversion:
    """Verify the ClaimMap is correctly converted to camelCase for the API."""

    @pytest.fixture
    def sample_claim_map(self):
        """A representative ClaimMap as stored in JSONB (snake_case)."""
        return {
            "claim_id": "test-claim-001",
            "normalised_claim": "The UK inflation rate is 3.2% as of December 2025.",
            "claim_type": "empirical",
            "elements": [
                {
                    "element_id": "e1",
                    "description": "The UK inflation rate is 3.2%.",
                    "evidence_refs": [
                        {"evidence_id": "ev-001", "relationship": "supports"},
                        {"evidence_id": "ev-002", "relationship": "challenges"},
                    ],
                    "state": "supported",
                    "uncertainty": None,
                },
                {
                    "element_id": "e2",
                    "description": "The figure is from December 2025.",
                    "evidence_refs": [
                        {"evidence_id": "ev-003", "relationship": "context"},
                    ],
                    "state": "unresolved",
                    "uncertainty": "Date not confirmed in evidence.",
                },
            ],
            "orientation": "The single required element is evidentially supported.",
            "metadata": {
                "decomposition_model": "gemini-2.5-flash-lite",
                "mapping_model": "gemini-2.5-flash-lite",
                "element_count": 2,
                "completed_at": "2026-02-15T12:00:00Z",
            },
        }

    def test_top_level_keys_are_camel_case(self, sample_claim_map):
        """Top-level ClaimMap keys must be camelCase."""
        result = _claim_map_to_camel_case(sample_claim_map)

        # These are the exact keys the frontend destructures in ClaimMapView
        assert "claimId" in result
        assert "normalisedClaim" in result
        assert "claimType" in result
        assert "elements" in result
        assert "orientation" in result
        assert "metadata" in result

        # Snake_case keys must NOT be present
        assert "claim_id" not in result
        assert "normalised_claim" not in result
        assert "claim_type" not in result

    def test_element_keys_are_camel_case(self, sample_claim_map):
        """Element keys must be camelCase (prevents the TypeError crash)."""
        result = _claim_map_to_camel_case(sample_claim_map)
        element = result["elements"][0]

        # These are the exact keys used in ElementList component
        assert "elementId" in element
        assert "description" in element
        assert "evidenceRefs" in element
        assert "state" in element
        assert "uncertainty" in element

        # Snake_case keys must NOT be present
        assert "element_id" not in element
        assert "evidence_refs" not in element

    def test_evidence_ref_keys_are_camel_case(self, sample_claim_map):
        """Evidence ref keys must be camelCase."""
        result = _claim_map_to_camel_case(sample_claim_map)
        ref = result["elements"][0]["evidenceRefs"][0]

        assert "evidenceId" in ref
        assert "relationship" in ref
        assert "evidence_id" not in ref

    def test_metadata_keys_are_camel_case(self, sample_claim_map):
        """Metadata keys must be camelCase."""
        result = _claim_map_to_camel_case(sample_claim_map)
        metadata = result["metadata"]

        assert "decompositionModel" in metadata
        assert "mappingModel" in metadata
        assert "elementCount" in metadata
        assert "completedAt" in metadata

        assert "decomposition_model" not in metadata
        assert "mapping_model" not in metadata

    def test_values_are_preserved(self, sample_claim_map):
        """Values must not change during key conversion."""
        result = _claim_map_to_camel_case(sample_claim_map)

        assert result["claimId"] == "test-claim-001"
        assert result["claimType"] == "empirical"
        assert result["elements"][0]["state"] == "supported"
        assert result["elements"][0]["evidenceRefs"][0]["relationship"] == "supports"
        assert result["elements"][1]["uncertainty"] == "Date not confirmed in evidence."
        assert result["metadata"]["elementCount"] == 2

    def test_null_claim_map_returns_null(self):
        """Null/None input should return None."""
        assert _claim_map_to_camel_case(None) is None

    def test_empty_claim_map_returns_empty(self):
        """Empty dict should return empty dict."""
        assert _claim_map_to_camel_case({}) == {}

    def test_empty_elements_preserved(self):
        """ClaimMap with empty elements array should work."""
        result = _claim_map_to_camel_case(
            {
                "claim_id": "test",
                "elements": [],
                "metadata": {},
            }
        )
        assert result["elements"] == []

    def test_empty_evidence_refs_preserved(self):
        """Element with no evidence refs should work."""
        result = _claim_map_to_camel_case(
            {
                "claim_id": "test",
                "elements": [
                    {
                        "element_id": "e1",
                        "description": "Test",
                        "evidence_refs": [],
                        "state": "unresolved",
                        "uncertainty": None,
                    }
                ],
                "metadata": {},
            }
        )
        assert result["elements"][0]["evidenceRefs"] == []


class TestStageProgressionContract:
    """Verify pipeline stages are monotonically increasing."""

    def test_stage_progress_is_monotonic(self):
        """All stages must have strictly increasing progress values."""
        from app.pipeline.progress import ProgressReporter

        stages = list(ProgressReporter.STAGE_PROGRESS.items())

        for i in range(1, len(stages)):
            prev_stage, prev_value = stages[i - 1]
            curr_stage, curr_value = stages[i]
            assert curr_value > prev_value, (
                f"Stage '{curr_stage}' ({curr_value}) must have higher progress "
                f"than '{prev_stage}' ({prev_value})"
            )

    def test_complete_stage_is_100(self):
        """The 'complete' stage must be at 100%."""
        from app.pipeline.progress import ProgressReporter

        assert ProgressReporter.STAGE_PROGRESS["complete"] == 100

    def test_starting_stage_is_0(self):
        """The 'starting' stage must be at 0%."""
        from app.pipeline.progress import ProgressReporter

        assert ProgressReporter.STAGE_PROGRESS["starting"] == 0
