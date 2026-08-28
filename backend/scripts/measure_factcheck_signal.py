"""Measure the factcheck signal's firing rate BEFORE the flag flips.

Item 7 stage 1 (audit/2026-08-28_rigour_and_refutation_design_review.md §3,
Option 7-A): the ENABLE_FACTCHECK_SIGNAL prompt variant re-keys every
classifier cassette in the replay bench, so flipping it is a decision that
carries a bench re-record. This script answers the question that decision
needs — how often does the LLM's `factcheck` boolean fire, on what, and how
many items would the promotion rule actually move — directly, over REAL stored
evidence, for pence.

Usage (from backend/):
    python -m scripts.measure_factcheck_signal            # dry run: sample + cost estimate, NO LLM calls
    python -m scripts.measure_factcheck_signal --run      # spend: classify the sample, print the report
    python -m scripts.measure_factcheck_signal --run --limit 100

Reads evidence items from backend/data/ledger/*.json (pipeline run dumps),
dedupes by URL, strips stored tier/type so every sampled item is re-classified
fresh with the signal ON. Touches no database and writes nothing.
"""

import argparse
import asyncio
import glob
import json
import os
import sys
from collections import Counter
from urllib.parse import urlparse

# Run as `python -m scripts.measure_factcheck_signal` from backend/.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings  # noqa: E402

LEDGER_GLOB = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "ledger",
    "*.json",
)


def _walk_evidence(node, out, depth=0):
    """Collect evidence-shaped dicts (url + title + some text) from arbitrary
    ledger JSON structure."""
    if depth > 8:
        return
    if isinstance(node, dict):
        if (
            node.get("url")
            and node.get("title")
            and (node.get("snippet") or node.get("text") or node.get("content"))
        ):
            out.append(node)
        for v in node.values():
            _walk_evidence(v, out, depth + 1)
    elif isinstance(node, list):
        for v in node:
            _walk_evidence(v, out, depth + 1)


def load_sample(limit: int):
    items, seen = [], set()
    for path in sorted(glob.glob(LEDGER_GLOB)):
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue
        found = []
        _walk_evidence(data, found)
        for ev in found:
            url = ev.get("url", "")
            if not url or url in seen:
                continue
            seen.add(url)
            items.append(
                {
                    "evidence_id": f"m-{len(items)}",
                    "title": ev.get("title", ""),
                    "source": ev.get("source", ev.get("domain", "")),
                    "url": url,
                    "snippet": (
                        ev.get("snippet") or ev.get("text") or ev.get("content") or ""
                    )[:300],
                    # Carry the stored flag for comparison, but strip
                    # tier/type so classify_batch re-classifies everything.
                    "_stored_is_factcheck": bool(ev.get("is_factcheck")),
                    "_stored_tier": ev.get("tier"),
                }
            )
            if len(items) >= limit:
                return items
    return items


def _domain(url: str) -> str:
    try:
        return urlparse(url).netloc.replace("www.", "").lower()
    except Exception:
        return ""


async def run(items, spend: bool):
    # Force the signal ON in-process only — prod/bench defaults untouched.
    settings.ENABLE_FACTCHECK_SIGNAL = True
    from app.pipeline.evidence_classifier import EvidenceClassifier

    n = len(items)
    # flash-lite ballpark: ~250 input + ~40 output tokens per item.
    est_in, est_out = n * 250, n * 40
    print(f"Sample: {n} distinct URLs from {len(glob.glob(LEDGER_GLOB))} ledger files")
    print(
        f"Estimated tokens: ~{est_in:,} in / ~{est_out:,} out (gemini flash-lite -> well under 1p)"
    )
    stored_flagged = sum(1 for i in items if i["_stored_is_factcheck"])
    print(
        f"Already flagged in stored data (Google Fact-Check API items): {stored_flagged}"
    )
    if not spend:
        print("\nDRY RUN — no LLM calls made. Re-run with --run to classify.")
        return

    classifier = EvidenceClassifier()
    await classifier.classify_batch(items)

    flagged = [i for i in items if i.get("is_factcheck")]
    newly = [i for i in flagged if not i["_stored_is_factcheck"]]
    promoted = [
        i for i in items if i.get("classification_method") == "factcheck_promotion"
    ]

    print(f"\n=== FACTCHECK SIGNAL over {n} items ===")
    print(
        f"flagged: {len(flagged)}  (newly: {len(newly)}, stored-API: {len(flagged) - len(newly)})"
    )
    print(f"promoted commentary/analysis -> reporting: {len(promoted)}")

    print("\nFlagged, by domain:")
    for dom, c in Counter(_domain(i["url"]) for i in flagged).most_common(30):
        print(f"  {c:3d}  {dom}")

    print("\nFlagged, by (tier, type) as classified this run:")
    for (t, ty), c in Counter(
        (i.get("tier"), i.get("evidence_type")) for i in flagged
    ).most_common():
        print(f"  {c:3d}  {t}/{ty}")

    print("\nPromoted items:")
    for i in promoted:
        print(f"  {_domain(i['url'])}  {i['title'][:70]}")

    usage = classifier.get_token_usage()
    print(f"\nTokens actually used: {usage}")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--limit", type=int, default=200, help="max distinct URLs to sample"
    )
    ap.add_argument(
        "--run", action="store_true", help="actually call the LLM (spends money)"
    )
    args = ap.parse_args()

    items = load_sample(args.limit)
    if not items:
        print("No evidence items found in backend/data/ledger/*.json")
        sys.exit(1)
    asyncio.run(run(items, spend=args.run))


if __name__ == "__main__":
    main()
