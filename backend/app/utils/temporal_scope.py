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

# A month name on its own. Used ONLY inside an interval's end fragment, where the
# connective ("…to September") has already established the temporal context — see
# `_first_month_level`. Never used for free-text bare months, which need the
# preposition in `_BARE_MONTH`.
_MONTH_TOKEN = re.compile(rf"\b({_MONTH_ALT})\b", re.I)


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


# ---------------------------------------------------------------------------
# Interval measures — the SECOND defect in production check 757f02c2
# ---------------------------------------------------------------------------
#
# The Irish-CSO item was removed by the jurisdiction gate, but the same check
# exposed a mismatch neither gate reaches: a rate of change over an interval is
# identified by the interval's END, not by the months it happens to mention.
#
#     element : "the twelve months to September 2024"          end = 2024-09
#     evidence: "between September 2024 and September 2025"     end = 2025-09
#
# Both name September 2024, so `is_out_of_period` correctly declines — one
# matching mention means the source is talking about our period. But the evidence
# measures a DIFFERENT twelve months, and a UK source making the same period-pair
# error would still be counted as a challenge.
#
# Comparing interval ENDS is what separates them. This is deliberately a separate
# check rather than a change to `is_out_of_period`, so it can only ever scope refs
# the period rule LEFT ALONE — it cannot alter that rule's count or its receipts.

# A period EXPRESSION, not a run of prose. An earlier version captured up to 44
# non-punctuation characters after the connective, which read "12 months to June
# 2024 and the 12 months to June 2025" as ONE interval ending June 2024 — the
# second interval was swallowed by the first fragment, so a two-measure element
# looked pinned to a single measure. Matching the period itself bounds the end
# exactly and lets `finditer` see the second interval.
_PERIOD_EXPR = (
    rf"(?:{_MONTH_ALT})\.?(?:\s*[\s\-/]\s*\d{{2,4}})?|\d{{4}}-\d{{2}}(?:-\d{{2}})?"
)

# "in the 12 months to September 2024", "in the year to September",
# "the annual rate to August 2025", "12-month rate to September 2024"
_TO_INTERVAL = re.compile(
    r"\b(?:(?:\d{1,2}|twelve)[\s-]*month[\s-]*(?:rate|period)?s?"
    r"|year|annual(?:\s+\w+){0,2})"
    rf"\s+to\s+(?:the\s+)?(?P<end>{_PERIOD_EXPR})",
    re.I,
)
# "between September 2024 and September 2025"
_BETWEEN_INTERVAL = re.compile(
    rf"\bbetween\s+(?:{_PERIOD_EXPR})\s+and\s+(?P<end>{_PERIOD_EXPR})", re.I
)
# "from September 2023 to September 2024"
_FROM_TO_INTERVAL = re.compile(
    rf"\bfrom\s+(?:{_PERIOD_EXPR})\s+to\s+(?P<end>{_PERIOD_EXPR})", re.I
)

_INTERVAL_PATTERNS = (_TO_INTERVAL, _BETWEEN_INTERVAL, _FROM_TO_INTERVAL)


def _first_month_level(
    fragment: str, published: Optional[datetime]
) -> Optional[Period]:
    """The nearest month-level period in a fragment, resolving a bare month.

    Nearest rather than any: in "September 2024 was 1.7% against 2% in August"
    the interval's end is the first period named after "to", not the later aside.

    The preposition guard `_bare_month_numbers` applies is deliberately NOT used
    here. This fragment sits immediately after an interval connective ("…to
    September"), which consumed the preposition, so demanding another one makes
    every bare-month interval unreadable — and "in the year to September" is
    ordinary phrasing, not an edge case. Capitalisation is still required, which is
    what keeps the modal "may" and the verb "march" out.
    """
    stated, consumed = _scan(fragment)
    month_level = sorted(p for p in stated if p.is_month_level)
    if month_level:
        return month_level[0]

    if published is None:
        return None
    months = {
        _MONTHS[m.group(1).lower()]
        for m in _MONTH_TOKEN.finditer(fragment)
        if m.group(1)[:1].isupper()
        and not any(start <= m.start(1) < end for start, end in consumed)
    }
    if len(months) != 1:
        return None
    return resolve_bare_month(months.pop(), published)


def interval_ends(
    text: Optional[str],
    published_date=None,
    date_basis: Optional[str] = None,
) -> Set[Period]:
    """Every interval END the text expresses, at month granularity.

    Empty when the text expresses no interval at all — which disarms the measure
    check, the safe direction.
    """
    if not text:
        return set()

    published = None
    if date_basis in TRUSTED_PUBLICATION_BASES:
        published = parse_date(published_date)

    ends: Set[Period] = set()
    for pattern in _INTERVAL_PATTERNS:
        for match in pattern.finditer(text):
            end = _first_month_level(match.group("end"), published)
            if end is not None:
                ends.add(end)
    return ends


def element_interval_end(description: Optional[str]) -> Optional[Period]:
    """The single interval END an element pins, or None.

    None when the element expresses no interval, or more than one — an element
    spanning two measures is not pinned to one and must not be scoped against.
    """
    ends = interval_ends(description)
    return ends.pop() if len(ends) == 1 else None


def is_measure_mismatch(
    target_end: Period,
    evidence_text: Optional[str],
    published_date=None,
    date_basis: Optional[str] = None,
) -> bool:
    """True when the evidence measures intervals and none ends where ours does.

    Requires the evidence to express an interval of its own: without one there is
    no measure to compare, so the item is left exactly as the mapper labelled it.
    """
    ends = interval_ends(evidence_text, published_date, date_basis)
    if not ends:
        return False
    return target_end not in ends


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
