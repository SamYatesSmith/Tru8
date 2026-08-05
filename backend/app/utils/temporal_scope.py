"""Temporal-scope tagger — F1 (2026-08-05).

Design: audit/2026-08-05_agent_tier_quality_findings.md (F1). A mechanical
post-process on mapping output that scopes out evidence about a DIFFERENT
period from the one an element pins, so a settled fact is not made to look
contested by figures from other months.

WHY IT IS MECHANICAL AND NOT A PROMPT
-------------------------------------
`MAPPING_PROMPT` has instructed the model for months that "evidence from one
time period does NOT support a claim about a different time period" — while the
evidence block it is given carries only id, title, tier, type and snippet. No
date, in any form. The rule was unaskable, and the failure it was meant to
prevent happened in production (check `618efbc4`):

    element: "UK CPI in September 2024 was less than 2 percent"   [TRUE, 1.7%]
    -> state: disputed, 4 supports / 6 challenges

The six challenges were 2.6% in June, 2.0% in May 2024, 3.27% for calendar
2024, and undated commentary about the 2% target. None of them bears on
September 2024. This is invariant #7's false-balancing failure.

NF-11: fragile behaviour needs a mechanical rule, not a prompt.

WHAT IT DOES, AND DELIBERATELY DOES NOT DO
------------------------------------------
Where an element pins ONE unambiguous month-level period and an evidence item
asserts periods of which NONE match it, the relationship is scoped to
"context". It NEVER deletes evidence and NEVER changes a state directly — the
state is derived downstream from the relationships, so scoping is visible in
the same basis metadata everything else is (invariant #5: every exclusion has
a receipt).

**Symmetric on purpose.** It scopes `supports` exactly as it scopes
`challenges`. A source about June bears on September in neither direction, and
a gate that only ever removed challenges would be a sycophancy mechanism —
precisely what invariant #7 forbids. Symmetric scoping can equally turn a
`supported` element into `unresolved`.

It fires ONLY when all three hold:

  1. the element carries exactly one distinct month-level period, AND
  2. the evidence text carries at least one explicit period, AND
  3. none of the evidence's periods matches the element's.

Evidence with no explicit period is LEFT ALONE. That leaves part of the
observed failure unfixed — the undated "still above target" commentary keeps
its `challenges` — because inferring a period from silence is guessing, and
over-firing hides genuine disputes, which is the same invariant breached from
the other side.

A bare year does NOT match a month-level element: "3.27% for 2024" is an annual
figure and does not establish or refute a September figure. That asymmetry is
the point of tracking granularity rather than just year.
"""

from __future__ import annotations

import re
from typing import List, NamedTuple, Optional, Set

_MONTHS = {
    "january": 1,
    "jan": 1,
    "february": 2,
    "feb": 2,
    "march": 3,
    "mar": 3,
    "april": 4,
    "apr": 4,
    "may": 5,
    "june": 6,
    "jun": 6,
    "july": 7,
    "jul": 7,
    "august": 8,
    "aug": 8,
    "september": 9,
    "sep": 9,
    "sept": 9,
    "october": 10,
    "oct": 10,
    "november": 11,
    "nov": 11,
    "december": 12,
    "dec": 12,
}

_MONTH_ALT = "|".join(sorted(_MONTHS, key=len, reverse=True))

# "September 2024", "Sept 2024"
_MONTH_YEAR = re.compile(rf"\b({_MONTH_ALT})\.?\s+(\d{{4}})\b", re.I)
# "26 October 2023"
_DAY_MONTH_YEAR = re.compile(rf"\b\d{{1,2}}\s+({_MONTH_ALT})\.?\s+(\d{{4}})\b", re.I)
# "October 26, 2023"
_MONTH_DAY_YEAR = re.compile(rf"\b({_MONTH_ALT})\.?\s+\d{{1,2}},\s*(\d{{4}})\b", re.I)
# "2024-09", "2024-09-16"
_ISO = re.compile(r"\b(\d{4})-(\d{2})(?:-\d{2})?\b")
# A bare four-digit year in a plausible range. Deliberately narrow: "1.7" or
# "2%" must never read as a year, and neither should arbitrary large numbers.
_YEAR = re.compile(r"\b(19\d{2}|20\d{2})\b")


class Period(NamedTuple):
    """A point in time at the granularity it was actually stated."""

    year: int
    month: Optional[int]  # None = the text said only a year

    @property
    def is_month_level(self) -> bool:
        return self.month is not None


def extract_periods(text: Optional[str]) -> Set[Period]:
    """Every explicit period the text states, at its stated granularity.

    Month-level mentions suppress the bare-year reading of the same string, so
    "September 2024" yields one month-level period rather than also (2024, None).
    """
    if not text:
        return set()

    periods: Set[Period] = set()
    consumed: List[tuple] = []

    for pattern in (_DAY_MONTH_YEAR, _MONTH_DAY_YEAR, _MONTH_YEAR):
        for m in pattern.finditer(text):
            periods.add(Period(int(m.group(2)), _MONTHS[m.group(1).lower()]))
            consumed.append(m.span())

    for m in _ISO.finditer(text):
        month = int(m.group(2))
        if 1 <= month <= 12:
            periods.add(Period(int(m.group(1)), month))
            consumed.append(m.span())

    for m in _YEAR.finditer(text):
        # Skip years already accounted for by a month-level match.
        if any(start <= m.start() < end for start, end in consumed):
            continue
        periods.add(Period(int(m.group(1)), None))

    return periods


def element_period(description: Optional[str]) -> Optional[Period]:
    """The single month-level period an element pins, or None.

    Returns None when the element names no month-level period, or names more
    than one — an element spanning "between March 2020 and June 2021" is not
    pinned to a point and must not be scoped against.
    """
    month_level = {p for p in extract_periods(description) if p.is_month_level}
    return month_level.pop() if len(month_level) == 1 else None


def is_out_of_period(target: Period, evidence_text: Optional[str]) -> bool:
    """True when the evidence states periods and none of them is the target.

    Silence is never out-of-period: evidence stating no period at all returns
    False and is left exactly as the mapper labelled it.
    """
    periods = extract_periods(evidence_text)
    if not periods:
        return False
    return target not in periods
