"""The figure scope gate (F2, 2026-09-23) through the real mapping parser.

A SUPPORT must state the element's figure; a sum or difference the mapper did is
not something the source said. Fixtures are the known-truth failures verbatim in
substance: Legum (summed part-period ranges), Kennedy (an 83% norm derived from
"68%, 16 points below"). Silence never fires. Supports only — the TTE case pins
that a challenge restating the figure is untouched.
Design: audit/2026-09-23_figure_scope_gate_design.md.
"""

import pytest

from app.core.config import settings
from app.pipeline.claim_map_analyzer import (
    _SCOPE_RECEIPT_KEYS,
    ClaimMapAnalyzer,
    _index_evidence,
)
from app.utils.figure_scope import (
    element_figures,
    is_unstated_figure,
    stated_figures,
)

LEGUM_ELEMENT = (
    "The total value of these securities trades is between $898 million and "
    "$2.87 billion since 2025."
)
KENNEDY_ELEMENT = (
    "The seasonal norm for EU-wide gas storage stocks as of 11 September is 83% full."
)

EVIDENCE = [
    {
        "evidence_id": "ev-bloomberg",
        "url": "https://www.bloomberg.com/news/articles/2026-07-02/trump-trades",
        "title": "Trump's 2025 trades",
        "snippet": "The total dollar value of the 2025 trades was between $600 million "
        "and $1.86 billion.",
        "tier": "reporting",
    },
    {
        "evidence_id": "ev-euronews",
        "url": "https://www.euronews.com/business/2026/05/15/trump",
        "title": "Q1 trades",
        "snippet": "Trades in the first quarter of 2026 were worth between $220m and $750m.",
        "tier": "reporting",
    },
    {
        "evidence_id": "ev-states-it",
        "url": "https://news.example/total",
        "title": "Totals",
        "snippet": "Since 2025 the trades total between $898 million and $2.87 billion.",
        "tier": "reporting",
    },
    {
        "evidence_id": "ev-silent",
        "url": "https://news.example/silent",
        "title": "Trading volume",
        "snippet": "The president's accounts traded heavily through 2025 and 2026.",
        "tier": "commentary",
    },
    {
        "evidence_id": "ev-in-passage",
        "url": "https://news.example/passage",
        "title": "Long read",
        "snippet": "The accounts made a record number of trades, worth $600 million.",
        "tier": "reporting",
        "text_provenance": {
            "passages": [
                {"text": "Across both years the value came to $898 million at least."}
            ]
        },
    },
]


def _claim_map(description=LEGUM_ELEMENT):
    return {
        "claim_id": "0",
        "normalised_claim": "Donald Trump has made trades worth $898 million to "
        "$2.87 billion since 2025.",
        "elements": [
            {
                "element_id": "e1",
                "description": description,
                "evidence_refs": [],
                "state": None,
            }
        ],
        "metadata": {},
    }


def _parse(rels, description=LEGUM_ELEMENT, evidence=EVIDENCE):
    """`rels` items are (evidence_id, relationship) or (..., reasoning).

    The default reasoning paraphrases the item's snippet, as the mapper does —
    so it cites the source's figures, which is what arms the gate.
    """
    snippets = {e["evidence_id"]: e.get("snippet", "") for e in evidence}
    analyzer = ClaimMapAnalyzer()
    cm = _claim_map(description)
    analyzer._parse_mapping_response(
        {
            "elements": [
                {
                    "element_id": "e1",
                    "state": "supported",
                    "evidence_refs": [
                        {
                            "evidence_id": rel[0],
                            "relationship": rel[1],
                            "reasoning": (
                                rel[2]
                                if len(rel) > 2
                                else f"Reports: {snippets[rel[0]]}"
                            ),
                        }
                        for rel in rels
                    ],
                }
            ]
        },
        cm,
        evidence,
    )
    return cm["elements"][0]


def _rel(elem, eid):
    for ref in elem["evidence_refs"]:
        if ref["evidence_id"] == eid:
            return getattr(ref["relationship"], "value", ref["relationship"])
    raise AssertionError(eid)


