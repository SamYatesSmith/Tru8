"""Sweep MAPPING_THINKING_BUDGET against frozen evidence pools (M1).

Phase A (--freeze): run N live checks on diverse claims, capture each claim's
pre-mapping scaffold + evidence pool to a JSON file. ~$0.15/claim.

Phase B (--sweep): for each budget in {None (dynamic), 4096, 2048, 1024, 0},
k repeats per claim, call the analyzer's mapping directly on deep copies of
the frozen pool. Deterministic input — only the mapping call varies. Reports
per budget: latency, thinking tokens, element-state agreement vs the
dynamic-modal baseline, evidence coverage, reasoning presence/length.

The dynamic (None) runs double as the variance floor: budget quality is
judged against dynamic's own k-run self-agreement, not against a single run.

Usage (Postgres + Redis up; local only, untracked like profile_stage_timings):
    cd backend
    python -m scripts.mapping_budget_sweep --freeze          # ~$0.45, ~5 min
    python -m scripts.mapping_budget_sweep --sweep           # ~$0.2-0.4, ~20 min
    python -m scripts.mapping_budget_sweep --sweep --repeats 2 --budgets 0,1024
"""

from __future__ import annotations

import argparse
import asyncio
import copy
import json
import statistics as stats
import time
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional

POOL_PATH = Path(__file__).parent / ".mapping_sweep_pool.json"

FREEZE_CLAIMS = [
    "The 2022 UK mini-budget caused a sharp rise in government borrowing costs.",
    "Global measles cases rose sharply in 2024 as vaccination rates declined.",
    "The EU imposed several rounds of sanctions on Russia following the 2022 invasion of Ukraine.",
]

SWEEP_BUDGETS_DEFAULT = [None, 4096, 2048, 1024, 0]  # None = dynamic (baseline)


# ---------------------------------------------------------------------------
# Phase A — freeze pools
# ---------------------------------------------------------------------------


def _strip_scaffold(claim_map: Dict[str, Any]) -> Dict[str, Any]:
    """Reduce a mapped claim_map back to its pre-mapping scaffold."""
    scaffold = copy.deepcopy(claim_map)
    scaffold["orientation"] = None
    scaffold["orientation_basis"] = None
    for el in scaffold.get("elements", []):
        el["evidence_refs"] = []
        el["state"] = None
        el["uncertainty"] = None
    return scaffold


async def _freeze_one(claim_text: str) -> Optional[Dict[str, Any]]:
    from app.core.database import async_session
    from app.pipeline.progress import ProgressReporter
    from app.pipeline.runner import run_pipeline
    from scripts.replay_bench.runner import (
        _bust_pipeline_caches,
        _cleanup_check,
        _create_check,
        _ensure_bench_user,
    )

    await _bust_pipeline_caches()
    input_data = {
        "input_type": "text",
        "content": claim_text,
        "url": None,
        "user_query": None,
    }
    async with async_session() as s:
        user = await _ensure_bench_user(s)
        check = await _create_check(s, user.id, input_data)
        cid, uid = check.id, user.id

    result = await asyncio.wait_for(
        run_pipeline(
            cid,
            uid,
            {**input_data, "file_path": None},
            ProgressReporter(cid),
        ),
        timeout=300,
    )
    async with async_session() as s:
        await _cleanup_check(s, cid)
    if not result:
        return None

    claims = result.get("claims") or result.get("selected_claims") or []
    if not claims:
        # runner returns claims under result["claims"]
        print(f"  WARNING: no claims in result keys={list(result.keys())[:12]}")
        return None
    claim = claims[0]
    cm = claim.get("claim_map")
    ev = claim.get("evidence") or []
    if not cm or not ev:
        print(f"  WARNING: missing claim_map or evidence (ev={len(ev)})")
        return None
    return {
        "claim_text": claim_text,
        "scaffold": _strip_scaffold(cm),
        "evidence": ev,
        "mapped_states_at_freeze": {
            el["element_id"]: el.get("state") for el in cm.get("elements", [])
        },
    }


async def freeze() -> None:
    pools = []
    for i, text in enumerate(FREEZE_CLAIMS, 1):
        print(f"--- freezing {i}/{len(FREEZE_CLAIMS)}: {text[:60]}...")
        try:
            pool = await _freeze_one(text)
        except Exception as exc:  # noqa: BLE001
            print(f"  ERROR {type(exc).__name__}: {exc}")
            continue
        if pool:
            n_el = len(pool["scaffold"].get("elements", []))
            print(f"  ok: {n_el} elements, {len(pool['evidence'])} evidence items")
            pools.append(pool)
    POOL_PATH.write_text(json.dumps(pools, indent=1), encoding="utf-8")
    print(f"\nFroze {len(pools)} pools -> {POOL_PATH}")


# ---------------------------------------------------------------------------
# Phase B — sweep
# ---------------------------------------------------------------------------


def _observe(claim_map: Dict[str, Any], pool_size: int) -> Dict[str, Any]:
    """Extract quality signals from a mapped claim_map."""
    states = {}
    refs_total = 0
    mapped_ids = set()
    reasoning_lens: List[int] = []
    for el in claim_map.get("elements", []):
        states[el["element_id"]] = el.get("state")
        for ref in el.get("evidence_refs", []) or []:
            refs_total += 1
            mapped_ids.add(ref.get("evidence_id"))
            reasoning_lens.append(len((ref.get("reasoning") or "").strip()))
    return {
        "states": states,
        "orientation": claim_map.get("orientation"),
        "refs_total": refs_total,
        "coverage": len(mapped_ids) / pool_size if pool_size else 0.0,
        "reasoning_nonempty_share": (
            sum(1 for L in reasoning_lens if L > 0) / len(reasoning_lens)
            if reasoning_lens
            else 0.0
        ),
        "reasoning_mean_len": (stats.mean(reasoning_lens) if reasoning_lens else 0.0),
    }


