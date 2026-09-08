from unittest.mock import AsyncMock

import pytest

from app.core.config import settings
from app.pipeline.claim_map_analyzer import ClaimMapAnalyzer, _index_evidence
from app.services.fact_applicability import source_time_anchor, target_day
from app.services.passage_mapping import complete_passage_pairs, plan_pairs
from app.services.text_provenance import capture_text_provenance


def fixture(text, day="2031-04-12", value=37):
    element = {
        "element_id": "e1",
        "description": f"The release setting was {value} units on {day}.",
        "evidence_refs": [
            {
                "evidence_id": "source",
                "relationship": "supports",
                "reasoning": "Original model interpretation",
            }
        ],
    }
    cm = {
        "normalised_claim": element["description"],
        "elements": [element],
        "metadata": {},
    }
    ev = {
        "evidence_id": "source",
        "url": "https://example.invalid",
        "_full_text": text,
        "snippet": text,
        "tier": "primary",
        "published_date": day,
    }
    capture_text_provenance(ev, cm["normalised_claim"], cm["elements"])
    return cm, ev


@pytest.mark.parametrize("period", ["morning", "afternoon", "evening"])
def test_explicit_part_of_day_retains_calendar_date(period):
    text = f"The release setting was 37 units on the {period} of April 12, 2031."
    cm, ev = fixture(text)
    day = target_day(cm["elements"][0]["description"], "")
    anchor = source_time_anchor(ev, cm["elements"][0]["description"], day)
    assert anchor and anchor["quote"] == text
    assert target_day(text, "") == day


@pytest.mark.parametrize("phrase", ["evening before", "morning after", "eve of"])
def test_relative_day_phrase_does_not_establish_named_date(phrase):
    text = f"The release setting was 37 units on the {phrase} April 12, 2031."
    cm, ev = fixture(text)
    day = target_day(cm["elements"][0]["description"], "")
    assert source_time_anchor(ev, cm["elements"][0]["description"], day) is None
    assert target_day(text, "") is None


@pytest.mark.parametrize(
    "text",
    [
        "Page clock: 2031-04-12. The release setting is 37 units.",
        "The release setting was 37 units as of 2031-03-01.",
        "The release setting will change effective from 2031-05-01.",
        "The release setting is not effective from 2031-04-01.",
        "The release setting is planned effective from 2031-04-01.",
        "The release setting is effective from 2031-04-01 until 2031-04-10.",
        "The release setting is 37. A different policy was active on 2031-04-12.",
    ],
)
def test_page_clocks_old_values_plans_and_wrong_topics_do_not_establish_day(text):
    cm, ev = fixture(text)
    assert (
        source_time_anchor(ev, cm["elements"][0]["description"], "2031-04-12") is None
    )


@pytest.mark.parametrize(
    "day,value", [("2031-04-12", 37), ("2028-11-09", 82), ("2040-02-29", 14)]
)
@pytest.mark.parametrize("wording", ["as of {day}", "on {day}", "effective from {day}"])
def test_varied_explicit_anchors_preserve_original_unicode_slices(day, value, wording):
    cm, ev = fixture(
        f"🙂 The release setting is {value} units {wording.format(day=day)}.",
        day,
        value,
    )
    anchor = source_time_anchor(ev, cm["elements"][0]["description"], day)
    assert anchor
    assert ev["_full_text"][anchor["start"] : anchor["end"]] == anchor["quote"]


def test_negation_at_target_day_is_still_dated_evidence():
    cm, ev = fixture(
        "As of 2031-04-12, the proposed release setting is not effective from 2031-04-01."
    )
    assert source_time_anchor(ev, cm["elements"][0]["description"], "2031-04-12")


@pytest.mark.parametrize("unit", ["units", "litres", "metres"])
def test_quantity_with_unit_can_link_a_dated_statement_without_repeated_noun(unit):
    cm, ev = fixture(
        f"As of 2031-04-12, a change to 37 {unit} is planned; no change has occurred yet."
    )
    description = cm["elements"][0]["description"].replace("units", unit)
    assert source_time_anchor(ev, description, "2031-04-12")


def test_same_number_with_different_units_does_not_link_topics():
    cm, ev = fixture("As of 2031-04-12, the fence was 37 metres high.")
    assert (
        source_time_anchor(ev, cm["elements"][0]["description"], "2031-04-12") is None
    )


