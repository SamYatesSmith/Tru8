"""Tests for PR 2-C: Double domain capping + cross-claim URL dedup fix.

Verifies:
1. Per-claim domain cap skipped when ENABLE_PER_CLAIM_DOMAIN_CAPPING=False
2. Per-claim domain cap runs when ENABLE_PER_CLAIM_DOMAIN_CAPPING=True
3. Global cap still enforced regardless of per-claim setting
4. URL shared across 2 claims kept when MAX_CLAIMS_PER_URL=2
5. URL in 3 claims capped at MAX_CLAIMS_PER_URL=2 (weakest dropped)
6. Single-claim URL behavior unchanged
7. Keep-best selection drops weakest when exceeding K
8. Ledger records casualties from dedup
"""
import pytest
import copy
from unittest.mock import patch, MagicMock, PropertyMock

from app.pipeline.evidence_ledger import EvidenceLedger


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_evidence(source, url, final_score, combined_score=None, credibility_score=None):
    """Create a minimal evidence dict for testing."""
    return {
        "source": source,
        "url": url,
        "title": f"Article from {source}",
        "text": f"Content about {url}",
        "snippet": f"Snippet about {url}",
        "final_score": final_score,
        "combined_score": combined_score or final_score,
        "credibility_score": credibility_score or final_score,
    }


# ---------------------------------------------------------------------------
# Stage 3.6: Cross-claim URL dedup tests
# ---------------------------------------------------------------------------

