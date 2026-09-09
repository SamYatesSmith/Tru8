"""Invented precision — an element must not be stricter than the claim.

Blind review of the 2026-09-09 regrade (audit/review_sheets/2026-09-09):
four of nineteen rejected labels were ONE element, "taking a daily dose of
*exactly* 5g of creatine", judged against sources that say 3–5 g. The user
wrote "5g of creatine daily"; the decomposer added "exactly", and every
source that gives a range then fails a test the claim never set. Same
family: "consists *strictly* of healthy adults".

This is the mechanical half of the fix (NF-11: a prompt line is a first
line of defence, never a guarantee). It strips a precision adverb from an
element when the claim itself does not carry it, and records what it
removed. It never adds words, never touches figures (measured on the
regrade: figures absent from the claim were only year-range expansions,
"2020-22" → "2022", which are faithful), and never fires when the claim
uses the adverb.
"""

import re
from typing import List, Optional, Tuple

# Measured on the 2026-09-09 post-fix regrade: the decomposer's precision
# words are open-ended — "consistently consume", "quantified average
# temperature", "verified maximum", "completely prevents", "specifically for
# the date". Each made an element demand something the claim never said.
_ADVERBS = (
    "exactly",
    "precisely",
    "strictly",
    "solely",
    "purely",
    "consistently",
    "specifically",
    "completely",
    "entirely",
    "absolutely",
    "wholly",
    "quantified",
    "verified",
)
_ADVERB_RE = re.compile(r"\b(" + "|".join(_ADVERBS) + r")\b\s*", re.I)


def strip_invented_precision(
    description: Optional[str], claim_text: Optional[str]
) -> Tuple[str, List[str]]:
    """Return (description without invented precision adverbs, adverbs removed).

    An adverb is kept when the claim text contains it (case-insensitive,
    whole word). Whitespace is normalised where a word was removed; a
    sentence-initial removal re-capitalises the next word.
    """
    text = description or ""
    claim = (claim_text or "").lower()
    removed: List[str] = []

    def keep_or_drop(m: re.Match) -> str:
        word = m.group(1)
        if re.search(r"\b" + re.escape(word.lower()) + r"\b", claim):
            return m.group(0)
        removed.append(word.lower())
        return ""

    out = _ADVERB_RE.sub(keep_or_drop, text)
    if not removed:
        return text, []
    out = re.sub(r"\s{2,}", " ", out).strip()
    out = re.sub(r"\s+([,.;:])", r"\1", out)
    if out and out[0].islower() and text[:1].isupper():
        out = out[0].upper() + out[1:]
    return out, removed
