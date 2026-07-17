"""§20 slice 3 eval gate — grounds-aware mapping on the real Gemini path.

For each battery claim: live grounds decompose (slice 2) → live mapping with
the GROUNDS_MAPPING_ADDENDUM (slice 3) over a CURATED synthetic evidence pool
whose leans are known by construction. Mechanical gates:
  (1) every element_id appears in the mapped output;
  (2) states/relationships from the enums only;
  (3) every referenced evidence_id resolves to the pool (no invented IDs);
  (4) at least one element gains >=1 evidence_ref (the mapper engaged);
  (5) grounds metadata still discloses (applied is True).

Printed for the coherence EYEBALL (not gated — P4 was about SEMANTIC quality):
per-element refs with relationship + reasoning, states, scope caveats.
Watch for: coercion (everything "supported" regardless of content),
question-treated-as-assertion, or the mapper inferring the parent claim.

GREEN = mechanical gates pass on ALL battery claims, 2 consecutive runs.
Run:  cd backend && python -m scripts.grounds_mapping_eval
Writes backend/scripts/.grounds_mapping_eval.json (appends run history).
"""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any, Dict, List

from app.pipeline.claim_map_analyzer import ClaimMapAnalyzer
from app.pipeline.opinion_symmetry import apply_grounds_stage

# Curated pools: leans are known by construction so the eyeball can judge
# whether the mapper read the evidence or coerced it.
BATTERY: List[Dict[str, Any]] = [
    {
        "claim": "The government's immigration policy is a disaster",
        "evidence": [
            {
                "evidence_id": "ev-tgt",
                "title": "Home Office policy statement",
                "snippet": "The policy's stated targets: reduce the asylum backlog to 20,000 cases by 2025 and cut small-boat crossings by half.",
                "tier": "primary",
                "evidence_type": "government",
            },
            {
                "evidence_id": "ev-bad1",
                "title": "National Audit Office report",
                "snippet": "The asylum backlog rose to 94,000 cases in 2024, far above the stated 20,000 target; processing costs exceeded projections by £1.2bn.",
                "tier": "primary",
                "evidence_type": "government",
            },
            {
                "evidence_id": "ev-good1",
                "title": "ONS labour statistics",
                "snippet": "Work-visa route processing times fell 40% year on year and employer sponsorship grew in shortage sectors.",
                "tier": "primary",
                "evidence_type": "statistical",
            },
            {
                "evidence_id": "ev-mixed",
                "title": "Migration Observatory analysis",
                "snippet": "Outcomes are mixed: enforcement targets missed, but legal-route reforms achieved most of their stated aims.",
                "tier": "reporting",
                "evidence_type": "analysis",
            },
            {
                "evidence_id": "ev-op",
                "title": "Newspaper opinion column",
                "snippet": "This policy is a shambles and everyone knows it.",
                "tier": "commentary",
                "evidence_type": "opinion",
            },
        ],
    },
    {
        "claim": "The situation in Gaza is a genocide",
        "evidence": [
            {
                "evidence_id": "ev-cas",
                "title": "UN OCHA casualty tracking",
                "snippet": "Documented deaths exceed 40,000, the majority civilians, per cross-checked ministry and UN monitoring figures.",
                "tier": "primary",
                "evidence_type": "government",
            },
            {
                "evidence_id": "ev-icj",
                "title": "ICJ provisional measures order",
                "snippet": "The Court found it plausible that acts within the scope of the Genocide Convention occurred and ordered provisional measures.",
                "tier": "primary",
                "evidence_type": "legal",
            },
            {
                "evidence_id": "ev-aid",
                "title": "WHO aid access report",
                "snippet": "Aid convoy entries fell below assessed need for eleven consecutive weeks; medical supply access is documented as restricted.",
                "tier": "primary",
                "evidence_type": "health",
            },
            {
                "evidence_id": "ev-deny",
                "title": "Government spokesperson statement",
                "snippet": "Officials state operations target militants, casualty figures are inflated, and there is no intent to harm civilians.",
                "tier": "reporting",
                "evidence_type": "statement",
            },
            {
                "evidence_id": "ev-bg",
                "title": "Encyclopaedia entry",
                "snippet": "The Genocide Convention (1948) defines genocide as acts committed with intent to destroy, in whole or in part, a national, ethnical, racial or religious group.",
                "tier": "reference",
                "evidence_type": "reference",
            },
        ],
    },
]

