"""Human-readable diff report for a bench run.

Advisory mode: warnings don't fail the run, only failures do.
Output uses ASCII glyphs (Windows console safe).
"""

from __future__ import annotations

from typing import Iterable, List, Sequence, Tuple

from .comparator import Diff


GLYPH = {
    "ok": "  OK ",
    "warning": " WARN",
    "failure": " FAIL",
    # The gate had nothing to fire on in this pool. NOT a pass: it is reported
    # on its own line and counted separately, so "unexercised" can never be
    # mistaken for "verified" when reading a run.
    "unexercised": "UNEX ",
}


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
    n_unex = sum(1 for d in diffs if d.is_unexercised())
    n_ok = len(diffs) - n_fail - n_warn - n_unex
    tail = f", {n_unex} unexercised" if n_unex else ""
    lines.append(f"  --- {claim_id}: {n_ok} ok, {n_warn} warn, {n_fail} fail{tail}")
    return "\n".join(lines)


def render_overall(per_claim: Iterable[Tuple[str, Sequence[Diff]]]) -> Tuple[str, int]:
    """Return (text, exit_code). exit_code=0 if no failures."""
    sections: List[str] = []
    total_ok = total_warn = total_fail = total_unex = 0
    for claim_id, diffs in per_claim:
        sections.append(render_claim_section(claim_id, diffs))
        total_fail += sum(1 for d in diffs if d.is_failure())
        total_warn += sum(1 for d in diffs if d.is_warning())
        total_unex += sum(1 for d in diffs if d.is_unexercised())
        total_ok += sum(1 for d in diffs if d.level == "ok")

    sections.append("")
    sections.append("=" * 64)
    # Unexercised never fails the run — but it is always named, because a
    # silently skipped guard is worse than a red one.
    unex = (
        f", {total_unex} UNEXERCISED (guard not tested this run)" if total_unex else ""
    )
    if total_fail:
        verdict = f"FAIL  {total_ok} ok, {total_warn} warn, {total_fail} fail{unex}"
        exit_code = 1
    elif total_warn:
        verdict = f"WARN  {total_ok} ok, {total_warn} warn (advisory — review){unex}"
        exit_code = 0
    else:
        verdict = f"PASS  {total_ok} ok{unex}"
        exit_code = 0
    sections.append(f"OVERALL: {verdict}")
    sections.append("=" * 64)

    return "\n".join(sections), exit_code
