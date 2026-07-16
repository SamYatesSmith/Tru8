"""Artefact-0 v3 — directional-lean metric + mechanical union guard.

v2 showed the completeness-critic is an invalid gate (it moves goalposts and
conflates "not exhaustive" with "skewed"), and that the revise stage could drop
a good element. v3 corrects both, per founder-approved design (plan §14):

  1. GATE = directional lean, not completeness.
     Classify each route confirm / neutral / disconfirm. A set PASSES when it is
     NOT confirm-dominated:  confirm_count <= neutral_count + disconfirm_count.
     (An all-neutral, two-directional set is ideal.)

  2. REBALANCE is UNION-guarded (mechanical, not trusted to the LLM).
     Every v1 route already classified neutral/disconfirm is PRESERVED in code.
     Only the confirm-leaning slots are replaced/topped-up with fresh neutral or
     disconfirming dimensions. A good element can never be dropped.

Scoped to normative_flagged only (empirical claims skip the whole stage).

Run:  python -m scripts.decompose_symmetry_eval_v3
Writes backend/scripts/.decompose_symmetry_eval_v3.json
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

from app.pipeline.claim_map_analyzer import ClaimMapAnalyzer

MAX_ELEMENTS = 5

LEAN_PROMPT = """\
You are auditing a research design for directional balance. You are given an
evaluative claim and a numbered list of empirical dimensions chosen to
investigate it.

For EACH dimension, classify how it is oriented AS PHRASED:
- "confirm"    — investigating it mainly builds the case FOR the claim, or the
                 wording presupposes the claim's conclusion.
- "disconfirm" — investigating it mainly builds the case AGAINST the claim
                 (mitigating factors, safeguards, countervailing forces).
- "neutral"    — a genuinely two-directional / open empirical question whose
                 answer could cut either way.

Respond with JSON only, a lean array in the SAME ORDER as the input:
{"leans": ["confirm"|"neutral"|"disconfirm", ...]}
The array length MUST equal the number of dimensions given.
"""

REBALANCE_PROMPT = """\
You are balancing a research design. You are given an evaluative claim, the
dimensions being KEPT (already balanced), and the number of additional slots
available.

Produce that many ADDITIONAL empirical dimensions that:
- are NEUTRAL and two-directional (an open question, never a directional
  assertion that presupposes the claim),
- deliberately include considerations whose findings could count AGAINST the
  claim (mitigating factors, safeguards, base rates, alternative explanations),
- are NOT already covered by the kept dimensions,
- never restate the value judgement itself.

Respond with JSON only:
{"elements": [{"description": "<empirical dimension>"}, ...]}
"""


async def _lean(
    analyzer: ClaimMapAnalyzer, claim: str, elements: List[str]
) -> List[str]:
    if not elements:
        return []
    numbered = "\n".join(f"{i + 1}. {e}" for i, e in enumerate(elements))
    parsed = await analyzer._call_llm(
        prompt=f"{LEAN_PROMPT}\n\nClaim: {claim}\n\nDimensions:\n{numbered}",
        temperature=0.0,
        max_tokens=500,
        label="lean_classify",
    )
    leans = (parsed or {}).get("leans") if isinstance(parsed, dict) else None
    if not isinstance(leans, list) or len(leans) != len(elements):
        # Defensive: unknown lean if the classifier misbehaves.
        return ["confirm"] * len(elements)
    return [str(x_).lower() for x_ in leans]


def _confirm_dominated(leans: List[str]) -> bool:
    c = leans.count("confirm")
    other = leans.count("neutral") + leans.count("disconfirm")
    return c > other


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
        label="decomp_rebalance",
    )
    return _extract(parsed)["elements"][:slots]


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

    for case in BATTERY:
        claim, label = case["claim"], case["label"]
        cand = await _decompose(analyzer, CANDIDATE_PROMPT, claim, "decomp_candidate")
        print("\n" + "=" * 78)
        print(f"[{label}]  {claim}  (type={cand['claim_type']})")

        if cand["claim_type"] != "normative_flagged":
            print("  (empirical — skipped)")
            results.append({"label": label, "claim": claim, "skipped": True})
            continue

        normative_total += 1
        v1 = cand["elements"]
        v1_leans = await _lean(analyzer, claim, v1)

        # ── mechanical union guard: keep every non-confirm route ──────────
        kept = [e for e, ln in zip(v1, v1_leans) if ln != "confirm"]
        slots = MAX_ELEMENTS - len(kept)
        additions = await _rebalance_add(analyzer, claim, kept, slots)
        final = (kept + additions)[:MAX_ELEMENTS]

        final_leans = await _lean(analyzer, claim, final)
        v1_dom = _confirm_dominated(v1_leans)
        final_dom = _confirm_dominated(final_leans)
        ok = not final_dom
        if ok:
            passed += 1

        def _dist(ls: List[str]) -> str:
            return (
                f"confirm={ls.count('confirm')} "
                f"neutral={ls.count('neutral')} "
                f"disconfirm={ls.count('disconfirm')}"
            )

        results.append(
            {
                "label": label,
                "claim": claim,
                "v1_elements": v1,
                "v1_leans": v1_leans,
                "v1_confirm_dominated": v1_dom,
                "kept_by_union": kept,
                "final_elements": final,
                "final_leans": final_leans,
                "final_confirm_dominated": final_dom,
                "pass": ok,
            }
        )

        print(f"  v1    [{_dist(v1_leans)}]  dominated={v1_dom}")
        print(f"  union kept {len(kept)}/{len(v1)} non-confirm routes")
        print(
            f"  FINAL [{_dist(final_leans)}]  dominated={final_dom}  "
            f"{'✅ PASS' if ok else '❌ FAIL'}"
        )
        for e, ln in zip(final, final_leans):
            print(f"      [{ln[:4]}] {e}")

    out_path = os.path.join(
        os.path.dirname(__file__), ".decompose_symmetry_eval_v3.json"
    )
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2, ensure_ascii=False)

    print("\n" + "=" * 78)
    print(
        f"DIRECTIONAL BALANCE: {passed}/{normative_total} normative claims "
        f"PASS (not confirm-dominated) after union-guarded rebalance."
    )
    print(f"Saved transcript → {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