# "contextual" is the mechanical all-context state (ElementState, 2026-05-12).
VALID_STATES = {"supported", "disputed", "unresolved", "contextual"}
VALID_RELS = {"supports", "challenges", "context"}


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
        pool_ids = {e["evidence_id"] for e in case["evidence"]}

        baseline = await analyzer.decompose_claim(claim, "eval")
        cm = await apply_grounds_stage(analyzer, claim, baseline)
        assert cm.get("metadata", {}).get("grounds", {}).get("applied") is True
        pre_ids = {e.get("element_id") for e in cm.get("elements") or []}
        cm = await analyzer.map_evidence_to_elements(cm, case["evidence"])

        elems = cm.get("elements") or []
        # Gate (1): every input element_id survives mapping (verify NIT: the
        # previous form could never fail — real set comparison now).
        all_ids_present = {e.get("element_id") for e in elems} == pre_ids

        def _plain(v):
            return v.value if hasattr(v, "value") else v

        bad_states = [
            str(_plain(e.get("state")))
            for e in elems
            if str(_plain(e.get("state"))) not in VALID_STATES
        ]
        bad_rels, bad_ids, ref_count = [], [], 0
        for e in elems:
            for r in e.get("evidence_refs") or []:
                ref_count += 1
                rel = str(
                    r.get("relationship").value
                    if hasattr(r.get("relationship"), "value")
                    else r.get("relationship")
                )
                if rel not in VALID_RELS:
                    bad_rels.append(rel)
                if r.get("evidence_id") not in pool_ids:
                    bad_ids.append(r.get("evidence_id"))
        disclosed = cm.get("metadata", {}).get("grounds", {}).get("applied") is True

        ok = (
            all_ids_present
            and not bad_states
            and not bad_rels
            and not bad_ids
            and ref_count >= 1
            and disclosed
        )
        if ok:
            passed += 1

        print("\n" + "=" * 78)
        print(f"[{claim}]")
        print(
            f"  elements={len(elems)}  refs={ref_count}  bad_states={bad_states}  "
            f"bad_rels={bad_rels}  bad_ids={bad_ids}  {'✅ PASS' if ok else '❌ FAIL'}"
        )
        for e in elems:
            state = e.get("state")
            state = state.value if hasattr(state, "value") else state
            print(f"  [{state}] {e.get('description', '')[:95]}")
            for r in e.get("evidence_refs") or []:
                rel = r.get("relationship")
                rel = rel.value if hasattr(rel, "value") else rel
                print(
                    f"      {rel:10s} {r.get('evidence_id'):8s} {str(r.get('reasoning'))[:80]}"
                )
        print("  EYEBALL: coercion? question-as-assertion? parent-claim inference?")

        results.append(
            {
                "claim": claim,
                "elements": [
                    {
                        "description": e.get("description"),
                        "state": str(
                            e.get("state").value
                            if hasattr(e.get("state"), "value")
                            else e.get("state")
                        ),
                        "refs": [
                            {
                                "evidence_id": r.get("evidence_id"),
                                "relationship": str(
                                    r.get("relationship").value
                                    if hasattr(r.get("relationship"), "value")
                                    else r.get("relationship")
                                ),
                                "reasoning": r.get("reasoning"),
                            }
                            for r in e.get("evidence_refs") or []
                        ],
                    }
                    for e in elems
                ],
                "pass": ok,
            }
        )

    out_path = os.path.join(os.path.dirname(__file__), ".grounds_mapping_eval.json")
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
    print(f"GROUNDS MAPPING: {passed}/{len(BATTERY)} pass")
    print("🟢 GREEN" if passed == len(BATTERY) else "🔴 NOT GREEN")
    print(f"Saved transcript → {out_path} (run {len(history)})")


if __name__ == "__main__":
    asyncio.run(main())
