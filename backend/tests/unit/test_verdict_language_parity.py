"""The PDF's verdict-language rule must equal the frontend's, byte for byte.

``web/lib/element-caveat.ts`` is the source of truth (Fix 1, 2026-09-02). If
either side changes its regex without the other, this fails.
"""

import re
from pathlib import Path

from app.utils.verdict_language import (
    INTENSIFIED_EVIDENCE_SOURCE,
    VERDICT_WORD_SOURCE,
    WITHHELD_NOTE,
    contains_verdict_language,
    public_note,
)

TS = Path(__file__).resolve().parents[3] / "web" / "lib" / "element-caveat.ts"


def _ts_regex(name: str) -> str:
    src = TS.read_text(encoding="utf-8")
    m = re.search(rf"const {name} =\s*/(.+?)/i;", src, re.S)
    assert m, f"{name} not found in element-caveat.ts"
    return m[1].strip()


def test_regexes_match_the_frontend():
    assert _ts_regex("VERDICT_WORD_RE") == VERDICT_WORD_SOURCE
    assert _ts_regex("INTENSIFIED_EVIDENCE_RE") == INTENSIFIED_EVIDENCE_SOURCE


def test_withheld_note_matches_the_frontend():
    src = (TS.parent / "system-interpretation.ts").read_text(encoding="utf-8")
    assert f"'{WITHHELD_NOTE}'" in src


def test_limits_pass_and_adjudications_are_withheld():
    limit = "The £22 million figure is an estimated loss, not official outturn data."
    verdict = "The evidence consistently refutes this element."
    assert not contains_verdict_language(limit)
    assert contains_verdict_language(verdict)
    assert public_note(limit) == limit
    assert public_note(verdict) == WITHHELD_NOTE
    assert public_note(None) == "" and public_note("  ") == ""
