from datetime import datetime

from app.models import Evidence
from app.services.evidence_payload import (
    evidence_for_mapping,
    evidence_from_mapping,
    prepare_new_evidence,
)


def test_remapping_preserves_classification_dates_and_source_provenance():
    original = Evidence(
        id="row",
        claim_id="claim",
        evidence_id="ev-source",
        url="https://example.org",
        source="Institution",
        title="Source",
        snippet="Stored basis",
        relevance_score=0.8,
        tier="primary",
        evidence_type="academic",
        classification_method="llm",
        content_basis="distilled",
        published_date=datetime(2026, 8, 1),
        date_basis="page_metadata",
        is_factcheck=True,
        factcheck_rating="False",
        corroboration_group_id=2,
        context_before="Before",
        context_after="After",
        archived_url="https://archive.org/source",
        api_metadata={"scope": "UK"},
        receipt_status="shown",
    )
    payload = evidence_for_mapping(original)
    assert payload["tier"] == "primary"
    assert payload["published_date"] == "2026-08-01T00:00:00"
    restored = evidence_from_mapping("claim", payload)
    assert evidence_for_mapping(restored) == payload
    assert restored.id != original.id


def test_ids_are_assigned_before_mapping_and_batch_duplicates_do_not_accumulate():
    items = [
        {"url": "https://existing"},
        {"url": "https://new", "tier": "primary"},
        {"url": "https://new"},
    ]
    result = prepare_new_evidence(items, {"https://existing"})
    assert len(result) == 1
    assert result[0]["evidence_id"].startswith("ev-")
    assert result[0]["tier"] == "primary"
    assert "evidence_id" not in items[1]
    assert prepare_new_evidence(items, {"https://existing"}) == result


def test_legacy_row_uses_database_identity_without_inventing_provenance():
    ev = Evidence(
        id="legacy",
        claim_id="claim",
        source="Source",
        url="https://example.org",
        title="Title",
        snippet="Text",
        relevance_score=0,
    )
    payload = evidence_for_mapping(ev)
    assert payload["evidence_id"] == "legacy"
    assert payload["date_basis"] is None
    assert payload["content_basis"] is None
