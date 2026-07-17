"""§20 slice 2 eval gate — the opinion grounds stage on the real Gemini path.

Proves the SHIPPING stage (app/pipeline/opinion_symmetry.apply_grounds_stage):
for each battery claim it runs the real baseline decompose then the real
stage, and gates MECHANICALLY on:
  (1) breadth >= 3;
  (2) ZERO value-predicate leaks — no element is a restatement of the bare
      judgement (the stage's own lock + per-case value-word bare-judgement
      check; legal-label routes that ADD substance are exempt by design, D2);
  (3) >= 80% of elements question-shaped (end in "?");
  (4) grounds metadata disclosed (applied, converged).

Recorded, NOT gated (per §20.6(6) — judgement stays with humans):
  - Gaza must show claim-side grounds (§4.2 routes: ICJ / intent / casualties)
    — eyeball the printout;
  - whataboutism watch (§20.2 finding 1): any element about a DIFFERENT
    actor's conduct than the claim's subject — eyeball the printout.

GREEN = mechanical gates pass on ALL battery claims, 2 consecutive runs
(v4 precedent). Run:  cd backend && python -m scripts.opinion_grounds_eval
Writes backend/scripts/.opinion_grounds_eval.json (appends run history).
"""

from __future__ import annotations

import asyncio
import json
import os
import re
from typing import Any, Dict, List

from app.pipeline.claim_map_analyzer import ClaimMapAnalyzer
from app.pipeline.opinion_symmetry import _is_restatement, apply_grounds_stage

# value_words: the bare judgement's predicate terms. An element that contains
# one AND is a restatement (adds <2 content words) is a leak; naming the term
# inside a substantive route (ICJ proceedings on genocide) is NOT a leak.
BATTERY: List[Dict[str, Any]] = [
    {
        "claim": "The proposed Warner Bros-Paramount merger is a real danger to American democracy",
        "value_words": ["danger"],
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

QUESTION_SHAPE_FLOOR = 0.8


def _is_question(text: str) -> bool:
    return text.rstrip().endswith("?")


def _bare_judgement_leak(claim: str, element: str, value_words: List[str]) -> bool:
    """A leak = the element carries a value word AND is a restatement.
    Substantive routes naming a legal label are exempt (add >=2 content words)."""
    t = element.lower()
    has_word = any(re.search(rf"\b{re.escape(w)}\b", t) for w in value_words)
    return has_word and _is_restatement(claim, element)


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
        baseline = await analyzer.decompose_claim(claim, "eval")
        cm = await apply_grounds_stage(analyzer, claim, baseline)

        elems = [e.get("description", "") for e in (cm.get("elements") or [])]
        grounds = cm.get("metadata", {}).get("grounds", {})

        breadth_ok = len(elems) >= 3
        leaks = [
            e for e in elems if _bare_judgement_leak(claim, e, case["value_words"])
        ]
        q_ratio = (
            sum(1 for e in elems if _is_question(e)) / len(elems) if elems else 0.0
        )
        shape_ok = q_ratio >= QUESTION_SHAPE_FLOOR
        disclosed = grounds.get("applied") is True

        ok = breadth_ok and not leaks and shape_ok and disclosed
        if ok:
            passed += 1

        print("\n" + "=" * 78)
        print(f"[{claim}]")
        print(
            f"  breadth={len(elems)}  leaks={len(leaks)}  question_ratio={q_ratio:.2f}  "
            f"converged={grounds.get('converged')}  {'✅ PASS' if ok else '❌ FAIL'}"
        )
        for e in elems:
            print(f"      - {e[:110]}")
        if leaks:
            print(f"  ⚠ VALUE-PREDICATE LEAK: {leaks}")
        print("  EYEBALL (not gated): claim-side grounds present? whataboutism?")

        results.append(
            {
                "claim": claim,
                "elements": elems,
                "breadth": len(elems),
                "leaks": leaks,
                "question_ratio": round(q_ratio, 2),
                "grounds": grounds,
                "pass": ok,
            }
        )

    out_path = os.path.join(os.path.dirname(__file__), ".opinion_grounds_eval.json")
    history: List[Any] = []
    if os.path.exists(out_path):
        try:
            with open(out_path, encoding="utf-8") as fh:
                history = json.load(fh)
        except Exception:
            history = []
    history.append({"run": len(history) + 1, "results": results})
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(history, fh, indent=2, ensure_ascii=False)

    print("\n" + "=" * 78)
    print(f"OPINION GROUNDS: {passed}/{len(BATTERY)} pass")
    print("🟢 GREEN" if passed == len(BATTERY) else "🔴 NOT GREEN")
    print(f"Saved transcript → {out_path} (run {len(history)})")


if __name__ == "__main__":
    asyncio.run(main())
