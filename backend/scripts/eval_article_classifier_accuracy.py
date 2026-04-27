#!/usr/bin/env python3
"""Article classifier accuracy probe (domain + jurisdiction).

Mirrors the production "focused mode" call shape: title="", url="",
content=<claim text>. Bypasses URL-pattern cache (no URL) and Redis cache
(empty URL is rejected by get_cached_classification).

Calls Google Gemini Flash-Lite (primary) and OpenAI gpt-4o-mini (fallback),
in parallel, and records both. Computes:

- Per-cell agreement (UK/US/EU/Global x Climate/Politics/Law/Finance/Health)
- Per-(provider) accuracy
- Mismatch list, grouped by error type

Usage:
    python scripts/eval_article_classifier_accuracy.py
    python scripts/eval_article_classifier_accuracy.py --primary-only
    python scripts/eval_article_classifier_accuracy.py --fallback-only

Output:
    backend/data/article_classifier_sample_<timestamp>.json
"""

import asyncio
import json
import sys
import os
import time
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

# Add backend to path so app.* imports work
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Load .env so API keys + settings are available
from dotenv import load_dotenv  # type: ignore

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from app.utils.article_classifier import (  # noqa: E402
    _classify_with_fallback_llm,
    _classify_with_llm,
    ArticleClassification,
    VALID_DOMAINS,
    VALID_JURISDICTIONS,
)


# ---------------------------------------------------------------------------
# SAMPLE MATRIX (40 claims): UK/US/EU/Global x Climate/Politics/Law/Finance/Health
# Each cell has 2 surface-variant claims where possible.
# Ground truth is conservative: jurisdiction is the locus of the *event*, not
# any peripheral mention. Domain may be one of {primary, secondary[]}.
# ---------------------------------------------------------------------------

