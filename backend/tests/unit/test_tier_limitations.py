"""The receipt for a reduced-tier result must list everything that was withheld.

WHY THIS FILE EXISTS
--------------------
Measured against production on 2026-08-05, across four paid checks:

  - `QUICK_LIMITATIONS` declared 6 omissions; `QUICK_CONFIG` disabled 10. The
    undeclared four were evidence distillation, post-filter recovery, and the
    two caps that shrink breadth — sources 20 -> 8, queries per element 3 -> 1.
    Breadth is what the tier is sold on, so those were the ones that mattered.
  - The list was duplicated verbatim in agent.py and agent_x402.py.
  - The existing test asserted `len(...) == 6`, so it passed throughout and
    would have kept passing however many stages were quietly switched off.

That last point is the reason this file is written the way it is. A test that
counts a hand-written list can only ever confirm the list is the length someone
typed. The guard has to compare the DECLARATION against the CONFIG, so that
disabling a stage without declaring it fails.

Invariant #5: no hidden curation — every exclusion has a receipt.
"""

import pytest

from app.core.tier_limitations import (
    _FIELD_SLUGS,
    limitations_for_tier,
    undeclared_reductions,
)
from app.pipeline.runner import DEFAULT_CONFIG, QUICK_CONFIG


# ---------------------------------------------------------------------------
# The guard that could not have existed before
# ---------------------------------------------------------------------------


def test_every_config_reduction_is_declared():
    """Disabling a stage in QUICK_CONFIG without naming it here must fail.

    This is the whole point of the module. If someone adds
    `enable_something_new=False` to QUICK_CONFIG and ships, callers would be
    charged for a reduced result whose receipt does not mention the reduction.
    """
    assert undeclared_reductions() == [], (
        "QUICK_CONFIG reduces these fields with no slug declared in "
        "_FIELD_SLUGS — a paying caller would not be told: "
        f"{undeclared_reductions()}"
    )


def test_the_four_previously_undeclared_reductions_are_present():
    """Pins the specific defect found in production, not just the mechanism."""
    quick = limitations_for_tier("quick")

    assert "no_evidence_distillation" in quick
    assert "no_post_filter_recovery" in quick
    assert "reduced_source_cap" in quick
    assert "reduced_query_breadth" in quick


def test_declared_slugs_correspond_to_real_config_differences():
    """No slug may claim a reduction that quick mode does not actually make.

    The opposite failure to the one above, and just as dishonest: telling a
    caller we withheld something we did not.
    """
    for field, slug in _FIELD_SLUGS.items():
        assert hasattr(
            DEFAULT_CONFIG, field
        ), f"{slug} names a field that does not exist"

    declared = set(limitations_for_tier("quick"))
    for field, slug in _FIELD_SLUGS.items():
        differs = getattr(QUICK_CONFIG, field) != getattr(DEFAULT_CONFIG, field)
        assert (slug in declared) is differs, (
            f"{slug} is {'declared' if slug in declared else 'absent'} but the "
            f"config field {field} {'differs' if differs else 'matches'}"
        )


# ---------------------------------------------------------------------------
# Which tier's receipt gets attached
# ---------------------------------------------------------------------------


def test_full_tier_withholds_nothing():
    assert limitations_for_tier("full") == []


@pytest.mark.parametrize("tier", [None, "lookup", "consensus", "unknown-future-tier"])
def test_unknown_tiers_claim_nothing_rather_than_guessing(tier):
    """A wrong receipt is worse than an absent one.

    Rows written before `Check.executed_tier` existed have None, and inventing
    limitations for them would be a fabricated receipt.
    """
    assert limitations_for_tier(tier) == []


def test_slugs_are_stable_public_api():
    """The original six are part of the agent API contract — never rename.

    Callers may branch on these strings. Adding is safe; renaming silently
    breaks anyone matching on them.
    """
    for slug in (
        "heuristic_classification",
        "no_factcheck_lookup",
        "no_api_sources",
        "no_llm_relevance_scoring",
        "no_coverage_recovery",
        "no_query_answering",
    ):
        assert slug in _FIELD_SLUGS.values()
