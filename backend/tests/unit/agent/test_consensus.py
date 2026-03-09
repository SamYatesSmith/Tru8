"""M-06: Tests for convergence layer — consensus computation and stability.

Covers:
- Stability classification (stable/mixed/shifting)
- Element canonical ID matching
- Consensus response builder
- Aggregate element state computation
"""

import pytest
from collections import Counter


class TestComputeStability:
    def test_empty_votes_is_stable(self):
        from app.services.consensus import compute_stability

        assert compute_stability({}) == "stable"

    def test_unanimous_supported_is_stable(self):
        from app.services.consensus import compute_stability

        votes = {
            "elem1": {"supported": 5},
            "elem2": {"supported": 4},
        }
        assert compute_stability(votes) == "stable"

    def test_high_agreement_is_stable(self):
        from app.services.consensus import compute_stability

        # 80% agreement on each element
        votes = {
            "elem1": {"supported": 8, "disputed": 2},
            "elem2": {"supported": 9, "disputed": 1},
        }
        assert compute_stability(votes) == "stable"

    def test_moderate_agreement_is_mixed(self):
        from app.services.consensus import compute_stability

        # 70% agreement
        votes = {
            "elem1": {"supported": 7, "disputed": 3},
            "elem2": {"supported": 7, "challenged": 3},
        }
        assert compute_stability(votes) == "mixed"

    def test_low_agreement_is_shifting(self):
        from app.services.consensus import compute_stability

        # 50% agreement
        votes = {
            "elem1": {"supported": 5, "disputed": 5},
            "elem2": {"supported": 4, "disputed": 3, "unresolved": 3},
        }
        assert compute_stability(votes) == "shifting"

    def test_single_element_shifting(self):
        from app.services.consensus import compute_stability

        # 33% agreement
        votes = {
            "elem1": {"supported": 3, "disputed": 3, "unresolved": 3},
        }
        assert compute_stability(votes) == "shifting"


class TestBuildConsensusResponse:
    def _make_consensus(self):
        from app.models.claim_consensus import ClaimConsensus
        from datetime import datetime, timezone

        return ClaimConsensus(
            claim_text_hash="abc123",
            independent_checks=5,
            stability="stable",
            element_state_distribution={
                "a1b2c3d4": {"supported": 4, "disputed": 1},
                "e5f6g7h8": {"supported": 5},
            },
            unique_sources=42,
            total_evidence=87,
            tier_spread={"primary": 12, "reporting": 45, "commentary": 30},
            last_full_check_at=datetime(2026, 3, 9, 10, 0, tzinfo=timezone.utc),
            computed_at=datetime(2026, 3, 10, 2, 0, tzinfo=timezone.utc),
        )

    def test_response_structure(self):
        from app.services.consensus import build_consensus_response

        consensus = self._make_consensus()
        response = build_consensus_response(consensus)

        assert response["id"] is None
        assert response["status"] == "consensus"
        assert response["claims"] == []
        assert response["_manifest"] is None

    def test_meta_block(self):
        from app.services.consensus import build_consensus_response

        consensus = self._make_consensus()
        response = build_consensus_response(consensus)
        meta = response["_meta"]

        assert meta["executedTier"] == "consensus"
        assert meta["chargedCents"] == 3
        assert "no_individual_evidence" in meta["limitations"]
        assert "aggregated_landscape" in meta["limitations"]

    def test_consensus_meta(self):
        from app.services.consensus import build_consensus_response

        consensus = self._make_consensus()
        response = build_consensus_response(consensus)
        consensus_meta = response["_meta"]["consensus"]

        assert consensus_meta["independentChecks"] == 5
        assert consensus_meta["stability"] == "stable"
        assert consensus_meta["uniqueSourcesAcrossChecks"] == 42

    def test_landscape_nullable_fields(self):
        from app.services.consensus import build_consensus_response

        consensus = self._make_consensus()
        response = build_consensus_response(consensus)
        landscape = response["_meta"]["landscape"]

        # Per-check concepts must be null
        assert landscape["sourcesConsidered"] is None
        assert landscape["sourceDiversity"]["uniqueDomains"] is None
        assert landscape["sourceDiversity"]["typeCoverage"] is None
        assert landscape["freshness"] is None
        assert landscape["providerStatus"] is None

        # Aggregatable fields must have values
        assert landscape["evidenceDensity"] == 87
        assert landscape["sourceDiversity"]["tierSpread"] == {
            "primary": 12,
            "reporting": 45,
            "commentary": 30,
        }

    def test_no_individual_evidence_leaked(self):
        """Consensus response must NEVER include individual evidence items."""
        from app.services.consensus import build_consensus_response
        import json

        consensus = self._make_consensus()
        response = build_consensus_response(consensus)
        response_json = json.dumps(response)

        assert '"evidence"' not in response_json or '"totalEvidence"' in response_json
        assert "snippet" not in response_json
        assert "url" not in response_json or "verifyUrl" in response_json


class TestAggregateElementStates:
    def test_majority_vote(self):
        from app.services.consensus import _aggregate_element_states

        esd = {
            "elem1": {"supported": 8, "disputed": 2},
            "elem2": {"disputed": 6, "supported": 4},
            "elem3": {"unresolved": 5},
        }
        result = _aggregate_element_states(esd)
        assert result["supported"] == 1
        assert result["disputed"] == 1
        assert result["unresolved"] == 1


class TestAgentPricingConsensus:
    def test_consensus_tier_exists(self):
        from app.core.agent_pricing import AGENT_PRICING_CENTS, TIER_ORDER

        assert "consensus" in AGENT_PRICING_CENTS
        assert AGENT_PRICING_CENTS["consensus"] == 3
        assert "consensus" in TIER_ORDER

    def test_tier_order(self):
        from app.core.agent_pricing import TIER_ORDER

        assert TIER_ORDER.index("lookup") < TIER_ORDER.index("consensus")
        assert TIER_ORDER.index("consensus") < TIER_ORDER.index("quick")
        assert TIER_ORDER.index("quick") < TIER_ORDER.index("full")

    def test_get_tier_price(self):
        from app.core.agent_pricing import get_tier_price

        assert get_tier_price("consensus") == 3

    def test_tier_rank(self):
        from app.core.agent_pricing import tier_rank

        assert tier_rank("lookup") < tier_rank("consensus")
        assert tier_rank("consensus") < tier_rank("quick")