SAMPLE: list[dict] = [
    # =================== CLIMATE ===================
    # UK Climate
    {
        "id": "climate-uk-1",
        "text": "The Climate Change Act 2008 set the UK's target of net zero emissions by 2050",
        "expected_domain": "Climate",
        "expected_jurisdiction": "UK",
        "notes": "litmus from verification arc — classified UK historically",
    },
    {
        "id": "climate-uk-2",
        "text": "The 2008 Climate Change Act commits the United Kingdom to net zero by 2050",
        "expected_domain": "Climate",
        "expected_jurisdiction": "UK",
        "notes": "litmus from verification arc — classified US historically (misroute)",
    },
    # US Climate
    {
        "id": "climate-us-1",
        "text": "The Inflation Reduction Act of 2022 allocated $369 billion to US climate programmes",
        "expected_domain": "Climate",
        "expected_jurisdiction": "US",
    },
    {
        "id": "climate-us-2",
        "text": "California became the first US state to mandate net-zero emissions by 2045",
        "expected_domain": "Climate",
        "expected_jurisdiction": "US",
    },
    # EU Climate
    {
        "id": "climate-eu-1",
        "text": "The European Green Deal aims to make the EU climate-neutral by 2050",
        "expected_domain": "Climate",
        "expected_jurisdiction": "EU",
    },
    {
        "id": "climate-eu-2",
        "text": "The EU Emissions Trading System covers around 40% of European greenhouse gas emissions",
        "expected_domain": "Climate",
        "expected_jurisdiction": "EU",
    },
    # Global Climate
    {
        "id": "climate-global-1",
        "text": "The Paris Agreement set a target of limiting global warming to 1.5C",
        "expected_domain": "Climate",
        "expected_jurisdiction": "Global",
    },
    {
        "id": "climate-global-2",
        "text": "Global atmospheric CO2 concentration reached 421 parts per million in 2024",
        "expected_domain": "Climate",
        "expected_jurisdiction": "Global",
    },
    # =================== POLITICS ===================
    # UK Politics
    {
        "id": "politics-uk-1",
        "text": "Keir Starmer became UK Prime Minister in July 2024",
        "expected_domain": "Politics",
        "expected_jurisdiction": "UK",
    },
    {
        "id": "politics-uk-2",
        "text": "Labour won 411 seats at the 2024 general election in Britain",
        "expected_domain": "Politics",
        "expected_jurisdiction": "UK",
    },
    # US Politics
    {
        "id": "politics-us-1",
        "text": "Donald Trump won the 2024 US Presidential election",
        "expected_domain": "Politics",
        "expected_jurisdiction": "US",
    },
    {
        "id": "politics-us-2",
        "text": "Republicans took control of the Senate in November 2024",
        "expected_domain": "Politics",
        "expected_jurisdiction": "US",
    },
    # EU Politics
    {
        "id": "politics-eu-1",
        "text": "Ursula von der Leyen was re-elected European Commission President in 2024",
        "expected_domain": "Politics",
        "expected_jurisdiction": "EU",
    },
    {
        "id": "politics-eu-2",
        "text": "The European Parliament has 720 MEPs as of the 2024 elections",
        "expected_domain": "Politics",
        "expected_jurisdiction": "EU",
    },
    # Global Politics
    {
        "id": "politics-global-1",
        "text": "The UN General Assembly has 193 member states",
        "expected_domain": "Politics",
        "expected_jurisdiction": "Global",
    },
    {
        "id": "politics-global-2",
        "text": "G20 leaders pledged climate finance support at the 2024 Rio summit",
        "expected_domain": "Politics",
        "expected_jurisdiction": "Global",
    },
    # =================== LAW ===================
    # UK Law
    {
        "id": "law-uk-1",
        "text": "The Equality Act 2010 consolidated UK anti-discrimination law into a single statute",
        "expected_domain": "Law",
        "expected_jurisdiction": "UK",
    },
    {
        "id": "law-uk-2",
        "text": "The UK Supreme Court ruled in Miller v Prime Minister that the prorogation of Parliament was unlawful",
        "expected_domain": "Law",
        "expected_jurisdiction": "UK",
    },
    # US Law
    {
        "id": "law-us-1",
        "text": "The US Supreme Court overturned Roe v Wade in 2022",
        "expected_domain": "Law",
        "expected_jurisdiction": "US",
    },
    {
        "id": "law-us-2",
        "text": "The Voting Rights Act of 1965 was a landmark US civil rights law",
        "expected_domain": "Law",
        "expected_jurisdiction": "US",
    },
    # EU Law
    {
        "id": "law-eu-1",
        "text": "The EU's General Data Protection Regulation came into force in May 2018",
        "expected_domain": "Law",
        "expected_jurisdiction": "EU",
    },
    {
        "id": "law-eu-2",
        "text": "The Digital Services Act is the European Union's flagship online platform regulation",
        "expected_domain": "Law",
        "expected_jurisdiction": "EU",
    },
    # Global Law
    {
        "id": "law-global-1",
        "text": "The Geneva Conventions establish the standards of international humanitarian law",
        "expected_domain": "Law",
        "expected_jurisdiction": "Global",
    },
    {
        "id": "law-global-2",
        "text": "The International Criminal Court is based in The Hague",
        "expected_domain": "Law",
        "expected_jurisdiction": "Global",
    },
    # =================== FINANCE ===================
    # UK Finance
    {
        "id": "finance-uk-1",
        "text": "The Bank of England raised interest rates to 5.25% in August 2023",
        "expected_domain": "Finance",
        "expected_jurisdiction": "UK",
    },
    {
        "id": "finance-uk-2",
        "text": "BP plc reported record profits of GBP 28 billion in 2022",
        "expected_domain": "Finance",
        "expected_jurisdiction": "UK",
        "notes": "litmus from verification arc — classified Global historically (misroute)",
    },
    # US Finance
    {
        "id": "finance-us-1",
        "text": "The Federal Reserve cut interest rates by 50 basis points in September 2024",
        "expected_domain": "Finance",
        "expected_jurisdiction": "US",
    },
    {
        "id": "finance-us-2",
        "text": "Apple Inc became the first US company valued at $3 trillion in 2022",
        "expected_domain": "Finance",
        "expected_jurisdiction": "US",
    },
    # EU Finance
    {
        "id": "finance-eu-1",
        "text": "The European Central Bank set its deposit facility rate at 3.25% in October 2024",
        "expected_domain": "Finance",
        "expected_jurisdiction": "EU",
    },
    {
        "id": "finance-eu-2",
        "text": "France's CAC 40 stock index closed above 8000 for the first time in March 2024",
        "expected_domain": "Finance",
        "expected_jurisdiction": "EU",
    },
    # Global Finance
    {
        "id": "finance-global-1",
        "text": "Global GDP grew 3.2% in 2024 according to the IMF",
        "expected_domain": "Finance",
        "expected_jurisdiction": "Global",
    },
    {
        "id": "finance-global-2",
        "text": "Bitcoin reached an all-time high of $100,000 in December 2024",
        "expected_domain": "Finance",
        "expected_jurisdiction": "Global",
    },
    # =================== HEALTH ===================
    # UK Health
    {
        "id": "health-uk-1",
        "text": "The NHS treats around 1.6 million people every 24 hours",
        "expected_domain": "Health",
        "expected_jurisdiction": "UK",
    },
    {
        "id": "health-uk-2",
        "text": "The UK introduced its sugar tax on soft drinks in April 2018",
        "expected_domain": "Health",
        "expected_jurisdiction": "UK",
    },
    # US Health
    {
        "id": "health-us-1",
        "text": "The CDC recommended COVID-19 boosters for all Americans over 65 in 2024",
        "expected_domain": "Health",
        "expected_jurisdiction": "US",
    },
    {
        "id": "health-us-2",
        "text": "Medicare covers approximately 65 million Americans",
        "expected_domain": "Health",
        "expected_jurisdiction": "US",
    },
    # EU Health
    {
        "id": "health-eu-1",
        "text": "France introduced mandatory measles vaccination for children in 2018",
        "expected_domain": "Health",
        "expected_jurisdiction": "EU",
    },
    {
        "id": "health-eu-2",
        "text": "Germany's statutory health insurance covers about 90% of its population",
        "expected_domain": "Health",
        "expected_jurisdiction": "EU",
    },
    # Global Health
    {
        "id": "health-global-1",
        "text": "WHO declared COVID-19 a pandemic on 11 March 2020",
        "expected_domain": "Health",
        "expected_jurisdiction": "Global",
    },
    {
        "id": "health-global-2",
        "text": "Malaria caused approximately 608,000 deaths globally in 2022",
        "expected_domain": "Health",
        "expected_jurisdiction": "Global",
    },
]


