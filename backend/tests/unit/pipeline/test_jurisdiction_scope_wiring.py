"""The jurisdiction gate through the real mapping parser — not the tagger alone.

WHY THIS FILE EXISTS SEPARATELY
------------------------------
"Test the wired seam" is a standing lesson here: `retrieve.py` spent months
reading a key nothing wrote, and halves-only tests hid NF-18. This gate depends on
`claim_map["metadata"]["jurisdiction"]`, written by `runner.py`, so the seam is
exactly the kind that has failed silently before. A runner-side test pins the
writer; this file pins the reader.

Reconstructs production check `757f02c2`: a TRUE, ONS-verbatim UK CPI claim that
came back `disputed` because the IRISH CSO was labelled `challenges`.
"""

import pytest

from app.models.claim_map import ElementState
from app.pipeline.claim_map_analyzer import ClaimMapAnalyzer

ELEMENT_TEXT = (
    "The rate of consumer price inflation in the UK for the twelve months to "
    "September 2024 was 1.7 percent."
)

EVIDENCE = [
    {
        "evidence_id": "ev-ons",
        "url": "https://www.ons.gov.uk/economy/inflationandpriceindices/bulletins/consumerpriceinflation/september2024",
        "title": "Consumer price inflation, UK - Office for National Statistics",
        "snippet": "The Consumer Prices Index (CPI) rose by 1.7% in the 12 months to September 2024, down from 2.2% in August.",
        "tier": "primary",
        "evidence_type": "data",
    },
    {
        # The live failure. Note: names neither Ireland nor the UK.
        "evidence_id": "ev-cso",
        "url": "https://www.cso.ie/en/releasesandpublications/ep/p-cpi/consumerpriceindexseptember2025/",
        "title": "Consumer Price Index September 2025 - Central Statistics Office",
        "snippet": "The Consumer Price Index (CPI) rose by 2.7% between September 2024 and September 2025, up from an annual increase of 2.0% in the 12 months to August 2025.",
        "tier": "primary",
        "evidence_type": "data",
    },
    {
        # Foreign press ABOUT the UK — must survive untouched.
        "evidence_id": "ev-irish-press",
        "url": "https://www.irishtimes.com/business/2024/10/16/uk-inflation-falls/",
        "title": "UK inflation falls unexpectedly",
        "snippet": "Inflation in the UK fell to 1.7% in the year to September 2024.",
        "tier": "reporting",
        "evidence_type": "news",
    },
]


@pytest.fixture(autouse=True)
def _isolate_from_the_measure_gate(monkeypatch):
    """Test ONE gate at a time.

    The CSO item is caught by the measure gate too — its "between September 2024
    and September 2025" measures a different twelve months from the element's
    "twelve months to September 2024". That overlap is deliberate defence in depth
    and is asserted explicitly in `test_the_measure_gate_catches_it_independently`
    below, but leaving it on here would mean the jurisdiction assertions passed
    whether or not the jurisdiction gate worked.
    """
    from app.core import config

    monkeypatch.setattr(config.settings, "ENABLE_MEASURE_SCOPE_GATE", False)


def _claim_map(jurisdiction="UK"):
    return {
        "claim_id": "0",
        "normalised_claim": "UK CPI inflation was 1.7 percent in the twelve months to September 2024.",
        "elements": [
            {
                "element_id": "e1",
                "description": ELEMENT_TEXT,
                "evidence_refs": [],
                "state": None,
            }
        ],
        "metadata": {"jurisdiction": jurisdiction},
    }


def _mapping_response():
    """What the mapper returned in production: Irish CPI as a challenge."""
    return {
        "elements": [
            {
                "element_id": "e1",
                "state": "disputed",
                "evidence_refs": [
                    {
                        "evidence_id": "ev-ons",
                        "relationship": "supports",
                        "reasoning": "ONS reports 1.7%.",
                    },
                    {
                        "evidence_id": "ev-cso",
                        "relationship": "challenges",
                        "reasoning": "Reports 2.7%, contradicting 1.7%.",
                    },
                    {
                        "evidence_id": "ev-irish-press",
                        "relationship": "supports",
                        "reasoning": "Reports 1.7% for the UK.",
                    },
                ],
            }
        ]
    }


def _parse(jurisdiction="UK", response=None):
    analyzer = ClaimMapAnalyzer()
    claim_map = _claim_map(jurisdiction)
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


def test_the_irish_release_no_longer_challenges_a_uk_claim():
    assert _rel(_parse(), "ev-cso") == "context"


def test_our_own_primary_keeps_its_support():
    assert _rel(_parse(), "ev-ons") == "supports"


