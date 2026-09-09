"""Absence of evidence is not evidence of absence — lexical, no LLM.

Astra finding 3 (creatine, 2026-09-07), reproduced on the 2026-09-09 regrade:
three sources saying "there isn't enough evidence", "no strong evidence
linking", "no large trials have demonstrated" were mapped as `challenges` and
the element read `disputed / all_challenges`. A statement that evidence is
LACKING bears on the element in neither direction: it is not a contrary
finding, and mapped the other way ("no evidence of harm" as support for
"is safe") it is not a supporting one either. Symmetric by construction.

This is deliberately narrow. A MEASURED null ("found identical admission
rates", "showed no reduction", "no significant difference was observed") is a
result and must stay a challenge; the detector refuses any sentence that
carries result framing beside the absence wording.
"""

import re
from typing import Dict, Optional

_ABSENCE = re.compile(
    r"\b(?:"
    r"(?:there\s+(?:is|are|was|were)\s+|is\s+|are\s+|remains?\s+|currently\s+)?"
    r"(?:not\s+enough|insufficient|limited|little|(?:a\s+)?lack\s+of|lacking|weak|"
    r"no(?:\s+(?:strong|robust|conclusive|direct|good|clear|convincing|solid|definitive|high-quality))?)"
    r"\s+(?:clinical\s+|scientific\s+|human\s+)?evidence"
    r"|evidence\s+(?:is|remains)\s+(?:lacking|limited|insufficient|inconclusive|weak|scarce|thin)"
    r"|(?:has|have)\s+not\s+(?:yet\s+)?been\s+(?:shown|proven|demonstrated|established|confirmed)"
    r"|(?:no|few)\s+(?:large|long-term|long-duration|randomi[sz]ed|controlled|human|clinical)?[\w\s,-]{0,40}?"
    r"(?:trials?|studies)\s+(?:have|has)\s+(?:yet\s+)?(?:demonstrated|shown|established|proven|confirmed)"
    r"|(?:un|not\s+(?:yet\s+)?)(?:proven|established)\b"
    r"|isn'?t\s+enough\s+evidence"
    r")",
    re.I,
)
# Result framing that turns "no …" into a finding, not a gap.
_MEASURED_NULL = re.compile(
    r"\b(?:found|observed|showed|reported|recorded|measured|demonstrated)\b[^.;]{0,60}?"
    r"\b(?:no|identical|similar|equal|comparable)\s+(?:significant\s+)?"
    r"(?:difference|reduction|effect|benefit|association|change|improvement|rates?)\b"
    r"|\b(?:identical|similar|equal)\s+(?:\w+\s+){0,3}rates?\b"
    r"|\bno\s+significant\s+(?:difference|effect|reduction|association|benefit)\b",
    re.I,
)
_SENTENCE = re.compile(r"(?<=[.!?])\s+")
_EXCERPT_CHARS = 200


def _hit(text: Optional[str]) -> Optional[str]:
    for sentence in _SENTENCE.split(text or ""):
        if _ABSENCE.search(sentence) and not _MEASURED_NULL.search(sentence):
            return sentence.strip()
    return None


def absence_of_evidence_match(
    reasoning: Optional[str], evidence_text: Optional[str]
) -> Optional[Dict[str, str]]:
    """Receipt entry when the reference rests on evidence being ABSENT, else None.

    The mapper's own `reasoning` is read first (it says what the source was
    used for: "states there is not enough evidence to support…"); the source
    text second. Either alone is enough. A sentence that also reports a
    measured null never matches.
    """
    for basis, text in (("reasoning", reasoning), ("text", evidence_text)):
        sentence = _hit(text)
        if sentence:
            return {
                "marker": "states that evidence is lacking",
                "basis": basis,
                "excerpt": sentence[:_EXCERPT_CHARS],
            }
    return None