# ---------------------------------------------------------------------------
# Sample run
# ---------------------------------------------------------------------------


def domain_match(expected: str, classification: ArticleClassification) -> bool:
    """Match if expected domain is primary OR appears in secondary list."""
    if classification is None:
        return False
    if classification.primary_domain == expected:
        return True
    if expected in classification.secondary_domains:
        return True
    return False


def jurisdiction_match(expected: str, classification: ArticleClassification) -> bool:
    if classification is None:
        return False
    return classification.jurisdiction == expected


async def classify_one(claim: dict, mode: str) -> dict:
    """Run a single claim through the classifier(s).

    Production focused-mode call shape: title="", url="", content=claim_text.
    """
    text = claim["text"]
    primary = None
    fallback = None

    if mode in ("primary", "both"):
        try:
            primary = await _classify_with_fallback_llm("", "", text)
        except Exception as e:
            print(f"  primary LLM error: {e}")

    if mode in ("fallback", "both"):
        try:
            fallback = await _classify_with_llm("", "", text, provider="openai")
        except Exception as e:
            print(f"  fallback LLM error: {e}")

    return {
        "id": claim["id"],
        "text": text,
        "expected_domain": claim["expected_domain"],
        "expected_jurisdiction": claim["expected_jurisdiction"],
        "notes": claim.get("notes", ""),
        "primary": primary.to_dict() if primary else None,
        "fallback": fallback.to_dict() if fallback else None,
    }


