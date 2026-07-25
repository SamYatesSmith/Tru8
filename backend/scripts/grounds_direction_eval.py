"""P21 Bug A — DIRECTIONAL gate for grounds-aware mapping (2026-07-25).

Why this exists
---------------
`grounds_mapping_eval.py` gates STRUCTURE only (every element mapped, valid
enums, resolvable ids, mapper engaged, metadata discloses). Direction was left
to a human eyeball (`:12-15` of that file). That is why Bug A shipped: T8's
backwards `+SUPPORTED` badge on a refuted ground was *structurally valid*, so
nothing mechanical objected. This harness closes that gap — it asserts WHICH
RELATIONSHIP the mapper picks, over pools whose correct answer is fixed by
construction.

What it isolates
----------------
Only the mapper. Claim maps are HAND-AUTHORED with `metadata.grounds.applied`
already True and question-shaped elements already written, so the decompose
stage never runs. Inputs are therefore byte-identical across repeats and the
ONLY source of variation is the LLM — which is exactly the uncertainty the
single live check (TRU-69E2-51DC) could not measure.

The matrix
----------
Six cells. Each pool has ONE target item whose correct relationship is fixed by
construction, plus distractors so the choice is non-trivial.

  WE_AFFIRM      whether/extent  + affirming evidence          -> supports
  WE_NEGATE      whether/extent  + negating evidence           -> challenges  ★ THE FIX
  ENUM_SUPPLY    enumerative     + evidence supplying answer    -> supports
  ENUM_GRIM      enumerative     + BAD-SOUNDING but responsive  -> supports    ★ THE TEETH
  ENUM_CONTRA    enumerative     + contradicts reported figure  -> challenges
  HYBRID         surface-enum w/ embedded comparison, negating  -> challenges  ★ THE LIVE SHAPE

ENUM_GRIM is the cell that matters most and the one the live check never
tested. TRU-69E2-51DC's two enumerative grounds (documented costs; documented
allocation decisions) both had *neutral-sounding* evidence, so they would have
been `supports` under the OLD rule too — they carry no discriminating
information. ENUM_GRIM asks the question that separates "the model understood
the two-shape rule" from "the model just flipped to negative-sounding =
challenges". If ENUM_GRIM fails, the fix over-corrected.

HYBRID reproduces the live e02 shape: surface form is enumerative ("What are
the documented outcomes...?") but it embeds a comparison, so it must be read
directionally. This is the boundary the rule rides on, and the reason the fix
is prompt-only rather than mechanical.

Gate
----
GREEN = every cell hits its expected relationship on EVERY repeat. Per-cell hit
rates are printed so a partial failure shows as instability rather than a flat
fail — instability is the finding that would justify building the mechanical
question-shape tagger (NF-11: fragile boundaries need a mechanical backstop).

Run
---
  cd backend && python -m scripts.grounds_direction_eval --repeats 5

Needs the PROD mapping model to be meaningful (Gemini 2.5 Flash). With no
GEMINI_API_KEY locally, run it against prod credentials:
  railway run python -m scripts.grounds_direction_eval --repeats 5

Writes backend/scripts/.grounds_direction_eval.json (appends run history).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from collections import Counter
from typing import Any, Dict, List

from app.pipeline.claim_map_analyzer import ClaimMapAnalyzer

# ── The battery ─────────────────────────────────────────────────────────────
# Every pool: exactly one TARGET item (relationship fixed by construction) plus
# distractors. `expect` is asserted against the target's mapped relationship.

BATTERY: List[Dict[str, Any]] = [
    {
        "cell": "WE_AFFIRM",
        "shape": "whether/extent",
        "claim": "Rolling out the vaccine to over-65s is indefensible",
        "question": "What is the clinical effectiveness of the vaccine against severe disease?",
        "target": "ev-target",
        "expect": "supports",
        "why": "Affirming answer to a whether/extent question. Must NOT have flipped to challenges.",
        "evidence": [
            {
                "evidence_id": "ev-target",
                "title": "Cohort study, national health registry",
                "snippet": "In a cohort of 1.2 million adults, vaccination was associated with 91% effectiveness against hospitalisation for severe disease, sustained over nine months.",
                "tier": "primary",
                "evidence_type": "academic",
            },
            {
                "evidence_id": "ev-dist1",
                "title": "Health department rollout schedule",
                "snippet": "The over-65s cohort was invited from 1 September, with second doses scheduled twelve weeks later across 1,400 sites.",
                "tier": "primary",
                "evidence_type": "government",
            },
            {
                "evidence_id": "ev-dist2",
                "title": "Newspaper column",
                "snippet": "Whatever the trial data says, the whole programme feels rushed and badly explained to the public.",
                "tier": "commentary",
                "evidence_type": "opinion",
            },
        ],
    },
    {
        "cell": "WE_NEGATE",
        "shape": "whether/extent",
        "claim": "Funding the therapy from the public health budget is indefensible",
        "question": "What is the clinical effectiveness of the therapy compared with placebo?",
        "target": "ev-target",
        "expect": "challenges",
        "why": "★ THE FIX. Negative answer to a whether/extent question. The OLD rule scored this `supports` because it 'ANSWERED the question'.",
        "evidence": [
            {
                "evidence_id": "ev-target",
                "title": "Systematic review of randomised trials",
                "snippet": "Across 42 randomised placebo-controlled trials, the therapy showed no effect beyond placebo for any indication examined.",
                "tier": "primary",
                "evidence_type": "academic",
            },
            {
                "evidence_id": "ev-dist1",
                "title": "Professional body membership register",
                "snippet": "The faculty was incorporated in 1950 and currently lists 1,100 registered practitioners.",
                "tier": "reporting",
                "evidence_type": "analysis",
            },
            {
                "evidence_id": "ev-dist2",
                "title": "Practitioner association blog",
                "snippet": "Patients consistently tell us they feel better after treatment, whatever the trials claim.",
                "tier": "commentary",
                "evidence_type": "opinion",
            },
        ],
    },
    {
        "cell": "ENUM_SUPPLY",
        "shape": "enumerative",
        "claim": "The department's handling of the waiting-list plan is indefensible",
        "question": "What were the stated targets in the department's published plan?",
        "target": "ev-target",
        "expect": "supports",
        "why": "Enumerative question; evidence supplies exactly what was asked. Baseline.",
        "evidence": [
            {
                "evidence_id": "ev-target",
                "title": "Department published delivery plan",
                "snippet": "The plan sets two targets: reduce the elective waiting list to 500,000 by 2026, and treat 95% of A&E attendances within four hours.",
                "tier": "primary",
                "evidence_type": "government",
            },
            {
                "evidence_id": "ev-dist1",
                "title": "Think-tank commentary",
                "snippet": "Ministers have set targets like this before and rarely met them; the credibility gap is the real story.",
                "tier": "commentary",
                "evidence_type": "opinion",
            },
            {
                "evidence_id": "ev-dist2",
                "title": "Regional news report",
                "snippet": "Two hospitals in the region opened additional day-surgery capacity in March.",
                "tier": "reporting",
                "evidence_type": "news",
            },
        ],
    },
    {
        "cell": "ENUM_GRIM",
        "shape": "enumerative",
        "claim": "The trust's infection-control record is indefensible",
        "question": "What was the recorded rate of hospital-acquired infection at the trust in 2024?",
        "target": "ev-target",
        "expect": "supports",
        "why": "★ THE TEETH. Enumerative question; the evidence SUPPLIES the figure asked for, but the figure sounds damning. Two-shape rule -> supports (it answers). A naive 'negative-sounding = challenges' read -> challenges. A failure here means the fix OVER-CORRECTED.",
        "evidence": [
            {
                "evidence_id": "ev-target",
                "title": "Regulator annual infection surveillance return",
                "snippet": "The trust recorded a hospital-acquired infection rate of 8.1% in 2024 — the highest of any trust in the region and well above the 2% national threshold.",
                "tier": "primary",
                "evidence_type": "government",
            },
            {
                "evidence_id": "ev-dist1",
                "title": "Trust board minutes",
                "snippet": "The board reviewed ward refurbishment scheduling and agreed to defer two projects to the next financial year.",
                "tier": "primary",
                "evidence_type": "government",
            },
            {
                "evidence_id": "ev-dist2",
                "title": "Local newspaper editorial",
                "snippet": "Something has gone badly wrong at this trust and somebody ought to answer for it.",
                "tier": "commentary",
                "evidence_type": "opinion",
            },
        ],
    },
    {
        "cell": "ENUM_CONTRA",
        "shape": "enumerative",
        "claim": "Continuing to fund the programme is indefensible",
        "question": "What are the documented annual costs of the programme?",
        "target": "ev-target",
        "expect": "challenges",
        "why": "Enumerative question; evidence CONTRADICTS the figure another source reports. Challenges, per the enumerative branch.",
        "evidence": [
            {
                "evidence_id": "ev-reported",
                "title": "Programme office cost statement",
                "snippet": "The programme office reports annual running costs of £4 million.",
                "tier": "primary",
                "evidence_type": "government",
            },
            {
                "evidence_id": "ev-target",
                "title": "National Audit Office value-for-money report",
                "snippet": "The £4 million figure excludes staff time and estate costs; the true annual cost of the programme is £11 million, nearly three times the published figure.",
                "tier": "primary",
                "evidence_type": "government",
            },
            {
                "evidence_id": "ev-dist1",
                "title": "Sector trade magazine",
                "snippet": "Programmes of this type typically run for five to seven years before review.",
                "tier": "reporting",
                "evidence_type": "analysis",
            },
        ],
    },
    {
        "cell": "HYBRID",
        "shape": "surface-enumerative, embedded comparison",
        "claim": "Offering the treatment on the public health service is indefensible",
        "question": "What are the documented patient outcomes for the treatment compared with standard care?",
        "target": "ev-target",
        "expect": "challenges",
        "why": "★ THE LIVE SHAPE (TRU-69E2-51DC e02). Surface form is enumerative but it embeds a comparison, so it must be read directionally. This is the boundary the prompt-only rule rides on.",
        "evidence": [
            {
                "evidence_id": "ev-target",
                "title": "Pooled analysis of controlled trials",
                "snippet": "Across 12 controlled trials, outcomes for patients receiving the treatment were no better than standard care on any measured endpoint, including symptom duration and readmission.",
                "tier": "primary",
                "evidence_type": "academic",
            },
            {
                "evidence_id": "ev-dist1",
                "title": "Service provision statistics",
                "snippet": "The treatment was offered at 14 sites in 2024, with 3,200 completed courses recorded.",
                "tier": "primary",
                "evidence_type": "statistical",
            },
            {
                "evidence_id": "ev-dist2",
                "title": "Patient forum thread",
                "snippet": "It worked for me when nothing else did — I would not want it taken away.",
                "tier": "commentary",
                "evidence_type": "opinion",
            },
        ],
    },
]


def _claim_map(case: Dict[str, Any]) -> Dict[str, Any]:
    """Hand-authored grounds claim_map — decompose never runs, so repeats are
    byte-identical and the LLM is the only variable."""
    return {
        "claim_id": f"dir-{case['cell'].lower()}",
        "normalised_claim": case["claim"],
        "claim_type": "normative_flagged",
        "elements": [
            {
                "element_id": "e1",
                "description": case["question"],
                "evidence_refs": [],
                "state": None,
                "uncertainty": None,
            }
        ],
        "orientation": None,
        "orientation_basis": None,
        "metadata": {
            "element_count": 1,
            # The marker `_grounds_applied` reads — this is what appends
            # GROUNDS_MAPPING_ADDENDUM to the mapping prompt.
            "grounds": {"applied": True, "converged": True, "element_count": 1},
        },
    }


def _plain(v: Any) -> Any:
    return v.value if hasattr(v, "value") else v


async def _run_case(analyzer: ClaimMapAnalyzer, case: Dict[str, Any]) -> Dict[str, Any]:
    cm = _claim_map(case)
    try:
        await analyzer.map_evidence_to_elements(cm, [dict(e) for e in case["evidence"]])
    except (
        Exception
    ) as exc:  # a dead key / transport error must not look like a verdict
        return {"cell": case["cell"], "error": f"{type(exc).__name__}: {exc}"}

    elems = cm.get("elements") or []
    refs = (elems[0].get("evidence_refs") or []) if elems else []
    got = None
    for r in refs:
        if r.get("evidence_id") == case["target"]:
            got = str(_plain(r.get("relationship")))
            break

    return {
        "cell": case["cell"],
        "expect": case["expect"],
        "got": got,  # None = target left unmapped
        "hit": got == case["expect"],
        "state": str(_plain(elems[0].get("state"))) if elems else None,
        "n_refs": len(refs),
        "refs": [
            {
                "evidence_id": r.get("evidence_id"),
                "relationship": str(_plain(r.get("relationship"))),
                "reasoning": r.get("reasoning"),
            }
            for r in refs
        ],
    }


async def main(repeats: int) -> None:
    analyzer = ClaimMapAnalyzer()
    per_cell: Dict[str, List[Dict[str, Any]]] = {c["cell"]: [] for c in BATTERY}

    for rep in range(1, repeats + 1):
        print(f"\n{'=' * 78}\nREPEAT {rep}/{repeats}")
        # Cases are independent -> run concurrently; repeats stay sequential so
        # a rate limit degrades throughput rather than corrupting the sample.
        outcomes = await asyncio.gather(
            *(_run_case(analyzer, case) for case in BATTERY)
        )
        for case, out in zip(BATTERY, outcomes):
            per_cell[case["cell"]].append(out)
            if out.get("error"):
                print(f"  {case['cell']:<12} ⚠️  {out['error'][:90]}")
                continue
            mark = "✅" if out["hit"] else "❌"
            got = out["got"] or "UNMAPPED"
            print(
                f"  {case['cell']:<12} {mark} expect={out['expect']:<10} "
                f"got={got:<10} state={out['state']} refs={out['n_refs']}"
            )
            if not out["hit"]:
                for r in out["refs"]:
                    if r["evidence_id"] == case["target"]:
                        print(f"       reasoning: {str(r['reasoning'])[:110]}")

    # ── verdict ─────────────────────────────────────────────────────────────
    print(f"\n{'=' * 78}\nPER-CELL HIT RATE ({repeats} repeats)\n")
    all_green = True
    summary = []
    for case in BATTERY:
        outs = per_cell[case["cell"]]
        errs = [o for o in outs if o.get("error")]
        hits = sum(1 for o in outs if o.get("hit"))
        n = len(outs) - len(errs)
        rate = f"{hits}/{n}" if n else "0/0"
        stable = n > 0 and hits == n
        drift = Counter(
            (o.get("got") or "UNMAPPED") for o in outs if not o.get("error")
        )
        if not stable:
            all_green = False
        star = "★" if case["cell"] in {"WE_NEGATE", "ENUM_GRIM", "HYBRID"} else " "
        print(
            f" {star} {case['cell']:<12} {rate:>6}  expect={case['expect']:<10} "
            f"seen={dict(drift)}{'  ⚠️ ERRORS=' + str(len(errs)) if errs else ''}"
        )
        summary.append(
            {
                "cell": case["cell"],
                "shape": case["shape"],
                "expect": case["expect"],
                "hits": hits,
                "n": n,
                "errors": len(errs),
                "seen": dict(drift),
                "stable": stable,
                "why": case["why"],
            }
        )

    print()
    if all_green:
        print("🟢 GREEN — every cell hit its expected relationship on every repeat.")
        print("   The two-shape rule is stable across draws on this battery.")
    else:
        print("🔴 NOT GREEN — at least one cell is wrong or UNSTABLE across draws.")
        print("   Instability (not a flat fail) is the signal that justifies the")
        print("   mechanical question-shape tagger (NF-11 backstop). Read `seen`.")

    out_path = os.path.join(os.path.dirname(__file__), ".grounds_direction_eval.json")
    history: List[Any] = []
    if os.path.exists(out_path):
        try:
            with open(out_path, encoding="utf-8") as fh:
                history = json.load(fh)
        except Exception:
            history = []
    history.append(
        {
            "run": len(history) + 1,
            "repeats": repeats,
            "green": all_green,
            "summary": summary,
            "raw": {k: v for k, v in per_cell.items()},
        }
    )
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(history, fh, indent=2, ensure_ascii=False)
    print(f"\nSaved transcript → {out_path} (run {len(history)})")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--repeats", type=int, default=5)
    args = ap.parse_args()
    asyncio.run(main(args.repeats))