def test_target_scope_inheritance_and_no_date_guessing():
    assert (
        target_day(
            "Next decision as of that date is scheduled for 19 April 2031.",
            "As of 12 April 2031, the setting was 37.",
        )
        == "2031-04-12"
    )
    assert target_day("Concurrent readers are supported", "Concurrency") is None
    assert target_day("The setting on 2031-04-12 and on 2031-04-13", "") is None


@pytest.mark.parametrize("direction", ["supports", "challenges"])
@pytest.mark.parametrize("enabled", [True, False])
def test_common_scope_path_enforces_symmetry_and_preserves_disabled_behavior(
    monkeypatch, direction, enabled
):
    monkeypatch.setattr(settings, "ENABLE_PASSAGE_MAPPING", enabled)
    cm, ev = fixture("The release setting is 37 units.")
    elem = cm["elements"][0]
    elem["evidence_refs"][0]["relationship"] = direction
    receipts = ClaimMapAnalyzer()._apply_scope_gates(elem, _index_evidence([ev]), cm)
    ref = elem["evidence_refs"][0]
    assert ref["relationship"] == ("context" if enabled else direction)
    if enabled:
        assert receipts["fact_applicability"]["scoped"][0]["was"] == direction
        assert "not established" in ref["reasoning"]


def test_generated_facts_and_publication_cannot_supply_anchor():
    cm, ev = fixture("The release setting is 37 units.")
    ev["snippet"] = "The release setting is 37 units as of 2031-04-12."
    assert (
        source_time_anchor(ev, cm["elements"][0]["description"], "2031-04-12") is None
    )


@pytest.mark.parametrize(
    "text",
    [
        "The release setting will be effective from 2031-04-01.",
        "The release setting might be effective from 2031-04-01.",
        "The release setting is effective from 2031-04-01 if approved.",
    ],
)
def test_future_and_conditional_intervals_do_not_establish_occurrence(text):
    cm, ev = fixture(text)
    assert (
        source_time_anchor(ev, cm["elements"][0]["description"], "2031-04-12") is None
    )


@pytest.mark.parametrize("edge", ["start", "end"])
def test_clipped_qualifications_do_not_create_an_anchor(edge):
    text = (
        "Not the release setting effective from 2031-04-01."
        if edge == "start"
        else "The release setting effective from 2031-04-01, unless approved."
    )
    cm, ev = fixture(text)
    start, end = (4, len(text)) if edge == "start" else (0, text.index(","))
    digest = ev["text_provenance"]["extraction_sha256"]
    ev["text_provenance"]["passages"] = [
        {
            "id": f"p-{digest[:16]}-{start}-{end}",
            "start": start,
            "end": end,
            "text": text[start:end],
        }
    ]
    assert (
        source_time_anchor(ev, cm["elements"][0]["description"], "2031-04-12") is None
    )


@pytest.mark.asyncio
async def test_passage_addition_cannot_bypass_gate(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_PASSAGE_MAPPING", True)
    cm, ev = fixture("The release setting is 37 units.")
    cm["elements"][0]["evidence_refs"] = []
    pairs, _ = plan_pairs(cm, [ev])
    analyzer = ClaimMapAnalyzer()
    analyzer._call_llm = AsyncMock(
        return_value={
            "pairs": [
                {
                    "pair_id": pairs[0]["pair_id"],
                    "relationship": "supports",
                    "reasoning": "Incorrect inference",
                    "citations": [
                        {
                            "passage_id": pairs[0]["passages"][0]["id"],
                            "quote": ev["_full_text"],
                        }
                    ],
                }
            ]
        }
    )
    await complete_passage_pairs(analyzer, cm, [ev])
    element = cm["elements"][0]
    assert element["evidence_refs"][0]["relationship"] == "context"
    assert element["state"] != "supported"
    assert element["basis"]["fact_applicability"]["scoped_count"] == 1


def test_initial_mapping_recomputes_state_after_date_exclusion(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_PASSAGE_MAPPING", True)
    cm, ev = fixture("The release setting is 37 units.")
    raw = {
        "elements": [
            {
                "element_id": "e1",
                "state": "supported",
                "evidence_refs": cm["elements"][0]["evidence_refs"],
            }
        ]
    }
    ClaimMapAnalyzer()._parse_mapping_response(raw, cm, [ev])
    assert cm["elements"][0]["evidence_refs"][0]["relationship"] == "context"
    assert cm["elements"][0]["state"] != "supported"
    assert cm["elements"][0]["basis"]["fact_applicability"]["scoped_count"] == 1
