"""Figure scope — a support must STATE the element's figure, not let us derive it.

The 2026-09-23 re-run of the known-truth set (audit/2026-09-23_figure_scope_gate_design.md)
left two records wrong in one way. Legum: "$898 million to $2.87 billion" badged
`supported` by sources stating $600m–$1.86bn for 2025 and $220m–$750m for Q1 2026 — the
mapper summed the part-periods. Kennedy: an 83% seasonal norm badged `supported` by
"68%, ~16 points below the five-year average" — the mapper did the subtraction. The
mapping prompt already forbids both; neither source says the figure.

This module is deliberately narrow and mechanical. It reads three kinds of figure —
percentages, currency amounts and counts of a named thing — and answers one question:
does the source state figures of the element's kind, none of which is the element's?
Silence (no figure of that kind) is never a mismatch. Any ONE matching figure satisfies
an element stating several ("£22m rather than the £53m forecast").

⚠️ Supports only — the caller decides that, and it is measured, not assumed: the mirror
(a challenge whose only figures MATCH) fired 4 times across 61 stored records and was
wrong every time. A challenge that repeats the number is disputing its meaning.

Known limitation: a source stating the same value about a different quantity matches.
The gate then leaves the mapper's call standing — no worse than without it.
"""

import re
from typing import List, NamedTuple, Optional, Tuple


class Figure(NamedTuple):
    kind: str  # "pct", "cur$", "cur£", "cur€", or "n:<noun>"
    value: float
    precision: float  # half the unit of the last stated digit


class ElementFigures(NamedTuple):
    figures: Tuple[Figure, ...]
    approximate: bool
    exact: bool


_MULTIPLIERS = {
    "thousand": 1e3,
    "k": 1e3,
    "million": 1e6,
    "mn": 1e6,
    "m": 1e6,
    "billion": 1e9,
    "bn": 1e9,
    "b": 1e9,
    "trillion": 1e12,
    "tn": 1e12,
}

# A number not glued to a word or decimal on its left ("CO2", "v1.2" are not figures).
_NUM = r"(?<![\w.])(\d{1,3}(?:,\d{3})+|\d+)(?:\.(\d+))?"

_PCT = re.compile(_NUM + r"\s?(?:%|per ?cent\b|percent\b)", re.I)
_CUR = re.compile(
    r"(?:US)?([$£€])\s?"
    + _NUM.replace(r"(?<![\w.])", "")
    + r"(?:\s?(thousand|million|billion|trillion|bn|mn|tn|k|m|b)\b)?",
    re.I,
)
_CNT = re.compile(
    _NUM
    + r"(?:\s?(thousand|million|billion|trillion))?\s+([a-z]{3,})(?:\s+([a-z]{3,}))?",
    re.I,
)

_APPROX = re.compile(
    r"\b(?:about|around|approximately|approx|roughly|almost|nearly|some|"
    r"close to|estimated)\b|~",
    re.I,
)

# A figure after one of these is a THRESHOLD, not a value: "unemployment fell
# below 5%" is supported by a source stating 4.2%. Such figures never arm the
# gate — matching a bound against a value would scope honest support (the
# coverage-recovery fixture caught exactly this on the first full run).
_BOUND_BEFORE = re.compile(
    r"\b(?:below|under|less than|fewer than|lower than|above|over|more than|"
    r"greater than|higher than|at least|at most|up to|in excess of|beyond|"
    r"upwards of|exceed(?:ed|s|ing)?|surpass(?:ed|es|ing)?|top(?:ped|s)?)\s*$",
    re.I,
)
_EXACT = re.compile(r"\bexactly\b", re.I)
_POINTS = re.compile(_NUM + r"\s?(?:percentage|basis)?\s?(?:points?|pp|bps?)\b", re.I)

# Words that follow a number without naming what is counted. Months keep a day of
# the month ("11 September") from reading as a count of Septembers.
_NOT_A_NOUN = frozenset(
    """
    per percent percentage points point and or of the to in on at a an than rather
    compared from for with by as net million billion trillion thousand years year
    months month weeks week days day hours hour times time
    january february march april may june july august september october november december
    """.split()
)


def _value(integer: str, decimal: Optional[str], mult: Optional[str]) -> float:
    number = float(integer.replace(",", "") + ("." + decimal if decimal else ""))
    return number * _MULTIPLIERS.get((mult or "").lower(), 1.0)


def _precision(integer: str, decimal: Optional[str], mult: Optional[str]) -> float:
    """Half the unit of the last stated digit.

    Trailing zeros read as rounding only for comma-grouped or multiplied figures
    ("29,000 trades", "£30m") — a bare "80%" is eighty, not "somewhere in the 80s".
    """
    scale = _MULTIPLIERS.get((mult or "").lower(), 1.0)
    if decimal:
        return 0.5 * 10 ** -len(decimal) * scale
    digits = integer.replace(",", "")
    zeros = len(digits) - len(digits.rstrip("0"))
    if "," not in integer and not mult:
        zeros = 0
    return 0.5 * 10**zeros * scale


