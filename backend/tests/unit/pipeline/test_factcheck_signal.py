"""Item 7 stage 1 — the factcheck signal (ENABLE_FACTCHECK_SIGNAL).

Pins the three repairs and, just as deliberately, the OFF state:

  OFF (the default) must be byte-identical to the pre-signal classifier —
  the prompt pair is what keys the replay bench's classifier cassettes, so
  any drift with the flag down kills the bench silently.

  ON: (1) the four-domain fallback marks search-path items; (2) the LLM's
  `factcheck: true` lands on the batch item (set only, never unset); (3) a
  flagged commentary/ANALYSIS item is promoted to reporting with the
  `factcheck_promotion` receipt — a floor, never a demotion — and the
  quality floors keep the last word over it.

Design: audit/2026-08-28_rigour_and_refutation_design_review.md §3 (7-A).
"""

import pytest

from app.core.config import settings
from app.pipeline.evidence_classifier import (
    CLASSIFICATION_SYSTEM_PROMPT,
    CLASSIFICATION_USER_PROMPT,
    FACTCHECK_CLASSIFICATION_SYSTEM_PROMPT,
    FACTCHECK_CLASSIFICATION_USER_PROMPT,
    _apply_factcheck_promotion,
    _apply_quality_floor,
    _classify_heuristic,
    _mark_factcheck_domains,
    _parse_factcheck_flags,
    _prompts,
)


