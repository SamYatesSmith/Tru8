"""Tests for query date anchor augmentation (2026-05-12).

Mechanical year-anchoring on LLM-generated queries. Surfaced by
live-test of Prompt 1 (November 2023 Autumn Statement): search
providers returned 2025 Budget content for a 2023-anchored claim
because the LLM Query Planner produced queries without the year,
and Google ranks recent content higher for recurring topics.
"""

from app.utils.query_date_anchor import (
    _extract_years_from_entities,
    augment_plans_with_date_anchor,
)


def _plan(claim_index, queries, element_id="e1"):
    return {
        "claim_index": claim_index,
        "element_id": element_id,
        "queries": list(queries),
        "freshness": "py",
        "reasoning": "",
    }


def _claim(claim_index, entities):
    return {
        "claim_index": claim_index,
        "text": f"Claim {claim_index}",
        "key_entities": list(entities),
    }


def _date(text):
    return {"text": text, "type": "DATE"}


# ── _extract_years_from_entities ─────────────────────────────────────


class TestExtractYears:
    def test_empty_entities(self):
        assert _extract_years_from_entities(None) == []
        assert _extract_years_from_entities([]) == []

    def test_single_4_digit_year(self):
        assert _extract_years_from_entities([_date("2023")]) == [2023]

    def test_year_inside_phrase(self):
        assert _extract_years_from_entities([_date("November 2023")]) == [2023]
        assert _extract_years_from_entities([_date("19 July 2022")]) == [2022]
        assert _extract_years_from_entities([_date("March 2024")]) == [2024]

    def test_iso_date(self):
        assert _extract_years_from_entities([_date("2022-07-19")]) == [2022]
        assert _extract_years_from_entities([_date("2023-11")]) == [2023]

    def test_multiple_years_unique(self):
        years = _extract_years_from_entities(
            [_date("2022"), _date("November 2023"), _date("2023-11-15")]
        )
        assert sorted(years) == [2022, 2023]

    def test_ignores_non_date_entities(self):
        bag = [
            {"text": "2023", "type": "AMOUNT"},  # not DATE
            {"text": "BoE", "type": "ORG"},
            _date("2024"),
        ]
        assert _extract_years_from_entities(bag) == [2024]

    def test_19xx_and_20xx_pattern(self):
        # Only 19xx/20xx matches; 18xx or 21xx don't.
        assert _extract_years_from_entities([_date("1999")]) == [1999]
        assert _extract_years_from_entities([_date("2099")]) == [2099]
        assert _extract_years_from_entities([_date("1899")]) == []
        assert _extract_years_from_entities([_date("2101")]) == []

    def test_malformed_entities_handled(self):
        bag = [None, "not-a-dict", {}, {"text": None, "type": "DATE"}]
        assert _extract_years_from_entities(bag) == []


# ── augment_plans_with_date_anchor ───────────────────────────────────


class TestNoOpCases:
    def test_empty_plans(self):
        assert augment_plans_with_date_anchor([], [_claim(0, [_date("2023")])]) == []

    def test_empty_claims(self):
        plans = [_plan(0, ["x"])]
        result = augment_plans_with_date_anchor(plans, [])
        assert result[0]["queries"] == ["x"]

    def test_no_date_entities(self):
        plans = [_plan(0, ["x"])]
        claims = [_claim(0, [{"text": "BoE", "type": "ORG"}])]
        result = augment_plans_with_date_anchor(plans, claims)
        assert result[0]["queries"] == ["x"]

    def test_three_plus_years_skip(self):
        # 3+ distinct years → genuinely ambiguous → no-op.
        # [Updated 2026-07-06, F1-D1: this test previously asserted no-op for
        # TWO years; two-year claims are now range/comparison-anchored — see
        # TestRangeAnchor. Three or more stays a no-op.]
        plans = [_plan(0, ["UK economy"])]
        claims = [_claim(0, [_date("2008"), _date("2020"), _date("1997")])]
        result = augment_plans_with_date_anchor(plans, claims)
        assert result[0]["queries"] == ["UK economy"]

    def test_year_already_in_query(self):
        # LLM did the right thing; no double-anchoring.
        plans = [_plan(0, ["Autumn Statement 2023 NI cut"])]
        claims = [_claim(0, [_date("November 2023")])]
        result = augment_plans_with_date_anchor(plans, claims)
        assert result[0]["queries"] == ["Autumn Statement 2023 NI cut"]


