"""Retained-passage helpers (text provenance windows).

`rank_passages` and `valid_passages` feed the relationship review and the
distiller. (The passage-mapping candidate and its `citations` readers were
removed 2026-10-07: audit/2026-10-07_passage_mapping_removal_plan.md.)
"""

import re
from collections import Counter

from app.services.text_provenance import _terms


def rank_passages(passages, terms):
    """Prefer terms that distinguish passages within this document.

    Raw overlap lets repeated background vocabulary crowd out a specific
    exception or endpoint. Frequency is computed from these retained passages,
    never from a maintained topic/domain dictionary.
    """
    tokens = [_terms(p["text"]) for p in passages]
    frequency = Counter(term for words in tokens for term in words)
    # Preserve exact compound identifiers (error codes, API/config names).
    # Their components are not interchangeable with surrounding prose.
    identifiers = {t for t in terms if re.fullmatch(r"\w+_\w+", t)}
    ranked = sorted(
        zip(passages, tokens),
        key=lambda pair: (
            -len(identifiers & pair[1]),
            -sum(1 / frequency[t] for t in terms & pair[1]),
        ),
    )
    return [passage for passage, words in ranked if terms & words]


def valid_passages(evidence):
    receipt = evidence.get("text_provenance") or {}
    if not isinstance(receipt, dict):
        return []
    digest = receipt.get("extraction_sha256", "")
    if (
        receipt.get("version") != 1
        or not isinstance(digest, str)
        or not re.fullmatch(r"[a-f0-9]{64}", digest)
    ):
        return []
    if (
        not isinstance(receipt.get("passages"), list)
        or type(receipt.get("extraction_characters")) is not int
    ):
        return []
    result = []
    for p in receipt.get("passages", []):
        if not isinstance(p, dict):
            continue
        start, end, text = p.get("start"), p.get("end"), p.get("text")
        if (
            type(start) is int
            and type(end) is int
            and 0 <= start < end
            and isinstance(text, str)
            and len(text) == end - start
            and len(text) <= 900
            and end <= receipt.get("extraction_characters", 0)
            and p.get("id") == f"p-{digest[:16]}-{start}-{end}"
        ):
            result.append(p)
    return result
