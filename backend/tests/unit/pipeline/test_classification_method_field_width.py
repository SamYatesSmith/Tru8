"""Regression test for the classification_method varchar(20) overflow bug.

Live test 2026-05-07 caught a StringDataRightTruncationError when Bug D
fired on the TRU-7C40 mammogram check: 'domain_concentration_cap'
(24 chars) overflowed the varchar(20) column. Three pre-existing B3
quality-floor values had the same shape (silently broken since
`dabec21` until any content triggered them).

This test scans the pipeline source for classification_method literals
and asserts each fits within the Evidence model's declared max_length.
Adding a future provenance value longer than the limit will fail this
test before it can ship.
"""

import re
from pathlib import Path

from app.models.check import Evidence


PIPELINE_DIR = Path(__file__).resolve().parents[3] / "app" / "pipeline"

# Capture: ev["classification_method"] = "..."  /  evidence["classification_method"] = "..."
_LITERAL_RE = re.compile(
    r'classification_method["\']\s*[\]=]\s*=?\s*["\']([^"\']+)["\']'
)


def _collect_classification_method_literals() -> set[str]:
    found: set[str] = set()
    for py in PIPELINE_DIR.rglob("*.py"):
        text = py.read_text(encoding="utf-8")
        for match in _LITERAL_RE.finditer(text):
            value = match.group(1)
            # Skip placeholders the regex might catch from comments / docstrings
            # (e.g. capture only literals that look like tokens).
            if re.fullmatch(r"[A-Za-z][A-Za-z0-9_+\-]*", value):
                found.add(value)
    return found


def test_classification_method_field_max_length_at_least_30():
    # Floor for the model field; some pre-existing B3 floor values are 30 chars.
    field = Evidence.model_fields["classification_method"]
    max_len = field.metadata[0].max_length if field.metadata else None
    # Pydantic v2 stores the constraint in .metadata; fall back to schema if needed.
    if max_len is None:
        for m in field.metadata or []:
            if hasattr(m, "max_length"):
                max_len = m.max_length
                break
    assert max_len is not None, "classification_method must declare a max_length"
    assert max_len >= 30, (
        f"Evidence.classification_method max_length is {max_len}, "
        f"but pre-existing values are up to 30 chars. Widen the column."
    )


def test_all_classification_method_literals_fit_field_width():
    field = Evidence.model_fields["classification_method"]
    max_len = None
    for m in field.metadata or []:
        if hasattr(m, "max_length"):
            max_len = m.max_length
            break
    assert max_len is not None
    literals = _collect_classification_method_literals()
    # Sanity: we should find at least the Bug D + B3 + classifier values.
    assert (
        "domain_concentration_cap" in literals
    ), f"Scanner missed Bug D's literal — check the regex. Found: {sorted(literals)}"
    overflowing = [v for v in literals if len(v) > max_len]
    assert not overflowing, (
        f"classification_method literals exceed varchar({max_len}): "
        f"{[(v, len(v)) for v in overflowing]}. "
        f"Either shorten the value or widen the column."
    )
