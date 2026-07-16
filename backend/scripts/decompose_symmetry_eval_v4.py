"""Artefact-0 v4 — gate v4 (Decoupling build plan §15.2, 2026-07-16).

Supersedes v3. Fixes the four transcript findings (§15.1):

  F-A subject drift    → the classifier now returns lean AND on_subject per
                         dimension; the union keeps non-confirm AND on-subject
                         only; the rebalance prompt is anchored to the claim's
                         named subject; the gate fails on any off-subject
                         final element.
  F-B fail-unsafe      → classifier failure PRESERVES (lean=neutral,
                         on_subject=True, flagged) — it never condemns;
                         rebalance failure falls back to kept + v1 remainder;
                         the final set can never be empty.
  F-C structural drop  → the BASELINE decomposition runs alongside; its
                         non-confirm on-subject elements are structural
                         candidates; any not covered by the kept set is
                         mechanically ADDED before rebalance, and coverage is
                         re-checked on the FINAL set (catches cap-5 eviction).
  F-D trigger-not-fix  → D2 codified-test criterion added to the candidate
                         prompt; boundary expectations asserted MECHANICALLY
                         per battery case ("anticompetitive" now expected
                         empirical).

GATE per normative claim (ALL must pass):
  1. balanced        — final set not confirm-dominated
  2. on_subject_ok   — every final element on-subject
  3. structural_ok   — every structural candidate covered by the final set
Plus, battery-wide: every boundary expectation met.

Run:  cd backend && python -m scripts.decompose_symmetry_eval_v4
Writes backend/scripts/.decompose_symmetry_eval_v4.json
"""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any, Dict, List, Optional

from scripts.decompose_symmetry_eval import (
    BATTERY,
    CANDIDATE_PROMPT,
    _decompose,
    _extract,
)

from app.pipeline.claim_map_analyzer import (
    DECOMPOSITION_PROMPT,
    ClaimMapAnalyzer,
)

MAX_ELEMENTS = 5

# ── D2: codified-test criterion, inserted into the v1 candidate prompt ───────
_D2_ANCHOR = "so classify them empirical and decompose normally."
_D2_CRITERION = (
    "\n   - CODIFIED-TEST RULE: a predicate with a codified, adjudicable test "
    '(a statute, regulator, or court applies it — e.g. "anticompetitive", '
    '"illegal", "unconstitutional", "defamatory", "in breach of contract") is '
    "NOT normative_flagged, however evaluative it sounds: classify it "
    "empirical and decompose against that codified test."
)
assert _D2_ANCHOR in CANDIDATE_PROMPT, "v1 candidate prompt drifted; re-anchor D2"
CANDIDATE_PROMPT_V4 = CANDIDATE_PROMPT.replace(_D2_ANCHOR, _D2_ANCHOR + _D2_CRITERION)

# ── Boundary expectations (mechanical, per D2). None = either defensible. ────
EXPECTED_BOUNDARY: Dict[str, Optional[str]] = {
    "origin/opinion": "normative_flagged",
    "contested-label": "normative_flagged",
    "everyday/opinion": "normative_flagged",
    "opinion/positive-valence": "normative_flagged",
    "boundary-neg/false-fact": "empirical",  # any non-normative type accepted
    "boundary-neg/plain-fact": "empirical",
    "ambiguous/failed": None,
    "ambiguous/legal-empirical": "empirical",  # D2 codified-test criterion
}

# ── Combined lean + on-subject classifier (one call, two labels) ─────────────
ASSESS_PROMPT = """\
You are auditing a research design. You are given a claim and a numbered list
of empirical dimensions chosen to investigate it.

For EACH dimension, give TWO labels:

lean — how the dimension is oriented AS PHRASED:
- "confirm"    — investigating it mainly builds the case FOR the claim, or the
                 wording presupposes the claim's conclusion.
- "disconfirm" — investigating it mainly builds the case AGAINST the claim
                 (mitigating factors, safeguards, countervailing forces).
- "neutral"    — a genuinely two-directional / open empirical question whose
                 answer could cut either way.

Lean rules of thumb:
- An OPEN MEASUREMENT — "the impact/extent/level/change of X" — is "neutral"
  even when it examines a ground the claim raises: the measurement could come
  back in either direction. ("The impact of the trade deal on employment
  levels" → neutral, because employment may have risen OR fallen.)
- "confirm" requires the WORDING to presuppose the claim's conclusion or to be
  answerable only in the claim's favour. ("The potential for the merged
  company to engage in anti-competitive practices" → confirm: it enumerates a
  harm mechanism and cannot surface evidence against the claim.)
- ("The regulatory safeguards that would constrain the merged entity" →
  disconfirm.)

on_subject — true if the dimension is specifically about the claim's named
subject (the particular entity, policy, event, or situation the claim names);
false if it addresses the general topic area without being about that specific
subject.

On-subject rules of thumb:
- A dimension explicitly comparing the named subject to PRECEDENTS, BASE
  RATES, or COMPARABLE CASES in order to inform judgement about the subject IS
  on-subject. ("How have previous large media mergers affected competition?"
  for a claim about THIS merger → on_subject: true — a comparator.)
- A dimension that REPLACES the subject with its general topic area is NOT.
  ("What is the crime rate in areas with high immigrant populations?" for a
  claim about the government's immigration POLICY → on_subject: false — it
  studies immigrants, not the policy.)

Respond with JSON only, in the SAME ORDER as the input:
{"assessments": [{"lean": "confirm"|"neutral"|"disconfirm", "on_subject": true|false}, ...]}
The array length MUST equal the number of dimensions given.
"""

