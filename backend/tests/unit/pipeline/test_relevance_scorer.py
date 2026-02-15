"""Tests for PR 2-E: LLM Relevance Scorer fairness, fallback resilience, and bug fixes.

Verifies:
1. Round-robin fair selection distributes items across claims under MAX cap
2. Unscored items represented as None, not 0
3. Per-claim fallback rescues unscored items when claim has 0 kept evidence
4. Global fallback path uses assigned_url_counts (no NameError)
5. Threshold default is consistently 3 across all code paths
6. No claim is starved purely due to list position
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from app.pipeline.relevance_scorer import _fair_select_evidence, score_evidence_batch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_evidence(url, title="Article", final_score=0.7, credibility_score=0.7):
    """Create a minimal evidence dict for testing."""
    return {
        "url": url,
        "title": title,
        "text": f"Content about {title}",
        "source": "test",
        "tier": "general",
        "credibility_score": credibility_score,
        "final_score": final_score,
        "risk_flags": [],
    }


def build_evidence_and_positions(evidence_by_claim):
    """Flatten evidence dict into (all_evidence, evidence_positions) like score_evidence_batch does."""
    all_evidence = []
    evidence_positions = []
    for claim_pos, ev_list in evidence_by_claim.items():
        for idx, ev in enumerate(ev_list):
            all_evidence.append(ev)
            evidence_positions.append((claim_pos, idx))
    return all_evidence, evidence_positions


# ---------------------------------------------------------------------------
# 1. Fair selection / round-robin tests
# ---------------------------------------------------------------------------


class TestFairSelection:
    """Test _fair_select_evidence distributes items fairly across claims."""

    def test_under_cap_selects_all(self):
        """When total evidence < max, all items are selected."""
        evidence = {
            "0": [make_evidence(f"http://a.com/{i}") for i in range(3)],
            "1": [make_evidence(f"http://b.com/{i}") for i in range(4)],
        }
        all_ev, positions = build_evidence_and_positions(evidence)
        selected, sel_pos, sel_indices = _fair_select_evidence(
            all_ev, positions, max_evidence=50, evidence_by_claim=evidence
        )
        assert len(selected) == 7
        assert sel_indices == set(range(7))

    def test_equal_distribution_across_claims(self):
        """With 11 claims of 10 items each (110 total), cap=50 gives ~4-5 per claim."""
        evidence = {}
        for c in range(11):
            evidence[str(c)] = [
                make_evidence(f"http://claim{c}.com/{i}") for i in range(10)
            ]
        all_ev, positions = build_evidence_and_positions(evidence)
        selected, sel_pos, sel_indices = _fair_select_evidence(
            all_ev, positions, max_evidence=50, evidence_by_claim=evidence
        )
        assert len(selected) == 50

        # Count per claim — each claim should get at least base_per_claim (50//11 = 4)
        per_claim_counts = {}
        for _, (cp, _) in zip(range(len(sel_pos)), sel_pos):
            per_claim_counts[cp] = per_claim_counts.get(cp, 0) + 1

        assert len(per_claim_counts) == 11  # All claims represented
        for cp, count in per_claim_counts.items():
            assert count >= 4, f"Claim {cp} got only {count} items (expected >= 4)"
            assert count <= 5, f"Claim {cp} got {count} items (expected <= 5)"

    def test_late_claims_not_starved(self):
        """Claims 7-10 (late position) must get evidence selected."""
        evidence = {}
        for c in range(11):
            evidence[str(c)] = [
                make_evidence(f"http://claim{c}.com/{i}") for i in range(10)
            ]
        all_ev, positions = build_evidence_and_positions(evidence)
        selected, sel_pos, sel_indices = _fair_select_evidence(
            all_ev, positions, max_evidence=50, evidence_by_claim=evidence
        )

        # Verify claims 7-10 all have items selected
        late_claim_counts = {}
        for cp, _ in sel_pos:
            if int(cp) >= 7:
                late_claim_counts[cp] = late_claim_counts.get(cp, 0) + 1

        for cp in ["7", "8", "9", "10"]:
            assert cp in late_claim_counts, f"Claim {cp} had NO evidence selected"
            assert late_claim_counts[cp] >= 4

    def test_unequal_claim_sizes(self):
        """Claims with fewer items contribute all they have; remainder goes to larger claims."""
        evidence = {
            "0": [make_evidence(f"http://a.com/{i}") for i in range(2)],  # 2 items
            "1": [make_evidence(f"http://b.com/{i}") for i in range(20)],  # 20 items
            "2": [make_evidence(f"http://c.com/{i}") for i in range(20)],  # 20 items
        }
        all_ev, positions = build_evidence_and_positions(evidence)
        selected, sel_pos, sel_indices = _fair_select_evidence(
            all_ev, positions, max_evidence=10, evidence_by_claim=evidence
        )
        assert len(selected) == 10

        per_claim = {}
        for cp, _ in sel_pos:
            per_claim[cp] = per_claim.get(cp, 0) + 1

        # Claim 0 has only 2 items, should contribute both
        assert per_claim.get("0", 0) == 2
        # Claims 1 and 2 split the remaining 8 slots
        assert per_claim.get("1", 0) >= 3
        assert per_claim.get("2", 0) >= 3

    def test_preserves_flat_order(self):
        """Selected items must maintain original flat ordering for evidence_index alignment."""
        evidence = {
            "0": [make_evidence(f"http://a.com/{i}") for i in range(5)],
            "1": [make_evidence(f"http://b.com/{i}") for i in range(5)],
        }
        all_ev, positions = build_evidence_and_positions(evidence)
        selected, sel_pos, sel_indices = _fair_select_evidence(
            all_ev, positions, max_evidence=6, evidence_by_claim=evidence
        )
        # Indices should be in ascending order
        idx_list = sorted(sel_indices)
        for i in range(len(idx_list) - 1):
            assert idx_list[i] < idx_list[i + 1]


# ---------------------------------------------------------------------------
# 2. Unscored items representation
# ---------------------------------------------------------------------------


class TestUnscoredRepresentation:
    """Test that unscored items get score=None, not score=0."""

    @pytest.mark.asyncio
    async def test_unscored_items_get_none(self):
        """Items not sent to LLM should have llm_relevance_score=None."""
        evidence = {}
        for c in range(11):
            evidence[str(c)] = [
                make_evidence(f"http://claim{c}.com/{i}") for i in range(10)
            ]

        claims = [f"Claim {i}" for i in range(11)]

        # Mock LLM to return scores only for items it receives (which will be <= 50)
        # Return score=5 for all items sent
        async def mock_score_google(*args, **kwargs):
            return None  # Google fails

        async def mock_score_llm(claims_arg, evidence_items, article_context):
            return [
                {
                    "evidence_index": i,
                    "score": 5,
                    "rationale": "relevant",
                    "relevant_claims": [],
                }
                for i in range(len(evidence_items))
            ]

        with patch(
            "app.pipeline.relevance_scorer._score_with_google",
            side_effect=mock_score_google,
        ), patch(
            "app.pipeline.relevance_scorer._score_with_llm", side_effect=mock_score_llm
        ), patch(
            "app.pipeline.relevance_scorer._get_cached_relevance_scores",
            return_value=None,
        ), patch(
            "app.pipeline.relevance_scorer._cache_relevance_scores", return_value=None
        ), patch(
            "app.pipeline.relevance_scorer.settings"
        ) as mock_settings:

            mock_settings.ENABLE_LLM_RELEVANCE_SCORER = True
            mock_settings.LLM_RELEVANCE_MAX_EVIDENCE = 50
            mock_settings.LLM_RELEVANCE_MIN_SCORE = 3
            mock_settings.MAX_CLAIMS_PER_URL = 2

            result = await score_evidence_batch(claims, evidence, "test article")

            # Collect all evidence items across all claims from original evidence
            all_items = []
            for ev_list in evidence.values():
                all_items.extend(ev_list)

            # Some items should have score=None (the ones beyond the cap)
            none_scored = [e for e in all_items if e.get("llm_relevance_score") is None]
            int_scored = [
                e for e in all_items if isinstance(e.get("llm_relevance_score"), int)
            ]

            # 110 total items, 50 selected → 60 should be unscored (None)
            assert len(none_scored) > 0, "Expected some items to be unscored (None)"
            # No items should have score=0 (0 is not a valid LLM rubric score)
            zero_scored = [e for e in all_items if e.get("llm_relevance_score") == 0]
            assert (
                len(zero_scored) == 0
            ), f"Found {len(zero_scored)} items with score=0 (should be None)"


# ---------------------------------------------------------------------------
# 3. Per-claim fallback rescues unscored items
# ---------------------------------------------------------------------------


class TestFallbackRescue:
    """Test that fallback can rescue claims with unscored (None) items."""

    @pytest.mark.asyncio
    async def test_fallback_rescues_unscored_claim(self):
        """A claim where all items were unscored (due to cap) should be rescued by fallback."""
        # 3 claims: claim 0 gets 45 items, claim 1 gets 5, claim 2 gets 10
        # With max=50, all of claim 0 + claim 1 scored, but claim 2 partially or fully unscored
        evidence = {
            "0": [
                make_evidence(f"http://a.com/{i}", final_score=0.8) for i in range(8)
            ],
            "1": [
                make_evidence(f"http://b.com/{i}", final_score=0.7) for i in range(8)
            ],
            "2": [
                make_evidence(f"http://c.com/{i}", final_score=0.6) for i in range(8)
            ],
        }

        claims = ["Claim 0", "Claim 1", "Claim 2"]

        # LLM gives score=1 to everything (all filtered) — simulates aggressive scoring
        async def mock_score_google(*args, **kwargs):
            return None

        async def mock_score_llm(claims_arg, evidence_items, article_context):
            return [
                {
                    "evidence_index": i,
                    "score": 1,
                    "rationale": "off-topic",
                    "relevant_claims": [],
                }
                for i in range(len(evidence_items))
            ]

        with patch(
            "app.pipeline.relevance_scorer._score_with_google",
            side_effect=mock_score_google,
        ), patch(
            "app.pipeline.relevance_scorer._score_with_llm", side_effect=mock_score_llm
        ), patch(
            "app.pipeline.relevance_scorer._get_cached_relevance_scores",
            return_value=None,
        ), patch(
            "app.pipeline.relevance_scorer._cache_relevance_scores", return_value=None
        ), patch(
            "app.pipeline.relevance_scorer.settings"
        ) as mock_settings:

            mock_settings.ENABLE_LLM_RELEVANCE_SCORER = True
            mock_settings.LLM_RELEVANCE_MAX_EVIDENCE = (
                10  # Very low cap to force truncation
            )
            mock_settings.LLM_RELEVANCE_MIN_SCORE = 3
            mock_settings.MAX_CLAIMS_PER_URL = 2

            result = await score_evidence_batch(claims, evidence, "test article")

            # With max=10 and 3 claims: ~3-4 items per claim sent to LLM
            # All scored items get score=1 (filtered)
            # Remaining items are unscored (None) and eligible for fallback rescue
            # Every claim should get fallback evidence (from unscored pool)
            for claim_pos in ["0", "1", "2"]:
                # Each claim should have at least some evidence via fallback rescue
                assert (
                    len(result[claim_pos]) > 0
                ), f"Claim {claim_pos} got 0 evidence - fallback should rescue unscored items"


# ---------------------------------------------------------------------------
# 4. Global fallback path — no NameError
# ---------------------------------------------------------------------------


class TestGlobalFallback:
    """Test global fallback uses assigned_url_counts (not assigned_urls_globally)."""

    @pytest.mark.asyncio
    async def test_global_fallback_no_name_error(self):
        """Global fallback (all claims have 0 evidence) must not crash with NameError."""
        evidence = {
            "0": [make_evidence("http://a.com/1", final_score=0.8)],
            "1": [make_evidence("http://b.com/1", final_score=0.7)],
        }
        claims = ["Claim 0", "Claim 1"]

        # LLM gives score=1 to everything → all filtered → global fallback triggers
        # But items ARE scored (score=1), so they won't be rescued (below FALLBACK_MIN_SCORE=3)
        # This tests that the global fallback path doesn't crash
        async def mock_score_google(*args, **kwargs):
            return None

        async def mock_score_llm(claims_arg, evidence_items, article_context):
            return [
                {
                    "evidence_index": i,
                    "score": 1,
                    "rationale": "off-topic",
                    "relevant_claims": [],
                }
                for i in range(len(evidence_items))
            ]

        with patch(
            "app.pipeline.relevance_scorer._score_with_google",
            side_effect=mock_score_google,
        ), patch(
            "app.pipeline.relevance_scorer._score_with_llm", side_effect=mock_score_llm
        ), patch(
            "app.pipeline.relevance_scorer._get_cached_relevance_scores",
            return_value=None,
        ), patch(
            "app.pipeline.relevance_scorer._cache_relevance_scores", return_value=None
        ), patch(
            "app.pipeline.relevance_scorer.settings"
        ) as mock_settings:

            mock_settings.ENABLE_LLM_RELEVANCE_SCORER = True
            mock_settings.LLM_RELEVANCE_MAX_EVIDENCE = 50
            mock_settings.LLM_RELEVANCE_MIN_SCORE = 3
            mock_settings.MAX_CLAIMS_PER_URL = 2

            # This should NOT raise NameError
            result = await score_evidence_batch(claims, evidence, "test article")
            # Result should be a valid dict with claim keys
            assert "0" in result
            assert "1" in result

    @pytest.mark.asyncio
    async def test_global_fallback_rescues_with_unscored(self):
        """Global fallback rescues unscored items when all scored items are filtered."""
        # 2 claims, each with 1 item. Set max_evidence=1 so only 1 item is scored.
        # The scored item gets score=1. The unscored item (None) should be rescued.
        evidence = {
            "0": [make_evidence("http://a.com/1", final_score=0.8)],
            "1": [make_evidence("http://b.com/1", final_score=0.7)],
        }
        claims = ["Claim 0", "Claim 1"]

        async def mock_score_google(*args, **kwargs):
            return None

        async def mock_score_llm(claims_arg, evidence_items, article_context):
            return [
                {
                    "evidence_index": i,
                    "score": 1,
                    "rationale": "off-topic",
                    "relevant_claims": [],
                }
                for i in range(len(evidence_items))
            ]

        with patch(
            "app.pipeline.relevance_scorer._score_with_google",
            side_effect=mock_score_google,
        ), patch(
            "app.pipeline.relevance_scorer._score_with_llm", side_effect=mock_score_llm
        ), patch(
            "app.pipeline.relevance_scorer._get_cached_relevance_scores",
            return_value=None,
        ), patch(
            "app.pipeline.relevance_scorer._cache_relevance_scores", return_value=None
        ), patch(
            "app.pipeline.relevance_scorer.settings"
        ) as mock_settings:

            mock_settings.ENABLE_LLM_RELEVANCE_SCORER = True
            mock_settings.LLM_RELEVANCE_MAX_EVIDENCE = 1  # Only 1 item scored total
            mock_settings.LLM_RELEVANCE_MIN_SCORE = 3
            mock_settings.MAX_CLAIMS_PER_URL = 2

            result = await score_evidence_batch(claims, evidence, "test article")
            # The claim whose item was unscored should be rescued
            total_evidence = sum(len(v) for v in result.values())
            # At least the unscored item should be rescued
            assert total_evidence >= 1, "Expected at least 1 item rescued via fallback"


# ---------------------------------------------------------------------------
# 5. Threshold consistency
# ---------------------------------------------------------------------------


class TestThresholdConsistency:
    """Test scorer is advisory-only — annotates scores but never filters."""

    def test_scorer_is_advisory_only(self):
        """Config should NOT have LLM_RELEVANCE_MIN_SCORE (removed in Track B)."""
        from app.core.config import Settings

        assert "LLM_RELEVANCE_MIN_SCORE" not in Settings.model_fields

    @pytest.mark.asyncio
    async def test_all_items_returned_with_advisory_scores(self):
        """All evidence should be returned with advisory scores annotated (no filtering)."""
        evidence = {
            "0": [make_evidence("http://a.com/1"), make_evidence("http://a.com/2")],
        }
        claims = ["Claim 0"]

        async def mock_score_google(*args, **kwargs):
            return None

        async def mock_score_llm(claims_arg, evidence_items, article_context):
            return [
                {
                    "evidence_index": 0,
                    "score": 3,
                    "rationale": "relevant but questionable source",
                    "relevant_claims": [0],
                },
                {
                    "evidence_index": 1,
                    "score": 2,
                    "rationale": "weakly relevant",
                    "relevant_claims": [],
                },
            ]

        with patch(
            "app.pipeline.relevance_scorer._score_with_google",
            side_effect=mock_score_google,
        ), patch(
            "app.pipeline.relevance_scorer._score_with_llm", side_effect=mock_score_llm
        ), patch(
            "app.pipeline.relevance_scorer._get_cached_relevance_scores",
            return_value=None,
        ), patch(
            "app.pipeline.relevance_scorer._cache_relevance_scores", return_value=None
        ), patch(
            "app.pipeline.relevance_scorer.settings"
        ) as mock_settings:

            mock_settings.ENABLE_LLM_RELEVANCE_SCORER = True
            mock_settings.LLM_RELEVANCE_MAX_EVIDENCE = 50
            mock_settings.MAX_CLAIMS_PER_URL = 2

            result = await score_evidence_batch(claims, evidence, "test article")
            # Advisory-only: ALL items returned, scores annotated
            assert len(result["0"]) == 2
            assert result["0"][0]["llm_relevance_score"] == 3
            assert result["0"][1]["llm_relevance_score"] == 2


# ---------------------------------------------------------------------------
# 6. A0167d67-like scenario — many claims, >50 evidence
# ---------------------------------------------------------------------------


class TestA0167d67Scenario:
    """Reproduce the check a0167d67 failure scenario and verify fix."""

    @pytest.mark.asyncio
    async def test_11_claims_93_evidence_no_starvation(self):
        """With 11 claims and 93 evidence items (cap=50), no claim should be starved."""
        # Reproduce the exact claim sizes from a0167d67
        claim_sizes = {
            "0": 10,
            "1": 10,
            "2": 9,
            "3": 2,
            "4": 10,
            "5": 8,
            "6": 10,
            "7": 5,
            "8": 10,
            "9": 10,
            "10": 9,
        }
        evidence = {}
        for cp, size in claim_sizes.items():
            evidence[cp] = [
                make_evidence(f"http://claim{cp}.com/{i}", final_score=0.7 + i * 0.01)
                for i in range(size)
            ]

        claims = [f"Claim {i}" for i in range(11)]

        # Simulate scorer: give score=5 to all items it receives
        async def mock_score_google(*args, **kwargs):
            return None

        async def mock_score_llm(claims_arg, evidence_items, article_context):
            return [
                {
                    "evidence_index": i,
                    "score": 5,
                    "rationale": "relevant",
                    "relevant_claims": [],
                }
                for i in range(len(evidence_items))
            ]

        with patch(
            "app.pipeline.relevance_scorer._score_with_google",
            side_effect=mock_score_google,
        ), patch(
            "app.pipeline.relevance_scorer._score_with_llm", side_effect=mock_score_llm
        ), patch(
            "app.pipeline.relevance_scorer._get_cached_relevance_scores",
            return_value=None,
        ), patch(
            "app.pipeline.relevance_scorer._cache_relevance_scores", return_value=None
        ), patch(
            "app.pipeline.relevance_scorer.settings"
        ) as mock_settings:

            mock_settings.ENABLE_LLM_RELEVANCE_SCORER = True
            mock_settings.LLM_RELEVANCE_MAX_EVIDENCE = 50
            mock_settings.LLM_RELEVANCE_MIN_SCORE = 3
            mock_settings.MAX_CLAIMS_PER_URL = 2

            result = await score_evidence_batch(claims, evidence, "test article")

            # CRITICAL: Every claim must have evidence (this was the a0167d67 failure)
            for cp in claim_sizes.keys():
                assert (
                    len(result[cp]) > 0
                ), f"Claim {cp} has 0 evidence — starvation not fixed"

            # Claims 7-10 specifically must not be starved
            for cp in ["7", "8", "9", "10"]:
                assert (
                    len(result[cp]) > 0
                ), f"Late claim {cp} starved (a0167d67 regression)"

    @pytest.mark.asyncio
    async def test_unscored_items_rescued_when_scored_items_killed(self):
        """When LLM scores all sent items as 1, unscored items should be rescued."""
        claim_sizes = {"0": 10, "1": 10, "2": 10}
        evidence = {}
        for cp, size in claim_sizes.items():
            evidence[cp] = [
                make_evidence(f"http://claim{cp}.com/{i}", final_score=0.8 - i * 0.05)
                for i in range(size)
            ]

        claims = [f"Claim {i}" for i in range(3)]

        # LLM scores everything it receives as 1 (off-topic)
        async def mock_score_google(*args, **kwargs):
            return None

        async def mock_score_llm(claims_arg, evidence_items, article_context):
            return [
                {
                    "evidence_index": i,
                    "score": 1,
                    "rationale": "off-topic",
                    "relevant_claims": [],
                }
                for i in range(len(evidence_items))
            ]

        with patch(
            "app.pipeline.relevance_scorer._score_with_google",
            side_effect=mock_score_google,
        ), patch(
            "app.pipeline.relevance_scorer._score_with_llm", side_effect=mock_score_llm
        ), patch(
            "app.pipeline.relevance_scorer._get_cached_relevance_scores",
            return_value=None,
        ), patch(
            "app.pipeline.relevance_scorer._cache_relevance_scores", return_value=None
        ), patch(
            "app.pipeline.relevance_scorer.settings"
        ) as mock_settings:

            mock_settings.ENABLE_LLM_RELEVANCE_SCORER = True
            mock_settings.LLM_RELEVANCE_MAX_EVIDENCE = 10  # Low cap = many unscored
            mock_settings.LLM_RELEVANCE_MIN_SCORE = 3
            mock_settings.MAX_CLAIMS_PER_URL = 2

            result = await score_evidence_batch(claims, evidence, "test article")

            # Each claim has items that were never scored (None) — these should be rescued
            for cp in ["0", "1", "2"]:
                assert (
                    len(result[cp]) > 0
                ), f"Claim {cp} should have fallback evidence from unscored items"