# ── parser ────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "text,expected",
    [
        ("stocks are 67% full", [("pct", 67.0)]),
        ("around 68 per cent", [("pct", 68.0)]),
        ("16 percentage points below", []),
        ("$898 million and $2.87 billion", [("cur$", 898e6), ("cur$", 2.87e9)]),
        ("a £36m donation", [("cur£", 36e6)]),
        ("28,700 securities trades", [("n:securitie", 28700.0), ("n:trade", 28700.0)]),
        ("as of 11 September 2026", []),
        ("since 1933", []),
        ("CO2 concentrations", []),
    ],
)
def test_stated_figures(text, expected):
    assert [(f.kind, f.value) for f in stated_figures(text)] == expected


def test_precision_rounding_only_for_grouped_or_multiplied_figures():
    el = element_figures("The norm is 83% full.")
    assert is_unstated_figure(el, "Storage is 80% full.")  # 80 is eighty, not 75–85
    el = element_figures("almost 28,700 trades")
    assert not is_unstated_figure(el, "nearly 29,000 trades")  # rounded to thousands
    el = element_figures("exactly 3,301 bees")
    assert is_unstated_figure(el, "3,300 bees")  # 'exactly' refuses source rounding


def test_approximation_widens_to_five_percent():
    el = element_figures("about 40% of the budget")
    assert not is_unstated_figure(el, "38% of the budget")
    assert is_unstated_figure(element_figures("40% of the budget"), "38% of the budget")


@pytest.mark.parametrize(
    "description",
    [
        "Unemployment fell below 5%",
        "Economic growth exceeded 2%",
        "Inflation stayed under 3%",
        "Trump made more than 20,000 trades",
        "Donors gave at least £10m",
    ],
)
def test_a_threshold_is_not_a_point_figure(description):
    """'Below 5%' is supported by 4.2% — a bound never arms the gate. Caught by
    the coverage-recovery fixture on the first full run (2026-09-23)."""
    assert element_figures(description) is None


def test_silence_and_other_kinds_never_fire():
    el = element_figures(KENNEDY_ELEMENT)
    assert not is_unstated_figure(el, "Storage is at a record low.")
    assert not is_unstated_figure(el, "Prices rose by $4 per megawatt hour.")


def test_any_figure_matching_satisfies_a_multi_figure_element():
    el = element_figures("a loss of £22 million rather than the £53 million forecast")
    assert not is_unstated_figure(el, "The rate raised £22m.")


# ── gate ──────────────────────────────────────────────────────────────────


def test_summed_part_periods_become_context_and_the_stated_figure_stays():
    elem = _parse(
        [
            ("ev-bloomberg", "supports"),
            ("ev-euronews", "supports"),
            ("ev-states-it", "supports"),
            ("ev-silent", "supports"),
        ]
    )
    assert _rel(elem, "ev-bloomberg") == "context"
    assert _rel(elem, "ev-euronews") == "context"
    assert _rel(elem, "ev-states-it") == "supports"
    assert _rel(elem, "ev-silent") == "supports"  # silence is the mapper's call
    entry = next(
        e
        for e in elem["basis"]["figure_scope"]["scoped"]
        if e["evidence_id"] == "ev-bloomberg"
    )
    assert entry["was"] == "supports" and entry["rule"] == "not_stated"
    assert entry["element_figures"] == ["$2,870,000,000", "$898,000,000"]
    assert entry["source_figures"] == ["$1,860,000,000", "$600,000,000"]


def test_a_norm_derived_from_a_points_gap_becomes_context():
    """Kennedy 54b8699b: euractiv states 62% and '15 percentage points below the
    10-year average'; the mapper filed it as supporting an 83% norm. The reasoning
    names a gap, not a percentage — it still rests on a number."""
    evidence = [
        {
            "evidence_id": "ev-euractiv",
            "url": "https://www.euractiv.com/news/historic-low-storage-levels/",
            "title": "Historic low storage levels are not a gas supply crisis",
            "snippet": "Across Europe, gas storage levels stand at around 62% – 15 "
            "percentage points below the 10-year average.",
            "tier": "reporting",
        }
    ]
    ref = (
        "ev-euractiv",
        "supports",
        "Reports levels are 15 percentage points below the 10-year average.",
    )
    elem = _parse([ref], description=KENNEDY_ELEMENT, evidence=evidence)
    assert _rel(elem, "ev-euractiv") == "context"