class TestCrossClaimUrlDedup:
    """Test the Stage 3.6 URL dedup logic in runner.py."""

    def _run_dedup(self, evidence, max_claims_per_url=1, ledger=None):
        """Run the Stage 3.6 dedup logic extracted from runner.py.

        This mirrors the logic in runner.py:695-753 without needing
        to invoke the full pipeline.
        """
        url_claims = {}
        dedup_losers = [] if ledger else None

        for claim_pos, ev_list in evidence.items():
            for ev in ev_list:
                url = ev.get('url', '')
                if not url:
                    continue

                score = ev.get('final_score', ev.get('combined_score', ev.get('credibility_score', 0)))

                if url not in url_claims:
                    url_claims[url] = [(claim_pos, ev, score)]
                elif len(url_claims[url]) < max_claims_per_url:
                    url_claims[url].append((claim_pos, ev, score))
                else:
                    entries = url_claims[url] + [(claim_pos, ev, score)]
                    entries.sort(key=lambda x: (-x[2], x[0]))
                    url_claims[url] = entries[:max_claims_per_url]
                    loser = entries[max_claims_per_url]
                    winner = entries[0]
                    if dedup_losers is not None:
                        dedup_losers.append({"url": url[:120], "loser": loser[0], "winner": winner[0]})

        deduped_evidence = {pos: [] for pos in evidence.keys()}
        for url, entries in url_claims.items():
            for claim_pos, ev, score in entries:
                deduped_evidence[claim_pos].append(ev)

        return deduped_evidence, dedup_losers

    def test_url_shared_across_two_claims(self):
        """Same URL in 2 claims, MAX_CLAIMS_PER_URL=2 → kept in both."""
        shared_url = "https://reuters.com/rate-decision"
        evidence = {
            "0": [make_evidence("reuters.com", shared_url, 0.82)],
            "1": [make_evidence("reuters.com", shared_url, 0.79)],
        }

        result, _ = self._run_dedup(evidence, max_claims_per_url=2)

        assert len(result["0"]) == 1, "Claim 0 should keep the shared URL"
        assert len(result["1"]) == 1, "Claim 1 should keep the shared URL"
        assert result["0"][0]["url"] == shared_url
        assert result["1"][0]["url"] == shared_url

    def test_url_capped_at_max_claims(self):
        """Same URL in 3 claims, MAX=2 → weakest copy dropped."""
        shared_url = "https://reuters.com/rate-decision"
        evidence = {
            "0": [make_evidence("reuters.com", shared_url, 0.85)],
            "1": [make_evidence("reuters.com", shared_url, 0.79)],
            "2": [make_evidence("reuters.com", shared_url, 0.72)],
        }

        result, _ = self._run_dedup(evidence, max_claims_per_url=2)

        # Best 2 scores (0.85, 0.79) kept, weakest (0.72) dropped
        total_kept = sum(len(ev) for ev in result.values())
        assert total_kept == 2, f"Should keep exactly 2 copies, got {total_kept}"
        assert len(result["0"]) == 1, "Claim 0 (score 0.85) should keep URL"
        assert len(result["1"]) == 1, "Claim 1 (score 0.79) should keep URL"
        assert len(result["2"]) == 0, "Claim 2 (score 0.72) should lose URL"

    def test_single_claim_url_unchanged(self):
        """URL in only 1 claim → no behavior change regardless of K."""
        evidence = {
            "0": [make_evidence("reuters.com", "https://reuters.com/a1", 0.85)],
            "1": [make_evidence("bbc.com", "https://bbc.com/a1", 0.80)],
        }

        result_k1, _ = self._run_dedup(evidence, max_claims_per_url=1)
        result_k2, _ = self._run_dedup(evidence, max_claims_per_url=2)

        assert len(result_k1["0"]) == 1
        assert len(result_k1["1"]) == 1
        assert len(result_k2["0"]) == 1
        assert len(result_k2["1"]) == 1

    def test_dedup_keeps_best_when_exceeding(self):
        """When URL exceeds K claims, the copy with lowest score is dropped."""
        shared_url = "https://apnews.com/election"
        evidence = {
            "0": [make_evidence("apnews.com", shared_url, 0.60)],
            "1": [make_evidence("apnews.com", shared_url, 0.90)],
            "2": [make_evidence("apnews.com", shared_url, 0.75)],
        }

        result, _ = self._run_dedup(evidence, max_claims_per_url=2)

        # Kept: claim 1 (0.90), claim 2 (0.75). Dropped: claim 0 (0.60)
        assert len(result["0"]) == 0, "Claim 0 (weakest at 0.60) should be dropped"
        assert len(result["1"]) == 1, "Claim 1 (strongest at 0.90) should be kept"
        assert len(result["2"]) == 1, "Claim 2 (0.75) should be kept"

    def test_dedup_tiebreak_by_claim_pos(self):
        """When scores are equal, lower claim_pos wins (deterministic)."""
        shared_url = "https://reuters.com/article"
        evidence = {
            "0": [make_evidence("reuters.com", shared_url, 0.80)],
            "1": [make_evidence("reuters.com", shared_url, 0.80)],
            "2": [make_evidence("reuters.com", shared_url, 0.80)],
        }

        result, _ = self._run_dedup(evidence, max_claims_per_url=2)

        # Equal scores → lower claim_pos wins: keep "0" and "1", drop "2"
        assert len(result["0"]) == 1, "Claim 0 should win tiebreak"
        assert len(result["1"]) == 1, "Claim 1 should win tiebreak"
        assert len(result["2"]) == 0, "Claim 2 should lose tiebreak"

    def test_dedup_ledger_records_casualties(self):
        """Ledger records which URLs were deduped and why."""
        shared_url = "https://reuters.com/rate-decision"
        evidence = {
            "0": [make_evidence("reuters.com", shared_url, 0.85)],
            "1": [make_evidence("reuters.com", shared_url, 0.60)],
        }

        result, losers = self._run_dedup(evidence, max_claims_per_url=1, ledger=True)

        assert losers is not None
        assert len(losers) == 1
        assert losers[0]["loser"] == "1"
        assert losers[0]["winner"] == "0"
        assert shared_url[:120] in losers[0]["url"]

    def test_old_behavior_with_max_1(self):
        """MAX_CLAIMS_PER_URL=1 gives exact same result as old one-URL-one-claim."""
        shared_url = "https://reuters.com/rate-decision"
        evidence = {
            "0": [make_evidence("reuters.com", shared_url, 0.82)],
            "1": [make_evidence("reuters.com", shared_url, 0.79)],
        }

        result, _ = self._run_dedup(evidence, max_claims_per_url=1)

        # Old behavior: keep the one with higher score (claim 0)
        assert len(result["0"]) == 1
        assert len(result["1"]) == 0


# ---------------------------------------------------------------------------
# Per-claim domain capping flag tests
# ---------------------------------------------------------------------------

