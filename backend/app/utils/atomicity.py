"""Element atomicity — is this element asking one question, or two?

A Claim Map element is meant to be ONE question. Measured on the live
decompose+grounds path (2026-07-29, 20 evaluative claims → 80 elements),
**21.2% ask two at once** and **13.8%** ask two that take DIFFERENT grading
rules. That second group is the damaging one: ``GROUNDS_MAPPING_ADDENDUM``
tells the mapper to pick ONE shape per element, so whichever half it reads,
the other is graded by the wrong standard — and the enumerative half is
usually trivially satisfiable, so the element badges ``supported`` while the
half that bears on the claim goes unchecked.

    "What are the projected passenger numbers for HS2, and how do these
     compare to initial estimates?"

Listing the forecasts satisfies half one. Whether they were missed — the half
that speaks to "catastrophic waste of money" — is never graded.

This module is the mechanical half of the fix (NF-11: a prompt rule is a first
line of defence, never a guarantee). It only ever *detects*; rewriting is the
caller's business.

Design: ``audit/2026-07-29_element_atomicity_design.md``.
"""

from __future__ import annotations

import re
from typing import List

# A coordinator MAY join two questions. On its own it means nothing — "costs
# and benefits" is one question — so a second INTERROGATIVE HEAD is required
# before we split. That requirement is the whole reason this under-splits by
# design, and it is what keeps conjoined noun phrases intact.
_COORDINATOR = re.compile(r",?\s+\b(?:and|or|but)\b\s+", re.I)

# Ordered longest-first so "to what extent" wins over a bare "what".
_WH = (
    r"(?:to\s+what\s+extent|how\s+(?:many|much|often|long|effective)|"
    r"what|which|why|when|where|who|whom|whose|how|whether|if)"
)
_AUX = r"(?:did|does|do|was|were|is|are|has|have|had|will|would|can|could|should)"
_INTERROGATIVE_HEAD = re.compile(rf"^\s*(?:{_WH}\b|{_AUX}\s+\w+)", re.I)

# Which half of the mapper's two-shape rule would grade this conjunct?
#   directional — "does the asked-about ground hold?"  (whether / to what extent)
#   enumerative — "supply an amount, record or list"    (what / which / how many)
_DIRECTIONAL_HEAD = re.compile(r"^\s*(?:to\s+what\s+extent|whether)\b", re.I)
_ENUMERATIVE_HEAD = re.compile(r"^\s*(?:what|which|how\s+(?:many|much))\b", re.I)
_DIRECTIONAL_ANY = re.compile(
    r"\b(?:to\s+what\s+extent|whether|did|does|do|was|were|is|are|has|have|had)\b",
    re.I,
)

DIRECTIONAL = "directional"
ENUMERATIVE = "enumerative"


def conjuncts(text: str) -> List[str]:
    """Split an element into the questions it actually asks.

    Splits ONLY where a coordinator is followed by a second interrogative
    head. One question in → one conjunct out, unchanged.
    """
    if not text:
        return []
    parts: List[str] = []
    cursor = 0
    for m in _COORDINATOR.finditer(text):
        if _INTERROGATIVE_HEAD.match(text[m.end() :]):
            parts.append(text[cursor : m.start()].strip())
            cursor = m.end()
    parts.append(text[cursor:].strip())
    return [p for p in parts if p]


def is_compound(text: str) -> bool:
    """True when the element asks more than one question."""
    return len(conjuncts(text)) > 1


def shape(text: str) -> str:
    """Which half of the mapper's two-shape rule grades this question?

    Head-anchored first (the head governs the question), falling back to a
    scan. Unknown shapes resolve to ``directional`` — the stricter rule, so an
    ambiguous question is never graded by the easier standard.
    """
    head = (text or "").strip()
    if _DIRECTIONAL_HEAD.match(head):
        return DIRECTIONAL
    if _ENUMERATIVE_HEAD.match(head):
        return ENUMERATIVE
    return ENUMERATIVE if _ENUMERATIVE_HEAD.search(head[:60]) else DIRECTIONAL


def is_mixed_shape(text: str) -> bool:
    """True when one element carries conjuncts of BOTH shapes.

    These are the elements the mapper cannot grade correctly by construction —
    it is told to choose one rule and there are two right answers.
    """
    parts = conjuncts(text)
    if len(parts) < 2:
        return False
    return len({shape(p) for p in parts}) > 1


def compound_indices(descriptions: List[str]) -> List[int]:
    """Positions of the compound descriptions, in order."""
    return [i for i, d in enumerate(descriptions) if is_compound(d or "")]
