"""Tests for query class augmentation (Step 1 of pool-diversity, 2026-05-12).

Mechanical class-targeted query expansion. Mirrors the test discipline
of the NF-18 sweep and NF-20-B propagation tests — wired-seam through
``retrieve.py`` is covered indirectly by the bench; this file pins the
pure-function semantics.

Provider site:-operator semantics were empirically confirmed by
``scripts/spike_site_operator.py`` on 2026-05-12 against Serper /
Brave / SerpAPI — all three honour ``site:X OR site:Y`` at 100%.
"""

import pytest

from app.utils.query_class_augmentation import augment_plans_with_class_queries


def _plan(claim_index: int, element_id: str, queries: list, freshness: str = "py"):
    return {
        "claim_index": claim_index,
        "element_id": element_id,
        "queries": list(queries),
        "freshness": freshness,
        "reasoning": "",
    }


class TestNoOpCases:
    def test_no_op_when_no_plans(self):
        assert (
            augment_plans_with_class_queries([], {"primary_domain": "Politics"}) == []
        )

    def test_no_op_when_no_classification(self):
        plans = [_plan(0, "e1", ["BP profit 2022"])]
        result = augment_plans_with_class_queries(plans, None)
        assert result[0]["queries"] == ["BP profit 2022"]

    def test_no_op_when_empty_classification(self):
        plans = [_plan(0, "e1", ["BP profit 2022"])]
        result = augment_plans_with_class_queries(plans, {})
        assert result[0]["queries"] == ["BP profit 2022"]

    def test_no_op_when_plan_has_no_queries(self):
        plans = [_plan(0, "e1", [])]
        result = augment_plans_with_class_queries(
            plans, {"primary_domain": "Finance", "jurisdiction": "UK"}
        )
        assert result[0]["queries"] == []

    def test_unknown_domain_falls_back_to_general(self):
        # An unmapped domain still gets the General class (news only) —
        # so callers don't have to enumerate every possible domain.
        plans = [_plan(0, "e1", ["claim text"])]
        result = augment_plans_with_class_queries(
            plans, {"primary_domain": "UnmappedDomain"}
        )
        assert len(result[0]["queries"]) == 2
        assert "site:bbc.co.uk" in result[0]["queries"][1]


class TestSingleClassAugmentation:
    """Domains that don't qualify for officials get exactly one
    class-targeted query appended per element."""

    def test_climate_gets_academic_class(self):
        plans = [_plan(0, "e1", ["1.5°C ocean heat anomalies"])]
        result = augment_plans_with_class_queries(plans, {"primary_domain": "Climate"})
        # 1 LLM + 1 class = 2 queries
        assert len(result[0]["queries"]) == 2
        assert result[0]["queries"][0] == "1.5°C ocean heat anomalies"  # untouched
        # First class for Climate is academic
        assert "site:nature.com" in result[0]["queries"][1]
        assert "site:doi.org" in result[0]["queries"][1]

    def test_sports_gets_news_class(self):
        plans = [_plan(0, "e1", ["Premier League title 2024"])]
        result = augment_plans_with_class_queries(plans, {"primary_domain": "Sports"})
        assert len(result[0]["queries"]) == 2
        assert "site:bbc.co.uk" in result[0]["queries"][1]

    def test_general_gets_news_class(self):
        plans = [_plan(0, "e1", ["some general claim"])]
        result = augment_plans_with_class_queries(plans, {"primary_domain": "General"})
        assert len(result[0]["queries"]) == 2
        assert "site:bbc.co.uk" in result[0]["queries"][1]


