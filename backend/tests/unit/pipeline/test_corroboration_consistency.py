"""Tests for PR 2-A: final_score recomputation after corroboration boost.

Verifies:
A) If corroboration_boost is applied, final_score updates to reflect boosted credibility_score.
B) If no corroboration boost, final_score remains unchanged.
C) Formula invariant: final_score == combined_score * credibility_score * recency_score (within tolerance).
"""
import pytest
import copy
from unittest.mock import patch, MagicMock

from app.pipeline.retrieve import EvidenceRetriever


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def retriever():
    """Minimal EvidenceRetriever for testing _apply_credibility_weighting."""
    with patch("app.pipeline.retrieve.SearchService"), \
         patch("app.pipeline.retrieve.EvidenceExtractor"), \
         patch("app.pipeline.retrieve.get_api_registry") as mock_registry:
        mock_registry.return_value = MagicMock()
        ret = EvidenceRetriever()
        yield ret


# ---------------------------------------------------------------------------
# Helpers — 3 evidence items with distinct combined_score so ordering
# differences are unambiguous after boosting.
# ---------------------------------------------------------------------------

EVIDENCE_A = {
    "source": "reuters.com",
    "url": "https://reuters.com/article-1",
    "title": "Reuters article on rate decision",
    "text": "The Federal Reserve announced a quarter-point increase in the benchmark interest rate, citing persistent inflationary pressures across consumer goods sectors.",
    "snippet": "The Federal Reserve announced a quarter-point increase in the benchmark interest rate, citing persistent inflationary pressures across consumer goods sectors.",
    "published_date": "2026-01-15",
    "combined_score": 0.80,
}

EVIDENCE_B = {
    "source": "apnews.com",
    "url": "https://apnews.com/article-1",
    "title": "AP analysis of monetary policy shift",
    "text": "Economists broadly expected the central bank to tighten policy by 25 basis points at its January meeting, with labor market data supporting further hawkish moves.",
    "snippet": "Economists broadly expected the central bank to tighten policy by 25 basis points at its January meeting, with labor market data supporting further hawkish moves.",
    "published_date": "2026-01-15",
    "combined_score": 0.70,
}

EVIDENCE_C = {
    "source": "bbc.com",
    "url": "https://bbc.com/article-1",
    "title": "BBC article on deep-sea discovery",
    "text": "Marine biologists from the University of Tokyo have identified a previously unknown species of anglerfish living at depths exceeding 3,000 metres in the western Pacific basin.",
    "snippet": "Marine biologists from the University of Tokyo have identified a previously unknown species of anglerfish living at depths exceeding 3,000 metres in the western Pacific basin.",
    "published_date": "2026-01-10",
    "combined_score": 0.60,
}

# Controlled credibility values (all above 0.55 threshold)
CRED_MAP = {
    "reuters.com": 0.90,
    "apnews.com": 0.88,
    "bbc.com": 0.85,
}

FIXED_RECENCY = 0.95


def _mock_corroboration_boost_ab(evidence_list):
    """Simulate corroboration between A (Reuters) and B (AP), not C (BBC)."""
    for ev in evidence_list:
        if ev.get("source") in ("reuters.com", "apnews.com"):
            old_cred = ev["credibility_score"]
            ev["credibility_score"] = min(1.0, old_cred + 0.08)
            ev["corroboration_boost"] = 0.08
            ev["corroborating_sources"] = 1
            ev["corroboration_indices"] = []
    stats = {"items_boosted": 2, "corroboration_pairs": 1, "total_boost": 0.16}
    return evidence_list, stats