def test_foreign_press_about_the_uk_keeps_its_support():
    """The limit that keeps this from being a blunt instrument."""
    assert _rel(_parse(), "ev-irish-press") == "supports"


def test_the_element_no_longer_reads_disputed():
    """The user-visible point: a true, ONS-verbatim claim stops looking contested."""
    assert _parse()["state"] != ElementState.disputed


def test_nothing_is_deleted():
    elem = _parse()
    assert len(elem["evidence_refs"]) == len(EVIDENCE)


# ---------------------------------------------------------------------------
# The receipt — invariant #5
# ---------------------------------------------------------------------------


def test_scoping_is_recorded_in_the_basis():
    receipt = _parse()["basis"]["jurisdiction_scope"]

    assert receipt["claim_jurisdiction"] == "UK"
    assert receipt["scoped_count"] == 1
    entry = receipt["scoped"][0]
    assert entry["evidence_id"] == "ev-cso"
    assert entry["was"] == "challenges"
    assert entry["source_country"] == "IE"


def test_no_receipt_when_nothing_was_scoped():
    elem = _parse(jurisdiction="Global")
    assert "jurisdiction_scope" not in elem["basis"]


# ---------------------------------------------------------------------------
# Symmetry — the property that stops this being a sycophancy dial
# ---------------------------------------------------------------------------


def test_a_foreign_official_SUPPORT_is_scoped_just_as_readily():
    """If this is ever relaxed so only challenges are scoped, the gate becomes a
    mechanism that can only make claims look better supported — invariant #7."""
    response = _mapping_response()
    for ref in response["elements"][0]["evidence_refs"]:
        if ref["evidence_id"] == "ev-cso":
            ref["relationship"] = "supports"

    elem = _parse(response=response)

    assert _rel(elem, "ev-cso") == "context"
    assert elem["basis"]["jurisdiction_scope"]["scoped"][0]["was"] == "supports"


# ---------------------------------------------------------------------------
# Non-country claims and rollback
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("jurisdiction", ["EU", "Global", None])
def test_non_country_claims_leave_everything_alone(jurisdiction):
    assert _rel(_parse(jurisdiction=jurisdiction), "ev-cso") == "challenges"


def test_a_missing_jurisdiction_key_is_safe():
    """If the runner ever stops writing it, the gate must go quiet, not crash.

    This is the failure mode that hid in retrieve.py for months — a reader whose
    key nobody writes. Here it degrades to today's behaviour instead.
    """
    analyzer = ClaimMapAnalyzer()
    claim_map = _claim_map()
    del claim_map["metadata"]["jurisdiction"]

    analyzer._parse_mapping_response(_mapping_response(), claim_map, EVIDENCE)

    assert _rel(claim_map["elements"][0], "ev-cso") == "challenges"


def test_flag_off_restores_the_old_behaviour(monkeypatch):
    from app.core import config

    monkeypatch.setattr(config.settings, "ENABLE_JURISDICTION_SCOPE_GATE", False)
    elem = _parse()

    assert _rel(elem, "ev-cso") == "challenges"
    assert "jurisdiction_scope" not in elem["basis"]


def test_the_measure_gate_catches_it_independently(monkeypatch):
    """The overlap the fixture above suppresses, asserted on purpose.

    With the jurisdiction gate OFF, the same Irish item is still scoped — by the
    measure gate, because it measures September 2024→September 2025 while the
    element measures the twelve months TO September 2024. Two independent
    mechanical reasons cover the production failure, and the receipt names which
    one acted.
    """
    from app.core import config

    monkeypatch.setattr(config.settings, "ENABLE_MEASURE_SCOPE_GATE", True)
    monkeypatch.setattr(config.settings, "ENABLE_JURISDICTION_SCOPE_GATE", False)

    elem = _parse()

    assert _rel(elem, "ev-cso") == "context"
    assert "jurisdiction_scope" not in elem["basis"]
    receipt = elem["basis"]["measure_scope"]
    assert receipt["element_interval_end"] == "2024-09"
    assert receipt["scoped"][0]["evidence_id"] == "ev-cso"
    assert "2025-09" in receipt["scoped"][0]["evidence_interval_ends"]


def test_jurisdiction_owns_the_ref_when_both_gates_apply(monkeypatch):
    """Ordering is behaviour: one gate owns a reference, never two.

    A domain is the least ambiguous signal available, so "wrong country" is the
    reason recorded when an item is both foreign and off-measure — and the same
    exclusion must not be double-counted in two receipts.
    """
    from app.core import config

    monkeypatch.setattr(config.settings, "ENABLE_MEASURE_SCOPE_GATE", True)

    elem = _parse()

    assert elem["basis"]["jurisdiction_scope"]["scoped_count"] == 1
    assert "measure_scope" not in elem["basis"]
