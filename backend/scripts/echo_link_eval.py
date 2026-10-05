"""Held-out eval for echo link confirmation (build plan §1 step 2-3; design §10 M3).

PAID: every pair goes through the production module's own prompt, call and
validation (`app.services.echo_link_confirmation`). Ask the founder before
running. Quote the cost from `--limit 6` (one call) before a full run.

Inputs: audit/echo_precision/model_inputs.json (production-shaped text: page
opening + original snippet + selector passages; NOT the labellers' windows,
plan review H2) + key_heldout.json (pool and evidence ids). Pairs are grouped
by pool and chunked within a pool, as in production. Trusted date_basis is not
available offline, so the `predates` check never fires here.

    python -m scripts.echo_link_eval --run r1 [--limit 6]
    python -m scripts.echo_link_eval --score r1 [r2]
"""

import argparse
import asyncio
import json
import math
import os
from collections import Counter, defaultdict
from datetime import datetime, timezone

from app.core.cost_constants import GEMINI3_FLASH_STANDARD_FROM_2027
from app.core.cost_constants import LLM_PRICING_USD_PER_1M as MODEL_PRICING
from app.services import echo_link_confirmation as elc
from app.services.google_ai import call_google_ai_with_usage

HERE = os.path.dirname(os.path.abspath(__file__))
DIR = os.path.normpath(os.path.join(HERE, "..", "..", "audit", "echo_precision"))
OUT = os.path.join(DIR, "eval_runs")


def is_recovery(pair):
    """Recovery items arrive after the stage runs; production never sees them."""
    return any(pair[s]["evidence_id"].startswith(("ev-rec", "ev-rpf")) for s in ("a", "b"))


def load_pairs():
    """Model inputs built the way production builds them (plan review H2):
    audit/echo_precision/model_inputs.json from build_model_inputs.py."""
    key = {
        k["id"]: k
        for k in json.load(open(os.path.join(DIR, "key_heldout.json"), encoding="utf-8"))
    }
    inputs = json.load(open(os.path.join(DIR, "model_inputs.json"), encoding="utf-8"))
    pairs = []
    for pid in sorted(inputs):
        k = key[pid]
        a = {**inputs[pid]["A"], "tier": "primary"}
        b = {**inputs[pid]["B"], "tier": k["B_tier"]}
        pairs.append({"id": pid, "pool": k["claim_id"], "a": a, "b": b, "strong": k["strong_facts"], "sim": 0.0})
    return pairs


async def run(tag, limit):
    pairs = load_pairs()
    if limit:
        pairs = pairs[:limit]
    usage = Counter()
    seconds = []

    async def call(prompt):
        parsed, u = await call_google_ai_with_usage(
            prompt,
            temperature=0,
            max_tokens=elc.MAX_OUTPUT_TOKENS,
            timeout=elc.timeout_s(),
            model=elc.model(),
            response_schema=elc.RESPONSE_SCHEMA,
        )
        for k, v in (u or {}).items():
            usage[k] += v or 0
        usage["calls"] += 1
        return parsed

    by_pool = defaultdict(list)
    for p in pairs:
        by_pool[p["pool"]].append(p)
    sem = asyncio.Semaphore(6)
    results = {}

    async def one(pool, ps):
        async with sem:
            # Production caps at ECHO_LINK_MAX_PAIRS per check; the eval must
            # judge every labelled pair, so the cap is lifted here only.
            out = (
                await elc.confirm_pairs(ps, call)
                if len(ps) <= elc.MAX_PAIRS
                else await _uncapped(ps, call)
            )
            seconds.extend(out["stats"]["call_seconds"])
            reasons = {r["derivative_id"]: r["reason"] for r in out["reasons"]}
            for p, rec in zip(_ordered(ps, out["records"]), out["records"]):
                results[p["id"]] = {**rec, "reason": reasons.get(rec["derivative_id"])}

    await asyncio.gather(*(one(k, v) for k, v in by_pool.items()))
    cost = _cost(usage)
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, f"{tag}.json")
    json.dump(
        {
            "tag": tag,
            "model": elc.model(),
            "contract": elc.CONTRACT,
            "at": datetime.now(timezone.utc).isoformat(),
            "pairs": len(pairs),
            "usage": dict(usage),
            "cost": cost,
            "call_seconds": sorted(seconds),
            "results": results,
        },
        open(path, "w", encoding="utf-8"),
        ensure_ascii=False,
        indent=1,
    )
    print(
        f"pairs {len(pairs)} calls {usage['calls']} status {Counter(r['status'] for r in results.values())}"
    )
    print(f"tokens {dict(usage)}")
    print(
        f"cost now ${cost['usd_now']:.4f} | from 2027 ${cost['usd_2027']:.4f} | per pair ${cost['usd_now'] / max(1, len(pairs)):.5f}"
    )
    if seconds:
        s = sorted(seconds)
        print(
            f"call seconds p50 {s[len(s) // 2]:.1f} p90 {s[int(len(s) * 0.9) - 1 if len(s) > 1 else 0]:.1f} max {s[-1]:.1f}"
        )
    print("wrote", path)


