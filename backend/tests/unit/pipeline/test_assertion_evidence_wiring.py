"""The 2026-08-13 gates through the real mapping parser — not the taggers alone.

Reconstructs production check TRU-018F-44AA: "Donald Trump stopped 6 wars"
returned "predominantly supports all 4" — the claimant's own press office
(primary, weight 3) plus press RECITALS of the claim outweighed PolitiFact's
"Pants on Fire" at commentary weight 1. Every reasoning string below is
verbatim from that check.

"Test the wired seam" is a standing lesson here: the gates depend on
`claim_map["metadata"]["subjects"]`, written by `runner.attach_claim_subjects`,
so the writer is pinned here too.
"""

import pytest

from app.pipeline.claim_map_analyzer import ClaimMapAnalyzer
from app.pipeline.runner import attach_claim_subjects

ELEMENT_TEXT = (
    "Donald Trump took actions that directly led to the cessation of "
    "hostilities in six specific wars."
)

EVIDENCE = [
    {
        # The claimant's own press office — interested party.
        "evidence_id": "ev-wh-solved",
        "url": "https://www.whitehouse.gov/videos/president-trump-ive-solved/",
        "title": 'President Trump: "I\'ve solved six wars in six months"',
        "snippet": 'President Trump: "I\'ve solved six wars in six months".',
        "tier": "primary",
        "evidence_type": "official",
    },
    {
        # Press RECITAL of the claim — mapped `supports` in production.
        "evidence_id": "ev-cbs",
        "url": "https://www.cbsnews.com/news/trump-ended-6-or-7-wars-what-record-shows/",
        "title": "Trump says he's ended 6 or 7 wars.",
        "snippet": "President Trump has repeatedly claimed credit for ending six or seven wars.",
        "tier": "reporting",
        "evidence_type": "news",
    },
    {
        # The professional refutation — must survive untouched.
        "evidence_id": "ev-politifact",
        "url": "https://politifact.com/factchecks/2025/oct/17/donald-trump/",
        "title": "No, Donald Trump isn't the first US president to solve a war",
        "snippet": "Fact-check rating: Pants on Fire",
        "tier": "commentary",
        "evidence_type": "opinion",
    },
    {
        # A congressman ENDORSING — aligned, not controlled; must survive.
        "evidence_id": "ev-davidson",
        "url": "https://davidson.house.gov/2019/10/trump-right-ending-endless-wars/",
        "title": "Trump is Right: Ending the Endless Wars Starts in Syria",
        "snippet": "President Donald Trump's withdrawal of forces from Syria is appropriate and long overdue.",
        "tier": "primary",
        "evidence_type": "official",
    },
]


def _claim_map(subjects=("donald trump",)):
    return {
        "claim_id": "0",
        "normalised_claim": "Donald Trump stopped six wars.",
        "elements": [
            {
                "element_id": "e3",
                "description": ELEMENT_TEXT,
                "evidence_refs": [],
                "state": None,
            }
        ],
        "metadata": {"jurisdiction": "US", "subjects": list(subjects)},
    }


def _mapping_response():
    """What the mapper returned in production, reasoning verbatim."""
    return {
        "elements": [
            {
                "element_id": "e3",
                "state": "supported",
                "evidence_refs": [
                    {
                        "evidence_id": "ev-wh-solved",
                        "relationship": "supports",
                        "reasoning": (
                            "This official statement directly quotes President "
                            "Trump saying, 'I've solved six wars in six months'."
                        ),
                    },
                    {
                        "evidence_id": "ev-cbs",
                        "relationship": "supports",
                        "reasoning": (
                            "This news report states Trump claimed to have "
                            "'settled six wars' and lists seven conflicts."
                        ),
                    },
                    {
                        "evidence_id": "ev-politifact",
                        "relationship": "challenges",
                        "reasoning": (
                            "This opinion piece, rated 'Pants on Fire', directly "
                            "challenges the idea that Trump's war-ending claims "
                            "are accurate."
                        ),
                    },
                    {
                        "evidence_id": "ev-davidson",
                        "relationship": "supports",
                        "reasoning": (
                            "This official statement supports the idea that "
                            "Trump took actions to end wars by highlighting his "
                            "withdrawal of forces from Syria."
                        ),
                    },
                ],
            }
        ]
    }