def test_a_support_resting_on_the_cause_not_the_number_is_untouched():
    """TRU-B4A3-C42D: "the mini-budget caused 30-year gilt yields to spike to 5.1%".
    A source confirming the CAUSE, whose reasoning names no figure, is not claiming
    the number — the bench caught the first build scoping it (2026-09-23)."""
    evidence = [
        {
            "evidence_id": "ev-boe",
            "url": "https://www.bankofengland.co.uk/financial-stability-report/2022",
            "title": "Financial Stability Report",
            "snippet": "Long-dated gilt yields rose by over 100 basis points; "
            "30-year nominal rates reached 4.5% in intraday trading.",
            "tier": "primary",
        }
    ]
    description = (
        "Liz Truss's mini-budget on 23 September 2022 caused 30-year UK gilt yields "
        "to spike to 5.1%."
    )
    cause = (
        "ev-boe",
        "supports",
        "Confirms the sharp rise in 30-year nominal gilt rates was triggered by the "
        "mini-budget.",
    )
    assert _rel(_parse([cause], description, evidence), "ev-boe") == "supports"
    number = ("ev-boe", "supports", "Reports 30-year rates reached 4.5%.")
    assert _rel(_parse([number], description, evidence), "ev-boe") == "context"


def test_a_figure_in_a_retained_passage_is_stated():
    elem = _parse([("ev-in-passage", "supports")])
    assert _rel(elem, "ev-in-passage") == "supports"


def test_kennedy_derived_norm_becomes_context():
    evidence = [
        {
            "evidence_id": "ev-eutoday",
            "url": "https://eutoday.net/europe-gas-storage-record-low/",
            "title": "Gas storage at record low",
            "snippet": "Other market estimates put inventories at around 68 per cent, "
            "approximately 16 percentage points below the five-year average.",
            "tier": "reporting",
        }
    ]
    elem = _parse(
        [("ev-eutoday", "supports")], description=KENNEDY_ELEMENT, evidence=evidence
    )
    assert _rel(elem, "ev-eutoday") == "context"


def test_supports_only_a_challenge_restating_the_figure_is_untouched():
    """Trust the Evidence restates the NHS triage 29% to dispute what caused it.
    The mirror rule would strip exactly this rebuttal (4 fires, 4 wrong)."""
    evidence = [
        {
            "evidence_id": "ev-tte",
            "url": "https://trusttheevidence.substack.com/p/the-miracle",
            "title": "The miracle cure",
            "snippet": "The 29% fall began before the app launched; the trend does not "
            "show the app caused it.",
            "tier": "commentary",
        },
        {
            "evidence_id": "ev-other-figure",
            "url": "https://news.example/other",
            "title": "Queues",
            "snippet": "Queues fell by 12%.",
            "tier": "reporting",
        },
    ]
    elem = _parse(
        [("ev-tte", "challenges"), ("ev-other-figure", "challenges")],
        description="AI triage through the NHS App caused a 29% reduction in queues.",
        evidence=evidence,
    )
    assert _rel(elem, "ev-tte") == "challenges"
    assert _rel(elem, "ev-other-figure") == "challenges"


def test_flag_off_key_registered_and_order(monkeypatch):
    assert "figure_scope" in _SCOPE_RECEIPT_KEYS
    assert _SCOPE_RECEIPT_KEYS[-1] == "echo_scope"
    gates = ClaimMapAnalyzer()._armed_scope_gates(
        _claim_map()["elements"][0], _claim_map(), _index_evidence(EVIDENCE)
    )
    keys = [g.key for g in gates]
    assert keys.index("figure_scope") < keys.index("echo_scope")
    if "date_scope" in keys:
        assert keys.index("date_scope") < keys.index("figure_scope")
    monkeypatch.setattr(settings, "ENABLE_FIGURE_SCOPE_GATE", False)
    elem = _parse([("ev-bloomberg", "supports")])
    assert _rel(elem, "ev-bloomberg") == "supports"