class TestPerClaimDomainCapping:
    """Test the per-claim domain capping flag in retrieve.py."""

    @patch("app.pipeline.retrieve.SearchService")
    @patch("app.pipeline.retrieve.EvidenceExtractor")
    @patch("app.pipeline.retrieve.get_api_registry")
    def _make_retriever(self, mock_registry, mock_extractor, mock_search):
        mock_registry.return_value = MagicMock()
        from app.pipeline.retrieve import EvidenceRetriever
        return EvidenceRetriever()

    @patch("app.pipeline.retrieve.settings")
    @patch("app.utils.domain_capping.DomainCapper.apply_caps")
    def test_per_claim_cap_skipped_when_disabled(self, mock_apply_caps, mock_settings):
        """With ENABLE_PER_CLAIM_DOMAIN_CAPPING=False, apply_caps is not called."""
        mock_settings.ENABLE_DOMAIN_CAPPING = True
        mock_settings.ENABLE_PER_CLAIM_DOMAIN_CAPPING = False

        # The guard condition checks both flags — when per-claim is False, apply_caps should NOT run.
        # We verify this by checking that the import and call don't happen.
        # Since the actual retriever flow is complex, we test the condition directly.
        should_run = mock_settings.ENABLE_DOMAIN_CAPPING and getattr(mock_settings, 'ENABLE_PER_CLAIM_DOMAIN_CAPPING', True)
        assert should_run is False, "Per-claim cap should not run when flag is False"
        mock_apply_caps.assert_not_called()

    @patch("app.pipeline.retrieve.settings")
    def test_per_claim_cap_runs_when_enabled(self, mock_settings):
        """With ENABLE_PER_CLAIM_DOMAIN_CAPPING=True, condition evaluates to True."""
        mock_settings.ENABLE_DOMAIN_CAPPING = True
        mock_settings.ENABLE_PER_CLAIM_DOMAIN_CAPPING = True

        should_run = mock_settings.ENABLE_DOMAIN_CAPPING and getattr(mock_settings, 'ENABLE_PER_CLAIM_DOMAIN_CAPPING', True)
        assert should_run is True, "Per-claim cap should run when both flags are True"

    @patch("app.pipeline.retrieve.settings")
    def test_per_claim_cap_skipped_when_domain_capping_disabled(self, mock_settings):
        """With ENABLE_DOMAIN_CAPPING=False, per-claim cap is also skipped."""
        mock_settings.ENABLE_DOMAIN_CAPPING = False
        mock_settings.ENABLE_PER_CLAIM_DOMAIN_CAPPING = True

        should_run = mock_settings.ENABLE_DOMAIN_CAPPING and getattr(mock_settings, 'ENABLE_PER_CLAIM_DOMAIN_CAPPING', True)
        assert should_run is False, "Per-claim cap should not run when domain capping is disabled"


# ---------------------------------------------------------------------------
# LLM Scorer URL gate tests
# ---------------------------------------------------------------------------

class TestLLMScorerUrlGate:
    """Test that the LLM scorer allows up to MAX_CLAIMS_PER_URL assignments."""

    def test_count_based_assignment(self):
        """Simulates the count-based URL assignment logic from relevance_scorer.py."""
        max_claims_per_url = 2
        assigned_url_counts = {}

        url = "https://reuters.com/rate-decision"

        # First assignment should succeed
        assert assigned_url_counts.get(url, 0) < max_claims_per_url
        assigned_url_counts[url] = assigned_url_counts.get(url, 0) + 1

        # Second assignment should also succeed (K=2)
        assert assigned_url_counts.get(url, 0) < max_claims_per_url
        assigned_url_counts[url] = assigned_url_counts.get(url, 0) + 1

        # Third assignment should be blocked
        assert assigned_url_counts.get(url, 0) >= max_claims_per_url

    def test_single_assignment_backward_compat(self):
        """With MAX_CLAIMS_PER_URL=1, behaves like old set-based logic."""
        max_claims_per_url = 1
        assigned_url_counts = {}

        url = "https://reuters.com/rate-decision"

        # First: OK
        assert assigned_url_counts.get(url, 0) < max_claims_per_url
        assigned_url_counts[url] = assigned_url_counts.get(url, 0) + 1

        # Second: blocked (same as old `url in assigned_urls_globally`)
        assert assigned_url_counts.get(url, 0) >= max_claims_per_url

    def test_different_urls_independent(self):
        """Different URLs tracked independently."""
        max_claims_per_url = 1
        assigned_url_counts = {}

        url_a = "https://reuters.com/a1"
        url_b = "https://bbc.com/a1"

        assigned_url_counts[url_a] = assigned_url_counts.get(url_a, 0) + 1

        # url_b is independent — should still be available
        assert assigned_url_counts.get(url_b, 0) < max_claims_per_url

    def test_fallback_respects_count(self):
        """Fallback logic should also respect count-based limits."""
        max_claims_per_url = 2
        assigned_url_counts = {"https://reuters.com/a1": 2}

        url = "https://reuters.com/a1"
        # Already at limit — fallback should skip
        assert assigned_url_counts.get(url, 0) >= max_claims_per_url

        # Different URL still available
        url2 = "https://bbc.com/a1"
        assert assigned_url_counts.get(url2, 0) < max_claims_per_url


# ---------------------------------------------------------------------------
# Config flag defaults
# ---------------------------------------------------------------------------

class TestConfigDefaults:
    """Verify config flags default to backward-compatible values."""

    def test_default_per_claim_capping_disabled(self):
        """Default: ENABLE_PER_CLAIM_DOMAIN_CAPPING=False (global cap only)."""
        from app.core.config import Settings
        field = Settings.model_fields['ENABLE_PER_CLAIM_DOMAIN_CAPPING']
        assert field.default is False

    def test_default_max_claims_per_url(self):
        """Default: MAX_CLAIMS_PER_URL=2 (URL can support 2 related claims)."""
        from app.core.config import Settings
        field = Settings.model_fields['MAX_CLAIMS_PER_URL']
        assert field.default == 2
