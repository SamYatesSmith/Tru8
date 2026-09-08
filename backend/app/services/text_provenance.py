"""Retain exact extraction windows for review, without inventing citations.

Offsets are Python Unicode character offsets in the captured extraction, not
HTML/PDF coordinates. Selection is lexical and never asserts a relationship.
The source document is not retained in full or certified complete.
"""

import hashlib
import re
from datetime import datetime, timezone

from app.services.temporal_provenance import temporal_receipt

WINDOW_CHARS = 900
MAX_PASSAGES = 8
STOP_WORDS = set(
    "a an the and or of to in is are was were be been for on by with from that this it as at does do can all any".split()
)


def _terms(text):
    return {
        t
        for t in re.findall(r"[\w]+", text.lower())
        if len(t) > 1 and t not in STOP_WORDS
    }


def select_passages(text: str, claim_text: str, elements: list[dict]) -> list[dict]:
    """Round-robin relevant windows across element descriptions, over ALL text.

    Fixed windows keep retained storage bounded. Word boundaries avoid splitting
    most words; exact slices (including whitespace) are retained unmodified.
    """
    windows = []
    start = 0
    while start < len(text):
        end = min(start + WINDOW_CHARS, len(text))
        if end < len(text):
            boundary = max(
                text.rfind("\n", start + WINDOW_CHARS // 2, end),
                text.rfind(" ", start + WINDOW_CHARS // 2, end),
            )
            if boundary > start:
                end = boundary + 1
        windows.append((start, end, _terms(text[start:end])))
        start = end
    queries = [
        (e.get("element_id"), _terms(e.get("description", ""))) for e in elements
    ]
    queries = [(eid, terms) for eid, terms in queries if terms]
    if not queries:
        queries = [(None, _terms(claim_text))]
    rankings = []
    for eid, terms in queries:
        ranked = sorted(
            range(len(windows)), key=lambda i: (-len(terms & windows[i][2]), i)
        )
        rankings.append((eid, [i for i in ranked if terms & windows[i][2]]))
    selected = set()
    for rank in range(MAX_PASSAGES):
        for _, indices in rankings:
            if rank < len(indices):
                selected.add(indices[rank])
                if len(selected) == MAX_PASSAGES:
                    break
        if len(selected) == MAX_PASSAGES:
            break
    if not selected and windows:
        selected.add(0)  # explicit leading fallback, not a relevance claim
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return [
        {
            "id": f"p-{digest[:16]}-{windows[i][0]}-{windows[i][1]}",
            "start": windows[i][0],
            "end": windows[i][1],
            "text": text[windows[i][0] : windows[i][1]],
            "matched_element_ids": [
                eid for eid, terms in queries if eid and terms & windows[i][2]
            ],
        }
        for i in sorted(selected)
    ]


def capture_text_provenance(item: dict, claim_text: str = "", elements=None):
    """Capture once, before distillation discards or replaces input text.

    Do not backfill receipts onto stored or replayed items with no fresh text.
    """
    if item.get("text_provenance"):
        return
    full_text = item.get("_full_text")
    if not isinstance(full_text, str) or not full_text.strip():
        return
    passages = select_passages(full_text, claim_text, elements or [])
    digest = hashlib.sha256(full_text.encode("utf-8")).hexdigest()
    item["text_provenance"] = {
        "version": 1,
        "capture_kind": "extracted_text",
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "source_url": item.get("url"),
        "input_content_basis": item.get("content_basis"),
        "extraction_sha256": digest,
        "extraction_characters": len(full_text),
        "retained_characters": sum(len(p["text"]) for p in passages),
        "offset_unit": "unicode_code_points",
        "selection_method": "lexical_element_windows_v1",
        "original_snippet": item.get("snippet") or item.get("text") or "",
        "passages": passages,
        "temporal": temporal_receipt(
            passages, digest, item.get("published_date"), item.get("date_basis")
        ),
    }


def finalize_distilled_payload(item: dict):
    """Run AFTER classification: mapper and persistence both prefer snippet."""
    if item.get("_distilled") and item.get("text"):
        item["snippet"] = item["text"]
