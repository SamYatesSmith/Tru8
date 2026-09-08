from datetime import datetime

import pytest

from app.services.text_provenance import capture_text_provenance
from app.services.temporal_provenance import publication_receipt
from app.services.evidence_payload import evidence_from_mapping, evidence_for_mapping
from app.api.v1.response_builder import _serialize_evidence


@pytest.mark.parametrize(
    "value,precision",
    [
        ("2025", "year"),
        ("2025-05", "month"),
        ("2025-05-08", "day"),
        ("2025-05-08T12:00:00Z", "timestamp"),
        ("8 May 2025", "day"),
        ("2025-13", "unknown"),
        ("2025-02-30", "unknown"),
        (None, "unknown"),
        (datetime(2025, 1, 1), "unknown"),
    ],
)
def test_supplied_precision_is_not_invented(value, precision):
    assert publication_receipt(value)["precision"] == precision


def capture(text, publication="2025"):
    item = {
        "url": "https://example.invalid",
        "_full_text": text,
        "published_date": publication,
        "date_basis": "page_metadata",
    }
    capture_text_provenance(item, "Bank Rate")
    return item


def test_dates_survive_storage_without_manufacturing_january_on_remap():
    item = capture("Bank Rate effective from 8 May 2025.")
    evidence = evidence_from_mapping("claim", item)
    assert evidence.published_date == datetime(2025, 1, 1)  # legacy DB field
    assert evidence_for_mapping(evidence)["published_date"] == "2025"
    receipt = _serialize_evidence(evidence)["textProvenance"]["temporal"]
    assert receipt["publication"]["supplied_value"] == "2025"
    assert receipt["publication"]["precision"] == "year"


def test_explicit_statements_keep_exact_offsets_and_no_inferred_interval():
    text = "🙂 Bank Rate was 4.25%, effective from 8 May 2025, effective until 7 August 2025. As of August 8, 2025, a different value applies."
    temporal = capture(text)["text_provenance"]["temporal"]
    assert [s["kind"] for s in temporal["statements"]] == [
        "effective_start",
        "effective_end",
        "as_of",
    ]
    assert temporal["applicability_status"] == "unestablished"
    for statement in temporal["statements"]:
        citation = statement["citation"]
        assert text[citation["start"] : citation["end"]] == citation["quote"]
        assert statement["review_status"] == "unreviewed"


@pytest.mark.parametrize(
    "text",
    [
        "Clock: 2026-09-08. Bank Rate 4.25%.",
        "Current Bank Rate 4.25%.",
        "Effective from 30 February 2025.",
        "Published 8 May 2025. Retrieved 8 September 2026.",
    ],
)
def test_clock_publication_and_invalid_dates_never_become_effective_dates(text):
    temporal = capture(text)["text_provenance"]["temporal"]
    assert temporal["statements"] == []
    assert temporal["applicability_status"] == "unestablished"


def test_negated_and_future_statements_are_only_unreviewed_candidates():
    temporal = capture(
        "It is not effective from 8 May 2025; the proposed rate would be effective from 8 May 2027."
    )["text_provenance"]["temporal"]
    assert len(temporal["statements"]) == 2
    assert all("not effective" in s["citation"]["quote"] for s in temporal["statements"])
    assert all(s["review_status"] == "unreviewed" for s in temporal["statements"])
    assert temporal["applicability_status"] == "unestablished"


def test_statement_budget_is_visible():
    temporal = capture("Bank Rate as of 2025-05-08. " * 20)["text_provenance"][
        "temporal"
    ]
    assert len(temporal["statements"]) == 12
    assert temporal["unretained_candidates"] == 8


def test_existing_receipts_are_not_reinterpreted():
    item = {
        "_full_text": "Effective from 8 May 2025",
        "text_provenance": {"version": 1, "passages": []},
    }
    capture_text_provenance(item)
    assert "temporal" not in item["text_provenance"]
