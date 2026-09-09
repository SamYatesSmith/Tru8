"""Verdict-language test for model-written free text — PARITY-LOCKED to
``web/lib/element-caveat.ts`` (the Fix 1 gate, 2026-09-02).

The frontend withholds an element caveat or a "System interpretation" from
the public record when it adjudicates the claim rather than describing a
limit of the evidence ("the evidence consistently refutes…"). The PDF is a
second rendering engine and used to print every note unfiltered; now that it
prints scope-review reasoning (Track Q step 8, 2026-09-09) it applies the
same rule. The two regexes below must stay byte-identical to the TypeScript
ones — ``tests/unit/test_verdict_language_parity.py`` reads both files.
"""

import re

# Words that adjudicate the claim rather than describe a limit of the evidence.
VERDICT_WORD_SOURCE = (
    r"\b(refut\w*|false|true|prove[sdn]?|proven|confirm\w*|debunk\w*|verdict|"
    r"incorrect|correct|wrong|fact-?check\w*)\b"
)
# An intensifier attached to the evidence noun: the model summarising the
# direction it has just assigned.
INTENSIFIED_EVIDENCE_SOURCE = (
    r"\b(evidence|sources?|data|studies|research)\b[^.;]{0,40}?"
    r"\b(strongly|consistently|clearly|overwhelmingly|conclusively|decisively|"
    r"unambiguously)\b|\b(strong|overwhelming|conclusive|clear|decisive|"
    r"unambiguous)\s+(evidence|support|challenge)\b"
)
_VERDICT_WORD = re.compile(VERDICT_WORD_SOURCE, re.I)
_INTENSIFIED = re.compile(INTENSIFIED_EVIDENCE_SOURCE, re.I)

WITHHELD_NOTE = "withheld from the public record (adjudicating wording)."


def contains_verdict_language(text: str) -> bool:
    """True when a model-written sentence adjudicates the claim."""
    if not isinstance(text, str) or not text.strip():
        return False
    return bool(_VERDICT_WORD.search(text) or _INTENSIFIED.search(text))


def public_note(text) -> str:
    """The sentence as written, or the withheld notice. Never rewritten."""
    if not isinstance(text, str) or not text.strip():
        return ""
    return WITHHELD_NOTE if contains_verdict_language(text) else text.strip()