async def run_sample(mode: str) -> list[dict]:
    print(f"Running {len(SAMPLE)} claims in mode={mode}...")
    # Run sequentially (kinder on rate limits and easier to read logs)
    results: list[dict] = []
    for i, claim in enumerate(SAMPLE):
        t0 = time.monotonic()
        result = await classify_one(claim, mode)
        dt = time.monotonic() - t0
        # Compact one-line per claim
        p = result.get("primary") or {}
        f = result.get("fallback") or {}
        p_str = (
            f"P:{p.get('primary_domain','-')}/{p.get('jurisdiction','-')}"
            if p
            else "P:-"
        )
        f_str = (
            f"F:{f.get('primary_domain','-')}/{f.get('jurisdiction','-')}"
            if f
            else "F:-"
        )
        exp = f"{claim['expected_domain']}/{claim['expected_jurisdiction']}"
        print(
            f"  [{i+1:>2}/{len(SAMPLE)}] {claim['id']:<22} exp={exp:<18} {p_str:<28} {f_str:<28} ({dt:.1f}s)"
        )
        results.append(result)
    return results


def summarise(results: list[dict], provider_key: str) -> dict:
    """Compute aggregates for one provider's outputs."""
    total = sum(1 for r in results if r.get(provider_key) is not None)
    if total == 0:
        return {"provider": provider_key, "total": 0}

    domain_correct = 0
    jurisdiction_correct = 0
    both_correct = 0
    primary_domain_correct = 0  # strict (domain in primary slot only)

    # Per-cell stats
    cell_stats: dict[tuple[str, str], dict] = defaultdict(
        lambda: {"total": 0, "dom_ok": 0, "jur_ok": 0, "both_ok": 0}
    )
    # Per-jurisdiction misroute matrix (where do mis-classifications go?)
    jur_confusion: dict[str, Counter] = defaultdict(Counter)
    dom_confusion: dict[str, Counter] = defaultdict(Counter)

    misroutes: list[dict] = []

    for r in results:
        c = r.get(provider_key)
        if c is None:
            continue
        exp_dom = r["expected_domain"]
        exp_jur = r["expected_jurisdiction"]
        actual = ArticleClassification.from_dict(c)
        dom_ok = domain_match(exp_dom, actual)
        primary_dom_ok = actual.primary_domain == exp_dom
        jur_ok = jurisdiction_match(exp_jur, actual)
        both_ok = dom_ok and jur_ok

        domain_correct += int(dom_ok)
        primary_domain_correct += int(primary_dom_ok)
        jurisdiction_correct += int(jur_ok)
        both_correct += int(both_ok)

        cell = (exp_dom, exp_jur)
        cell_stats[cell]["total"] += 1
        cell_stats[cell]["dom_ok"] += int(dom_ok)
        cell_stats[cell]["jur_ok"] += int(jur_ok)
        cell_stats[cell]["both_ok"] += int(both_ok)

        jur_confusion[exp_jur][actual.jurisdiction] += 1
        dom_confusion[exp_dom][actual.primary_domain] += 1

        if not both_ok:
            misroutes.append(
                {
                    "id": r["id"],
                    "text": r["text"],
                    "expected": f"{exp_dom}/{exp_jur}",
                    "actual_primary": actual.primary_domain,
                    "actual_secondary": actual.secondary_domains,
                    "actual_jurisdiction": actual.jurisdiction,
                    "confidence": actual.confidence,
                    "reasoning": actual.reasoning,
                    "dom_ok": dom_ok,
                    "primary_dom_ok": primary_dom_ok,
                    "jur_ok": jur_ok,
                    "notes": r.get("notes", ""),
                }
            )

    return {
        "provider": provider_key,
        "total": total,
        "domain_correct": domain_correct,  # primary or secondary contains expected
        "primary_domain_correct": primary_domain_correct,  # strict
        "jurisdiction_correct": jurisdiction_correct,
        "both_correct": both_correct,
        "domain_acc": domain_correct / total,
        "primary_domain_acc": primary_domain_correct / total,
        "jurisdiction_acc": jurisdiction_correct / total,
        "both_acc": both_correct / total,
        "cell_stats": {f"{d}/{j}": v for (d, j), v in cell_stats.items()},
        "jur_confusion": {k: dict(v) for k, v in jur_confusion.items()},
        "dom_confusion": {k: dict(v) for k, v in dom_confusion.items()},
        "misroutes": misroutes,
    }


