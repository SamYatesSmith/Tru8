"""F3 scope-sensitivity eval — tagger detection on REAL decomposed wording.

Design: audit/2026-07-07_f3_design_review.md §4. Phase A measures the ONE thing
the unit tests can't: whether the mechanical tagger fires on the element wording
the LLM decomposer actually produces (it may rephrase "Britain is the only
country" into "The UK water sector is fully privatised" — dropping the very
tokens the lexicon keys on). This is the NF-18 "test the wired path" lesson
applied to detection.

Phase A is DECOMPOSE-ONLY — one Gemini call per claim, no retrieval/mapping
spend. It records the detection baseline + confirms no scope caveat exists yet
(the response layer is Phase B). Phase B will extend this to the full pipeline
and measure caveat fire/false-positive rate against the same pool.

Metric per claim:
  * expect ∈ {geographic, universal, both, none}
  * hit  = the expected category fired on ≥1 decomposed element
  * fp   = for controls (expect=none), ANY element flagged = a false positive

Usage:
    python -m scripts.f3_scope_eval --label baseline
    python -m scripts.f3_scope_eval --compare      # prints the detection table

LIVE decompose (real Gemini). Results → scripts/.f3_scope_eval_<label>.json
(gitignored dot-file). Local-only tooling — not part of the shipped product.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

# expect: which category SHOULD fire. "none" = control (must stay silent).
POOL = [
    {
        "key": "water_britain",
        "claim": "Britain is the only country in the world with a fully privatised water system.",
        "expect": "both",
        "why": "Founder's flagship (TRU-EC8D-8BC8): composite geography (Britain⊋E&W) + universal ('only … in the world').",
    },
    {
        "key": "lhc_europe",
        "claim": "Only European countries contributed to building the Large Hadron Collider.",
        "expect": "both",
        "why": "Second flagship (TRU-EAB8-2652): 'European' composite + 'only … countries' bounded-universal.",
    },
    {
        "key": "moon_us",
        "claim": "The United States is the only country to have landed people on the Moon.",
        "expect": "both",
        "why": "Composite ('United States') + universal ('the only country').",
    },
    {
        "key": "america_economy",
        "claim": "America has the largest economy in the world.",
        "expect": "both",
        "why": "'America' composite + 'in the world' universal; the 'largest' superlative is deliberately NOT flagged (v1).",
    },
    {
        "key": "first_nation",
        "claim": "New Zealand was the first country to give women the vote.",
        "expect": "universal",
        "why": "'first country' universal; 'New Zealand' is not a composite → geographic should stay silent.",
    },
    {
        "key": "no_other_constitution",
        "claim": "No other nation has a codified constitution as old as this one.",
        "expect": "universal",
        "why": "'no other' universal, no composite geography.",
    },
    {
        "key": "ctrl_france_nuclear",
        "claim": "France generates most of its electricity from nuclear power.",
        "expect": "none",
        "why": "CONTROL: 'France' is not a composite; 'most' superlative excluded → must stay silent.",
    },
    {
        "key": "ctrl_inflation",
        "claim": "Inflation is currently above the central bank's two percent target.",
        "expect": "none",
        "why": "CONTROL: no geography, no universal → silent. (Deliberately no 'UK' — that would legitimately flag.)",
    },
    {
        "key": "ctrl_bills",
        "claim": "Household water bills rose by forty percent over the last year.",
        "expect": "none",
        "why": "CONTROL: plain empirical; 'last year' must not trip the 'last <scope-noun>' family.",
    },
    {
        "key": "ctrl_everest",
        "claim": "Mount Everest is the tallest mountain above sea level.",
        "expect": "none",
        "why": "CONTROL: 'tallest' superlative excluded, no composite geography → silent.",
    },
]

_CATS = ("geographic", "universal")


async def _decompose_one(claim_text: str, claim_id: str) -> dict:
    """Run decompose ONLY and return each element's description + scope_flags."""
    from app.pipeline.claim_map_analyzer import ClaimMapAnalyzer

    analyzer = ClaimMapAnalyzer()
    error = None
    elements = []
    try:
        cm = await asyncio.wait_for(
            analyzer.decompose_claim(claim_text, claim_id), timeout=120
        )
        for e in cm["elements"]:
            elements.append(
                {
                    "element_id": e["element_id"],
                    "description": e["description"],
                    "scope_flags": e.get("scope_flags"),
                }
            )
    except Exception as e:  # noqa: BLE001
        error = f"{type(e).__name__}: {e}"
    return {"elements": elements, "error": error}