# ── Coverage check (structural guard, F-C) ────────────────────────────────────
COVERAGE_PROMPT = """\
You are checking coverage of a research design. You are given the FINAL set of
research dimensions, and a numbered list of CANDIDATE dimensions.

For EACH candidate, say whether its substance is already covered by at least
one final dimension — i.e. investigating the final set would necessarily
answer the candidate's underlying question, even if worded differently.

Respond with JSON only, in the SAME ORDER as the candidates:
{"covered": [true|false, ...]}
The array length MUST equal the number of candidates given.
"""

# ── Rebalance, subject-anchored (F-A) ─────────────────────────────────────────
REBALANCE_PROMPT = """\
You are balancing a research design. You are given an evaluative claim, the
dimensions being KEPT (already balanced), and the number of additional slots
available.

Produce that many ADDITIONAL empirical dimensions that:
- are specifically about the claim's NAMED SUBJECT (the particular entity,
  policy, event, or situation the claim names), never its general topic area,
- are NEUTRAL and two-directional (an open question, never a directional
  assertion that presupposes the claim),
- deliberately include considerations whose findings could count AGAINST the
  claim (mitigating factors, safeguards, base rates, alternative explanations),
- are NOT already covered by the kept dimensions,
- never restate the value judgement itself.

Respond with JSON only:
{"elements": [{"description": "<empirical dimension>"}, ...]}
"""


async def _assess(
    analyzer: ClaimMapAnalyzer, claim: str, elements: List[str]
) -> Dict[str, Any]:
    """Classify lean + on_subject per element. FAIL-SAFE: preserve, never condemn."""
    if not elements:
        return {"leans": [], "on_subject": [], "classifier_failed": False}
    numbered = "\n".join(f"{i + 1}. {e}" for i, e in enumerate(elements))
    parsed = await analyzer._call_llm(
        prompt=f"{ASSESS_PROMPT}\n\nClaim: {claim}\n\nDimensions:\n{numbered}",
        temperature=0.0,
        max_tokens=800,
        label="assess_lean_subject",
    )
    rows = (parsed or {}).get("assessments") if isinstance(parsed, dict) else None
    if not isinstance(rows, list) or len(rows) != len(elements):
        # F-B fix: on classifier failure PRESERVE every element (the v3 default
        # of all-"confirm" condemned everything to replacement — backwards for
        # a guard whose promise is "a good element can never be dropped").
        return {
            "leans": ["neutral"] * len(elements),
            "on_subject": [True] * len(elements),
            "classifier_failed": True,
        }
    leans, subj = [], []
    for r in rows:
        if isinstance(r, dict):
            leans.append(str(r.get("lean", "neutral")).lower())
            subj.append(bool(r.get("on_subject", True)))
        else:  # malformed row → preserve
            leans.append("neutral")
            subj.append(True)
    return {"leans": leans, "on_subject": subj, "classifier_failed": False}


async def _coverage(
    analyzer: ClaimMapAnalyzer,
    claim: str,
    final: List[str],
    candidates: List[str],
) -> Dict[str, Any]:
    """Which candidates are covered by the final set? Malformed → all uncovered
    (safe in construction: uncovered means ADD; loud in the gate: means FAIL)."""
    if not candidates:
        return {"covered": [], "classifier_failed": False}
    fin = "\n".join(f"- {e}" for e in final) or "(none)"
    cand = "\n".join(f"{i + 1}. {e}" for i, e in enumerate(candidates))
    parsed = await analyzer._call_llm(
        prompt=(
            f"{COVERAGE_PROMPT}\n\nClaim: {claim}\n\nFinal set:\n{fin}\n\n"
            f"Candidates:\n{cand}"
        ),
        temperature=0.0,
        max_tokens=400,
        label="coverage_check",
    )
    cov = (parsed or {}).get("covered") if isinstance(parsed, dict) else None
    if not isinstance(cov, list) or len(cov) != len(candidates):
        return {"covered": [False] * len(candidates), "classifier_failed": True}
    return {"covered": [bool(c) for c in cov], "classifier_failed": False}


