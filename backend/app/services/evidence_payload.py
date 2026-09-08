"""Lossless stored-evidence boundary for research and remapping.

Only database identity is excluded. Dates retain their provenance and all
classification, source independence and extraction fields survive a round trip.
"""

import hashlib
from typing import Any

from app.models import Evidence
from app.utils.date_utils import parse_date


def evidence_for_mapping(evidence: Evidence) -> dict[str, Any]:
    payload = evidence.model_dump(mode="json", exclude={"id", "claim_id", "created_at"})
    payload["evidence_id"] = evidence.evidence_id or evidence.id
    payload["text"] = evidence.snippet
    publication = ((evidence.text_provenance or {}).get("temporal") or {}).get(
        "publication"
    ) or {}
    if publication.get("representation") == "supplied_string":
        # Preserve pre-storage precision on strengthening. Do not reconstruct it
        # from a January 1 datetime or manufacture receipts for old records.
        payload["published_date"] = publication.get("supplied_value")
    return payload


def prepare_new_evidence(items: list[dict], existing_urls: set[str]) -> list[dict]:
    """Deduplicate within the incoming batch too, assigning IDs BEFORE mapping."""
    seen = set(existing_urls)
    result = []
    for item in items:
        url = item.get("url")
        if not url or url in seen:
            continue
        seen.add(url)
        item = dict(item)
        item["evidence_id"] = (
            item.get("evidence_id")
            or "ev-" + hashlib.sha256(url.encode()).hexdigest()[:12]
        )
        result.append(item)
    return result


def evidence_from_mapping(claim_id: str, payload: dict) -> Evidence:
    fields = set(Evidence.model_fields) - {"id", "claim_id", "created_at"}
    values = {key: value for key, value in payload.items() if key in fields}
    values.update(
        claim_id=claim_id,
        source=payload.get("source") or "Unknown",
        title=payload.get("title") or "",
        snippet=payload.get("snippet") or payload.get("text") or "",
        published_date=parse_date(payload.get("published_date")),
        relevance_score=float(payload.get("relevance_score") or 0),
        receipt_status=payload.get("receipt_status") or "shown",
    )
    if values.get("factcheck_date"):
        values["factcheck_date"] = parse_date(values["factcheck_date"])
    return Evidence(**values)
