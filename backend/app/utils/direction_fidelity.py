"""Direction fidelity — a causal element must keep the claim's outcome direction.

Three blind label reviews on 2026-09-10 (audit/2026-09-10_decomposition_specificity.md
§8) put five of seven reviewer misreads on ONE shape of element. The claim:

    "Sweden's decision not to impose a general lockdown caused it to have
     LOWER excess mortality in 2020-22 than every other European country."

decomposed on one record per run to

    "Sweden's lack of a general lockdown was the primary driver of its
     mortality outcomes."

The direction ("lower") is gone, so a source saying no-lockdown produced MORE
deaths reads, to a blind reader, as support for the element. The sibling
record that kept "lower" was never misread. Lost specificity — the mirror of
the invented-specificity fault the same day's build removed.

This module is the mechanical half (NF-11: a prompt rule is a first line of
defence, never a guarantee). It only ever *detects*; the rewrite is the
analyzer's business (ClaimMapAnalyzer._repair_lost_direction). It fires only
when the CLAIM carries a directional word, the ELEMENT asserts a causal link,
and the element carries none of the claim's directional words.
"""

from __future__ import annotations

import re
from typing import List, Set

# Directional words a claim uses for an outcome. Matched as whole words; a
# stem (first four letters, or the whole word when shorter) is what the
# element must echo, so "lower" is satisfied by "lower"/"lowest"/"low",
# "reduced" by "reduction", "rose" only by "rose".
_DIRECTIONAL = re.compile(
    r"\b(lower|higher|more|less|fewer|greater|smaller|larger|bigger|better|worse|"
    r"faster|slower|cheaper|cleaner|dirtier|safer|riskier|stronger|weaker|longer|"
    r"shorter|lowest|highest|most|least|fewest|best|worst|"
    r"reduc\w*|increas\w*|decreas\w*|declin\w*|ris(?:e|es|en|ing)|rose|"
    r"fall\w*|fell|drop\w*|grow\w*|grew|improv\w*|worsen\w*|cut|doubl\w*|halv\w*)\b",
    re.I,
)


def _stem(word: str) -> str:
    w = word.lower()
    return w[:4] if len(w) > 4 else w


def claim_directions(claim_text: str) -> Set[str]:
    """Stems of the directional words the claim carries."""
    return {_stem(m.group(1)) for m in _DIRECTIONAL.finditer(claim_text or "")}


def _is_causal(description: str) -> bool:
    # Imported lazily: the analyzer imports this module at load time.
    from app.pipeline.claim_map_analyzer import _is_causal_link

    return _is_causal_link(description)


def lost_direction(description: str, claim_text: str) -> bool:
    """True when a causal element carries none of the claim's directional words."""
    if not description or not claim_text:
        return False
    stems = claim_directions(claim_text)
    if not stems:
        return False
    if not _is_causal(description):
        return False
    words = re.findall(r"[a-z]+", description.lower())
    return not any(_stem(w) in stems for w in words)


def lost_direction_indices(descriptions: List[str], claim_text: str) -> List[int]:
    """Positions of the causal descriptions that lost the claim's direction."""
    return [
        i for i, d in enumerate(descriptions) if lost_direction(d or "", claim_text)
    ]


def keeps_direction(description: str, claim_text: str) -> bool:
    """True when ``description`` carries at least one of the claim's directional stems."""
    stems = claim_directions(claim_text)
    if not stems:
        return True
    words = re.findall(r"[a-z]+", (description or "").lower())
    return any(_stem(w) in stems for w in words)
