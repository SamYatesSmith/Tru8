"""Mechanical historical-marker detection (F-R2a/R2f, 2026-07-09).

One shared lexicon answering a single question: does this claim text signal
that its subject matter is HISTORICAL — about the past in general, without
naming a year? Claims that do name a year are already handled by the DATE
entity paths (B4 web unwindowing, academic `extract_claim_year` backward
widening); this lexicon covers the gap those paths cannot see, found live on
TRU-C051-3024 ("Many doctors historically recommended a daily glass of red
wine" — no DATE entity → academic search windowed to now−2y → the
French-paradox literature was excluded by construction; see
audit/2026-07-09_retrieval_quality_plan.md).

Mechanical by design (NF-11 rule: mechanical over prompt-only). Consumers:
- app/services/api_adapters/academic.py `_resolve_min_year` (F-R2a): widen
  the paper-search year floor when a historical marker is present.
- app/pipeline/runner.py Stage 3.8 post-filter recovery (F-R2f): drop the
  hardcoded past-year freshness window for historical claims.

Deliberately narrow lexicon: every phrase must UNAMBIGUOUSLY point at the
past. Words like "history"/"historic" alone are excluded ("historic
victory", "history-making") — only adverbial/prepositional past framings
qualify. False negatives are safe (behaviour unchanged); false positives
widen a search window, which costs recall precision on breaking-news claims.
"""

import re

# Word-boundary phrases that frame a claim as being about the past.
_HISTORICAL_MARKERS = re.compile(
    r"(?:"
    r"\bhistorically\b"
    r"|\bhistorical records?\b"
    r"|\bhistorical accounts?\b"
    r"|\btraditionally\b"
    r"|\bused to\b"
    r"|\bin the past\b"
    r"|\bfor (?:centuries|decades|generations)\b"
    r"|\bcenturies ago\b"
    r"|\bdecades ago\b"
    r"|\bin (?:ancient|medieval|victorian|roman) times?\b"
    r"|\bthroughout history\b"
    r"|\bonce (?:widely )?(?:believed|thought|recommended|prescribed|used)\b"
    r"|\bformerly\b"
    r"|\bin (?:earlier|former|previous) (?:times|eras|generations)\b"
    r")",
    re.IGNORECASE,
)


def has_historical_marker(text: str) -> bool:
    """True when the text frames its subject as historical without a year.

    Purely lexical — no LLM, no entities. Callers that also have DATE
    entities should prefer the explicit year (it is more precise); this is
    the fallback signal for year-less historical claims.
    """
    if not text:
        return False
    return bool(_HISTORICAL_MARKERS.search(text))