def test_an_element_without_figures_does_not_arm_the_gate():
    cm = _claim_map("The Letby inquiry recommended a statutory barring system.")
    gates = ClaimMapAnalyzer()._armed_scope_gates(
        cm["elements"][0], cm, _index_evidence(EVIDENCE)
    )
    assert "figure_scope" not in [g.key for g in gates]


# ── sentence-level period (2026-09-23, Kennedy 16133434) ─────────────────


# The live page also names September 2026 (its update line), which is why the
# whole-item temporal gate stayed silent and this sentence-level rule is needed.
GEF_TEXT = (
    "Updated 13 September 2026. The EU gas storage level sits at about 68.04% of working capacity as of "
    "August 20, 2026. How to read this chart The blue line is where storage "
    "actually went: it started the season near 83% on November 1, 2025, fell "
    "steadily through the heating months. - According to global-energy-flow.com, "
    "the norm for this date is about 82%, per EnergyRiskIQ."
)
KENNEDY_NORM = (
    "As of 11 September 2026, the seasonal norm for EU-wide gas storage stocks is 83% full."
)


def test_82_does_not_state_83():
    """The rounding ranges touch at 82.5; touching is not matching."""
    el = element_figures("The norm is 83% full.")
    assert is_unstated_figure(el, "the norm for this date is about 82%")


def test_a_matching_figure_only_in_another_periods_sentence_is_not_stated():
    from app.utils.figure_scope import unstated_reason
    from app.utils.temporal_scope import element_period

    el = element_figures(KENNEDY_NORM)
    period = element_period(KENNEDY_NORM)
    assert unstated_reason(el, GEF_TEXT, period) == "other_period"
    # Without a pinned period the rule cannot arm: the figure is on the page.
    assert unstated_reason(el, GEF_TEXT, None) is None


@pytest.mark.parametrize(
    "sentence",
    [
        "Storage is well below the historical average of 83% in early September.",
        "The five-year norm for September 2026 is 83%.",
        "In 2026 the seasonal norm stands at 83%.",
    ],
)
def test_an_undated_or_same_period_sentence_keeps_the_figure(sentence):
    from app.utils.figure_scope import unstated_reason
    from app.utils.temporal_scope import element_period

    el = element_figures(KENNEDY_NORM)
    assert unstated_reason(el, sentence, element_period(KENNEDY_NORM)) is None


def test_gate_scopes_the_other_period_support_with_its_reason():
    evidence = [
        {
            "evidence_id": "ev-gef",
            "url": "https://global-energy-flow.com/storage/trajectory/",
            "title": "EU Gas Storage Level 2026",
            "snippet": GEF_TEXT,
            "tier": "primary",
        }
    ]
    ref = (
        "ev-gef",
        "supports",
        "Notes the 5-year seasonal norm around mid-September is approximately 82% to 83%.",
    )
    elem = _parse([ref], description=KENNEDY_NORM, evidence=evidence)
    assert _rel(elem, "ev-gef") == "context"
    entry = elem["basis"]["figure_scope"]["scoped"][0]
    assert entry["rule"] == "other_period"
    assert entry["element_period"] == "2026-09"


# ── count named by a "number of" phrase (2026-09-23, Legum 06ef2b65) ──────


LEGUM_COUNT = "The number of securities trades made by Donald Trump since 2025 is almost 28,700."


def test_a_number_of_phrase_names_what_a_bare_count_counts():
    el = element_figures(LEGUM_COUNT)
    assert el is not None and el.approximate
    assert {f.kind for f in el.figures} == {"n:securitie", "n:trade"}
    assert {f.value for f in el.figures} == {28700.0}


@pytest.mark.parametrize(
    "source,unstated",
    [
        ("Financial disclosures reveal over 17,000 stock trades.", True),
        ("advisers made more than 21,000 securities trades in 2025", True),
        ("nearly 29000 securities trades in 17 months", False),
        ("roughly 28,700 trades over 17 months", False),
    ],
)
def test_part_period_counts_do_not_state_the_total(source, unstated):
    assert is_unstated_figure(element_figures(LEGUM_COUNT), source) is unstated


def test_without_a_number_of_phrase_a_bare_number_arms_nothing():
    assert element_figures("Version 3.22.0 was released on January 22, 2018.") is None
    assert element_figures("The mission launched in 1984.") is None
