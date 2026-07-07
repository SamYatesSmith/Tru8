"""F3 scope-sensitivity tagger tests (2026-07-07).

Design: audit/2026-07-07_f3_design_review.md §3.1. The tagger is the mechanical,
NF-11-safe detection layer under F3 — it flags elements whose wording is
scope-sensitive (composite geography / universal quantifier) so the Phase-B
response can attach a descriptive caveat. These tests pin BOTH halves that
matter: the flagship shapes fire, and the false-positive controls stay silent
(a scope tool that cries wolf is worse than none — design §4).
"""

import pytest

from app.utils.scope_sensitivity import (
    apply_scope_flags,
    detect_scope_flags,
)


# ── Geographic composites fire ───────────────────────────────────────────────


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Britain has a privatised water system", "britain"),
        ("British water companies are privatised", "british"),
        ("The United Kingdom privatised its railways", "united kingdom"),
        ("UK inflation rose last month", "uk"),
        ("Only European countries contributed to the LHC", "european"),
        ("Europe has a single market", "europe"),
        ("The European Union sets the tariff", "european union"),
        ("America has the largest economy", "america"),
        ("The United States landed people on the Moon", "united states"),
        ("Scandinavia has high union density", "scandinavia"),
        ("The British Isles share a landmass", "british isles"),
    ],
)
def test_geographic_composites_flagged(text, expected):
    assert expected in detect_scope_flags(text)["geographic"]


# ── Universal / absolute quantifiers fire ────────────────────────────────────


@pytest.mark.parametrize(
    "text,expected_any",
    [
        (
            "Britain is the only country in the world with privatised water",
            {"the only", "only country", "in the world", "only <scope-noun>"},
        ),
        (
            "The US remains the only country to have landed on the Moon",
            {"the only", "only country", "only <scope-noun>"},
        ),
        ("Only European countries contributed to the collider", {"only <scope-noun>"}),
        ("No other nation has achieved this", {"no other"}),
        ("It was the first country to legalise it", {"first country", "first to"}),
        ("This is the sole surviving example", {"sole"}),
        ("The vaccine is unique among approved treatments", {"unique"}),
        ("It is used worldwide", {"worldwide"}),
        ("Every country signed the treaty", {"every country"}),
    ],
)
def test_universal_quantifiers_flagged(text, expected_any):
    got = set(detect_scope_flags(text)["universal"])
    assert got & expected_any, f"expected one of {expected_any}, got {got}"


# ── False-positive controls stay SILENT (the number that matters) ────────────


@pytest.mark.parametrize(
    "text",
    [
        "The company only reported 3% growth in the first quarter",  # only/first ≠ universal
        "It rained all day and the shop was open only briefly",  # all day / only briefly
        "France generates most of its electricity from nuclear power",  # non-composite place
        "Germany and Japan rebuilt their economies",  # non-composite places
        "Water bills rose by 40% last year",  # plain empirical
        "The bridge is the fastest way across the river",  # 'way', not 'only'
        "Unemployment fell in the last three months",  # 'last' but not 'last country'
    ],
)
def test_false_positive_controls_silent(text):
    flags = detect_scope_flags(text)
    assert flags["geographic"] == []
    assert flags["universal"] == []


def test_bare_only_and_first_do_not_fire():
    """Bare 'only'/'first' are deliberately excluded (design §3.1)."""
    assert detect_scope_flags("only 3% of firms")["universal"] == []
    assert detect_scope_flags("in the first quarter of 2024")["universal"] == []


