"""Necessary source-time anchors for explicit day-scoped assertions.

An anchor is not entailment proof. This deliberately narrow, opt-in gate cannot
resolve implicit dates, relative dates, synonyms or arbitrary effective intervals.
It never uses a model paraphrase, publication timestamp or the system clock.
"""

import re

from app.services.temporal_provenance import _DATE, _parse_stated_date
from app.services.text_provenance import _terms

_POINT = re.compile(
    rf"\b(?:as\s+of|on(?:\s+the\s+(?:morning|afternoon|evening)\s+of)?)\s+(?P<date>{_DATE})\b",
    re.I,
)
_START = re.compile(rf"\b(?:effective|in\s+force)\s+from\s+(?P<date>{_DATE})\b", re.I)
_END = re.compile(
    rf"\b(?:effective\s+|in\s+force\s+)?until\s+(?P<date>{_DATE})\b", re.I
)
_NOT_ESTABLISHED = re.compile(
    r"\b(?:not|never|no|proposed|planned|proposal|plan|may|might|could|would|will|if|unless|pending)\b",
    re.I,
)
_GENERIC = {"units", "unit", "date", "dated", "current", "next", "due", "scheduled"}
_QUANTITY = re.compile(r"\b\d+(?:[.,]\d+)?\s*(?:%|[a-z]+\b)", re.I)


def target_day(element, claim):
    """Read explicit scope only; inherit a leading claim-level 'as of' clause."""
    own = {_parse_stated_date(m.group("date")) for m in _POINT.finditer(element or "")}
    own.discard(None)
    if len(own) == 1:
        return next(iter(own))
    if own:
        return None  # Multiple periods require a richer contract.
    leading = re.match(rf"\s*As\s+of\s+(?P<date>{_DATE})\b", claim or "", re.I)
    return _parse_stated_date(leading.group("date")) if leading else None


def _fact_terms(text):
    return {
        t for t in _terms(re.sub(_DATE, " ", text, flags=re.I)) if not t.isnumeric()
    } - _GENERIC


def _quantities(text):
    # A number alone is not a topic link. Preserve its adjacent unit and remove
    # dates first, so a shared day/month cannot masquerade as a measurement.
    without_dates = re.sub(_DATE, " ", text, flags=re.I)
    return {
        re.sub(r"\s+", "", m.group().lower()) for m in _QUANTITY.finditer(without_dates)
    }


def source_time_anchor(evidence, element, day):
    """Find an original sentence linking this topic to a day/explicit interval.

    Lexical overlap only avoids accepting dates about wholly different topics;
    it does not establish that the cited fact supports or contradicts the element.
    Return the complete sentence and extraction identity for audit, never a new
    relationship. A missing anchor means only 'not established in retained text'.
    """
    from app.services.passage_mapping import valid_passages

    terms = _fact_terms(element)
    quantities = _quantities(element)
    if not terms and not quantities:
        return None
    for passage in valid_passages(evidence):
        text = passage["text"]
        for sentence in re.finditer(r"[^\n]+?(?:[.!?](?=\s|$)|(?=\n)|$)", text):
            quote = sentence.group()
            # Windows may start/end mid-sentence, losing a qualification.
            if sentence.start() == 0 and passage["start"] != 0:
                continue
            if (
                sentence.end() == len(text)
                and passage["end"]
                < evidence["text_provenance"]["extraction_characters"]
                and not quote.rstrip().endswith((".", "!", "?"))
            ):
                continue
            if not (
                terms.intersection(_fact_terms(quote))
                or quantities.intersection(_quantities(quote))
            ):
                continue
            point = any(
                _parse_stated_date(m.group("date")) == day
                for m in _POINT.finditer(quote)
            )
            interval = False
            starts = [
                _parse_stated_date(m.group("date")) for m in _START.finditer(quote)
            ]
            ends = [_parse_stated_date(m.group("date")) for m in _END.finditer(quote)]
            if len(starts) == 1 and starts[0] and not _NOT_ESTABLISHED.search(quote):
                interval = starts[0] <= day and (
                    not ends
                    or (len(ends) == 1 and ends[0] is not None and day <= ends[0])
                )
            if point or interval:
                start = passage["start"] + sentence.start()
                return {
                    "passage_id": passage["id"],
                    "quote": quote,
                    "start": start,
                    "end": start + len(quote),
                    "extraction_sha256": evidence["text_provenance"][
                        "extraction_sha256"
                    ],
                }
    return None