def _noun(word: Optional[str]) -> Optional[str]:
    if not word:
        return None
    w = word.lower()
    if w in _NOT_A_NOUN:
        return None
    return w[:-1] if w.endswith("s") and not w.endswith("ss") else w


def _is_year(integer: str, decimal: Optional[str], mult: Optional[str]) -> bool:
    if decimal or mult or "," in integer:
        return False
    return 1800 <= int(integer) <= 2100


def _scan(text: str) -> List[Tuple[Figure, int]]:
    """Every figure the text states, with the offset where its expression starts."""
    out: List[Tuple[Figure, int]] = []
    taken: List[Tuple[int, int]] = []

    for m in _PCT.finditer(text):
        figure = Figure("pct", _value(m[1], m[2], None), _precision(m[1], m[2], None))
        out.append((figure, m.start()))
        taken.append(m.span())
    for m in _CUR.finditer(text):
        figure = Figure(
            "cur" + m[1], _value(m[2], m[3], m[4]), _precision(m[2], m[3], m[4])
        )
        out.append((figure, m.start()))
        taken.append(m.span())
    for m in _CNT.finditer(text):
        if any(a < m.end(1) and m.start(1) < b for a, b in taken):
            continue
        if _is_year(m[1], m[2], m[3]):
            continue
        value, precision = _value(m[1], m[2], m[3]), _precision(m[1], m[2], m[3])
        # "28,700 securities trades": either word may be the thing counted.
        for word in (m[4], m[5]):
            noun = _noun(word)
            if noun:
                out.append((Figure("n:" + noun, value, precision), m.start()))
    return out


def stated_figures(text: Optional[str]) -> List[Figure]:
    """Every percentage, currency amount and counted quantity the text states."""
    return [figure for figure, _ in _scan(text or "")]


def element_figures(description: Optional[str]) -> Optional[ElementFigures]:
    """The point figures an element states, or None when it states none.

    Thresholds ("below 5%", "more than 20,000 trades") are left out.
    """
    text = description or ""
    figures = [
        figure
        for figure, start in _scan(text)
        if not _BOUND_BEFORE.search(text[max(0, start - 30) : start])
    ]
    if not figures:
        return None
    return ElementFigures(
        figures=tuple(figures),
        approximate=bool(_APPROX.search(description or "")),
        exact=bool(_EXACT.search(description or "")),
    )


def _matches(element: ElementFigures, want: Figure, have: Figure) -> bool:
    if want.kind != have.kind:
        return False
    tolerance = want.precision
    if element.approximate:
        tolerance = max(tolerance, 0.05 * abs(want.value))
    if not element.exact:
        tolerance += have.precision
    return abs(want.value - have.value) <= tolerance


def same_kind_figures(element: ElementFigures, text: Optional[str]) -> List[Figure]:
    kinds = {f.kind for f in element.figures}
    return [f for f in stated_figures(text) if f.kind in kinds]


def rests_on_a_figure(element: ElementFigures, reasoning: Optional[str]) -> bool:
    """Does the mapper's reasoning for a reference cite a figure of the element's kind?

    An element can assert a figure AND something else ("the mini-budget caused
    yields to spike to 5.1%"). A source supporting only the cause, whose reasoning
    names no figure, is not claiming the number and is left alone — the replay
    bench caught exactly this on TRU-B4A3-C42D (2026-09-23). All 24 fires on the
    61-record prototype cite a figure in their reasoning, so this costs nothing
    on the failures the gate exists for.
    """
    kinds = {f.kind for f in element.figures}
    if any(f.kind in kinds for f in stated_figures(reasoning)):
        return True
    # A percentage reached by arithmetic on a GAP ("15 percentage points below the
    # average") rests on a number too, though a gap is not itself a `pct` figure.
    # Kennedy 54b8699b (2026-09-23): euractiv states 62% and "15 percentage points
    # below the 10-year average"; the mapper filed it as supporting an 83% norm.
    return "pct" in kinds and bool(_POINTS.search(reasoning or ""))


def is_unstated_figure(element: ElementFigures, text: Optional[str]) -> bool:
    """True when the text states figures of the element's kind and none is the element's.

    Silence is never a mismatch: a source with no figure of that kind returns False.
    """
    stated = same_kind_figures(element, text)
    if not stated:
        return False
    return not any(
        _matches(element, want, have) for want in element.figures for have in stated
    )


def format_figure(f: Figure) -> str:
    value = f"{f.value:,.10g}"
    if f.kind == "pct":
        return f"{value}%"
    if f.kind.startswith("cur"):
        return f"{f.kind[3:]}{value}"
    return f"{value} {f.kind[2:]}"