async def _map_once(pool: Dict[str, Any], budget: Optional[int]) -> Dict[str, Any]:
    from app.pipeline.claim_map_analyzer import ClaimMapAnalyzer

    scaffold = copy.deepcopy(pool["scaffold"])
    evidence = copy.deepcopy(pool["evidence"])

    analyzer = ClaimMapAnalyzer()
    analyzer.mapping_thinking_budget = budget  # the knob under test

    t0 = time.monotonic()
    await analyzer.map_evidence_batch([{"claim_map": scaffold, "evidence": evidence}])
    elapsed = time.monotonic() - t0

    usage = analyzer.get_token_usage()
    obs = _observe(scaffold, len(evidence))
    obs.update(
        {
            "elapsed_s": round(elapsed, 2),
            "thinking_tokens": usage.get("thinking_tokens", 0),
            "output_tokens": usage.get("output_tokens", 0),
            "models_used": analyzer.get_models_used(),
            "fallback_fired": analyzer.get_fallback_status(),
        }
    )
    return obs


def _modal_states(runs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Per-element modal state across runs."""
    by_el: Dict[str, Counter] = {}
    for r in runs:
        for eid, st in r["states"].items():
            by_el.setdefault(eid, Counter())[st] += 1
    return {eid: c.most_common(1)[0][0] for eid, c in by_el.items()}


def _agreement(states: Dict[str, Any], baseline: Dict[str, Any]) -> float:
    keys = set(baseline) | set(states)
    if not keys:
        return 1.0
    same = sum(1 for k in keys if states.get(k) == baseline.get(k))
    return same / len(keys)


async def sweep(budgets: List[Optional[int]], repeats: int) -> None:
    pools = json.loads(POOL_PATH.read_text(encoding="utf-8"))
    print(f"Sweeping {len(pools)} pools x {len(budgets)} budgets x {repeats} repeats\n")

    # results[budget_label][pool_idx] = list of observations
    results: Dict[str, Dict[int, List[Dict[str, Any]]]] = {}
    for budget in budgets:
        label = "dynamic" if budget is None else str(budget)
        results[label] = {}
        for pi, pool in enumerate(pools):
            runs = []
            for k in range(repeats):
                try:
                    obs = await _map_once(pool, budget)
                except Exception as exc:  # noqa: BLE001
                    print(f"  ERROR budget={label} pool={pi} k={k}: {exc}")
                    continue
                runs.append(obs)
                print(
                    f"  budget={label:>7} pool={pi} k={k}: "
                    f"{obs['elapsed_s']:6.1f}s think={obs['thinking_tokens']:>5} "
                    f"out={obs['output_tokens']:>5} cov={obs['coverage']:.2f} "
                    f"states={list(obs['states'].values())}"
                )
            results[label][pi] = runs

    # Baseline: dynamic modal states per pool
    baselines = {pi: _modal_states(results["dynamic"][pi]) for pi in range(len(pools))}
    # Dynamic self-agreement = variance floor
    print("\n" + "=" * 78)
    print(
        f"{'budget':>8} {'lat mean':>9} {'lat min-max':>13} {'think':>7} "
        f"{'agree':>7} {'cov':>6} {'reason%':>8} {'r-len':>6}"
    )
    print("-" * 78)
    for label, by_pool in results.items():
        lats, thinks, agrees, covs, rshares, rlens = [], [], [], [], [], []
        for pi, runs in by_pool.items():
            for r in runs:
                lats.append(r["elapsed_s"])
                thinks.append(r["thinking_tokens"])
                agrees.append(_agreement(r["states"], baselines[pi]))
                covs.append(r["coverage"])
                rshares.append(r["reasoning_nonempty_share"])
                rlens.append(r["reasoning_mean_len"])
        if not lats:
            continue
        print(
            f"{label:>8} {stats.mean(lats):8.1f}s "
            f"{min(lats):5.1f}-{max(lats):5.1f}s "
            f"{stats.mean(thinks):7.0f} "
            f"{stats.mean(agrees):6.1%} {stats.mean(covs):6.2f} "
            f"{stats.mean(rshares):7.1%} {stats.mean(rlens):6.0f}"
        )
    print("=" * 78)
    print("agree = element-state agreement vs dynamic-modal baseline;")
    print("dynamic's own row is the variance floor (self-agreement at temp 0.2).")

    out = Path(__file__).parent / ".mapping_sweep_results.json"
    out.write_text(json.dumps(results, indent=1), encoding="utf-8")
    print(f"raw results -> {out}")


# ---------------------------------------------------------------------------


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--freeze", action="store_true", help="Phase A: freeze pools")
    ap.add_argument("--sweep", action="store_true", help="Phase B: run the sweep")
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument(
        "--budgets",
        default=None,
        help="comma list, e.g. 'dynamic,4096,2048,1024,0' (default all)",
    )
    args = ap.parse_args()

    if args.freeze:
        asyncio.run(freeze())
    if args.sweep:
        budgets: List[Optional[int]] = SWEEP_BUDGETS_DEFAULT
        if args.budgets:
            budgets = [
                None if b.strip() in ("dynamic", "none") else int(b)
                for b in args.budgets.split(",")
            ]
        asyncio.run(sweep(budgets, args.repeats))
    if not args.freeze and not args.sweep:
        print("nothing to do: pass --freeze and/or --sweep")


if __name__ == "__main__":
    main()
