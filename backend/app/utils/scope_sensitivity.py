"""Scope-sensitivity tagger — F3 Phase A (2026-07-07).

Design: audit/2026-07-07_f3_design_review.md §3.1. A mechanical post-process on
decompose output that flags elements whose wording is scope-sensitive, so the F3
response layer (Phase B) can attach a *descriptive* caveat WITHOUT re-scoping or
adjudicating the claim ("we organise; you decide"). NF-11-safe: pure lexical
detection, no LLM, no prompt dependency — the Phase-B caveat is gated on these
flags, not on prose.

Two flag categories — they de-risk differently (design §1), so Phase B treats
them separately:

  * ``geographic`` — composite geographies routinely conflated with a sub-part
    (Britain ⊋ England/Wales/Scotland; Europe continent vs EU; America vs USA).
    Detection ONLY here; turning this into a caveat needs the evidence's actual
    reach, which is LLM/Phase-B work (design option R-G2).

  * ``universal`` — absolute / universal quantifiers whose truth cannot be
    established by positive instances ("the only country in the world", "first
    nation to", "no other"). The Phase-B caveat here is mechanical but
    tier-gated (design option R-U1) so a universal backed by a primary complete
    registry isn't flagged as under-determined.

Tight by design (§3.1): the lexicons stay narrow and are widened only on eval
evidence. Superlatives (largest / most / best / first-of-N) are deliberately
NOT in v1 — high false-positive rate — deferred pending the F3 eval pool.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional

# ── Lexicons ────────────────────────────────────────────────────────────────
# Composite geographies commonly conflated with a sub-part. NOT "any place
# name" — that would fire on nearly every claim. Bare ambiguous tokens
# ("us", "eu", "gb", dotted "U.K.") are intentionally excluded to hold the
# false-positive rate down; add forms only when the eval pool demands them.
_GEOGRAPHIC: List[str] = [
    "britain",
    "british",
    "great britain",
    "united kingdom",
    "uk",
    "british isles",
    "europe",
    "european",
    "european union",
    "america",
    "american",
    "united states",
    "usa",
    "the americas",
    "scandinavia",
    "scandinavian",
]

# Absolute / universal quantifiers. Bare "only"/"first"/"all" are excluded
# (they read as "merely N" / ordinal / distributive far too often — "only 3%",
# "the first quarter", "all day"); the flag rides targeted phrases instead so
# the signal is the universal *scope claim*, not the loose word.
_UNIVERSAL: List[str] = [
    "sole",
    "solely",
    "unique",
    "worldwide",
    "globally",
    "only country",
    "only nation",
    "no other",
    "no country",
    "in the world",
    "on earth",
    "first country",
    "first nation",
    "first to",
    "every country",
    "all countries",
]


# Shape patterns the literal phrases can't capture. The flagship "only
# European countries contributed…" (TRU-EAB8-2652) is a universal but bare
# "only" is excluded (FP-prone), so match "only [adj/number] <scope-noun>"
# directly — a bounded-universal claim ("only European countries", "only two
# nations", "only country").
#
# The filler tokens between "only" and the scope-noun must NOT be determiners /
# partitives / conjunctions (a, the, some, few, when, of, …): those turn it into
# a "merely N" or conditional reading ("only a few countries", "only when
# countries cooperate") — the exact non-universal readings that excluding bare
# "only" was meant to avoid. Verified 2026-07-07 (F3 Phase A adversarial review)
# — the earlier `\w+{0,2}` filler admitted them.
_FILLER_STOP = r"a|an|the|some|few|several|many|most|of|when|if|and|or|but|any|no|to"
_UNIVERSAL_SHAPES: List[tuple] = [
    (
        "only <scope-noun>",
        r"\bonly\s+"
        r"(?:(?!(?:" + _FILLER_STOP + r")\b)\w+\s+){0,2}"
        r"(?:countr(?:y|ies)|nations?|states?|peoples?|persons?|places?)\b",
    ),
]


def _compile(terms: List[str]) -> List[tuple]:
    """Return (canonical_term, compiled_pattern) pairs, word-boundary anchored."""
    return [(t, re.compile(r"\b" + re.escape(t) + r"\b", re.IGNORECASE)) for t in terms]


_GEO_PATTERNS = _compile(_GEOGRAPHIC)
_UNI_PATTERNS = _compile(_UNIVERSAL) + [
    (label, re.compile(pat, re.IGNORECASE)) for label, pat in _UNIVERSAL_SHAPES
]


def _match(text: str, patterns: List[tuple]) -> List[str]:
    """Canonical terms whose pattern occurs in text — deduped, sorted (stable)."""
    hits = {term for term, pat in patterns if pat.search(text)}
    return sorted(hits)


def detect_scope_flags(text: Optional[str]) -> Dict[str, List[str]]:
    """Detect scope-sensitive wording in a single element description.

    Returns ``{"geographic": [...], "universal": [...]}`` of the canonical
    lexicon terms that matched (each list possibly empty). Whitespace is
    collapsed first so multi-word phrases match across newlines/runs.
    """
    if not text or not isinstance(text, str):
        return {"geographic": [], "universal": []}
    normalised = re.sub(r"\s+", " ", text)
    return {
        "geographic": _match(normalised, _GEO_PATTERNS),
        "universal": _match(normalised, _UNI_PATTERNS),
    }


def apply_scope_flags(elements: List[dict]) -> int:
    """Tag each element in place with ``scope_flags`` when its wording is
    scope-sensitive.

    Mutates ``element["scope_flags"] = {"geographic": [...], "universal": [...]}``
    ONLY when at least one category matched — an absent ``scope_flags`` is itself
    the "not scope-sensitive" signal Phase B reads, keeping element records lean.
    Idempotent (overwrites, never appends). Returns the number of flagged
    elements.

    Inert to the LLM prompts: the mapper serialises only element_id +
    description (claim_map_analyzer.py:966-968, :1165-1167), so this field never
    reaches a prompt body and cannot drift replay cassettes.
    """
    flagged = 0
    for elem in elements or []:
        flags = detect_scope_flags(elem.get("description"))
        if flags["geographic"] or flags["universal"]:
            elem["scope_flags"] = flags
            flagged += 1
    return flagged