async def _uncapped(ps, call):
    saved = elc.max_pairs
    elc.max_pairs = lambda: len(ps)
    try:
        return await elc.confirm_pairs(ps, call)
    finally:
        elc.max_pairs = saved


def _ordered(ps, records):
    """Map records back to pairs by (original_id, derivative_id)."""
    by = {(p["a"]["evidence_id"], p["b"]["evidence_id"]): p for p in ps}
    return [by[(r["original_id"], r["derivative_id"])] for r in records]


def _cost(usage):
    m = elc.model()
    now = MODEL_PRICING.get(m, {"input": 0, "output": 0})
    later = GEMINI3_FLASH_STANDARD_FROM_2027.get(m, now)
    out_tokens = usage.get("output_tokens", 0) + usage.get("thinking_tokens", 0)
    f = (
        lambda p: (usage.get("input_tokens", 0) * p["input"] + out_tokens * p["output"])
        / 1e6
    )
    return {"usd_now": f(now), "usd_2027": f(later)}


def wilson_lower(k, n, z=1.96):
    if n == 0:
        return 0.0
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    r = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (c - r) / d


def score(tags):
    labels = {
        l["id"]: l
        for l in json.load(
            open(os.path.join(DIR, "labels_heldout.json"), encoding="utf-8")
        )
    }
    key = {
        k["id"]: k
        for k in json.load(
            open(os.path.join(DIR, "key_heldout.json"), encoding="utf-8")
        )
    }
    rec = {p["id"]: is_recovery(p) for p in load_pairs()}
    runs = [
        json.load(open(os.path.join(OUT, f"{t}.json"), encoding="utf-8")) for t in tags
    ]
    for run_ in runs:
        res = run_["results"]
        print(
            f"\n== {run_['tag']} ({run_['pairs']} pairs, ${run_['cost']['usd_now']:.3f}) =="
        )
        strata = {
            "main (no recovery)": lambda i: not rec[i],
            "recovery": lambda i: rec[i],
            "all": lambda i: True,
            "gate_would_scope": lambda i: key[i].get("gate_would_scope_v2", key[i]["gate_would_scope"]) and not rec[i],
            "stored_text": lambda i: key[i]["verbatim_source"] == "stored",
            "refetched_text": lambda i: key[i]["verbatim_source"] == "refetched",
        }
        for name, keep in strata.items():
            # Plan review M7: pairs repeating a dev-set URL pair are not held out.
            ids = [i for i in res if keep(i) and not key[i].get("dev_url_pair")]
            conf = [i for i in ids if res[i]["status"] == "confirmed"]
            k = sum(labels[i]["label"] == "relay" for i in conf)
            relays = [i for i in ids if labels[i]["label"] == "relay"]
            found = sum(res[i]["status"] == "confirmed" for i in relays)
            indep = sum(labels[i]["label"] == "independent" for i in conf)
            prec = k / len(conf) if conf else float("nan")
            print(
                f"{name:17s} n={len(ids):3d} confirmed={len(conf):3d} relay={k:3d} indep={indep:2d} "
                f"precision={prec:.3f} wilson_lb={wilson_lower(k, len(conf)):.3f} recall={found}/{len(relays)}"
            )
        whole = [
            i
            for i in res
            if res[i]["status"] == "confirmed" and res[i].get("extent") == "whole"
        ]
        print(
            f"whole-extent confirmed {len(whole)} (relay {sum(labels[i]['label'] == 'relay' for i in whole)})"
        )
        print("status", dict(Counter(r["status"] for r in res.values())))
        print(
            "cue_not_found details",
            dict(
                Counter(
                    r.get("detail")
                    for r in res.values()
                    if r["status"] == "cue_not_found"
                )
            ),
        )
        wrong = [
            i
            for i in res
            if res[i]["status"] == "confirmed" and labels[i]["label"] != "relay"
        ]
        for i in wrong:
            print(
                f"  FALSE CONFIRM {i} label={labels[i]['label']} cue={res[i].get('cue')!r}"
            )
    if len(runs) == 2:
        a, b = runs[0]["results"], runs[1]["results"]
        common = set(a) & set(b)
        flips = [
            i
            for i in common
            if (a[i]["status"] == "confirmed") != (b[i]["status"] == "confirmed")
        ]
        print(
            f"\nflip rate (confirmed vs not) {len(flips)}/{len(common)} = {len(flips) / max(1, len(common)):.3f}"
        )


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--run")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--score", nargs="+")
    args = ap.parse_args()
    if args.score:
        score(args.score)
    elif args.run:
        asyncio.run(run(args.run, args.limit))
    else:
        ap.error("--run TAG or --score TAG [TAG]")
