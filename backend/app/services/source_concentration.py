"""Publisher concentration is descriptive, not a source classification."""

from collections import Counter

from app.utils.url_utils import extract_domain


def source_concentration(evidence, claim_map=None):
    """Count mapped documents by host without inferring study independence."""
    mapped = (
        None
        if claim_map is None
        else {
            ref["evidence_id"]
            for element in claim_map.get("elements", [])
            for ref in element.get("evidence_refs", [])
        }
    )
    shown = [
        e
        for e in evidence
        if (
            e.get("receipt_status") == "shown"
            if mapped is None
            else (e.get("evidence_id") or e.get("id")) in mapped
            and e.get("receipt_status") != "excluded"
        )
    ]
    counts = Counter(
        extract_domain(e.get("url") or "", fallback=e.get("source") or "unknown")
        or "unknown"
        for e in shown
    )
    return {
        "basis": "mapped_documents_by_domain",
        "mapped_documents": len(shown),
        "domains": [
            {"domain": domain, "documents": count}
            for domain, count in sorted(
                counts.items(), key=lambda item: (-item[1], item[0])
            )
        ],
        "independence": "not_established",
    }
