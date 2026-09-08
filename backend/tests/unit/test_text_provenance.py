"""Fixed-document checks: retention, not retrieval or model-quality claims."""

import hashlib

from app.services.text_provenance import (
    capture_text_provenance,
    select_passages,
    finalize_distilled_payload,
)
from app.services.evidence_payload import evidence_from_mapping, evidence_for_mapping
from app.api.v1.response_builder import _serialize_evidence


def test_late_sqlite_exception_and_rate_table_are_retained_exactly():
    lead = "General documentation overview. " * 600
    busy = "SQLite may still return SQLITE_BUSY when another connection performs cleanup.\n"
    rate = "Bank Rate\t4.25%\nEffective from 8 May 2025.\n"
    document = lead + busy + ("Other information. " * 600) + rate
    elements = [
        {"element_id": "e1", "description": "SQLite SQLITE_BUSY cleanup exception"},
        {"element_id": "e2", "description": "Bank Rate effective value"},
    ]
    passages = select_passages(document, "Claim", elements)
    retained = "".join(p["text"] for p in passages)
    assert busy.strip() in retained
    assert rate.strip() in retained
    assert len(retained) <= 7200
    assert len(passages) <= 8
    for passage in passages:
        assert passage["text"] == document[passage["start"] : passage["end"]]
    assert passages == select_passages(document, "Claim", elements)


def test_provenance_survives_orm_roundtrip_and_api_with_original_separate():
    full = "Captured café 🙂 source text. " * 50
    item = {
        "url": "https://example.invalid/source",
        "snippet": "Original snippet",
        "_full_text": full,
        "content_basis": "full",
        "text": "Original snippet",
    }
    capture_text_provenance(item, "source")
    item.update(text="Generated summary", _distilled=True)
    finalize_distilled_payload(item)
    assert item["snippet"] == "Generated summary"
    receipt = item["text_provenance"]
    assert receipt["original_snippet"] == "Original snippet"
    assert receipt["extraction_sha256"] == hashlib.sha256(full.encode()).hexdigest()
    saved = evidence_from_mapping("claim", item)
    assert evidence_for_mapping(saved)["text_provenance"] == receipt
    assert _serialize_evidence(saved)["textProvenance"] == receipt
    assert all(p["text"] == full[p["start"] : p["end"]] for p in receipt["passages"])


def test_legacy_or_snippet_only_items_do_not_gain_extraction_claims():
    for item in [
        {"text": "Search snippet"},
        {"_distilled": True, "text": "Generated facts"},
        {"_full_text": ""},
    ]:
        capture_text_provenance(item, "Claim")
        assert "text_provenance" not in item


def test_capture_does_not_overwrite_prior_source_version():
    item = {"_full_text": "Version one", "text": "snippet"}
    capture_text_provenance(item, "version")
    original = item["text_provenance"]
    item["_full_text"] = "Version two"
    capture_text_provenance(item, "version")
    assert item["text_provenance"] is original
    assert original["passages"][0]["text"] == "Version one"