def print_summary(s: dict):
    p = s["provider"]
    if s.get("total", 0) == 0:
        print(f"\n[{p}] No data.")
        return
    n = s["total"]
    print(f"\n=== {p.upper()} (n={n}) ===")
    print(
        f"  Domain (any slot)    : {s['domain_correct']:>2}/{n} = {s['domain_acc']*100:>5.1f}%"
    )
    print(
        f"  Primary-domain only  : {s['primary_domain_correct']:>2}/{n} = {s['primary_domain_acc']*100:>5.1f}%"
    )
    print(
        f"  Jurisdiction         : {s['jurisdiction_correct']:>2}/{n} = {s['jurisdiction_acc']*100:>5.1f}%"
    )
    print(
        f"  Both correct         : {s['both_correct']:>2}/{n} = {s['both_acc']*100:>5.1f}%"
    )

    print("\n  Per-cell (jur correct / total):")
    cells = s["cell_stats"]
    domains = ["Climate", "Politics", "Law", "Finance", "Health"]
    jurs = ["UK", "US", "EU", "Global"]
    print(f"    {'':<10} " + " ".join(f"{j:>8}" for j in jurs))
    for d in domains:
        row = [d]
        for j in jurs:
            cell = cells.get(f"{d}/{j}")
            if cell is None:
                row.append(f"{'-':>8}")
            else:
                row.append(f"{cell['jur_ok']}/{cell['total']:>2}")
        print(f"    {row[0]:<10} " + " ".join(f"{x:>8}" for x in row[1:]))

    print("\n  Jurisdiction confusion (rows=expected, cols=actual):")
    print(f"    {'':<10} " + " ".join(f"{j:>8}" for j in jurs))
    for j_exp in jurs:
        row = [j_exp]
        actual = s["jur_confusion"].get(j_exp, {})
        for j_act in jurs:
            row.append(str(actual.get(j_act, 0)))
        print(f"    {row[0]:<10} " + " ".join(f"{x:>8}" for x in row[1:]))

    print(f"\n  Misroutes: {len(s['misroutes'])}")
    for m in s["misroutes"]:
        flags = []
        if not m["jur_ok"]:
            flags.append("JUR")
        if not m["dom_ok"]:
            flags.append("DOM")
        print(
            f"    [{m['id']:<22}] {m['expected']:<18} -> "
            f"{m['actual_primary']}+{m['actual_secondary']}/{m['actual_jurisdiction']} "
            f"conf={m['confidence']} [{','.join(flags)}]"
        )
        if m.get("notes"):
            print(f"        note: {m['notes']}")


async def main():
    args = sys.argv[1:]
    if "--primary-only" in args:
        mode = "primary"
    elif "--fallback-only" in args:
        mode = "fallback"
    else:
        mode = "both"

    results = await run_sample(mode)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = Path(__file__).resolve().parent.parent / "data"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"article_classifier_sample_{timestamp}.json"

    summaries = {}
    if mode in ("primary", "both"):
        summaries["primary"] = summarise(results, "primary")
        print_summary(summaries["primary"])
    if mode in ("fallback", "both"):
        summaries["fallback"] = summarise(results, "fallback")
        print_summary(summaries["fallback"])

    output = {
        "timestamp": timestamp,
        "mode": mode,
        "n_claims": len(SAMPLE),
        "raw": results,
        "summaries": summaries,
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)
    print(f"\nResults saved to {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