def _parse(subjects=("donald trump",), response=None):
    analyzer = ClaimMapAnalyzer()
    claim_map = _claim_map(subjects)
    analyzer._parse_mapping_response(
        response or _mapping_response(), claim_map, EVIDENCE
    )
    return claim_map["elements"][0]


def _rel(elem, evidence_id):
    for ref in elem["evidence_refs"]:
        if ref["evidence_id"] == evidence_id:
            return getattr(ref["relationship"], "value", ref["relationship"])
    raise AssertionError(f"{evidence_id} missing from refs")


# ---------------------------------------------------------------------------
# The production failure, pinned
# ---------------------------------------------------------------------------


def test_the_claimants_own_press_office_no_longer_supports():
    assert _rel(_parse(), "ev-wh-solved") == "context"


def test_a_press_recital_of_the_claim_no_longer_supports():
    assert _rel(_parse(), "ev-cbs") == "context"


def test_the_professional_refutation_survives():
    assert _rel(_parse(), "ev-politifact") == "challenges"


def test_an_endorsement_survives():
    """Aligned is not controlled, and endorsement is not recital."""
    assert _rel(_parse(), "ev-davidson") == "supports"


def test_nothing_is_deleted():
    assert len(_parse()["evidence_refs"]) == len(EVIDENCE)


# ---------------------------------------------------------------------------
# Receipts — invariant #5 — and gate ownership (one gate, one receipt)
# ---------------------------------------------------------------------------


def test_the_interested_party_owns_the_white_house_ref():
    """Both new gates would fire on ev-wh-solved; the domain signal is the less
    ambiguous one, so interested-party runs first and owns the reference. If
    this ever flips, the `break` in _apply_scope_gates or the gate order has
    been broken — both are behaviour, not taste."""
    basis = _parse()["basis"]
    ip_ids = [e["evidence_id"] for e in basis["interested_party"]["scoped"]]
    assert "ev-wh-solved" in ip_ids
    recital_ids = [
        e["evidence_id"] for e in basis.get("recital_scope", {}).get("scoped", [])
    ]
    assert "ev-wh-solved" not in recital_ids


def test_the_recital_receipt_names_its_evidence_and_marker():
    receipt = _parse()["basis"]["recital_scope"]
    entry = next(e for e in receipt["scoped"] if e["evidence_id"] == "ev-cbs")
    assert entry["was"] == "supports"
    assert entry["found_in"] == "reasoning"
    assert "claim" in entry["marker"]


def test_the_interested_party_receipt_names_the_domain():
    receipt = _parse()["basis"]["interested_party"]
    entry = next(e for e in receipt["scoped"] if e["evidence_id"] == "ev-wh-solved")
    assert entry["was"] == "supports"
    assert "whitehouse.gov" in entry["domain"]
    assert entry["subject_matched"] == "donald trump"


# ---------------------------------------------------------------------------
# Symmetry — the property that stops this being a sycophancy dial
# ---------------------------------------------------------------------------


def test_a_self_serving_DENIAL_is_scoped_just_as_readily():
    """If this is ever relaxed so only supports are scoped, the gate becomes a
    mechanism that can only make claims look better supported — invariant #7
    forbids distortion in either direction."""
    response = _mapping_response()
    for ref in response["elements"][0]["evidence_refs"]:
        if ref["evidence_id"] == "ev-wh-solved":
            ref["relationship"] = "challenges"

    elem = _parse(response=response)

    assert _rel(elem, "ev-wh-solved") == "context"
    entry = next(
        e
        for e in elem["basis"]["interested_party"]["scoped"]
        if e["evidence_id"] == "ev-wh-solved"
    )
    assert entry["was"] == "challenges"


# ---------------------------------------------------------------------------
# Safe directions and rollback
# ---------------------------------------------------------------------------


