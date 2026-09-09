"""Day-level date scope — a different DAY in the same month is a different date.

The temporal gate (app/utils/temporal_scope.py) works at month level by
design: "September 2024" is the unit inflation figures are stated in. That
leaves a gap the 2026-09-09 blind review caught: an element pinning a full
date ("SQLite 3.22.0 was released on January 22, 2018") was labelled
`supports` by a source that says "released on Tuesday, January 23, 2018".
Same month, so the temporal gate is silent; the day disagrees, so the
source does not support the element.

This module is deliberately narrow. It fires ONLY when the element pins
exactly one full date and the evidence states at least one full date in the
SAME month and year, none of them the element's day. A source about a
different month is the temporal gate's business; a source that names no
full date is left alone (silence is never a mismatch). Symmetric: a
challenge from the wrong day is scoped exactly as a support is.
"""

import re
from typing import NamedTuple, Optional, Set

from app.utils.temporal_scope import _MONTH_ALT, _MONTHS


class Day(NamedTuple):
    year: int
    month: int
    day: int


# "22 January 2018", "22nd January 2018", "January 22, 2018", "Jan 22 2018",
# "2018-01-22", "22/01/2018" is NOT read (day/month order is ambiguous).
_DAY_MONTH_YEAR = re.compile(
    rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+({_MONTH_ALT})\.?,?\s+(\d{{4}})\b", re.I
)
_MONTH_DAY_YEAR = re.compile(
    rf"\b({_MONTH_ALT})\.?\s+(\d{{1,2}})(?:st|nd|rd|th)?,?\s+(\d{{4}})\b", re.I
)
_ISO_DAY = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")


def stated_days(text: Optional[str]) -> Set[Day]:
    """Every full date the text states."""
    out: Set[Day] = set()
    for m in _DAY_MONTH_YEAR.finditer(text or ""):
        d, mo, y = int(m.group(1)), _MONTHS[m.group(2).lower()], int(m.group(3))
        if 1 <= d <= 31:
            out.add(Day(y, mo, d))
    for m in _MONTH_DAY_YEAR.finditer(text or ""):
        mo, d, y = _MONTHS[m.group(1).lower()], int(m.group(2)), int(m.group(3))
        if 1 <= d <= 31:
            out.add(Day(y, mo, d))
    for m in _ISO_DAY.finditer(text or ""):
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if 1 <= mo <= 12 and 1 <= d <= 31:
            out.add(Day(y, mo, d))
    return out


# A date framed as a STATE boundary ("as of 7 September 2026", "by", "until",
# "since") is not the date of an event. A source about the same state that
# names a different day (the next meeting, the last decision) is not off-day;
# it was scoped wrongly on the 2026-09-09 post-fix regrade (Bank Rate: two
# supports naming "17 September" lost). Only event dates arm the gate.
_STATE_FRAMING = re.compile(
    r"\b(?:as\s+of|as\s+at|by|until|till|since|from|before|after|through|effective)\s*(?:the\s+)?$",
    re.I,
)
_ANY_DATE = re.compile(
    rf"(?:{_DAY_MONTH_YEAR.pattern})|(?:{_MONTH_DAY_YEAR.pattern})|(?:{_ISO_DAY.pattern})",
    re.I,
)


def element_day(description: Optional[str]) -> Optional[Day]:
    """The single EVENT date an element pins, or None.

    None when the element names no full date, more than one, or frames its
    one date as a state boundary ("as of …", "by …", "until …")."""
    days = stated_days(description)
    if len(days) != 1:
        return None
    for m in _ANY_DATE.finditer(description or ""):
        lead = (description or "")[max(0, m.start() - 24) : m.start()]
        if _STATE_FRAMING.search(lead):
            return None
    return days.pop()


def is_off_day(target: Day, evidence_text: Optional[str]) -> bool:
    """True when the evidence states a full date in the target's month and
    year, and none of its full dates is the target day."""
    days = stated_days(evidence_text)
    same_month = {d for d in days if (d.year, d.month) == (target.year, target.month)}
    return bool(same_month) and target not in days


def format_day(d: Day) -> str:
    return f"{d.year:04d}-{d.month:02d}-{d.day:02d}"