# ── Successful augmentation ──────────────────────────────────────────


class TestAnchorAppended:
    def test_prompt_1_repro_november_2023(self):
        # Real Politics case: claim has "November 2023" DATE; LLM
        # produced query without the year; search providers default
        # to 2025 content. Anchor must append 2023.
        plans = [
            _plan(0, ["Autumn Statement NI cut OBR forecast"]),
            _plan(0, ["IFS warning departmental spending"]),
        ]
        claims = [
            _claim(
                0,
                [
                    {"text": "Autumn Statement", "type": "EVENT"},
                    _date("November 2023"),
                    {"text": "OBR", "type": "ORG"},
                ],
            )
        ]
        result = augment_plans_with_date_anchor(plans, claims)
        for plan in result:
            for q in plan["queries"]:
                assert "2023" in q

    def test_anchors_to_unique_year_per_claim(self):
        # Two different claims, two different years; each gets its
        # own anchor independently.
        plans = [
            _plan(0, ["GBR coral bleaching"]),
            _plan(1, ["UK Autumn Statement NI"]),
        ]
        claims = [
            _claim(0, [_date("March 2024")]),
            _claim(1, [_date("November 2023")]),
        ]
        result = augment_plans_with_date_anchor(plans, claims)
        assert result[0]["queries"] == ["GBR coral bleaching 2024"]
        assert result[1]["queries"] == ["UK Autumn Statement NI 2023"]

    def test_only_appends_to_queries_missing_year(self):
        # Mixed: one query has 2023, one doesn't. Only the one
        # without gets anchored.
        plans = [_plan(0, ["NI cut 2023 details", "OBR forecast cut"])]
        claims = [_claim(0, [_date("November 2023")])]
        result = augment_plans_with_date_anchor(plans, claims)
        assert result[0]["queries"] == [
            "NI cut 2023 details",
            "OBR forecast cut 2023",
        ]

    def test_returns_same_list_for_chaining(self):
        # Mutates in place + returns same reference — matches
        # augment_plans_with_class_queries pattern so the retrieve.py
        # wiring composes cleanly.
        plans = [_plan(0, ["x"])]
        claims = [_claim(0, [_date("2023")])]
        result = augment_plans_with_date_anchor(plans, claims)
        assert result is plans


# ── F1-D1: two-year range/comparison anchoring (2026-07-06) ─────────
# Design: audit/2026-07-03_f1f2_design_review.md §3 (Option D1). A range
# claim ("built between 1998 and 2008") yields exactly two DATE-entity
# years; the old exactly-one rule left such queries unanchored and the
# providers' recency ranking buried period material. Both years are
# appended (ascending): range-covering for era claims and side-neutral
# for two-year comparison claims.


class TestRangeAnchor:
    def test_two_years_both_appended_ascending(self):
        plans = [_plan(0, ["LHC construction timeline"])]
        claims = [_claim(0, [_date("1998"), _date("2008")])]
        result = augment_plans_with_date_anchor(plans, claims)
        assert result[0]["queries"] == ["LHC construction timeline 1998 2008"]

    def test_two_years_in_one_entity_phrase(self):
        # "between 1998 and 2008" arrives as a single DATE entity.
        plans = [_plan(0, ["LHC construction timeline"])]
        claims = [_claim(0, [_date("between 1998 and 2008")])]
        result = augment_plans_with_date_anchor(plans, claims)
        assert result[0]["queries"] == ["LHC construction timeline 1998 2008"]

    def test_only_missing_year_appended(self):
        plans = [_plan(0, ["LHC 2008 completion"])]
        claims = [_claim(0, [_date("1998"), _date("2008")])]
        result = augment_plans_with_date_anchor(plans, claims)
        assert result[0]["queries"] == ["LHC 2008 completion 1998"]

    def test_both_years_present_no_op(self):
        plans = [_plan(0, ["LHC 1998 2008 construction"])]
        claims = [_claim(0, [_date("1998"), _date("2008")])]
        result = augment_plans_with_date_anchor(plans, claims)
        assert result[0]["queries"] == ["LHC 1998 2008 construction"]

    def test_comparison_shape_gets_both_sides(self):
        # Two-year comparison claims must not be skewed to one side.
        plans = [_plan(0, ["UK GDP growth comparison"])]
        claims = [_claim(0, [_date("2019"), _date("2024")])]
        result = augment_plans_with_date_anchor(plans, claims)
        assert result[0]["queries"] == ["UK GDP growth comparison 2019 2024"]

    def test_single_year_behaviour_unchanged(self):
        plans = [_plan(0, ["water privatisation England"])]
        claims = [_claim(0, [_date("1989")])]
        result = augment_plans_with_date_anchor(plans, claims)
        assert result[0]["queries"] == ["water privatisation England 1989"]


