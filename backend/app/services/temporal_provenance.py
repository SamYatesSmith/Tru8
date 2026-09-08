"""Capture temporal statements, without equating a date mention with applicability.

Only retained extraction passages are inspected. No publisher/domain preference,
current clock, publication date or model paraphrase establishes an effective date.
These are review candidates, never input to relationship/state arithmetic.
"""

import re
from datetime import date, datetime

_MONTH = r"(?:January|February|March|April|May|June|July|August|September|October|November|December)"
_DATE = rf"(?:\d{{4}}-\d{{2}}-\d{{2}}|\d{{1,2}} {_MONTH} \d{{4}}|{_MONTH} \d{{1,2}}, \d{{4}})"
_STATEMENT = re.compile(
    rf"\b(?P<marker>effective\s+(?:from|on|until)|in\s+force\s+(?:from|until)|as\s+of)\s+(?P<date>{_DATE})\b",
    re.I,
)
MAX_STATEMENTS = 12


def _context_bounds(text: str, start: int, end: int) -> tuple[int, int]:
    """Keep negation/planning context, never quote only the positive date phrase."""
    left, right = 0, len(text)
    for boundary in re.finditer(r"[.!?](?:\s+|$)|\n", text):
        if boundary.end() <= start:
            left = boundary.end()
        elif boundary.start() >= end:
            right = boundary.end()
            break
    return left, right


def publication_receipt(value, basis=None) -> dict:
    """Preserve the value supplied to capture, including missing/unknown precision."""
    precision = "unknown"
    if isinstance(value, (datetime, date)):
        raw = value.isoformat()
        # An earlier parser may have expanded a year to January 1.
        representation = "normalised_date"
    elif isinstance(value, str):
        raw = value
        representation = "supplied_string"
        cleaned = value.strip()
        if re.fullmatch(r"\d{4}", cleaned):
            precision = "year"
        elif re.fullmatch(r"\d{4}-\d{2}", cleaned):
            try:
                datetime.strptime(cleaned, "%Y-%m")
                precision = "month"
            except ValueError:
                pass
        elif _parse_stated_date(cleaned):
            precision = "day"
        else:
            try:
                datetime.fromisoformat(cleaned.replace("Z", "+00:00"))
                precision = "timestamp" if "T" in cleaned or " " in cleaned else "day"
            except ValueError:
                pass
    else:
        raw = None
        representation = "missing"
    return {
        "supplied_value": raw,
        "representation": representation,
        "precision": precision,
        "date_basis": basis,
    }


def _parse_stated_date(value: str):
    for fmt in ("%Y-%m-%d", "%d %B %Y", "%B %d, %Y"):
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def temporal_receipt(
    passages: list[dict], digest: str, publication, basis=None
) -> dict:
    statements = []
    candidate_count = 0
    for passage in passages:
        for match in _STATEMENT.finditer(passage["text"]):
            stated_date = _parse_stated_date(match.group("date"))
            if not stated_date:
                continue
            candidate_count += 1
            if len(statements) >= MAX_STATEMENTS:
                continue
            marker = match.group("marker").lower()
            kind = (
                "as_of"
                if marker.startswith("as")
                else (
                    "effective_end" if marker.endswith("until") else "effective_start"
                )
            )
            start, end = _context_bounds(passage["text"], match.start(), match.end())
            statements.append(
                {
                    "kind": kind,
                    "stated_date": stated_date,
                    "review_status": "unreviewed",
                    "citation": {
                        "passage_id": passage["id"],
                        "quote": passage["text"][start:end],
                        "start": passage["start"] + start,
                        "end": passage["start"] + end,
                        "extraction_sha256": digest,
                    },
                }
            )
    return {
        "version": 1,
        "publication": publication_receipt(publication, basis),
        "applicability_status": "unestablished",
        "scan_scope": "retained_passages",
        "candidate_count": candidate_count,
        "unretained_candidates": candidate_count - len(statements),
        "statements": statements,
    }
