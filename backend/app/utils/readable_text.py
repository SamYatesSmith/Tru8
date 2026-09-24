"""Unreadable-text floor (A− M2, 2026-09-24).

A reference whose source text is a JavaScript wall, a login wall or an empty
shell cannot bear on an element in either direction. Record 580fd5b4 filed
PurpleAir as a CHALLENGE on retained text that read, in full, "PurpleAir You
need to enable JavaScript to run this app".

Measured on the 156 directional references of the 19 graded records
(2026-09-24): a raw word count does not separate them — PurpleAir has 6
content words and a genuine ACS abstract has 7. Removing the title and any
boilerplate sentence first, then requiring 5 content words, fires on exactly
one reference: PurpleAir. Symmetric: supports and challenges alike.
"""

from __future__ import annotations

import re
from typing import Optional

_BOILERPLATE = re.compile(
    r"[^.!?\n]*(?:enable\s+javascript|javascript\s+is\s+(?:disabled|required)|"
    r"enable\s+cookies|access\s+denied|checking\s+your\s+browser|"
    r"verify\s+you\s+are\s+(?:a\s+)?human|register\s*/?\s*login|"
    r"sign\s+in\s+to\s+(?:continue|read)|subscribe\s+to\s+(?:continue|read)|"
    r"page\s+not\s+found|404\s+not\s+found)[^.!?\n]*[.!?]?",
    re.IGNORECASE,
)
_STOP = frozenset(
    "the and for that with this from have has had were was been are its their "
    "there which will would could should about into than then them they what "
    "when where who whom your you our not but can may also more most such only "
    "over under need run app".split()
)
MIN_CONTENT_WORDS = 5


def content_word_count(text: Optional[str], title: Optional[str] = None) -> int:
    """Distinct content words left once the title and boilerplate are removed."""
    body = text or ""
    if title:
        body = body.replace(title, " ")
    body = _BOILERPLATE.sub(" ", body)
    words = {
        w.lower()
        for w in re.findall(r"[A-Za-z]{3,}", body)
        if w.lower() not in _STOP
    }
    # A data table is content, not a wall: Statista's retained text on record
    # b8cf098b is mostly figures ("2025 |427.49 |2024 |425.4").
    numbers = set(re.findall(r"\d[\d.,]*\d", body))
    return len(words) + len(numbers)


def is_unreadable(text: Optional[str], title: Optional[str] = None) -> bool:
    """A wall with little left once it is removed, or text that is all but empty.

    Word count ALONE is not the test: a short genuine sentence ("The release
    setting is 37 units.") has four content words and is evidence. The floor
    needs a wall or boilerplate sentence to have been present, unless the text
    is effectively empty (fewer than two content words).
    """
    if _BOILERPLATE.search(text or ""):
        # A wall: judge what is left once the title and the wall are removed.
        return content_word_count(text, title) < MIN_CONTENT_WORDS
    # No wall: the title counts as content (a snippet that IS the headline
    # still states something), so only near-empty text fires.
    return content_word_count(text) < 2