class TestOfficialsClassAddedForHighValueDomains:
    """Politics / Finance / Health / Law get TWO class queries when
    a jurisdiction is set — news AND jurisdiction-aware officials."""

    def test_uk_politics_gets_news_plus_uk_officials(self):
        plans = [_plan(0, "e1", ["Bank of England rate decision"])]
        result = augment_plans_with_class_queries(
            plans, {"primary_domain": "Finance", "jurisdiction": "UK"}
        )
        # 1 LLM + 1 news + 1 UK officials = 3 queries
        assert len(result[0]["queries"]) == 3
        # News class (first)
        assert "site:bbc.co.uk" in result[0]["queries"][1]
        # UK officials class (second)
        assert "site:gov.uk" in result[0]["queries"][2]
        assert "site:parliament.uk" in result[0]["queries"][2]

    def test_us_finance_gets_news_plus_us_officials(self):
        plans = [_plan(0, "e1", ["SEC enforcement action 2024"])]
        result = augment_plans_with_class_queries(
            plans, {"primary_domain": "Finance", "jurisdiction": "US"}
        )
        assert len(result[0]["queries"]) == 3
        assert "site:sec.gov" in result[0]["queries"][2]
        assert "site:federalreserve.gov" in result[0]["queries"][2]

    def test_health_with_jurisdiction_gets_both_classes(self):
        plans = [_plan(0, "e1", ["NHS waiting list 2024"])]
        result = augment_plans_with_class_queries(
            plans, {"primary_domain": "Health", "jurisdiction": "UK"}
        )
        assert len(result[0]["queries"]) == 3
        # Academic comes first for Health
        assert "site:nature.com" in result[0]["queries"][1]
        # UK officials includes NHS
        assert "site:nhs.uk" in result[0]["queries"][2]

    def test_high_value_domain_no_jurisdiction_falls_back_to_one_class(self):
        # If jurisdiction is missing for a domain that would otherwise
        # qualify for officials, we still get the news class.
        plans = [_plan(0, "e1", ["claim"])]
        result = augment_plans_with_class_queries(plans, {"primary_domain": "Politics"})
        assert len(result[0]["queries"]) == 2  # only news, no officials
        assert "site:bbc.co.uk" in result[0]["queries"][1]

    def test_low_value_domain_with_jurisdiction_no_officials(self):
        # Sports + UK should NOT get UK-officials class — Sports isn't
        # in _DOMAINS_WORTH_OFFICIAL.
        plans = [_plan(0, "e1", ["claim"])]
        result = augment_plans_with_class_queries(
            plans, {"primary_domain": "Sports", "jurisdiction": "UK"}
        )
        assert len(result[0]["queries"]) == 2  # news only
        # No gov.uk in the augmented queries
        for q in result[0]["queries"]:
            assert "site:gov.uk" not in q


class TestPerElementApplication:
    def test_each_element_independently_augmented(self):
        plans = [
            _plan(0, "e1", ["GBR coral bleaching 2024"]),
            _plan(0, "e2", ["Coral Sea temperature anomaly"]),
            _plan(0, "e3", ["AIMS attribution study"]),
        ]
        result = augment_plans_with_class_queries(plans, {"primary_domain": "Climate"})
        # Every plan got augmented
        for plan in result:
            assert len(plan["queries"]) == 2
            assert (
                "site:doi.org" in plan["queries"][1]
                or "site:nature.com" in plan["queries"][1]
            )

    def test_base_query_used_for_augmentation_is_first_llm_query(self):
        # The class string is appended to the FIRST LLM query (most-
        # confident), not to all of them.
        plans = [_plan(0, "e1", ["first query", "second query", "third query"])]
        result = augment_plans_with_class_queries(plans, {"primary_domain": "Climate"})
        # Original 3 preserved, then 1 augmented
        assert len(result[0]["queries"]) == 4
        assert result[0]["queries"][0] == "first query"
        assert result[0]["queries"][1] == "second query"
        assert result[0]["queries"][2] == "third query"
        # Augmented query starts with "first query " not "second query "
        assert result[0]["queries"][3].startswith("first query ")
        assert "site:doi.org" in result[0]["queries"][3]


class TestIntegrationWithRetrievePipeline:
    """End-to-end query-plan shape check. retrieve.py:325 caps at 5;
    augmenter must produce ≤5 queries even on the worst-case domain."""

    def test_worst_case_within_per_element_cap(self):
        # Worst case: 3 LLM queries + 1 academic class + 1 officials class = 5 total
        plans = [
            _plan(0, "e1", ["q1", "q2", "q3"]),
        ]
        result = augment_plans_with_class_queries(
            plans, {"primary_domain": "Health", "jurisdiction": "UK"}
        )
        # Augmented length = 5 — exactly at the cap. Anything more
        # would be clipped by retrieve.py:325.
        assert len(result[0]["queries"]) == 5

    def test_returns_same_list_reference_for_chaining(self):
        # Mutates in place + returns the same list — matches the
        # _inject_freshness_for_historical_dates pattern.
        plans = [_plan(0, "e1", ["claim"])]
        result = augment_plans_with_class_queries(plans, {"primary_domain": "Climate"})
        assert result is plans