def test_no_subjects_no_gates():
    elem = _parse(subjects=())
    assert _rel(elem, "ev-wh-solved") == "supports"
    assert _rel(elem, "ev-cbs") == "supports"
    assert "interested_party" not in elem["basis"]
    assert "recital_scope" not in elem["basis"]


def test_an_attribution_shaped_element_disarms_the_recital_gate():
    """An element asserting a SAYING is legitimately supported by a report of
    the saying. The interested-party gate still applies — control of the outlet
    is a property of the source, not of the element's shape."""
    analyzer = ClaimMapAnalyzer()
    claim_map = _claim_map()
    claim_map["elements"][0][
        "description"
    ] = "Donald Trump stated that six wars had ended."
    analyzer._parse_mapping_response(_mapping_response(), claim_map, EVIDENCE)
    elem = claim_map["elements"][0]
    assert _rel(elem, "ev-cbs") == "supports"  # recital gate disarmed
    assert _rel(elem, "ev-wh-solved") == "context"  # interested party still on


def test_flags_off_restore_the_old_behaviour(monkeypatch):
    from app.core import config

    monkeypatch.setattr(config.settings, "ENABLE_INTERESTED_PARTY_GATE", False)
    monkeypatch.setattr(config.settings, "ENABLE_RECITAL_SCOPE_GATE", False)

    elem = _parse()
    assert _rel(elem, "ev-wh-solved") == "supports"
    assert _rel(elem, "ev-cbs") == "supports"


def test_the_recital_gate_catches_the_white_house_independently(monkeypatch):
    """Defence in depth: with interested-party off, the White House quote is
    still a recital ("quotes President Trump saying") and must not support."""
    from app.core import config

    monkeypatch.setattr(config.settings, "ENABLE_INTERESTED_PARTY_GATE", False)

    elem = _parse()
    assert _rel(elem, "ev-wh-solved") == "context"
    recital_ids = [e["evidence_id"] for e in elem["basis"]["recital_scope"]["scoped"]]
    assert "ev-wh-solved" in recital_ids


# ---------------------------------------------------------------------------
# The writer side of the seam — runner.attach_claim_subjects
# ---------------------------------------------------------------------------


def test_the_runner_writes_the_subjects_the_gates_read():
    claim = {
        "key_entities": [
            {"text": "Donald Trump", "type": "PERSON"},
            {"text": "Iran War", "type": "EVENT"},
        ]
    }
    claim_map = {}
    written = attach_claim_subjects(claim, claim_map)
    assert written == ["donald trump"]
    assert claim_map["metadata"]["subjects"] == ["donald trump"]


def test_the_runner_writes_an_empty_list_when_there_are_no_entities():
    """The key must EXIST even when empty — a reader whose key nobody writes is
    the failure that hid in retrieve.py for months."""
    claim_map = {}
    assert attach_claim_subjects({}, claim_map) == []
    assert claim_map["metadata"]["subjects"] == []


# ---------------------------------------------------------------------------
# Phase C (2026-08-17): the extract-stage claimant joins the subject set
# ---------------------------------------------------------------------------
# The NHS outreach record's blind spot: "NHS England" was typed
# PRODUCT-adjacent in key_entities, subjects came out ["gp practices"], and
# both gates were structurally silent. Entity TYPING must not decide
# attribution — the claimant field does.


def test_the_claimant_arms_the_gates_even_when_entity_typing_missed_it():
    claim = {
        "key_entities": [{"text": "GP practices", "type": "PRODUCT"}],
        "claimant": "NHS England",
    }
    claim_map = {}
    written = attach_claim_subjects(claim, claim_map)
    assert written == ["nhs england"]


def test_a_claimant_that_is_also_a_typed_entity_appears_once():
    claim = {
        "key_entities": [{"text": "Donald Trump", "type": "PERSON"}],
        "claimant": "Donald Trump",
    }
    assert attach_claim_subjects(claim, {}) == ["donald trump"]


def test_a_blank_or_missing_claimant_changes_nothing():
    """None/whitespace must not arm the gates — an unattributed claim's safe
    direction is silence."""
    assert attach_claim_subjects({"claimant": None}, {}) == []
    assert attach_claim_subjects({"claimant": "   "}, {}) == []


