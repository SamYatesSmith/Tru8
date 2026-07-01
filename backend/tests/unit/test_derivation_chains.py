"""Unit tests for corroboration.annotate_derivation_chains (2026-07-01).

Regression guard for the echo-detector ordering bug: derivation chains only
form when tier classification has already run (tier == "primary"). The
retrieve-time corroboration pass ran before classify, so chains never formed.
"""

from app.utils.corroboration import annotate_derivation_chains


def _item(eid, tier, domain, snippet):
    return {
        "evidence_id": eid,
        "tier": tier,
        "source": domain,
        "url": f"https://{domain}/article",
        "snippet": snippet,
    }


def test_chain_forms_for_primary_with_two_independent_rereporters():
    evs = [
        _item(
            "e1",
            "primary",
            "nature.com",
            "The 2024 eruption released 42% more energy than 2019.",
        ),
        _item(
            "e2",
            "reporting",
            "independentnews.com",
            "Scientists report the 2024 eruption released 42% more energy.",
        ),
        _item(
            "e3",
            "reporting",
            "anothernews.org",
            "A 42% energy increase was recorded in the 2024 eruption.",
        ),
    ]
    n = annotate_derivation_chains(evs)
    assert n == 1
    assert set(evs[0].get("derivation_chain", [])) == {"e2", "e3"}
    # Only the primary carries a chain.
    assert "derivation_chain" not in evs[1]
    assert "derivation_chain" not in evs[2]


def test_no_chain_when_fewer_than_two_rereporters():
    evs = [
        _item(
            "e1",
            "primary",
            "nature.com",
            "The 2024 eruption released 42% more energy than 2019.",
        ),
        _item(
            "e2",
            "reporting",
            "independentnews.com",
            "The 2024 eruption released 42% more energy.",
        ),
    ]
    assert annotate_derivation_chains(evs) == 0
    assert "derivation_chain" not in evs[0]


def test_reproduces_ordering_bug_no_tiers_no_chain():
    # This is the pre-fix state: corroboration ran before classify, so tiers
    # were unset -> no item is "primary" -> no chain can form.
    evs = [
        _item(
            "e1",
            None,
            "nature.com",
            "The 2024 eruption released 42% more energy than 2019.",
        ),
        _item(
            "e2",
            None,
            "independentnews.com",
            "The 2024 eruption released 42% more energy.",
        ),
        _item(
            "e3", None, "anothernews.org", "A 42% energy increase was recorded in 2024."
        ),
    ]
    assert annotate_derivation_chains(evs) == 0
    assert all("derivation_chain" not in e for e in evs)


def test_same_owner_as_primary_is_not_an_independent_derivative():
    # bbc.com re-reporting bbc.co.uk is the same ownership group -> not counted;
    # only the independent outlet remains -> one derivative -> no chain.
    evs = [
        _item(
            "e1",
            "primary",
            "bbc.co.uk",
            "The 2024 eruption released 42% more energy than 2019.",
        ),
        _item(
            "e2", "reporting", "bbc.com", "The 2024 eruption released 42% more energy."
        ),
        _item("e3", "reporting", "independent.co.uk", "A 42% energy increase in 2024."),
    ]
    assert annotate_derivation_chains(evs) == 0


def test_empty_and_single_item_pools():
    assert annotate_derivation_chains([]) == 0
    assert (
        annotate_derivation_chains(
            [_item("e1", "primary", "nature.com", "42% in 2024")]
        )
        == 0
    )