@pytest.fixture
def signal_on(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_FACTCHECK_SIGNAL", True)


@pytest.fixture
def signal_off(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_FACTCHECK_SIGNAL", False)


def _item(url="https://example.org/a", **kw):
    base = {
        "evidence_id": "ev-1",
        "title": "A factcheck of the claim",
        "source": url.split("/")[2],
        "url": url,
        "snippet": "We checked the claim against the data.",
    }
    base.update(kw)
    return base


# ── The OFF state is the pre-signal classifier, byte for byte ─────────────


class TestFlagOffIsByteIdentical:
    @pytest.mark.unit
    def test_default_is_on(self):
        # Flipped ON 2026-08-28 after the firing-rate measurement (zero false
        # positives over 200 items) and the fa08cff7 probe; the bench was
        # re-recorded the same day. Flipping back re-keys the cassettes again.
        assert type(settings).model_fields["ENABLE_FACTCHECK_SIGNAL"].default is True

    @pytest.mark.unit
    def test_prompts_off_are_the_originals(self, signal_off):
        assert _prompts() == (
            CLASSIFICATION_SYSTEM_PROMPT,
            CLASSIFICATION_USER_PROMPT,
        )

    @pytest.mark.unit
    def test_original_prompts_carry_no_factcheck_wording(self, signal_off):
        # Guards against someone "simplifying" to one mutated prompt pair.
        assert "factcheck" not in CLASSIFICATION_SYSTEM_PROMPT.lower()
        assert "factcheck" not in CLASSIFICATION_USER_PROMPT.lower()

    @pytest.mark.unit
    def test_prompts_on_are_the_factcheck_variants(self, signal_on):
        sys_p, user_p = _prompts()
        assert sys_p == FACTCHECK_CLASSIFICATION_SYSTEM_PROMPT
        assert user_p == FACTCHECK_CLASSIFICATION_USER_PROMPT
        assert '"factcheck"' in sys_p or "factcheck" in sys_p
        assert '"factcheck": <true|false>' in user_p

    @pytest.mark.unit
    def test_variant_extends_rather_than_rewrites_the_original(self):
        # The ON system prompt must CONTAIN the original verbatim — tier/type
        # definitions must not fork between the two states.
        assert FACTCHECK_CLASSIFICATION_SYSTEM_PROMPT.startswith(
            CLASSIFICATION_SYSTEM_PROMPT
        )


# ── Domain fallback marking ───────────────────────────────────────────────


class TestDomainMarking:
    @pytest.mark.unit
    @pytest.mark.parametrize(
        "url",
        [
            "https://www.snopes.com/fact-check/some-claim/",
            "https://www.politifact.com/factchecks/2026/aug/x/",
            "https://www.factcheck.org/2026/08/a-check/",
            "https://fullfact.org/health/a-check/",
        ],
    )
    def test_the_four_domains_are_marked(self, url):
        items = [_item(url=url)]
        assert _mark_factcheck_domains(items) == 1
        assert items[0]["is_factcheck"] is True

    @pytest.mark.unit
    def test_other_domains_are_not_marked(self):
        items = [_item(url="https://www.carbonbrief.org/factcheck-wildfires/")]
        # Carbon Brief is NOT on the fallback list — its flag must come from
        # the LLM's content judgement, never a roster (invariant #6).
        assert _mark_factcheck_domains(items) == 0
        assert "is_factcheck" not in items[0]

    @pytest.mark.unit
    def test_already_flagged_items_are_not_recounted(self):
        items = [_item(url="https://www.snopes.com/x/", is_factcheck=True)]
        assert _mark_factcheck_domains(items) == 0
        assert items[0]["is_factcheck"] is True


# ── LLM flag parsing ──────────────────────────────────────────────────────


class TestParseFactcheckFlags:
    @pytest.mark.unit
    def test_true_lands_on_the_right_index(self):
        raw = {
            "classifications": [
                {
                    "index": 0,
                    "tier": "commentary",
                    "type": "analysis",
                    "factcheck": True,
                },
                {
                    "index": 1,
                    "tier": "reporting",
                    "type": "news_reporting",
                    "factcheck": False,
                },
            ]
        }
        assert _parse_factcheck_flags(raw, 2) == [True, False]

    @pytest.mark.unit
    def test_absent_field_is_false(self):
        raw = {
            "classifications": [{"index": 0, "tier": "commentary", "type": "analysis"}]
        }
        assert _parse_factcheck_flags(raw, 1) == [False]

    @pytest.mark.unit
    def test_non_boolean_truthiness_is_refused(self):
        # Strictly `is True`: "true", 1, "yes" all read False (conservative).
        raw = {
            "classifications": [
                {
                    "index": 0,
                    "tier": "commentary",
                    "type": "analysis",
                    "factcheck": "true",
                },
                {"index": 1, "tier": "commentary", "type": "analysis", "factcheck": 1},
            ]
        }
        assert _parse_factcheck_flags(raw, 2) == [False, False]

    @pytest.mark.unit
    def test_bare_list_and_bad_indices_tolerated(self):
        raw = [
            {"index": 0, "tier": "commentary", "type": "analysis", "factcheck": True},
            {"index": 99, "tier": "commentary", "type": "analysis", "factcheck": True},
            "not-a-dict",
        ]
        assert _parse_factcheck_flags(raw, 2) == [True, False]


# ── The promotion rule ────────────────────────────────────────────────────


class TestFactcheckPromotion:
    @pytest.mark.unit
    def test_flagged_commentary_analysis_is_promoted(self):
        ev = _item(is_factcheck=True, tier="commentary", evidence_type="analysis")
        assert _apply_factcheck_promotion(ev) == "factcheck_promotion"
        assert ev["tier"] == "reporting"
        assert ev["evidence_type"] == "analysis"
        assert ev["classification_method"] == "factcheck_promotion"

    @pytest.mark.unit
    def test_flagged_opinion_is_not_promoted(self):
        # BOTH signals must agree — a mis-flagged opinion column stays put.
        ev = _item(is_factcheck=True, tier="commentary", evidence_type="opinion")
        assert _apply_factcheck_promotion(ev) is None
        assert ev["tier"] == "commentary"

    @pytest.mark.unit
    @pytest.mark.parametrize("tier", ["primary", "reporting"])
    def test_promotion_is_a_floor_never_a_demotion(self, tier):
        ev = _item(is_factcheck=True, tier=tier, evidence_type="analysis")
        assert _apply_factcheck_promotion(ev) is None
        assert ev["tier"] == tier

    @pytest.mark.unit
    def test_unflagged_analysis_is_untouched(self):
        ev = _item(tier="commentary", evidence_type="analysis")
        assert _apply_factcheck_promotion(ev) is None
        assert ev["tier"] == "commentary"

    @pytest.mark.unit
    def test_quality_floors_keep_the_last_word(self):
        # A Substack "factcheck": promotion lifts it to reporting, then the
        # blog platform floor (which runs after, "regardless of the LLM ...
        # verdict") pins it back to commentary/opinion. Order is behaviour.
        ev = _item(
            url="https://someone.substack.com/p/factcheck",
            source="someone.substack.com",
            is_factcheck=True,
            tier="commentary",
            evidence_type="analysis",
        )
        assert _apply_factcheck_promotion(ev) == "factcheck_promotion"
        assert ev["tier"] == "reporting"
        assert _apply_quality_floor(ev) == "blog_platform_floor"
        assert ev["tier"] == "commentary"
        assert ev["evidence_type"] == "opinion"
        assert ev["classification_method"] == "blog_platform_floor"


# ── The heuristic path's long-standing rule stays pinned ──────────────────


class TestHeuristicFactcheckRule:
    @pytest.mark.unit
    def test_flagged_item_classifies_reporting_analysis(self):
        # The decided answer the promotion rule promotes TO — if this moves,
        # the promotion rule's target must move with it.
        tier, ev_type = _classify_heuristic(_item(is_factcheck=True))
        assert (tier, ev_type) == ("reporting", "analysis")


# ── End to end through classify_batch (mocked LLM) ────────────────────────


class TestClassifyBatchIntegration:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_llm_flag_marks_and_promotes(self, signal_on, monkeypatch):
        from app.pipeline.evidence_classifier import EvidenceClassifier

        items = [
            _item(url="https://www.carbonbrief.org/factcheck/", evidence_id="ev-cb"),
            _item(url="https://news.example.com/story", evidence_id="ev-news"),
        ]
        classifier = EvidenceClassifier()

        async def fake_llm(user_prompt):
            # The ON-state user prompt must be the factcheck variant.
            assert "flag factchecks" in user_prompt
            return {
                "classifications": [
                    {
                        "index": 0,
                        "tier": "commentary",
                        "type": "analysis",
                        "factcheck": True,
                    },
                    {
                        "index": 1,
                        "tier": "reporting",
                        "type": "news_reporting",
                        "factcheck": False,
                    },
                ]
            }

        monkeypatch.setattr(classifier, "_call_llm", fake_llm)
        await classifier.classify_batch(items)

        assert items[0]["is_factcheck"] is True
        assert items[0]["tier"] == "reporting"
        assert items[0]["classification_method"] == "factcheck_promotion"
        assert not items[1].get("is_factcheck")
        assert items[1]["tier"] == "reporting"
        assert items[1]["classification_method"] == "llm"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_flag_off_touches_nothing(self, signal_off, monkeypatch):
        from app.pipeline.evidence_classifier import EvidenceClassifier

        items = [_item(url="https://www.snopes.com/fact-check/x/", evidence_id="ev-sn")]
        classifier = EvidenceClassifier()

        async def fake_llm(user_prompt):
            # OFF state: the original template — no factcheck instruction and
            # no factcheck field in the response schema. (The item's own title
            # may say "factcheck"; assert on the template's markers only.)
            assert "flag factchecks" not in user_prompt
            assert '"factcheck"' not in user_prompt
            return {
                "classifications": [
                    {"index": 0, "tier": "commentary", "type": "analysis"},
                ]
            }

        monkeypatch.setattr(classifier, "_call_llm", fake_llm)
        await classifier.classify_batch(items)

        assert "is_factcheck" not in items[0]
        assert items[0]["tier"] == "commentary"
        assert items[0]["classification_method"] == "llm"
