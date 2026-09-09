"""The day-level date scope gate (2026-09-09, blind review) through the real
mapping parser. Same month is the temporal gate's silence; a different DAY is
this gate's business. Silence never fires; symmetric."""

import pytest

from app.core.config import settings
from app.pipeline.claim_map_analyzer import _SCOPE_RECEIPT_KEYS, ClaimMapAnalyzer
from app.utils.date_scope import Day, element_day, is_off_day, stated_days

EVIDENCE = [
    {
        "evidence_id": "ev-choco",
        "url": "https://community.chocolatey.org/packages/sqlite/3.22.0",
        "title": "SQLite 3.22.0",
        "snippet": "SQLite version 3.22.0 was released on Tuesday, January 23, 2018.",
        "tier": "primary",
    },
    {
        "evidence_id": "ev-official",
        "url": "https://sqlite.org/releaselog/3_22_0.html",
        "title": "Release 3.22.0",
        "snippet": "SQLite Release 3.22.0 On 2018-01-22.",
        "tier": "primary",
    },
    {
        "evidence_id": "ev-month",
        "url": "https://blog.example/wal",
        "title": "WAL read-only",
        "snippet": "Since January 2018 SQLite can read WAL databases without write access.",
        "tier": "commentary",
    },
    {
        "evidence_id": "ev-other-month",
        "url": "https://news.example/old",
        "title": "Older release",
        "snippet": "Version 3.21.0 was released on 24 October 2017.",
        "tier": "reporting",
    },
]


def _claim_map():
    return {
        "claim_id": "0",
        "normalised_claim": "SQLite 3.22.0 was released on January 22, 2018.",
        "elements": [
            {
                "element_id": "e1",
                "description": "Version 3.22.0 of SQLite was released on January 22, 2018.",
                "evidence_refs": [],
                "state": None,
            }
        ],
        "metadata": {},
    }


def _parse(rels):
    analyzer = ClaimMapAnalyzer()
    cm = _claim_map()
    analyzer._parse_mapping_response(
        {
            "elements": [
                {
                    "element_id": "e1",
                    "state": "supported",
                    "evidence_refs": [
                        {"evidence_id": e, "relationship": r, "reasoning": "t"}
                        for e, r in rels
                    ],
                }
            ]
        },
        cm,
        EVIDENCE,
    )
    return cm["elements"][0]


def _rel(elem, eid):
    for ref in elem["evidence_refs"]:
        if ref["evidence_id"] == eid:
            return getattr(ref["relationship"], "value", ref["relationship"])
    raise AssertionError(eid)


@pytest.mark.parametrize(
    "text,days",
    [
        ("released on Tuesday, January 23, 2018", {Day(2018, 1, 23)}),
        (
            "released on 22nd January 2018 and again 1 February 2018",
            {Day(2018, 1, 22), Day(2018, 2, 1)},
        ),
        ("On 2018-01-22 the release went out", {Day(2018, 1, 22)}),
        ("in January 2018", set()),
        ("22/01/2018", set()),
    ],
)
def test_stated_days(text, days):
    assert stated_days(text) == days


def test_element_day_needs_exactly_one_full_date():
    assert element_day("Released on January 22, 2018.") == Day(2018, 1, 22)
    assert element_day("Between 22 January 2018 and 23 January 2018.") is None
    assert element_day("Released in January 2018.") is None


def test_off_day_is_same_month_different_day_only():
    t = Day(2018, 1, 22)
    assert is_off_day(t, "released on Tuesday, January 23, 2018")
    assert not is_off_day(t, "SQLite Release 3.22.0 On 2018-01-22.")
    assert not is_off_day(t, "released on 24 October 2017")  # temporal gate's business
    assert not is_off_day(t, "released in January 2018")  # silence


def test_wrong_day_support_becomes_context_and_right_day_stays():
    elem = _parse(
        [
            ("ev-choco", "supports"),
            ("ev-official", "supports"),
            ("ev-month", "supports"),
        ]
    )
    assert _rel(elem, "ev-choco") == "context"
    assert _rel(elem, "ev-official") == "supports"
    assert _rel(elem, "ev-month") == "supports"
    entry = elem["basis"]["date_scope"]["scoped"][0]
    assert entry["evidence_id"] == "ev-choco" and entry["was"] == "supports"
    assert entry["element_day"] == "2018-01-22" and entry["evidence_days"] == [
        "2018-01-23"
    ]


def test_symmetric_and_different_month_left_to_temporal():
    elem = _parse([("ev-choco", "challenges"), ("ev-other-month", "challenges")])
    assert _rel(elem, "ev-choco") == "context"
    # October 2017 is a different period: the TEMPORAL gate owns it, not this one.
    assert "ev-other-month" not in [
        e["evidence_id"] for e in elem["basis"]["date_scope"]["scoped"]
    ]


def test_flag_off_and_key_registered_and_order(monkeypatch):
    assert "date_scope" in _SCOPE_RECEIPT_KEYS
    assert _SCOPE_RECEIPT_KEYS[-1] == "echo_scope"
    from app.pipeline.claim_map_analyzer import _index_evidence

    gates = ClaimMapAnalyzer()._armed_scope_gates(
        _claim_map()["elements"][0], _claim_map(), _index_evidence(EVIDENCE)
    )
    keys = [g.key for g in gates]
    assert (
        keys.index("temporal_scope")
        < keys.index("date_scope")
        < keys.index("echo_scope")
    )
    monkeypatch.setattr(settings, "ENABLE_DATE_SCOPE_GATE", False)
    elem = _parse([("ev-choco", "supports")])
    assert _rel(elem, "ev-choco") == "supports"