# ---------------------------------------------------------------------------
# The two post-mapping merge paths — found OPEN by acceptance run 6f88a77f
# ---------------------------------------------------------------------------
# The first live acceptance run after the gates shipped had whitehouse.gov's
# "365 WINS" release re-entering the causal elements as `supports` — through
# the completion census and coverage recovery, which merged refs and re-derived
# state WITHOUT running the gates. These tests pin both seams.

WH_365 = {
    "evidence_id": "ev-wh-365",
    "url": "https://www.whitehouse.gov/releases/2026/01/365-wins-in-365-days/",
    "title": "365 WINS IN 365 DAYS: President Trump's Return Marks ...",
    "snippet": "Peace deals ending multiple wars under President Trump.",
    "tier": "primary",
    "evidence_type": "official",
}

WH_365_REF = {
    "evidence_id": "ev-wh-365",
    "relationship": "supports",
    "reasoning": (
        "This statement claims 'peace deals ending multiple wars' under "
        "President Trump, suggesting actions were taken to end hostilities."
    ),
}


def _canned_llm(response):
    async def fake_call_llm(*args, **kwargs):
        return response

    return fake_call_llm


async def test_the_completion_census_cannot_bypass_the_gates(monkeypatch):
    """MAP COMPLETION merges leftover refs and re-derives state; before
    2026-08-13 it did so ungated, which is exactly how the acceptance run's
    e4 stayed `supported`."""
    analyzer = ClaimMapAnalyzer()
    claim_map = _claim_map()
    elem = claim_map["elements"][0]
    elem["evidence_refs"] = [
        {
            "evidence_id": "ev-politifact",
            "relationship": "challenges",
            "reasoning": "Rated Pants on Fire, directly challenges the claim.",
        }
    ]
    # A prior gate receipt that the basis recompute must NOT destroy.
    elem["basis"] = {
        "recital_scope": {
            "claim_subjects": ["donald trump"],
            "scoped_count": 1,
            "scoped": [{"evidence_id": "ev-cbs", "was": "supports"}],
        }
    }

    monkeypatch.setattr(
        analyzer,
        "_call_llm",
        _canned_llm(
            {"elements": [{"element_id": "e3", "additional_refs": [WH_365_REF]}]}
        ),
    )

    evidence_list = [e for e in EVIDENCE if e["evidence_id"] == "ev-politifact"] + [
        WH_365
    ]
    await analyzer._complete_unmapped_evidence(claim_map, evidence_list)

    assert _rel(elem, "ev-wh-365") == "context"
    ip_ids = [e["evidence_id"] for e in elem["basis"]["interested_party"]["scoped"]]
    assert "ev-wh-365" in ip_ids
    # The main pass's receipt survived the basis recompute.
    recital = elem["basis"]["recital_scope"]
    assert recital["scoped_count"] == 1
    assert recital["scoped"][0]["evidence_id"] == "ev-cbs"


async def test_coverage_recovery_cannot_bypass_the_gates(monkeypatch):
    """RECOVERY MAP is the seam the acceptance run's ev-rec-* refs came
    through — whitehouse.gov supporting a Trump claim, unscoped."""
    analyzer = ClaimMapAnalyzer()
    claim_map = _claim_map()
    elem = claim_map["elements"][0]
    elem["state"] = None

    monkeypatch.setattr(
        analyzer,
        "_call_llm",
        _canned_llm(
            {
                "elements": [
                    {
                        "element_id": "e3",
                        "state": "supported",
                        "evidence_refs": [WH_365_REF],
                    }
                ]
            }
        ),
    )

    await analyzer.map_evidence_to_specific_elements(claim_map, ["e3"], [WH_365])

    assert _rel(elem, "ev-wh-365") == "context"
    ip_ids = [e["evidence_id"] for e in elem["basis"]["interested_party"]["scoped"]]
    assert "ev-wh-365" in ip_ids
    # With its only directional ref scoped, the element cannot read supported.
    state = getattr(elem["state"], "value", elem["state"])
    assert state != "supported"
