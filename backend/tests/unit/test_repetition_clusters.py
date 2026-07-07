"""Unit tests for corroboration.annotate_repetition_clusters — finding F4
(2026-07-07).

Talking-point repetition: several NON-primary sources reciting the SAME
formulation with NO primary source behind them. Distinct from echo (which needs
a primary anchor) and from thin (commentary-only / single-outlet). Purely
structural detection — no score, no verdict.

The mechanical gates under test:
  - shared FORMULATION (near-verbatim sentence), not shared conclusion/number
  - ZERO primary tier in the cluster (a primary makes it echo's job)
  - spans ≥2 independent ownership groups (single outlet is already "thin")
  - ≥3 members
Plus the on-side aggregation surfaced in the element basis.
"""

from app.utils.corroboration import annotate_repetition_clusters
from app.pipeline.claim_map_analyzer import _compute_element_basis

# The talking-point sentence from the F4 trigger case (TRU-EC8D-8BC8): a long,
# distinctive formulation copy-pasted across outlets.
_SHARED = (
    "England and Wales are the only countries in the world with a fully "
    "privatised water system."
)


def _item(eid, tier, domain, snippet):
    return {
        "evidence_id": eid,
        "tier": tier,
        "source": domain,
        "url": f"https://{domain}/article",
        "snippet": snippet,
    }


def test_fires_on_shared_formulation_no_primary():
    evs = [
        _item(
            "e1",
            "reporting",
            "reporterone.com",
            f"A new report examines the sector. {_SHARED}",
        ),
        _item(
            "e2",
            "commentary",
            "commentarytwo.org",
            f"Campaigners have argued this. {_SHARED}",
        ),
        _item(
            "e3",
            "commentary",
            "thinktank.net",
            f"The think tank published today. {_SHARED}",
        ),
    ]
    assert annotate_repetition_clusters(evs) == 1
    ids = {e.get("repetition_cluster_id") for e in evs}
    assert ids == {1}  # all three in the one cluster


def test_no_cluster_when_wording_differs_same_conclusion():
    # Same conclusion, each in its own words — healthy independent reporting.
    evs = [
        _item(
            "e1",
            "reporting",
            "reporterone.com",
            "Only England and Wales sold their entire water utilities to private investors.",
        ),
        _item(
            "e2",
            "reporting",
            "papertwo.com",
            "Across Britain the water networks passed into private ownership during the eighties.",
        ),
        _item(
            "e3",
            "commentary",
            "blogthree.org",
            "Private companies took full control of drinking water supply in that jurisdiction.",
        ),
    ]
    assert annotate_repetition_clusters(evs) == 0
    assert all("repetition_cluster_id" not in e for e in evs)


def test_primary_in_cluster_excluded_as_echo():
    # A primary sharing the formulation makes this syndication-from-primary
    # (echo's territory) — F4 must not also fire on it.
    evs = [
        _item("e1", "primary", "gov.example", f"Official record. {_SHARED}"),
        _item("e2", "reporting", "reporterone.com", f"As reported. {_SHARED}"),
        _item("e3", "commentary", "commentarytwo.org", f"Commentators note. {_SHARED}"),
    ]
    assert annotate_repetition_clusters(evs) == 0
    assert all("repetition_cluster_id" not in e for e in evs)


def test_single_ownership_group_is_not_repetition():
    # Same formulation but all from one outlet -> one ownership group -> that is
    # "single-outlet thin", not unanchored breadth.
    evs = [
        _item("e1", "reporting", "onesite.com", f"Piece one. {_SHARED}"),
        _item("e2", "reporting", "onesite.com", f"Piece two. {_SHARED}"),
        _item("e3", "commentary", "onesite.com", f"Piece three. {_SHARED}"),
    ]
    assert annotate_repetition_clusters(evs) == 0


def test_below_min_cluster_size():
    evs = [
        _item("e1", "reporting", "reporterone.com", f"Intro one. {_SHARED}"),
        _item("e2", "commentary", "commentarytwo.org", f"Intro two. {_SHARED}"),
    ]
    assert annotate_repetition_clusters(evs) == 0


def test_short_boilerplate_does_not_match():
    # The only text three items literally share is a short line; long content
    # differs. Short sentences are dropped, so nothing matches.
    evs = [
        _item(
            "e1",
            "reporting",
            "reporterone.com",
            "Read more. Water reform in the north followed a decade of underinvestment.",
        ),
        _item(
            "e2",
            "commentary",
            "commentarytwo.org",
            "Read more. The pricing regulator has faced criticism from several directions.",
        ),
        _item(
            "e3",
            "commentary",
            "thinktank.net",
            "Read more. Household bills rose sharply after the ownership change took effect.",
        ),
    ]
    assert annotate_repetition_clusters(evs) == 0


def test_empty_and_small_pools():
    assert annotate_repetition_clusters([]) == 0
    assert (
        annotate_repetition_clusters([_item("e1", "reporting", "a.com", _SHARED)]) == 0
    )
    assert (
        annotate_repetition_clusters(
            [
                _item("e1", "reporting", "a.com", _SHARED),
                _item("e2", "commentary", "b.com", _SHARED),
            ]
        )
        == 0
    )


def test_basis_surfaces_repetition_on_the_side():
    # Post-annotation, the on-side aggregation reports the dominant cluster.
    evs = [
        _item("e1", "reporting", "reporterone.com", _SHARED),
        _item("e2", "commentary", "commentarytwo.org", _SHARED),
        _item("e3", "commentary", "thinktank.net", _SHARED),
    ]
    annotate_repetition_clusters(evs)
    element = {
        "element_id": "el1",
        "evidence_refs": [
            {"evidence_id": "e1", "relationship": "supports"},
            {"evidence_id": "e2", "relationship": "supports"},
            {"evidence_id": "e3", "relationship": "supports"},
        ],
    }
    basis = _compute_element_basis(element, evs)
    rep = basis["support_structure"]["repetition"]
    assert rep["max_cluster_on_side"] == 3
    assert rep["distinct_domains"] == 3
    # Challenge side is empty -> zeroed, never absent.
    assert basis["challenge_structure"]["repetition"] == {
        "max_cluster_on_side": 0,
        "distinct_domains": 0,
    }
