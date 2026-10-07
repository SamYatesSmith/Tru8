"""Retained-passage helpers (text provenance windows).

`rank_passages` and `valid_passages` feed the relationship review and the
distiller. `validate_citations` and `cited_context` read `citations` that the
removed passage-mapping candidate stored on evidence refs; they are kept for
such legacy records until a production read confirms none exist (removal plan
2026-10-07, Build B). Exact-text checks are not entailment checks.
"""

import re
from collections import Counter

from app.services.text_provenance import _terms

MAX_PASSAGES_PER_PAIR = 2


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


def validate_citations(raw, pair):
    if not isinstance(raw, list) or not 1 <= len(raw) <= MAX_PASSAGES_PER_PAIR:
        return None
    passages = {p["id"]: p for p in pair["passages"]}
    citations = []
    for citation in raw:
        if not isinstance(citation, dict):
            return None
        passage = passages.get(citation.get("passage_id"))
        quote = citation.get("quote")
        if (
            not passage
            or not isinstance(quote, str)
            or not quote.strip()
            or quote not in passage["text"]
        ):
            return None
        start = passage["start"] + passage["text"].index(quote)
        citations.append(
            {
                "passage_id": passage["id"],
                "quote": quote,
                "start": start,
                "end": start + len(quote),
                "extraction_sha256": pair["evidence"]["text_provenance"][
                    "extraction_sha256"
                ],
            }
        )
    return citations


def cited_context(citations, evidence):
    """Use the same captured context on later scope-gate/recovery passes."""
    passages = valid_passages(evidence)
    pair = {"passages": passages, "evidence": evidence}
    validated = validate_citations(citations, pair)
    if not validated or validated != citations:
        return None
    ids = {c["passage_id"] for c in validated}
    return "\n".join(p["text"] for p in passages if p["id"] in ids)
