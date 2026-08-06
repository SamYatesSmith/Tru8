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

2026-08-06 — TWO NAMED MISSES, CLOSED
-------------------------------------
The shipped rule fired ZERO times across the whole replay corpus and across two
live proof checks, and a conservative rule that does not fire proves nothing.
Live check `b0a720f8` showed exactly how it was missing its own failure mode: a
report titled *"UK September-25 CPI Inflation Report"* (published 2025-10-22,
snippet *"CPI increased by 3.8% YoY in September"*) was used to CHALLENGE a
September 2024 element. Three reasons, two of them mechanical:

  1. `September-25` — a two-digit year behind a delimiter. Not parsed. Neither
     was `September-2025`, because the month/year pattern required whitespace.
  2. The snippet names a month with NO year anywhere. Not parsed.
  3. The rule ignored `published_date` entirely.

(1) is pure lexical tightening. (2)+(3) together are an INFERENCE — the source
never stated the year — so they are deliberately separable and separately
disableable via ENABLE_TEMPORAL_PUBLICATION_RESOLUTION. This corrects the
original reasoning that `published_date` must not be used at all: it is a poor
guide to the period a source *covers*, but a good one for resolving a bare month
the source *names*. A report published 22 Oct 2025 saying "in September" means
September 2025.

Three guards keep the inference from over-firing, because over-firing hides
genuine disputes — invariant #7 breached from the other side:

  * PROVENANCE. Only `date_basis` values in TRUSTED_PUBLICATION_BASES resolve a
    bare month. `url_inferred_suspect` is refused by name: F2 classified it as
    probably the host's upload date, not publication. Unknown/absent provenance
    is refused too — trust is opt-in.
  * A TEMPORAL PREPOSITION must precede the month ("in September", "to
    September"). This is what stops the modal verb "may" — and "march" as a
    verb — being read as a month.
  * CAPITALISATION. "in May" is a month; "continued to march" is not. Both
    guards are needed: the preposition alone admits "began to march".

Residual, accepted and recorded rather than hidden: a forward-looking mention
("the target for December", published October) resolves to the PREVIOUS
December, and a year-only `published_date` parses to 1 January, which skews the
same comparison. Both are visible in the receipt (`period_from`, `date_basis`),
so a wrong scoping is auditable rather than silent.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import List, NamedTuple, Optional, Set

from app.utils.date_provenance import (
    DATE_BASIS_API,
    DATE_BASIS_ENGINE,
    DATE_BASIS_PAGE,
)
from app.utils.date_utils import parse_date

#: `date_basis` values whose date may resolve a bare month. Deliberately an
#: allowlist: `url_inferred_suspect` is likely an upload path, and a missing
#: basis tells us nothing, so neither earns the inference.
TRUSTED_PUBLICATION_BASES = frozenset(
    {DATE_BASIS_PAGE, DATE_BASIS_ENGINE, DATE_BASIS_API}
)

# Pivot for two-digit years. "Sep-25" is 2025; "Jan-99" is 1999.
_TWO_DIGIT_PIVOT = 79

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

# "September 2024", "Sept 2024", and (2026-08-06) "September-2025", "Sep/2025".
# The separator was whitespace-only, which missed every hyphenated report title.
_MONTH_YEAR = re.compile(rf"\b({_MONTH_ALT})\.?\s*[\s\-/]\s*(\d{{4}})\b", re.I)
# "September-25", "Sep/25" — a two-digit year, DELIMITER-STRICT on purpose.
# A bare space is not accepted: "September 25" is far more likely to be the 25th
# of September than the year 2025, and reading a day as a year would scope out
# on-period evidence. The hyphen/slash forms are how report titles label periods.
_MONTH_SHORT_YEAR = re.compile(rf"\b({_MONTH_ALT})\.?\s*[-/]\s*(\d{{2}})\b", re.I)
# "26 October 2023"
_DAY_MONTH_YEAR = re.compile(rf"\b\d{{1,2}}\s+({_MONTH_ALT})\.?\s+(\d{{4}})\b", re.I)
# "October 26, 2023"
_MONTH_DAY_YEAR = re.compile(rf"\b({_MONTH_ALT})\.?\s+\d{{1,2}},\s*(\d{{4}})\b", re.I)
# "2024-09", "2024-09-16"
_ISO = re.compile(r"\b(\d{4})-(\d{2})(?:-\d{2})?\b")
# A bare four-digit year in a plausible range. Deliberately narrow: "1.7" or
# "2%" must never read as a year, and neither should arbitrary large numbers.
_YEAR = re.compile(r"\b(19\d{2}|20\d{2})\b")

# A month named with no year attached, behind a temporal preposition. Both this
# and the capitalisation check in `_bare_month_numbers` are required: the
# preposition alone still admits "began to march", and capitalisation alone
# still admits a sentence-initial "May".
_BARE_MONTH = re.compile(
    rf"\b(?:in|for|during|through|to|of|since|until|by)\s+({_MONTH_ALT})\b",
    re.I,
)


class Period(NamedTuple):
    """A point in time at the granularity it was actually stated."""

    year: int
    month: Optional[int]  # None = the text said only a year

    @property
    def is_month_level(self) -> bool:
        return self.month is not None


class PeriodReading(NamedTuple):
    """What the evidence says about time, split by how we came to know it.

    `stated` is what the text itself asserts. `inferred` is what a bare month
    resolved to using the publication date — a weaker basis, kept separate so
    the receipt can say which one drove a scoping decision.
    """

    stated: Set[Period]
    inferred: Set[Period]

    @property
    def all_periods(self) -> Set[Period]:
        return self.stated | self.inferred


def _expand_two_digit_year(value: int) -> int:
    return 2000 + value if value <= _TWO_DIGIT_PIVOT else 1900 + value


def _scan(text: str) -> tuple[Set[Period], List[tuple]]:
    """Periods stated in the text, plus the spans month-level matches consumed."""
    periods: Set[Period] = set()
    consumed: List[tuple] = []

    for pattern in (_DAY_MONTH_YEAR, _MONTH_DAY_YEAR, _MONTH_YEAR):
        for m in pattern.finditer(text):
            periods.add(Period(int(m.group(2)), _MONTHS[m.group(1).lower()]))
            consumed.append(m.span())

    for m in _MONTH_SHORT_YEAR.finditer(text):
        # A four-digit form already read here wins — never re-read its tail.
        if any(start <= m.start() < end for start, end in consumed):
            continue
        periods.add(
            Period(
                _expand_two_digit_year(int(m.group(2))),
                _MONTHS[m.group(1).lower()],
            )
        )
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

    return periods, consumed


def extract_periods(text: Optional[str]) -> Set[Period]:
    """Every explicit period the text states, at its stated granularity.

    Month-level mentions suppress the bare-year reading of the same string, so
    "September 2024" yields one month-level period rather than also (2024, None).
    """
    if not text:
        return set()
    return _scan(text)[0]


def _bare_month_numbers(text: str, consumed: List[tuple]) -> Set[int]:
    """Months named with no year attached, behind a temporal preposition.

    Capitalisation is required. Together with the preposition in `_BARE_MONTH`
    this is what keeps the modal "may" and the verb "march" out: "inflation may
    rise" has no preposition, "continued to march" has no capital.
    """
    months: Set[int] = set()
    for m in _BARE_MONTH.finditer(text):
        # The month token, not the preposition, is what a month-year match ate.
        if any(start <= m.start(1) < end for start, end in consumed):
            continue
        token = m.group(1)
        if not token[:1].isupper():
            continue
        months.add(_MONTHS[token.lower()])
    return months


def resolve_bare_month(month: int, published: datetime) -> Period:
    """The year a bare month most likely means, given when it was published.

    A report published October 2025 saying "in September" means September 2025.
    Saying "in December" means December 2024 — December 2025 had not happened.
    """
    year = published.year if month <= published.month else published.year - 1
    return Period(year, month)


def read_evidence_periods(
    text: Optional[str],
    published_date=None,
    date_basis: Optional[str] = None,
) -> PeriodReading:
    """Everything we can establish about the periods an evidence item concerns.

    Pass `published_date`/`date_basis` to allow bare-month resolution; pass
    neither (or leave the flag off upstream) and this reduces exactly to the
    stated-periods-only behaviour F1 shipped with.
    """
    if not text:
        return PeriodReading(set(), set())

    stated, consumed = _scan(text)

    if date_basis not in TRUSTED_PUBLICATION_BASES:
        return PeriodReading(stated, set())

    published = parse_date(published_date)
    if published is None:
        return PeriodReading(stated, set())

    inferred = {
        resolve_bare_month(month, published)
        for month in _bare_month_numbers(text, consumed)
    }
    return PeriodReading(stated, inferred - stated)


def element_period(description: Optional[str]) -> Optional[Period]:
    """The single month-level period an element pins, or None.

    Returns None when the element names no month-level period, or names more
    than one — an element spanning "between March 2020 and June 2021" is not
    pinned to a point and must not be scoped against.
    """
    month_level = {p for p in extract_periods(description) if p.is_month_level}
    return month_level.pop() if len(month_level) == 1 else None


def is_out_of_period(
    target: Period,
    evidence_text: Optional[str],
    published_date=None,
    date_basis: Optional[str] = None,
) -> bool:
    """True when the evidence carries periods and none of them is the target.

    Silence is never out-of-period: evidence carrying no period at all returns
    False and is left exactly as the mapper labelled it.
    """
    periods = read_evidence_periods(evidence_text, published_date, date_basis)
    if not periods.all_periods:
        return False
    return target not in periods.all_periods
