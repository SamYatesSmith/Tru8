"""Does the mapper treat a recital of the claim as SUPPORT? (2026-08-25)

WHY
---
On 2026-08-25 the wildfire claim was re-run after the Gemini 2.5 -> 3.x
migration. Matt Ridley's tweet — which IS the claim being checked — came back
mapped as `supports` on both elements. The 21 August run of the same claim
mapped it `context`, with the mapper's own reasoning citing "a recital of the
claim itself".

Two findings came out of investigating that, and this script tests the second:

1. The MECHANICAL recital gate never fired on either run. It arms only when
   `claim_map["metadata"]["subjects"]` is non-empty (claim_map_analyzer.py:2522),
   and this claim names no claimant, so `subjects` is []. The gate was built for
   TRU-018F-44AA ("Trump stopped 6 wars"), which HAS a named subject — claims
   without one were never in its test set. Structural, not a model issue.

2. Which means the only live defence was the RECITAL CHECK rule in
   MAPPING_PROMPT — a prompt-only defence. 2.5-flash obeyed it; 3.5-flash-lite
   did not. **That is what this script measures**, and n=1 is not enough to call
   it: it could be one bad roll.

METHOD
------
The pool is FROZEN (scripts/.recital_pool.json — the real 21 Aug evidence set,
including the Ridley tweet). Retrieval never runs, so run-to-run churn — which
was measured at 62% of URLs between identical checks — cannot confound the
result. Only the model and the repeat index vary.

Counting `supports` on the recital item is the whole measurement. A recital
counted as support is the TRU-018F-44AA failure and an invariant #7 breach:
"X claimed Y" is never evidence of Y.

USAGE
    python -m scripts.recital_repeat_probe --dry-run
    python -m scripts.recital_repeat_probe --run --repeats 5
"""

from __future__ import annotations

import argparse
import asyncio
import copy
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

POOL_PATH = Path(__file__).parent / ".recital_pool.json"
RESULTS_PATH = Path(__file__).parent / ".recital_repeat_results.json"

RECITAL_EVIDENCE_ID = "ev-de4aa1eb9d71"  # the Ridley tweet — it IS the claim

MODELS = ["gemini-2.5-flash", "gemini-3.5-flash-lite", "gemini-3.7-flash"]

# ~12k in / ~4.75k out per mapping call, USD/1M from cost_constants.
_RATES = {
    "gemini-2.5-flash": (0.30, 2.50),
    "gemini-3.5-flash-lite": (0.30, 2.50),
    "gemini-3.7-flash": (0.75, 3.75),
}


def _estimate_usd(models: List[str], repeats: int) -> float:
    return sum(
        repeats
        * (
            12_000 / 1e6 * _RATES.get(m, (0.3, 2.5))[0]
            + 4_750 / 1e6 * _RATES.get(m, (0.3, 2.5))[1]
        )
        for m in models
    )


async def _map_once(pool: Dict[str, Any], model: str) -> Dict[str, Any]:
    from app.pipeline.claim_map_analyzer import ClaimMapAnalyzer

    scaffold = copy.deepcopy(pool["scaffold"])
    evidence = copy.deepcopy(pool["evidence"])

    analyzer = ClaimMapAnalyzer()
    analyzer.mapping_google_model = model

    try:
        await analyzer.map_evidence_batch(
            [{"claim_map": scaffold, "evidence": evidence}]
        )
    except Exception as exc:  # noqa: BLE001
        return {"model": model, "error": str(exc)}

    out: Dict[str, Any] = {"model": model, "recital": {}, "states": {}, "reasoning": {}}
    for el in scaffold.get("elements") or []:
        eid = el.get("element_id")
        out["states"][eid] = el.get("state")
        for ref in el.get("evidence_refs") or []:
            if ref.get("evidence_id") == RECITAL_EVIDENCE_ID:
                out["recital"][eid] = ref.get("relationship")
                out["reasoning"][eid] = (ref.get("reasoning") or "")[:180]

    served = analyzer.get_models_used()
    out["model_served"] = served.get("batch_mapping") or served.get("mapping") or ""
    out["arm_applied"] = model.lower() in (out["model_served"] or "").lower()
    return out


async def run(models: List[str], repeats: int) -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

    pool = json.loads(POOL_PATH.read_text(encoding="utf-8"))[0]
    results: Dict[str, List[Dict[str, Any]]] = {}

    for model in models:
        results[model] = []
        for k in range(repeats):
            r = await _map_once(pool, model)
            results[model].append(r)
            rec = r.get("recital") or {}
            flag = "  <-- RECITAL AS SUPPORT" if "supports" in rec.values() else ""
            print(
                f"  {model:<24} k={k}: recital={rec or 'unmapped'} "
                f"states={r.get('states')}{flag}"
            )

    RESULTS_PATH.write_text(json.dumps(results, indent=1), encoding="utf-8")
    print(f"\nraw -> {RESULTS_PATH}")

    print("\n" + "=" * 78)
    print(
        f"{'model':<26} {'supports':>9} {'context':>9} {'challenges':>11} {'unmapped':>9}"
    )
    print("-" * 78)
    for model, runs in results.items():
        c = Counter()
        for r in runs:
            rec = r.get("recital") or {}
            if not rec:
                c["unmapped"] += 1
                continue
            for v in rec.values():
                c[v or "none"] += 1
        print(
            f"{model:<26} {c['supports']:>9} {c['context']:>9} "
            f"{c['challenges']:>11} {c['unmapped']:>9}"
        )
    print("=" * 78)
    print("counts are per element-reference across all repeats (2 elements/run).")
    print("`supports` on a recital = the TRU-018F-44AA failure, invariant #7 breach.")
    bad = [
        r for runs in results.values() for r in runs if not r.get("arm_applied", True)
    ]
    if bad:
        print(
            f"\n[!] {len(bad)} run(s) served by a different model — those rows are invalid."
        )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", action="store_true", help="execute (SPENDS MONEY)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--repeats", type=int, default=5)
    ap.add_argument("--models", default=None)
    args = ap.parse_args()

    models = (
        [m.strip() for m in args.models.split(",") if m.strip()]
        if args.models
        else list(MODELS)
    )
    if not POOL_PATH.exists():
        print(f"missing frozen pool: {POOL_PATH}")
        return

    est = _estimate_usd(models, args.repeats)
    print(
        f"plan: {len(models)} models x {args.repeats} repeats = "
        f"{len(models) * args.repeats} mapping calls (no retrieval)"
    )
    print(f"      models: {', '.join(models)}")
    print(f"estimated spend: ~${est:.2f} (~{est * 78:.0f}p)")
    if args.dry_run or not args.run:
        print("\ndry run — nothing spent.")
        return
    asyncio.run(run(models, args.repeats))


if __name__ == "__main__":
    main()
