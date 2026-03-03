"""Tests for compact mode in agent responses (L-03).

When ?compact=true, agent responses strip evidence[] arrays from each
claim but preserve claimMap + _meta block.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.api.v1.response_builder import build_agent_response, _compute_landscape


class TestComputeLandscape:
    """_compute_landscape derives metrics from claims data."""

    def test_empty_claims(self):
        landscape = _compute_landscape([])
        assert landscape["elementCount"] == 0
        assert landscape["evidenceDensity"] == 0
        assert landscape["sourcesConsidered"] == 0

    def test_counts_elements(self):
        claims_data = [
            {
                "claimMap": {
                    "elements": [
                        {"state": "supported"},
                        {"state": "disputed"},
                    ]
                },
                "evidence": [],
            }
        ]
        landscape = _compute_landscape(claims_data)
        assert landscape["elementCount"] == 2
        assert landscape["elementStates"] == {"supported": 1, "disputed": 1}

    def test_counts_evidence(self):
        claims_data = [
            {
                "claimMap": {"elements": []},
                "evidence": [
                    {"tier": "primary"},
                    {"tier": "reporting"},
                    {"tier": "primary"},
                ],
            }
        ]
        landscape = _compute_landscape(claims_data)
        assert landscape["evidenceDensity"] == 3
        assert landscape["sourcesConsidered"] == 3
        assert landscape["sourceDiversity"]["tierSpread"] == {
            "primary": 2,
            "reporting": 1,
        }

    def test_handles_missing_claim_map(self):
        claims_data = [
            {"claimMap": None, "evidence": []},
        ]
        landscape = _compute_landscape(claims_data)
        assert landscape["elementCount"] == 0

    def test_handles_missing_tier(self):
        claims_data = [
            {"claimMap": {"elements": []}, "evidence": [{"tier": None}]},
        ]
        landscape = _compute_landscape(claims_data)
        assert landscape["sourceDiversity"]["tierSpread"] == {}