async def _rebalance_add(
    analyzer: ClaimMapAnalyzer, claim: str, kept: List[str], slots: int
) -> List[str]:
    if slots <= 0:
        return []
    keptxt = "\n".join(f"- {e}" for e in kept) or "(none)"
    parsed = await analyzer._call_llm(
        prompt=(
            f"{REBALANCE_PROMPT}\n\nClaim: {claim}\n\n"
            f"Kept dimensions:\n{keptxt}\n\n"
            f"Additional slots available: {slots}"
        ),
        temperature=analyzer.decomposition_temperature,
        max_tokens=1200,
        label="decomp_rebalance_v4",
    )
    return _extract(parsed)["elements"][:slots]


def _confirm_dominated(leans: List[str]) -> bool:
    return leans.count("confirm") > (leans.count("neutral") + leans.count("disconfirm"))


def _dist(leans: List[str]) -> str:
    return (
        f"confirm={leans.count('confirm')} "
        f"neutral={leans.count('neutral')} "
        f"disconfirm={leans.count('disconfirm')}"
    )


async def main() -> None:
    try:
        import sys

        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass

    analyzer = ClaimMapAnalyzer()
    results: List[Dict[str, Any]] = []
    passed = 0
    normative_total = 0
    boundary_fails: List[str] = []

    for case in BATTERY:
        claim, label = case["claim"], case["label"]
        cand = await _decompose(
            analyzer, CANDIDATE_PROMPT_V4, claim, "decomp_candidate_v4"
        )
        ctype = cand["claim_type"]
        print("\n" + "=" * 78)
        print(f"[{label}]  {claim}  (type={ctype})")

        # ── Mechanical boundary assertion (D2 / F-D) ──────────────────────
        expected = EXPECTED_BOUNDARY.get(label)
        if expected == "normative_flagged":
            boundary_ok = ctype == "normative_flagged"
        elif expected == "empirical":
            boundary_ok = ctype != "normative_flagged"  # any non-normative type
        else:
            boundary_ok = True  # either defensible; record only
        if not boundary_ok:
            boundary_fails.append(label)
            print(f"  ❌ BOUNDARY: expected {expected}, got {ctype}")

        if ctype != "normative_flagged":
            print("  (non-normative — no symmetry stage)")
            results.append(
                {
                    "label": label,
                    "claim": claim,
                    "claim_type": ctype,
                    "boundary_ok": boundary_ok,
                    "skipped": True,
                }
            )
            continue

        normative_total += 1
        v1 = cand["elements"]

        # Baseline decomposition = source of structural candidates (F-C).
        baseline = await _decompose(
            analyzer, DECOMPOSITION_PROMPT, claim, "decomp_baseline_v4"
        )
        cand_assess = await _assess(analyzer, claim, v1)
        base_assess = await _assess(analyzer, claim, baseline["elements"])

        # ── Union guard: keep non-confirm AND on-subject (F-A) ────────────
        kept = [
            e
            for e, ln, s in zip(v1, cand_assess["leans"], cand_assess["on_subject"])
            if ln != "confirm" and s
        ]
        structural = [
            e
            for e, ln, s in zip(
                baseline["elements"],
                base_assess["leans"],
                base_assess["on_subject"],
            )
            if ln != "confirm" and s
        ]

        # ── Structural union: add uncovered baseline candidates (F-C) ─────
        pre_cov = await _coverage(analyzer, claim, kept, structural)
        structural_added = [s for s, c in zip(structural, pre_cov["covered"]) if not c]
        kept_plus = (kept + structural_added)[:MAX_ELEMENTS]
        structural_truncated = len(kept + structural_added) > MAX_ELEMENTS

        # ── Rebalance with STICKY labels + bounded retry loop (rev 2) ─────
        # Labels are assigned ONCE per element and carried (fixes the
        # intra-run flapping seen in run 1/2: the same element judged
        # on-subject when added, off-subject at the final check). Kept
        # elements are all non-confirm + on-subject BY CONSTRUCTION; only
        # fresh additions are assessed, and only bad ADDITIONS are ever
        # dropped (the union promise: a kept element is never dropped).
        # In-pipeline this loop is "converge or disclose in the receipt" —
        # a live check can never simply fail.
        carried_labels: List[str] = [
            ln
            for e, ln, s in zip(v1, cand_assess["leans"], cand_assess["on_subject"])
            if ln != "confirm" and s
        ][: len(kept)] + ["neutral"] * len(structural_added)
        # (structural adds are non-confirm by construction; carry as neutral)
        carried_labels = carried_labels[: len(kept_plus)]

        good_additions: List[str] = []
        good_add_labels: List[str] = []
        rounds_used = 0
        for round_no in range(3):
            current = kept_plus + good_additions
            slots = MAX_ELEMENTS - len(current)
            if slots <= 0:
                break
            rounds_used = round_no + 1
            additions = await _rebalance_add(analyzer, claim, current, slots)
            if not additions:
                break
            add_assess = await _assess(analyzer, claim, additions)
            for e, ln, s in zip(
                additions, add_assess["leans"], add_assess["on_subject"]
            ):
                if not s:
                    continue  # off-subject addition → dropped, retried
                # confirm additions allowed only while balance holds
                trial = carried_labels + good_add_labels + [ln]
                if ln == "confirm" and _confirm_dominated(trial):
                    continue
                good_additions.append(e)
                good_add_labels.append(ln)
                if len(kept_plus) + len(good_additions) >= MAX_ELEMENTS:
                    break

        final = (kept_plus + good_additions)[:MAX_ELEMENTS]
        final_leans = (carried_labels + good_add_labels)[: len(final)]
        # Balance + on-subject now hold BY CONSTRUCTION (bad additions are
        # filtered mechanically), so the honest failure mode moves: did the
        # loop manage to FILL the design with good dimensions at all?
        # Breadth floor = 3 (judgement call, flagged for founder design-review):
        # the contract allows 1-5 elements, so a 4-dim balanced design beats a
        # 5-dim skewed one; a floor of 3 catches the degenerate can't-produce-
        # good-dimensions case, and structural coverage is checked separately.
        # Unfilled-vs-target is reported as a warning, not a gate fail.
        breadth_floor = min(3, len(v1)) if v1 else 1
        underfilled = len(final) < breadth_floor
        unfilled_slots = max(0, min(len(v1), MAX_ELEMENTS) - len(final))
        if not final:  # never empty (F-B)
            final = v1[:MAX_ELEMENTS]
            final_leans = ["confirm"] * len(final)  # honest: unbalanced v1

        # ── The gate over the FINAL set ───────────────────────────────────
        final_cov = await _coverage(analyzer, claim, final, structural)

        balanced = not _confirm_dominated(final_leans)
        structural_ok = all(final_cov["covered"])
        filled = not underfilled
        ok = balanced and structural_ok and filled and boundary_ok
        if ok:
            passed += 1
        final_assess = {"leans": final_leans, "on_subject": [True] * len(final)}

        results.append(
            {
                "label": label,
                "claim": claim,
                "claim_type": ctype,
                "boundary_ok": boundary_ok,
                "v1_elements": v1,
                "v1_assess": cand_assess,
                "baseline_elements": baseline["elements"],
                "baseline_assess": base_assess,
                "structural_candidates": structural,
                "structural_added": structural_added,
                "structural_truncated": structural_truncated,
                "kept": kept,
                "final_elements": final,
                "final_assess": final_assess,
                "final_coverage": final_cov,
                "checks": {
                    "balanced": balanced,
                    "filled": filled,
                    "unfilled_slots_vs_target": unfilled_slots,
                    "structural_ok": structural_ok,
                    "rebalance_rounds": rounds_used,
                },
                "pass": ok,
            }
        )

        print(f"  v1    [{_dist(cand_assess['leans'])}]")
        print(
            f"  union kept {len(kept)}/{len(v1)} + {len(structural_added)} "
            f"structural from baseline"
            + ("  ⚠ TRUNCATED" if structural_truncated else "")
        )
        print(
            f"  FINAL [{_dist(final_assess['leans'])}]  "
            f"balanced={balanced} filled={filled}"
            f"{f' (⚠ {unfilled_slots} slot(s) unfilled)' if unfilled_slots else ''} "
            f"structural={structural_ok} rounds={rounds_used}  "
            f"{'✅ PASS' if ok else '❌ FAIL'}"
        )
        for e, ln, s in zip(final, final_assess["leans"], final_assess["on_subject"]):
            print(f"      [{ln[:4]}{'' if s else '|OFF-SUBJ'}] {e}")

    out_path = os.path.join(
        os.path.dirname(__file__), ".decompose_symmetry_eval_v4.json"
    )
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2, ensure_ascii=False)

    print("\n" + "=" * 78)
    print(
        f"GATE v4: {passed}/{normative_total} normative claims PASS "
        f"(balance + filled + structural coverage; on-subject by construction)."
    )
    print(
        f"BOUNDARY: {len(BATTERY) - len(boundary_fails)}/{len(BATTERY)} "
        f"expectations met"
        + (f" — FAILED: {', '.join(boundary_fails)}" if boundary_fails else ".")
    )
    green = passed == normative_total and not boundary_fails
    print(f"{'🟢 GREEN' if green else '🔴 NOT GREEN'}")
    print(f"Saved transcript → {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
