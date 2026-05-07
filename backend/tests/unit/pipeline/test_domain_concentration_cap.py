"""Tests for _apply_domain_concentration_cap (Bug D — V1 quality plan 2026-05-06).

Demotes per-claim items when a single domain's share of receipt_status='shown'
items exceeds 35%. Lowest-relevance primary/reporting items demote first;
items already at tier='commentary' are skipped. Demoted items get
classification_method='domain_concentration_cap' for UI surfacing.
"""

import pytest

from app.pipeline.runner import _apply_domain_concentration_cap


def _ev(url, tier, evidence_type="news_reporting", relevance=3, status="shown"):
    """Builder for a minimal Evidence-shaped dict."""
    return {
        "url": url,
        "tier": tier,
        "evidence_type": evidence_type,
        "llm_relevance_score": relevance,
        "receipt_status": status,
        "source": "test",
    }


def _wiki(relevance=3, tier="primary"):
    return _ev(f"https://en.wikipedia.org/wiki/{relevance}", tier, relevance=relevance)


def _other(domain, relevance=3, tier="primary"):
    return _ev(f"https://{domain}/x", tier, relevance=relevance)


class TestDomainConcentrationCap:
    def test_no_demote_when_below_threshold(self):
        # 3 of 10 = 30% — below 35% threshold
        evidence = [_wiki(relevance=i) for i in range(3)] + [
            _other(f"d{i}.com", relevance=i + 5) for i in range(7)
        ]
        demoted = _apply_domain_concentration_cap(evidence)
        assert demoted == 0
        assert all(e["tier"] == "primary" for e in evidence)

    def test_no_demote_at_exactly_threshold(self):
        # 7 of 20 = 35% — exactly at threshold (cap fires only on >threshold)
        evidence = [_wiki(relevance=i) for i in range(7)] + [
            _other(f"d{i}.com", relevance=i + 100) for i in range(13)
        ]
        demoted = _apply_domain_concentration_cap(evidence)
        assert demoted == 0

    def test_demote_above_threshold(self):
        # 12 of 25 = 48% — TRU-B3A4 shape. Target = int(0.35 * 25) = 8.
        # Excess = 12 - 8 = 4 to demote.
        evidence = [_wiki(relevance=i + 1) for i in range(12)] + [
            _other(f"d{i}.com", relevance=i + 100) for i in range(13)
        ]
        demoted = _apply_domain_concentration_cap(evidence)
        assert demoted == 4

    def test_demote_picks_lowest_relevance_first(self):
        # Wikipedia items have relevance 1, 2, 3, 4, 5, 10, 10, 10, 10, 10
        # at 10 of 20 = 50%. Target = 7. Excess = 3. The 3 lowest-relevance
        # (1, 2, 3) should demote.
        wiki_items = [_wiki(relevance=r) for r in (1, 2, 3, 4, 5)] + [
            _wiki(relevance=10) for _ in range(5)
        ]
        evidence = wiki_items + [_other(f"d{i}.com", relevance=50) for i in range(10)]
        _apply_domain_concentration_cap(evidence)
        # Items with relevance 1, 2, 3 should now be commentary
        demoted_relevances = sorted(
            [e["llm_relevance_score"] for e in wiki_items if e["tier"] == "commentary"]
        )
        assert demoted_relevances == [1, 2, 3]

    def test_demoted_items_get_correct_fields(self):
        evidence = [_wiki(relevance=i + 1) for i in range(10)] + [
            _other(f"d{i}.com", relevance=50) for i in range(10)
        ]
        _apply_domain_concentration_cap(evidence)
        demoted = [e for e in evidence if e["tier"] == "commentary"]
        assert len(demoted) > 0
        for e in demoted:
            assert e["tier"] == "commentary"
            assert e["evidence_type"] == "analysis"
            assert e["classification_method"] == "domain_concentration_cap"

    def test_skips_items_already_commentary(self):
        # 1 wiki already commentary + 9 wiki primary + 10 others = 20 total.
        # pr_count for wiki = 9, pr_share = 9/20 = 45% (above 35% threshold).
        # target_pr = int(0.35 * 20) = 7. excess = 9 - 7 = 2.
        # Demote 2 lowest-relevance primary items (relevance 2, 3); leave the
        # already-commentary item untouched.
        wiki_already_comm = [_wiki(relevance=1, tier="commentary")]
        wiki_primary = [
            _wiki(relevance=r, tier="primary") for r in (2, 3, 4, 5, 6, 7, 8, 9, 10)
        ]
        others = [_other(f"d{i}.com", relevance=50) for i in range(10)]
        evidence = wiki_already_comm + wiki_primary + others

        demoted = _apply_domain_concentration_cap(evidence)
        assert demoted == 2

        # Originally commentary stays untouched (no classification_method set)
        for e in wiki_already_comm:
            assert e["tier"] == "commentary"
            assert "classification_method" not in e

        # 2 lowest-relevance primary items demoted: those with relevance 2, 3
        demoted_from_primary = [e for e in wiki_primary if e["tier"] == "commentary"]
        assert sorted(e["llm_relevance_score"] for e in demoted_from_primary) == [2, 3]

    def test_no_demote_when_pr_share_already_below_via_existing_commentary(self):
        # 4 wiki already commentary + 4 wiki primary + 8 others = 16 total.
        # pr_count for wiki = 4. pr_share = 4/16 = 25% (BELOW 35%) — visual
        # dominance is already honestly labelled because half of wiki's
        # presence is commentary. No demote.
        wiki_already_comm = [
            _wiki(relevance=r, tier="commentary") for r in (1, 2, 3, 4)
        ]
        wiki_primary = [_wiki(relevance=r, tier="primary") for r in (5, 6, 7, 8)]
        others = [_other(f"d{i}.com", relevance=50) for i in range(8)]
        evidence = wiki_already_comm + wiki_primary + others

        demoted = _apply_domain_concentration_cap(evidence)
        assert demoted == 0
        # Primary items still primary
        assert all(e["tier"] == "primary" for e in wiki_primary)

    def test_no_demote_when_all_excess_already_commentary(self):
        # 10 wiki items, all already commentary. No demotable candidates.
        evidence = [_wiki(relevance=r, tier="commentary") for r in range(1, 11)] + [
            _other(f"d{i}.com", relevance=50) for i in range(10)
        ]
        demoted = _apply_domain_concentration_cap(evidence)
        assert demoted == 0

    def test_only_counts_shown_items(self):
        # 10 wiki items but 6 are excluded (not 'shown'). Effective shown set:
        # 4 wiki + 10 others = 14. 4/14 = 28% — below threshold, no demote.
        wiki_shown = [_wiki(relevance=r) for r in range(1, 5)]
        wiki_excluded = [
            _ev(
                f"https://en.wikipedia.org/wiki/{r}",
                "primary",
                relevance=r,
                status="excluded",
            )
            for r in range(5, 11)
        ]
        others = [_other(f"d{i}.com", relevance=50) for i in range(10)]
        evidence = wiki_shown + wiki_excluded + others
        demoted = _apply_domain_concentration_cap(evidence)
        assert demoted == 0

    def test_zero_evidence_returns_zero(self):
        assert _apply_domain_concentration_cap([]) == 0

    def test_idempotent_re_application(self):
        evidence = [_wiki(relevance=i + 1) for i in range(10)] + [
            _other(f"d{i}.com", relevance=50) for i in range(10)
        ]
        first = _apply_domain_concentration_cap(evidence)
        second = _apply_domain_concentration_cap(evidence)
        assert first > 0
        # Second pass: previously demoted items are now commentary and skip;
        # remaining primary wiki items are at or below threshold → no further
        # demote.
        assert second == 0

    def test_threshold_override(self):
        # 5 of 20 = 25%. Below 35% default but above 20% override.
        evidence = [_wiki(relevance=i + 1) for i in range(5)] + [
            _other(f"d{i}.com", relevance=50) for i in range(15)
        ]
        demoted = _apply_domain_concentration_cap(evidence, threshold=0.20)
        # target = int(0.20 * 20) = 4. excess = 5 - 4 = 1.
        assert demoted == 1

    def test_caps_multiple_dominant_domains(self):
        # Both wiki AND example.com over threshold in same claim.
        wiki = [_wiki(relevance=i + 1) for i in range(10)]
        ex = [_other("example.com", relevance=i + 1) for i in range(10)]
        evidence = wiki + ex  # 20 total; both 10/20 = 50%
        demoted = _apply_domain_concentration_cap(evidence)
        # target = int(0.35 * 20) = 7. excess per domain = 3. total = 6.
        assert demoted == 6

    def test_target_count_floors_at_one(self):
        # Tiny pool: 2 items, both wiki. share = 100%. target = max(1, int(0.35*2)) = 1.
        # excess = 1.
        evidence = [_wiki(relevance=1), _wiki(relevance=2)]
        demoted = _apply_domain_concentration_cap(evidence)
        assert demoted == 1
        # Lowest-relevance (1) demoted, higher (2) kept.
        kept = [e for e in evidence if e["tier"] == "primary"]
        demoted_items = [e for e in evidence if e["tier"] == "commentary"]
        assert len(kept) == 1 and kept[0]["llm_relevance_score"] == 2
        assert len(demoted_items) == 1 and demoted_items[0]["llm_relevance_score"] == 1