@pytest.mark.parametrize(
    "text",
    [
        "only when countries cooperate on climate can it work",  # conditional
        "only a few countries attended the summit",  # partitive "merely N"
        "only some nations ratified the treaty",  # partitive
        "only most countries agreed to the terms",  # partitive
        "the only way forward is reform",  # rhetorical
        "there is only one way to do this",  # rhetorical
    ],
)
def test_only_scope_noun_regex_rejects_non_universal_filler(text):
    """The 'only <scope-noun>' shape must NOT fire when the filler is a
    determiner/partitive/conjunction — that's the 'merely N' / conditional
    reading (F3 Phase A adversarial review, 2026-07-07). The earlier loose
    ``\\w+{0,2}`` filler admitted all of these."""
    assert detect_scope_flags(text)["universal"] == []


def test_only_scope_noun_regex_still_fires_on_bounded_universals():
    """Adjective / number filler between 'only' and the scope-noun must still
    fire ('only European countries', 'only two nations', 'only country')."""
    assert (
        "only <scope-noun>"
        in detect_scope_flags("only European countries")["universal"]
    )
    assert (
        "only <scope-noun>"
        in detect_scope_flags("only two nations signed")["universal"]
    )
    assert (
        "only <scope-noun>"
        in detect_scope_flags("it is the only country to")["universal"]
    )


def test_word_boundary_no_substring_hits():
    """'uk' must not match inside 'duke'; geographic stays empty."""
    assert detect_scope_flags("The Duke of Edinburgh visited")["geographic"] == []
    assert detect_scope_flags("A ukulele festival")["geographic"] == []


# ── Determinism + shape ──────────────────────────────────────────────────────


def test_output_is_sorted_and_deduped():
    flags = detect_scope_flags("Britain, Britain, and British interests")
    assert flags["geographic"] == sorted(set(flags["geographic"]))
    # 'britain' appears twice in text but once in output
    assert flags["geographic"].count("britain") == 1


@pytest.mark.parametrize("bad", [None, "", 123, [], {}])
def test_non_string_input_returns_empty(bad):
    flags = detect_scope_flags(bad)
    assert flags == {"geographic": [], "universal": []}


def test_multiword_matches_across_whitespace_runs():
    """Collapsed whitespace lets phrases span newlines/double spaces."""
    assert "in the world" in detect_scope_flags("only one in  the\n world")["universal"]


# ── apply_scope_flags (the in-place mutator wired into decompose) ─────────────


def test_apply_sets_field_only_when_flagged():
    els = [
        {"element_id": "e1", "description": "Britain is the only country in the world"},
        {"element_id": "e2", "description": "Water bills rose 40% last year"},
    ]
    n = apply_scope_flags(els)
    assert n == 1
    assert "scope_flags" in els[0]
    assert els[0]["scope_flags"]["geographic"] == ["britain"]
    assert "scope_flags" not in els[1]  # lean records: absent = not sensitive


def test_apply_is_idempotent():
    els = [{"element_id": "e1", "description": "Only European countries did"}]
    apply_scope_flags(els)
    first = dict(els[0]["scope_flags"])
    apply_scope_flags(els)  # re-run
    assert els[0]["scope_flags"] == first  # overwrites, no accumulation


def test_apply_handles_missing_and_empty_descriptions():
    els = [
        {"element_id": "e1"},  # no description key
        {"element_id": "e2", "description": ""},
        {"element_id": "e3", "description": None},
    ]
    assert apply_scope_flags(els) == 0
    assert all("scope_flags" not in e for e in els)


def test_apply_handles_empty_and_none_list():
    assert apply_scope_flags([]) == 0
    assert apply_scope_flags(None) == 0


# ── Flagship end-to-end shapes (the cases that motivated F3) ──────────────────


def test_flagship_water_claim():
    f = detect_scope_flags(
        "England and Wales are the only countries in the world "
        "with a fully privatised water system"
    )
    assert "the only" in f["universal"] or "only <scope-noun>" in f["universal"]
    assert "in the world" in f["universal"]


def test_flagship_lhc_claim_geographic_and_universal():
    f = detect_scope_flags(
        "Only European countries contributed to building the Large Hadron Collider"
    )
    assert "european" in f["geographic"]
    assert "only <scope-noun>" in f["universal"]
