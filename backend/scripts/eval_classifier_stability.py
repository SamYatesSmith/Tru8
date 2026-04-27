#!/usr/bin/env python3
"""Article classifier stability probe.

Hypothesis: the misroutes observed in the 2026-04-27 verification arc were
stochastic (LLM non-determinism at temperature 0.1) rather than deterministic
surface-phrasing fragility — because the same claims classify correctly on a
single steady-state run.

Procedure: run a small set of high-signal claims N times each (default 10),
record the distribution of (primary_domain, jurisdiction) outputs.

Usage:
    python scripts/eval_classifier_stability.py
    python scripts/eval_classifier_stability.py --runs 20
"""

import asyncio
import json
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv  # type: ignore

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from app.utils.article_classifier import _classify_with_fallback_llm  # noqa: E402


CLAIMS = [
    # ---- Currency-cue probe (BP series) ----
    # variant-bp-2 (from prior run) failed 10/10: $ flipped jurisdiction to Global.
    # Probe whether $ vs £ is sufficient on its own, or whether other cues co-vary.
    {
        "id": "bp-plc-gbp",
        "text": "BP plc reported record profits of GBP 28 billion in 2022",
        "expected": ("Finance", "UK"),
    },
    {
        "id": "bp-plc-usd",
        "text": "BP plc reported record profits of $40 billion in 2022",
        "expected": ("Finance", "UK"),
    },
    {
        "id": "bp-bare-usd",
        "text": "BP reported record profits of $40 billion in 2022",
        "expected": ("Finance", "UK"),
    },
    {
        "id": "bp-british-usd",
        "text": "British oil major BP reported record profits of $40 billion in 2022",
        "expected": ("Finance", "UK"),
    },
    # ---- US symmetric probe (does sterling currency flip US -> UK?) ----
    {
        "id": "exxon-bare-usd",
        "text": "ExxonMobil reported record profits of $56 billion in 2022",
        "expected": ("Finance", "US"),
    },
    {
        "id": "exxon-bare-gbp",
        "text": "ExxonMobil reported record profits of GBP 50 billion in 2022",
        "expected": ("Finance", "US"),
    },
    # ---- Year-position probe ("Foo 2008" vs "2008 Foo") ----
    # In prior arc: "Climate Change Act 2008 set the UK's target..." -> UK
    #               "The 2008 Climate Change Act commits the United Kingdom..." -> US
    # Both classify UK now (10/10), so probe more precisely
    {
        "id": "act-uk-bare",
        "text": "The Climate Change Act 2008 commits the country to net zero by 2050",
        "expected": ("Climate", "UK"),  # ambiguous-by-design
    },
    {
        "id": "act-bare",
        "text": "The 2008 Climate Change Act commits the country to net zero by 2050",
        "expected": ("Climate", "UK"),  # ambiguous-by-design (UK only world has this)
    },
    # ---- Multi-jurisdiction stressor ----
    {
        "id": "multi-1",
        "text": "Apple Inc paid 13 billion euros in back taxes after the EU competition ruling",
        "expected": ("Law", "EU"),  # US company, EU jurisdiction = locus
    },
]


async def run_one(text: str) -> dict:
    c = await _classify_with_fallback_llm("", "", text)
    if c is None:
        return {
            "primary_domain": None,
            "jurisdiction": None,
            "secondary": [],
            "confidence": 0,
        }
    return {
        "primary_domain": c.primary_domain,
        "jurisdiction": c.jurisdiction,
        "secondary": c.secondary_domains,
        "confidence": c.confidence,
    }


async def main():
    args = sys.argv[1:]
    runs = 10
    if "--runs" in args:
        runs = int(args[args.index("--runs") + 1])

    print(
        f"Stability probe: {len(CLAIMS)} claims x {runs} runs each = {len(CLAIMS) * runs} calls\n"
    )

    results = []
    for claim in CLAIMS:
        cid = claim["id"]
        exp_dom, exp_jur = claim["expected"]
        outputs = []
        t0 = time.monotonic()
        for r in range(runs):
            out = await run_one(claim["text"])
            outputs.append(out)
        dt = time.monotonic() - t0

        jur_counts = Counter(o["jurisdiction"] for o in outputs)
        dom_counts = Counter(o["primary_domain"] for o in outputs)
        jur_correct = sum(1 for o in outputs if o["jurisdiction"] == exp_jur)
        dom_primary_correct = sum(1 for o in outputs if o["primary_domain"] == exp_dom)
        dom_any_correct = sum(
            1
            for o in outputs
            if o["primary_domain"] == exp_dom or exp_dom in (o["secondary"] or [])
        )

        result = {
            "id": cid,
            "text": claim["text"],
            "expected": f"{exp_dom}/{exp_jur}",
            "n_runs": runs,
            "jur_correct": jur_correct,
            "dom_primary_correct": dom_primary_correct,
            "dom_any_correct": dom_any_correct,
            "jur_distribution": dict(jur_counts),
            "dom_distribution": dict(dom_counts),
            "outputs": outputs,
            "elapsed_s": round(dt, 1),
        }
        results.append(result)

        print(f"[{cid}] {claim['text'][:70]}")
        print(f"  expected: {exp_dom}/{exp_jur}")
        print(f"  jur: {jur_correct}/{runs} correct  dist={dict(jur_counts)}")
        print(
            f"  dom: {dom_primary_correct}/{runs} primary  {dom_any_correct}/{runs} any-slot  "
            f"dist={dict(dom_counts)}"
        )
        print(f"  ({dt:.1f}s)\n")

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = Path(__file__).resolve().parent.parent / "data"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"article_classifier_stability_{timestamp}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(
            {"timestamp": timestamp, "runs_per_claim": runs, "results": results},
            f,
            indent=2,
        )
    print(f"Saved: {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
