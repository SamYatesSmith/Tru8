"""Phase 1b live eval — the in-pipeline symmetry stage on the real Gemini path.

Proves the SHIPPING stage (app/pipeline/opinion_symmetry.apply_symmetry_stage),
not a copy: for each battery claim it runs the real decompose (baseline) then
the real stage, and asserts the final assertion set is (1) balanced — not
claim-direction-dominated, (2) breadth >= 3 where possible, (3) free of the
value predicate, and reports the direction mix + convergence. The gate and the
product can no longer drift apart (1a lesson).

Run:  cd backend && python -m scripts.opinion_symmetry_eval
Writes backend/scripts/.opinion_symmetry_eval.json

⛔ HISTORICAL WITNESS (frozen 2026-07-17, plan §20 slice 1). This eval tested
the option-C direction-forcing stage, which was REMOVED after this very script
caught it manufacturing false balance ("Gaza is a genocide" → denialist brief;
plan §19). The transcript `.opinion_symmetry_eval.json` is the regression
witness — do not overwrite it. The module symbols this script imports
(apply_symmetry_stage, _claim_dominated) no longer exist; the code below is
kept verbatim as the record of what was tested. Slice 2 ships the replacement
gate for the reworked grounds stage.
"""

from __future__ import annotations

import sys

sys.exit(
    "HISTORICAL WITNESS — frozen at plan §20 slice 1 (2026-07-17). "
    "This tested the removed option-C direction-forcing stage; see the module "
    "docstring and .opinion_symmetry_eval.json (do not overwrite). "
    "The slice-2 eval gate replaces this script."
)

import asyncio
import json
import os
import re
from typing import Any, Dict, List

from app.pipeline.claim_map_analyzer import ClaimMapAnalyzer
from app.pipeline.opinion_symmetry import _claim_dominated, apply_symmetry_stage

# Claim + the value words that must NOT appear in any element (word-lock check).
BATTERY: List[Dict[str, Any]] = [
    {
        "claim": "The proposed Warner Bros-Paramount merger is a real danger to American democracy",
        "value_words": ["danger", "threat to democracy"],
    },
    {
        "claim": "The government's immigration policy is a disaster",
        "value_words": ["disaster", "catastrophe"],
    },
    {
        "claim": "The new trade deal is a triumph for British workers",
        "value_words": ["triumph", "victory"],
    },
    {
        "claim": "The situation in Gaza is a genocide",
        "value_words": ["genocide"],
    },
]


async def _baseline_map(analyzer: ClaimMapAnalyzer, claim: str) -> Dict[str, Any]:
    cm = await analyzer.decompose_claim(claim, "eval")
    return cm


def _has_value_word(text: str, words: List[str]) -> bool:
    t = text.lower()
    return any(re.search(rf"\b{re.escape(w)}\b", t) for w in words)


async def main() -> None:
    try:
        import sys

        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass

    analyzer = ClaimMapAnalyzer()
    results: List[Dict[str, Any]] = []
    passed = 0

    for case in BATTERY:
        claim = case["claim"]
        baseline = await _baseline_map(analyzer, claim)
        # Force the normative path regardless of the classifier's label — the eval
        # tests the STAGE, and the runner gates classification separately.
        cm = await apply_symmetry_stage(analyzer, claim, baseline)

        elems = cm.get("elements") or []
        dirs = [e.get("basis", {}).get("direction") for e in elems]
        sym = cm.get("metadata", {}).get("symmetry", {})
        balanced = not _claim_dominated([d for d in dirs if d])
        breadth_ok = len(elems) >= min(3, len(elems)) and len(elems) >= 1
        vw_hits = [
            e["description"]
            for e in elems
            if _has_value_word(e.get("description", ""), case["value_words"])
        ]
        ok = balanced and len(elems) >= 3 and not vw_hits
        if ok:
            passed += 1

        print("\n" + "=" * 78)
        print(f"[{claim}]")
        print(
            f"  directions={sym.get('directions')}  balanced={balanced}  "
            f"converged={sym.get('converged')}  rounds={sym.get('rounds')}  "
            f"{'✅ PASS' if ok else '❌ FAIL'}"
        )
        for e, d in zip(elems, dirs):
            print(f"      [{str(d)[:7]:7s}] {e.get('description', '')[:95]}")
        if vw_hits:
            print(f"  ⚠ VALUE-WORD LEAK: {vw_hits}")

        results.append(
            {
                "claim": claim,
                "directions": sym.get("directions"),
                "balanced": balanced,
                "converged": sym.get("converged"),
                "value_word_leak": vw_hits,
                "elements": [
                    {"description": e.get("description"), "direction": d}
                    for e, d in zip(elems, dirs)
                ],
                "pass": ok,
            }
        )

    out_path = os.path.join(os.path.dirname(__file__), ".opinion_symmetry_eval.json")
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2, ensure_ascii=False)

    print("\n" + "=" * 78)
    print(
        f"OPINION SYMMETRY: {passed}/{len(BATTERY)} pass (balanced + breadth + no value-word)"
    )
    print("🟢 GREEN" if passed == len(BATTERY) else "🔴 NOT GREEN")
    print(f"Saved transcript → {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
