"""Concentration describes document distribution without changing source roles."""

import copy
from app.services.source_concentration import source_concentration


def test_concentration_preserves_roles_counts_and_order():
    evidence = [
        {
            "evidence_id": str(i),
            "url": f"https://docs.example/a{i}",
            "tier": "primary",
            "evidence_type": "official_statement",
            "classification_method": "llm",
            "receipt_status": "shown",
        }
        for i in range(12)
    ] + [
        {
            "url": "https://other.example/a",
            "tier": "commentary",
            "receipt_status": "shown",
        }
    ]
    before = copy.deepcopy(evidence)
    result = source_concentration(evidence)
    assert result["mapped_documents"] == 13
    assert result["domains"][0] == {"domain": "docs.example", "documents": 12}
    assert result["independence"] == "not_established"
    assert evidence == before
    assert source_concentration(evidence) == result


def test_unmapped_and_excluded_do_not_inflate_mapped_concentration():
    evidence = [
        {"url": "https://a.example", "receipt_status": status}
        for status in ("shown", "unmapped", "excluded")
    ]
    assert source_concentration(evidence)["mapped_documents"] == 1
    assert source_concentration([])["domains"] == []


def test_strengthening_recomputes_from_current_refs_not_old_receipts():
    evidence = [
        {"evidence_id": "old", "url": "https://a.example", "receipt_status": "shown"},
        {
            "evidence_id": "new",
            "url": "https://b.example",
            "receipt_status": "classified",
        },
    ]
    cm = {
        "elements": [
            {"evidence_refs": [{"evidence_id": "new"}, {"evidence_id": "new"}]}
        ]
    }
    assert source_concentration(evidence, cm)["domains"] == [
        {"domain": "b.example", "documents": 1}
    ]
