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


def element_day(description: Optional[str]) -> Optional[Day]:
    """The single full date an element pins, or None (none, or more than one)."""
    days = stated_days(description)
    return days.pop() if len(days) == 1 else None


def is_off_day(target: Day, evidence_text: Optional[str]) -> bool:
    """True when the evidence states a full date in the target's month and
    year, and none of its full dates is the target day."""
    days = stated_days(evidence_text)
    same_month = {d for d in days if (d.year, d.month) == (target.year, target.month)}
    return bool(same_month) and target not in days


def format_day(d: Day) -> str:
    return f"{d.year:04d}-{d.month:02d}-{d.day:02d}"