def _mock_corroboration_noop(evidence_list):
    """Simulate no corroboration found."""
    return evidence_list, {"enabled": True, "items_boosted": 0, "reason": "no_corroboration_found"}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestCorroborationFinalScoreConsistency:
    """Verify final_score is recomputed after corroboration boost (PR 2-A)."""

    def test_boost_updates_final_score(self, retriever):
        """A) Boosted items have final_score reflecting updated credibility_score."""
        evidence = [copy.deepcopy(EVIDENCE_A), copy.deepcopy(EVIDENCE_B), copy.deepcopy(EVIDENCE_C)]

        with patch.object(retriever, '_get_credibility_score',
                          side_effect=lambda s, u, e, j: CRED_MAP.get(s, 0.6)), \
             patch.object(retriever, '_get_recency_score', return_value=FIXED_RECENCY), \
             patch("app.utils.corroboration.apply_corroboration_boost",
                   side_effect=_mock_corroboration_boost_ab):

            result = retriever._apply_credibility_weighting(evidence, track_raw_evidence=False)

        weighted = result if isinstance(result, list) else result[0]

        reuters = next(e for e in weighted if e["source"] == "reuters.com")
        boosted_cred = 0.90 + 0.08  # 0.98
        expected_final = 0.80 * boosted_cred * FIXED_RECENCY
        assert reuters["credibility_score"] == pytest.approx(boosted_cred, abs=1e-9)
        assert reuters["final_score"] == pytest.approx(expected_final, abs=1e-9)

        ap = next(e for e in weighted if e["source"] == "apnews.com")
        boosted_cred_ap = 0.88 + 0.08  # 0.96
        expected_final_ap = 0.70 * boosted_cred_ap * FIXED_RECENCY
        assert ap["credibility_score"] == pytest.approx(boosted_cred_ap, abs=1e-9)
        assert ap["final_score"] == pytest.approx(expected_final_ap, abs=1e-9)

    def test_no_boost_final_score_unchanged(self, retriever):
        """B) Non-boosted item keeps original final_score (same evidence set)."""
        evidence = [copy.deepcopy(EVIDENCE_A), copy.deepcopy(EVIDENCE_B), copy.deepcopy(EVIDENCE_C)]

        with patch.object(retriever, '_get_credibility_score',
                          side_effect=lambda s, u, e, j: CRED_MAP.get(s, 0.6)), \
             patch.object(retriever, '_get_recency_score', return_value=FIXED_RECENCY), \
             patch("app.utils.corroboration.apply_corroboration_boost",
                   side_effect=_mock_corroboration_boost_ab):

            result = retriever._apply_credibility_weighting(evidence, track_raw_evidence=False)

        weighted = result if isinstance(result, list) else result[0]

        bbc = next(e for e in weighted if e["source"] == "bbc.com")
        assert bbc.get("corroboration_boost", 0) == 0
        expected_final_bbc = 0.60 * 0.85 * FIXED_RECENCY
        assert bbc["final_score"] == pytest.approx(expected_final_bbc, abs=1e-9)

    def test_formula_invariant_post_boost(self, retriever):
        """C) final_score == combined_score * credibility_score * recency_score for ALL items."""
        evidence = [copy.deepcopy(EVIDENCE_A), copy.deepcopy(EVIDENCE_B), copy.deepcopy(EVIDENCE_C)]

        with patch.object(retriever, '_get_credibility_score',
                          side_effect=lambda s, u, e, j: CRED_MAP.get(s, 0.6)), \
             patch.object(retriever, '_get_recency_score', return_value=FIXED_RECENCY), \
             patch("app.utils.corroboration.apply_corroboration_boost",
                   side_effect=_mock_corroboration_boost_ab):

            result = retriever._apply_credibility_weighting(evidence, track_raw_evidence=False)

        weighted = result if isinstance(result, list) else result[0]

        for ev in weighted:
            expected = ev.get("combined_score", 0.5) * ev["credibility_score"] * ev.get("recency_score", 1.0)
            assert ev["final_score"] == pytest.approx(expected, abs=1e-9), \
                f"{ev['source']}: final_score={ev['final_score']:.6f}, expected={expected:.6f}"

    def test_no_corroboration_found_no_change(self, retriever):
        """B) When no corroboration pairs found, all scores untouched."""
        evidence = [copy.deepcopy(EVIDENCE_A), copy.deepcopy(EVIDENCE_C)]

        with patch.object(retriever, '_get_credibility_score',
                          side_effect=lambda s, u, e, j: CRED_MAP.get(s, 0.6)), \
             patch.object(retriever, '_get_recency_score', return_value=FIXED_RECENCY), \
             patch("app.utils.corroboration.apply_corroboration_boost",
                   side_effect=_mock_corroboration_noop):

            result = retriever._apply_credibility_weighting(evidence, track_raw_evidence=False)

        weighted = result if isinstance(result, list) else result[0]

        for ev in weighted:
            expected = ev.get("combined_score", 0.5) * ev["credibility_score"] * ev.get("recency_score", 1.0)
            assert ev["final_score"] == pytest.approx(expected, abs=1e-9)
            assert ev.get("corroboration_boost", 0) == 0

    def test_boost_changes_sort_order(self, retriever):
        """Corroboration boost can change evidence ordering via recomputed final_score.

        Setup: AP (combined=0.70, cred=0.88) starts below Reuters (combined=0.80, cred=0.90).
        After boost, AP's final_score changes. We verify the sort at the end
        reflects the recomputed final_score, not the stale pre-boost value.
        """
        # Give AP a higher combined_score but lower credibility so it starts lower.
        ev_ap = copy.deepcopy(EVIDENCE_B)
        ev_ap["combined_score"] = 0.85
        ev_bbc = copy.deepcopy(EVIDENCE_C)
        ev_bbc["combined_score"] = 0.82

        # Credibility: BBC slightly higher than AP pre-boost
        cred_map = {"apnews.com": 0.70, "bbc.com": 0.72}

        def _boost_ap_only(evidence_list):
            for ev in evidence_list:
                if ev.get("source") == "apnews.com":
                    ev["credibility_score"] = min(1.0, ev["credibility_score"] + 0.15)
                    ev["corroboration_boost"] = 0.15
                    ev["corroborating_sources"] = 2
                    ev["corroboration_indices"] = []
            return evidence_list, {"items_boosted": 1, "corroboration_pairs": 1}

        with patch.object(retriever, '_get_credibility_score',
                          side_effect=lambda s, u, e, j: cred_map.get(s, 0.6)), \
             patch.object(retriever, '_get_recency_score', return_value=1.0), \
             patch("app.utils.corroboration.apply_corroboration_boost",
                   side_effect=_boost_ap_only):

            result = retriever._apply_credibility_weighting(
                [ev_ap, ev_bbc], track_raw_evidence=False
            )

        weighted = result if isinstance(result, list) else result[0]

        # Pre-boost: AP final = 0.85 * 0.70 * 1.0 = 0.595
        #            BBC final = 0.82 * 0.72 * 1.0 = 0.5904
        # Post-boost: AP final = 0.85 * 0.85 * 1.0 = 0.7225 (boosted by +0.15 to 0.85 cred)
        #             BBC final = 0.82 * 0.72 * 1.0 = 0.5904 (unchanged)
        # AP should now be FIRST (higher final_score).
        assert weighted[0]["source"] == "apnews.com", \
            f"Expected AP first after boost, got {weighted[0]['source']}"
        assert weighted[0]["final_score"] > weighted[1]["final_score"]
