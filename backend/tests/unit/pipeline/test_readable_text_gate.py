"""Unreadable-text floor (A− M2, 2026-09-24).

Record 580fd5b4 filed PurpleAir as a CHALLENGE on retained text that read, in
full, "PurpleAir You need to enable JavaScript to run this app". Measured on
the 156 directional refs of the 19 graded records: this rule fires on that one
reference only (score 0); the next lowest real source scores 9.
"""

import pytest

from app.pipeline.claim_map_analyzer import ClaimMapAnalyzer, _SCOPE_RECEIPT_KEYS
from app.utils.readable_text import content_word_count, is_unreadable

WALL = {
    "evidence_id": "ev-wall",
    "url": "https://www.purpleair.com/blog/mediterranean-wildfires-2026",
    "title": "PurpleAir",
    "snippet": "PurpleAir You need to enable JavaScript to run this app",
    "tier": "commentary",
    "evidence_type": "analysis",
}
TABLE = {
    "evidence_id": "ev-table",
    "url": "https://www.statista.com/statistics/1091926/co2",
    "title": "Atmospheric CO2 concentration",
    "snippet": "2025 |427.49 |2024 |425.4 |2023 |421.86",
    "tier": "reporting",
    "evidence_type": "data",
}


def _map():
    return {
        "claim_id": "0",
        "normalised_claim": "2026 is the quietest year for wildfires in Europe.",
        "elements": [{"element_id": "e1", "description": "Burned area in Europe in 2026 is the lowest on record.", "evidence_refs": [], "state": None}],
        "metadata": {},
    }


def _resp(rel, evidence_id="ev-wall"):
    return {"elements": [{"element_id": "e1", "evidence_refs": [{"evidence_id": evidence_id, "relationship": rel, "reasoning": "x"}]}]}


def _rel(elem, evidence_id):
    for ref in elem["evidence_refs"]:
        if ref["evidence_id"] == evidence_id:
            r = ref["relationship"]
            return r.value if hasattr(r, "value") else r
    raise AssertionError("missing")


@pytest.mark.parametrize("rel", ["supports", "challenges"])
def test_a_javascript_wall_bears_in_neither_direction(rel):
    cm = _map()
    ClaimMapAnalyzer()._parse_mapping_response(_resp(rel), cm, [WALL])
    elem = cm["elements"][0]
    assert _rel(elem, "ev-wall") == "context"
    receipt = elem["basis"]["readable_text"]
    assert receipt["scoped"][0]["rule"] == "no_readable_text"
    assert receipt["scoped"][0]["was"] == rel


def test_a_data_table_is_content():
    cm = _map()
    ClaimMapAnalyzer()._parse_mapping_response(_resp("supports", "ev-table"), cm, [TABLE])
    assert _rel(cm["elements"][0], "ev-table") == "supports"


def test_counts():
    assert content_word_count(WALL["snippet"], WALL["title"]) == 0
    assert not is_unreadable("the concentration of CO2 in the atmosphere has risen from 172 to 300 ppm", "x")
    assert not is_unreadable("Delo gives Reform record donation of 36m pounds today", "Reform")


def test_the_receipt_key_survives_later_passes():
    assert "readable_text" in _SCOPE_RECEIPT_KEYS
    # Temporal stays FIRST (test-pinned elsewhere); this gate is second.
    assert _SCOPE_RECEIPT_KEYS.index("readable_text") == _SCOPE_RECEIPT_KEYS.index("temporal_scope") + 1


def test_flag_off(monkeypatch):
    from app.core import config

    monkeypatch.setattr(config.settings, "ENABLE_READABLE_TEXT_GATE", False)
    cm = _map()
    ClaimMapAnalyzer()._parse_mapping_response(_resp("challenges"), cm, [WALL])
    assert _rel(cm["elements"][0], "ev-wall") == "challenges"


def test_a_short_genuine_sentence_is_evidence():
    # No wall present: four content words is a real statement, not a shell.
    assert not is_unreadable("The release setting is 37 units.", "Release note")
    assert is_unreadable("", "Anything")
