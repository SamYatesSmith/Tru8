"""Range-period gate: a source published before a range ends cannot establish
a total or comparison over that range (A− option 3, 2026-09-24).

Design + review: audit/2026-09-24_a_minus_range_period_{design,review}.md.

Record e6e0c00d: GAO's "37 models as of March 2018" was filed as a CHALLENGE to
"Between 2010 and 2020, the CMS Innovation Center launched 54 models", and the
element read disputed. Record 6ad65eb5: a 2021 ONS release covering 2020 was a
challenge to Sweden's excess mortality "in 2020-22". A source written before a
period ends cannot state what happened over the whole of it.

Only for elements that TOTAL or COMPARE over the range (a figure, "lower
than", "the most"...). For a universal or negated element ("grew every year",
"chose not to lock down in 2020-22") a mid-range source is a valid
counterexample, and demoting it would be the sycophancy invariant #7 forbids
(review finding). Symmetric: supports and challenges alike.
"""

from __future__ import annotations

import datetime as _dt
import re
from typing import Any, Dict, Optional, Tuple

from app.utils.temporal_scope import TRUSTED_PUBLICATION_BASES, element_period

#: A range introduced as the claim's PERIOD by a temporal preposition. "the
#: 2010-2020 plan" and "Section 1981-1983" have no preposition and do not arm.
_RANGE = re.compile(
    r"\b(?:between|from|in|during|over|throughout|across|for)\s+"
    r"((?:19|20)\d{2})\s*(?:-|–|—|to|and|through|until)\s*((?:19|20)?\d{2})\b"
    r"(?!\s*(?:plan|budget|strategy|programme|program|framework|act|season|term|"
    r"parliament|agenda|period\s+plan|target)s?\b)",
    re.IGNORECASE,
)
#: A total or comparison over the range.
_AGGREGATE = re.compile(
    r"\b(?:than|lowest|highest|most|least|largest|smallest|biggest|fewest|"
    r"total|overall|cumulative|combined|in\s+all|altogether|"
    # a figure in words: "almost one million clinicians" (record e6e0c00d)
    r"hundred|thousand|million|billion|trillion|dozen)\b",
    re.IGNORECASE,
)
#: Universal or negated: a single counterexample from mid-range bears on these.
_UNIVERSAL = re.compile(
    r"\b(?:every|each)\s+(?:year|month|quarter|season)\b|\bannually\b|"
    r"\bconsistently\b|\balways\b|\bnever\b|\bnot\b|n't\b|\bno\b|\bnone\b|\bwithout\b",
    re.IGNORECASE,
)
_YEARISH = re.compile(r"\b(?:19|20)\d{2}\b")
_FIGURE = re.compile(r"\d")


def element_range(
    description: Optional[str], today: Optional[_dt.date] = None
) -> Optional[Tuple[int, int]]:
    """(start, end) of the closed PAST range an aggregate element spans, or None."""
    text = description or ""
    # One gate owns an element shape: a month-level period is temporal's
    # ("2010-12" can read as December 2010 there).
    if element_period(text) is not None:
        return None
    if _UNIVERSAL.search(text):
        return None
    this_year = (today or _dt.date.today()).year
    for m in _RANGE.finditer(text):
        start = int(m.group(1))
        raw = m.group(2)
        end = int(raw) if len(raw) == 4 else int(m.group(1)[:2] + raw)
        # A one-year span is often a fiscal year ("2019-20" ends in spring);
        # a future end is a forecast, and every source predates it.
        if end - start < 2 or end > this_year:
            continue
        without_range = text[: m.start()] + text[m.end() :]
        figure = _FIGURE.search(_YEARISH.sub(" ", without_range))
        if figure or _AGGREGATE.search(text):
            return start, end
    return None


def _published(ev: Dict[str, Any]) -> Optional[_dt.date]:
    if ev.get("date_basis") not in TRUSTED_PUBLICATION_BASES:
        return None
    value = ev.get("published_date")
    if isinstance(value, _dt.datetime):
        return value.date()
    if isinstance(value, _dt.date):
        return value
    if isinstance(value, str) and len(value) >= 10:
        try:
            return _dt.date.fromisoformat(value[:10])
        except ValueError:
            return None
    return None


def published_before_range_end(ev: Dict[str, Any], end_year: int) -> bool:
    """True when the source's trusted publication date is before 1 December of
    the range's end year. No trusted date never fires."""
    published = _published(ev)
    return published is not None and published < _dt.date(end_year, 12, 1)
