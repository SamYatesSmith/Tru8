"""Range-period gate (A− option 3, 2026-09-24).

Record e6e0c00d: GAO's "37 models as of March 2018" challenged "Between 2010
and 2020 … launched 54 models" and the element read disputed. A source
published before a range ends cannot establish a total over it. Only for
AGGREGATE elements: for a universal or negated one a mid-range source is a
valid counterexample (review finding; invariant #7).
"""

import datetime as dt

import pytest

from app.pipeline.claim_map_analyzer import ClaimMapAnalyzer, _SCOPE_RECEIPT_KEYS
from app.utils.range_period import element_range, published_before_range_end

TODAY = dt.date(2026, 9, 24)


@pytest.mark.parametrize(
    "element,expected",
    [
        ("Between 2010 and 2020, the CMS Innovation Center launched 54 demonstration models nationwide.", (2010, 2020)),
        ("Sweden experienced lower excess mortality in 2020-22 than every other European country.", (2020, 2022)),
        ("The models launched between 2010 and 2020 encompassed almost one million clinicians.", (2010, 2020)),
        ("From 2015 to 2019 the NHS hired 20,000 nurses.", (2015, 2019)),
    ],
)
def test_aggregate_range_elements_arm(element, expected):
    assert element_range(element, TODAY) == expected


@pytest.mark.parametrize(
    "element",
    [
        "Sweden chose not to impose a general lockdown in 2020-22.",  # negated
        "The economy grew every year between 2010 and 2020.",  # universal
        "The 2010-2020 plan cut emissions by 40%.",  # a name, not the period
        "Emissions will fall 40% between 2020 and 2030.",  # a forecast
        "Spending in 2019-20 was £10bn.",  # one-year / fiscal span
        "Section 1981-1983 applies to 54 cases.",  # not introduced as a period
        "The Innovation Center operated between 2010 and 2020.",  # no total or comparison
        "Inflation in 2010-12 was 3%.",  # month-level reading belongs to temporal
    ],
)
def test_non_aggregate_or_non_period_ranges_do_not_arm(element):
    assert element_range(element, TODAY) is None


def test_publication_cutoff_and_trusted_dates_only():
    trusted = {"date_basis": "page_metadata"}
    assert published_before_range_end({**trusted, "published_date": "2018-03-26"}, 2020)
    assert published_before_range_end({**trusted, "published_date": "2022-08-16"}, 2022)
    assert not published_before_range_end({**trusted, "published_date": "2022-12-05"}, 2022)
    assert not published_before_range_end({"date_basis": "url_inferred_suspect", "published_date": "2018-03-26"}, 2020)
    assert not published_before_range_end({"date_basis": "page_metadata"}, 2020)  # no date


def _map():
    return {
        "claim_id": "0",
        "normalised_claim": "Between 2010 and 2020, the CMS Innovation Center launched 54 models.",
        "elements": [
            {
                "element_id": "e1",
                "description": "Between 2010 and 2020, the CMS Innovation Center launched 54 demonstration models nationwide.",
                "evidence_refs": [],
                "state": None,
            }
        ],
        "metadata": {},
    }


GAO = {
    "evidence_id": "ev-gao",
    "url": "https://www.gao.gov/products/gao-18-302",
    "title": "CMS Innovation Center: Model Implementation and Center Performance",
    "snippet": "As of March 1, 2018, the Innovation Center had implemented 37 models.",
    "published_date": "2018-03-26T00:00:00",
    "date_basis": "engine",
    "tier": "primary",
    "evidence_type": "official",
}


def _resp(rel):
    return {"elements": [{"element_id": "e1", "evidence_refs": [{"evidence_id": "ev-gao", "relationship": rel, "reasoning": "x"}]}]}


def _rel(cm):
    r = cm["elements"][0]["evidence_refs"][0]["relationship"]
    return r.value if hasattr(r, "value") else r


@pytest.mark.parametrize("rel", ["supports", "challenges"])
def test_wired_a_pre_range_end_source_bears_in_neither_direction(rel):
    cm = _map()
    ClaimMapAnalyzer()._parse_mapping_response(_resp(rel), cm, [GAO])
    assert _rel(cm) == "context"
    entry = cm["elements"][0]["basis"]["range_period"]["scoped"][0]
    assert entry["rule"] == "published_before_range_end"
    assert entry["element_range"] == "2010-2020"
    assert entry["was"] == rel


def test_wired_flag_off(monkeypatch):
    from app.core import config

    monkeypatch.setattr(config.settings, "ENABLE_RANGE_PERIOD_GATE", False)
    cm = _map()
    ClaimMapAnalyzer()._parse_mapping_response(_resp("challenges"), cm, [GAO])
    assert _rel(cm) == "challenges"


def test_receipt_key_and_labels():
    from app.api.v1.checks import _SCOPE_NOTE_LABELS

    assert "range_period" in _SCOPE_RECEIPT_KEYS
    assert "range_period" in _SCOPE_NOTE_LABELS and "readable_text" in _SCOPE_NOTE_LABELS
    # Straight after date_scope (review).
    assert _SCOPE_RECEIPT_KEYS.index("range_period") == _SCOPE_RECEIPT_KEYS.index("date_scope") + 1


@pytest.mark.parametrize(
    "element",
    [
        # aggregate AND universal/negated: a mid-range source is a counterexample
        "Sweden had lower excess mortality than Norway in every year from 2020 to 2022.",
        "Unemployment was not above 5% in any year between 2010 and 2020.",
    ],
)
def test_a_universal_or_negated_aggregate_does_not_arm(element):
    assert element_range(element, TODAY) is None