def _summarise(entry: dict, elements: list, error) -> dict:
    # Union of flags across the claim's elements, per category.
    fired = {
        c: sorted(
            {t for e in elements for t in (e.get("scope_flags") or {}).get(c, [])}
        )
        for c in _CATS
    }
    expect = entry["expect"]
    geo_hit = bool(fired["geographic"])
    uni_hit = bool(fired["universal"])

    if expect == "none":
        # A control: success = silent everywhere. Any flag is a false positive.
        hit = not (geo_hit or uni_hit)
        false_positive = geo_hit or uni_hit
    elif expect == "geographic":
        hit = geo_hit
        false_positive = uni_hit  # geographic control on the universal side
    elif expect == "universal":
        hit = uni_hit
        false_positive = geo_hit
    else:  # both
        hit = geo_hit and uni_hit
        false_positive = False
    return {
        "key": entry["key"],
        "expect": expect,
        "elements": len(elements),
        "fired": fired,
        "hit": hit,
        "false_positive": bool(false_positive),
        "error": error,
    }


async def run_label(label: str) -> None:
    out_path = BACKEND_DIR / "scripts" / f".f3_scope_eval_{label}.json"
    results = []
    for i, entry in enumerate(POOL):
        print(f"... decomposing {entry['key']} ...", flush=True)
        r = await _decompose_one(entry["claim"], f"TRU-F3EV-{i:04d}")
        summary = _summarise(entry, r["elements"], r["error"])
        summary["elements_detail"] = r["elements"]
        results.append(summary)
        mark = "ok " if summary["hit"] and not summary["false_positive"] else "!! "
        print(
            f"    {mark}{entry['key']}: expect={summary['expect']} "
            f"geo={summary['fired']['geographic']} uni={summary['fired']['universal']}"
            + (f"  [ERROR {summary['error']}]" if summary["error"] else ""),
            flush=True,
        )
    hits = sum(1 for r in results if r["hit"])
    fps = sum(1 for r in results if r["false_positive"])
    out_path.write_text(
        json.dumps(
            {
                "label": label,
                "at": datetime.now().isoformat(),
                "detection_hits": f"{hits}/{len(results)}",
                "false_positives": fps,
                "results": results,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\n{hits}/{len(results)} detection hits, {fps} false positives -> {out_path}")


def _print_table(data: dict) -> None:
    print(
        f"{'claim':22} {'expect':10} {'hit':4} {'FP':3} | geographic / universal fired"
    )
    for r in data["results"]:
        g = ",".join(r["fired"]["geographic"]) or "-"
        u = ",".join(r["fired"]["universal"]) or "-"
        print(
            f"{r['key']:22} {r['expect']:10} "
            f"{'Y' if r['hit'] else 'n':4} {'Y' if r['false_positive'] else '.':3} | {g}  /  {u}"
        )
    print(
        f"\n{data['detection_hits']} hits / {data['false_positives']} false positives"
    )


def compare() -> None:
    for label in ("baseline",):
        p = BACKEND_DIR / "scripts" / f".f3_scope_eval_{label}.json"
        if not p.exists():
            print(f"(no {label} run yet: {p.name})")
            continue
        print(f"===== {label} =====")
        _print_table(json.loads(p.read_text(encoding="utf-8")))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--label", choices=["baseline", "after"])
    g.add_argument("--compare", action="store_true")
    args = p.parse_args()
    if args.compare:
        compare()
    else:
        asyncio.run(run_label(args.label))