# ── F1-D1 corrective: current/future years excluded (2026-07-06) ─────
# Found by the bench gate: TRU-5647-FA4F claim 1 carried DATE entities
# [2022, <current>] (the current year arrives spuriously via article
# context / "as of" references). Anchoring BOTH polluted a past-event
# query with today's year — and the same current-year entity disables
# B4. Rule: drop years >= current year from the anchor set BEFORE the
# 1-or-2 rule. The recent side of any comparison needs no anchoring
# help; recency ranking already favours it.


class TestCurrentYearExcluded:
    CY = 2026  # injected current year for determinism

    def test_past_plus_current_anchors_past_only(self):
        plans = [_plan(0, ["London boroughs damage estimate"])]
        claims = [_claim(0, [_date("2022"), _date("2026")])]
        result = augment_plans_with_date_anchor(plans, claims, _current_year=self.CY)
        assert result[0]["queries"] == ["London boroughs damage estimate 2022"]

    def test_two_past_years_still_both(self):
        plans = [_plan(0, ["LHC construction timeline"])]
        claims = [_claim(0, [_date("1998"), _date("2008")])]
        result = augment_plans_with_date_anchor(plans, claims, _current_year=self.CY)
        assert result[0]["queries"] == ["LHC construction timeline 1998 2008"]

    def test_single_current_year_still_anchors(self):
        # Documented behaviour preserved: a lone current-year claim still
        # anchors ("lower stakes since recent content is what Google wants
        # to return anyway").
        plans = [_plan(0, ["UK spring statement"])]
        claims = [_claim(0, [_date("2026")])]
        result = augment_plans_with_date_anchor(plans, claims, _current_year=self.CY)
        assert result[0]["queries"] == ["UK spring statement 2026"]

    def test_future_year_dropped(self):
        plans = [_plan(0, ["stadium completion deadline"])]
        claims = [_claim(0, [_date("2030"), _date("2022")])]
        result = augment_plans_with_date_anchor(plans, claims, _current_year=self.CY)
        assert result[0]["queries"] == ["stadium completion deadline 2022"]

    def test_recent_past_pair_drops_current_only(self):
        plans = [_plan(0, ["rate decision comparison"])]
        claims = [_claim(0, [_date("2025"), _date("2026")])]
        result = augment_plans_with_date_anchor(plans, claims, _current_year=self.CY)
        assert result[0]["queries"] == ["rate decision comparison 2025"]

    def test_three_past_years_still_no_op(self):
        plans = [_plan(0, ["UK economy"])]
        claims = [_claim(0, [_date("1997"), _date("2008"), _date("2020")])]
        result = augment_plans_with_date_anchor(plans, claims, _current_year=self.CY)
        assert result[0]["queries"] == ["UK economy"]


# ── Composition with class augmentation ──────────────────────────────


class TestComposition:
    def test_class_augmentation_inherits_date_anchor(self):
        # When date-anchor runs FIRST, then class augmentation, the
        # class-targeted queries inherit the year in their base. This
        # is the production wiring order in retrieve.py.
        from app.utils.query_class_augmentation import (
            augment_plans_with_class_queries,
        )

        plans = [_plan(0, ["Autumn Statement OBR"])]
        claims = [_claim(0, [_date("November 2023")])]

        # Date anchor first
        plans = augment_plans_with_date_anchor(plans, claims)
        # Now class augmentation
        plans = augment_plans_with_class_queries(
            plans, {"primary_domain": "Finance", "jurisdiction": "UK"}
        )

        # All queries — base + augmented — should contain 2023
        for q in plans[0]["queries"]:
            assert "2023" in q, f"Query missing year anchor: {q!r}"
        # And the class queries should be present (site: filters)
        site_count = sum(1 for q in plans[0]["queries"] if "site:" in q)
        assert site_count >= 1, "Class augmentation didn't fire"
