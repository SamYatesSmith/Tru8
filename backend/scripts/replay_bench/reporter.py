"""Human-readable diff report for a bench run.

Advisory mode: warnings don't fail the run, only failures do.
Output uses ASCII glyphs (Windows console safe).
"""

from __future__ import annotations

from typing import Iterable, List, Sequence, Tuple

from .comparator import Diff


GLYPH = {"ok": "  OK ", "warning": " WARN", "failure": " FAIL"}


def render_claim_section(claim_id: str, diffs: Sequence[Diff]) -> str:
    lines = [f"\n=== {claim_id} ==="]
    if not diffs:
        lines.append("  (no assertions in golden — bench captured observation only)")
        return "\n".join(lines)
    for d in diffs:
        lines.append(
            f"  [{GLYPH[d.level]}] {d.signal:<48} {d.message}"
            f"\n          expected: {d.expected!r}"
            f"\n          observed: {d.observed!r}"
        )
    n_fail = sum(1 for d in diffs if d.is_failure())
    n_warn = sum(1 for d in diffs if d.is_warning())
    n_ok = len(diffs) - n_fail - n_warn
    lines.append(f"  --- {claim_id}: {n_ok} ok, {n_warn} warn, {n_fail} fail")
    return "\n".join(lines)


def render_overall(per_claim: Iterable[Tuple[str, Sequence[Diff]]]) -> Tuple[str, int]:
    """Return (text, exit_code). exit_code=0 if no failures."""
    sections: List[str] = []
    total_ok = total_warn = total_fail = 0
    for claim_id, diffs in per_claim:
        sections.append(render_claim_section(claim_id, diffs))
        total_fail += sum(1 for d in diffs if d.is_failure())
        total_warn += sum(1 for d in diffs if d.is_warning())
        total_ok += sum(1 for d in diffs if d.level == "ok")

    sections.append("")
    sections.append("=" * 64)
    if total_fail:
        verdict = f"FAIL  {total_ok} ok, {total_warn} warn, {total_fail} fail"
        exit_code = 1
    elif total_warn:
        verdict = f"WARN  {total_ok} ok, {total_warn} warn (advisory — review)"
        exit_code = 0
    else:
        verdict = f"PASS  {total_ok} ok"
        exit_code = 0
    sections.append(f"OVERALL: {verdict}")
    sections.append("=" * 64)

    return "\n".join(sections), exit_code
