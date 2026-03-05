"""PQ-06 Adapter Scorecard — measure adapter selection, firing, and success rates.

Runs a diverse corpus of 20 claims through the adapter selection + API call path
(without the full pipeline) and produces per-adapter metrics. Gives empirical data
for scrap/fix/expand decisions.

Usage:
    # Full scorecard (all 20 claims, real API calls)
    python scripts/adapter_scorecard.py

    # Run specific claims by ID
    python scripts/adapter_scorecard.py --claims sc-01,sc-05,sc-09

    # Dry run (selection only, no API calls)
    python scripts/adapter_scorecard.py --dry-run

    # Output as JSON
    python scripts/adapter_scorecard.py --json

    # Verbose mode (per-claim detail)
    python scripts/adapter_scorecard.py --verbose
"""

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from collections import defaultdict
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings
from app.services.government_api_client import get_api_registry
from app.services.api_adapters import initialize_adapters
from app.utils.claim_keyword_router import get_keyword_router
from app.pipeline.retrieve import JURISDICTION_ADAPTER_PREFERENCES

logger = logging.getLogger(__name__)

# Mirror the cap from retrieve.py
MAX_ADAPTERS_PER_CLAIM = 3

CORPUS_PATH = Path(__file__).resolve().parent.parent / "data" / "scorecard_claims.json"


def load_corpus(claim_ids: list[str] | None = None) -> list[dict]:
    """Load test claims from corpus JSON."""
    with open(CORPUS_PATH) as f:
        claims = json.load(f)

    if claim_ids:
        claims = [c for c in claims if c["id"] in claim_ids]
        found = {c["id"] for c in claims}
        missing = set(claim_ids) - found
        if missing:
            logger.warning(f"Claims not found in corpus: {missing}")

    return claims


def select_adapters_for_claim(
    claim: dict, registry, keyword_router
) -> tuple[list, list, list]:
    """Run adapter selection logic for a single claim.

    Mirrors retrieve.py lines 1930-1985.

    Returns:
        (all_selected, capped, cut_adapters)
    """
    domain = claim["expected_domain"]
    jurisdiction = claim.get("expected_jurisdiction", "Global")

    # Step 1: Domain-based selection
    relevant = registry.get_adapters_for_domain(domain, jurisdiction)

    # Step 2: Keyword routing
    keyword_adds = keyword_router.get_additional_adapters(
        claim["claim_text"], relevant, registry
    )
    all_selected = relevant + keyword_adds

    # Step 3: Jurisdiction-preference sort + cap (mirrors retrieve.py)
    if len(all_selected) > MAX_ADAPTERS_PER_CLAIM:
        preferences = JURISDICTION_ADAPTER_PREFERENCES.get(jurisdiction, [])
        if preferences:

            def _priority(adapter):
                try:
                    return preferences.index(adapter.api_name)
                except ValueError:
                    return len(preferences) + 1

            all_selected_sorted = sorted(all_selected, key=_priority)
        else:
            all_selected_sorted = list(all_selected)

        capped = all_selected_sorted[:MAX_ADAPTERS_PER_CLAIM]
        cut = all_selected_sorted[MAX_ADAPTERS_PER_CLAIM:]
    else:
        capped = list(all_selected)
        cut = []

    return all_selected, capped, cut


def detect_routing_gaps(claim: dict, all_selected: list, registry) -> list[dict]:
    """Compare expected adapters with actually selected ones.

    Returns list of gap descriptions.
    """
    selected_names = {a.api_name for a in all_selected}
    expected_names = set(claim.get("expected_adapters", []))
    all_registered = {a.api_name for a in registry.get_all_adapters()}

    gaps = []
    for expected in expected_names:
        if expected not in all_registered:
            gaps.append(
                {
                    "claim_id": claim["id"],
                    "adapter": expected,
                    "type": "not_registered",
                    "detail": f"{expected} not in registry (API key not set?)",
                }
            )
        elif expected not in selected_names:
            gaps.append(
                {
                    "claim_id": claim["id"],
                    "adapter": expected,
                    "type": "not_selected",
                    "detail": f"{expected} registered but not selected for domain={claim['expected_domain']}, jurisdiction={claim.get('expected_jurisdiction', 'Global')}",
                }
            )

    return gaps


async def run_scorecard(
    claims: list[dict], dry_run: bool = False, verbose: bool = False
) -> dict:
    """Run the full adapter scorecard.

    Args:
        claims: List of claim dicts from corpus
        dry_run: If True, only run selection (no API calls)
        verbose: If True, collect per-claim detail

    Returns:
        Scorecard results dict
    """
    registry = get_api_registry()

    # Initialise adapters if registry is empty
    if len(registry.get_all_adapters()) == 0:
        initialize_adapters()

    keyword_router = get_keyword_router()

    registered_names = [a.api_name for a in registry.get_all_adapters()]
    print(f"\nRegistered adapters ({len(registered_names)}): {registered_names}\n")

    # Per-adapter stats
    adapter_stats = defaultdict(
        lambda: {
            "selected": 0,
            "capped_out": 0,
            "fired": 0,
            "success": 0,
            "zero_results": 0,
            "error": 0,
            "timeout": 0,
            "total_results": 0,
            "latencies_ms": [],
        }
    )

    all_gaps = []
    all_cap_victims = []
    claim_details = []

    for claim in claims:
        claim_id = claim["id"]
        if verbose:
            print(f"\n--- {claim_id}: {claim['claim_text'][:70]}...")

        # Selection
        all_selected, capped, cut = select_adapters_for_claim(
            claim, registry, keyword_router
        )

        for a in all_selected:
            adapter_stats[a.api_name]["selected"] += 1

        for a in cut:
            adapter_stats[a.api_name]["capped_out"] += 1
            all_cap_victims.append(
                {
                    "claim_id": claim_id,
                    "adapter": a.api_name,
                    "filled_by": [c.api_name for c in capped],
                }
            )

        # Routing gap detection
        gaps = detect_routing_gaps(claim, all_selected, registry)
        all_gaps.extend(gaps)

        if verbose:
            print(
                f"  Domain: {claim['expected_domain']}, Jurisdiction: {claim.get('expected_jurisdiction', 'Global')}"
            )
            print(f"  Selected: {[a.api_name for a in all_selected]}")
            print(f"  Capped to: {[a.api_name for a in capped]}")
            if cut:
                print(f"  Cut: {[a.api_name for a in cut]}")
            if gaps:
                for g in gaps:
                    print(f"  GAP: {g['detail']}")

        claim_detail = {
            "claim_id": claim_id,
            "domain": claim["expected_domain"],
            "jurisdiction": claim.get("expected_jurisdiction", "Global"),
            "selected": [a.api_name for a in all_selected],
            "capped_to": [a.api_name for a in capped],
            "cut": [a.api_name for a in cut],
            "gaps": gaps,
            "results": {},
        }

        # Fire adapters (unless dry run)
        if not dry_run:
            for adapter in capped:
                name = adapter.api_name
                adapter_stats[name]["fired"] += 1
                t0 = time.monotonic()
                try:
                    result = await asyncio.wait_for(
                        asyncio.to_thread(
                            adapter.search_with_cache,
                            claim["claim_text"],
                            claim["expected_domain"],
                            claim.get("expected_jurisdiction", "Global"),
                            [],
                        ),
                        timeout=15.0,
                    )
                    elapsed_ms = round((time.monotonic() - t0) * 1000)
                    adapter_stats[name]["latencies_ms"].append(elapsed_ms)

                    if result and len(result) > 0:
                        adapter_stats[name]["success"] += 1
                        adapter_stats[name]["total_results"] += len(result)
                        claim_detail["results"][name] = {
                            "count": len(result),
                            "latency_ms": elapsed_ms,
                        }
                        if verbose:
                            print(f"  {name}: {len(result)} results ({elapsed_ms}ms)")
                    else:
                        adapter_stats[name]["zero_results"] += 1
                        claim_detail["results"][name] = {
                            "count": 0,
                            "latency_ms": elapsed_ms,
                        }
                        if verbose:
                            print(f"  {name}: 0 results ({elapsed_ms}ms)")

                except asyncio.TimeoutError:
                    elapsed_ms = round((time.monotonic() - t0) * 1000)
                    adapter_stats[name]["timeout"] += 1
                    claim_detail["results"][name] = {"error": "timeout"}
                    if verbose:
                        print(f"  {name}: TIMEOUT ({elapsed_ms}ms)")

                except Exception as e:
                    elapsed_ms = round((time.monotonic() - t0) * 1000)
                    adapter_stats[name]["error"] += 1
                    claim_detail["results"][name] = {"error": str(e)}
                    if verbose:
                        print(f"  {name}: ERROR: {e}")

        claim_details.append(claim_detail)

    return {
        "claim_count": len(claims),
        "dry_run": dry_run,
        "registered_adapters": registered_names,
        "adapter_stats": dict(adapter_stats),
        "routing_gaps": all_gaps,
        "cap_victims": all_cap_victims,
        "claim_details": claim_details,
    }


def compute_derived_metrics(stats: dict) -> dict:
    """Add derived metrics (avg latency, avg results per fire)."""
    for name, s in stats.items():
        latencies = s.pop("latencies_ms", [])
        if latencies:
            s["avg_latency_ms"] = round(sum(latencies) / len(latencies))
            s["max_latency_ms"] = round(max(latencies))
        else:
            s["avg_latency_ms"] = 0
            s["max_latency_ms"] = 0

        if s["fired"] > 0:
            s["avg_results_per_fire"] = round(s["total_results"] / s["fired"], 1)
        else:
            s["avg_results_per_fire"] = 0.0

    return stats


def print_table(results: dict):
    """Print formatted scorecard table."""
    stats = results["adapter_stats"]
    stats = compute_derived_metrics(stats)
    dry_run = results["dry_run"]

    mode = "DRY RUN (selection only)" if dry_run else "LIVE (real API calls)"
    print(f"\nPQ-06 Adapter Scorecard — {results['claim_count']} claims — {mode}")
    print("=" * 110)

    if dry_run:
        # Selection-only table
        header = f"{'Adapter':<30}  {'Selected':>8}  {'Capped':>6}"
        print(header)
        print("-" * len(header))

        for name in sorted(
            stats.keys(), key=lambda n: stats[n]["selected"], reverse=True
        ):
            s = stats[name]
            print(f"{name:<30}  {s['selected']:>8}  {s['capped_out']:>6}")
    else:
        # Full table
        header = (
            f"{'Adapter':<30}  {'Sel':>3}  {'Cap':>3}  {'Fire':>4}  "
            f"{'OK':>3}  {'0-R':>3}  {'Err':>3}  {'T/O':>3}  "
            f"{'Results':>7}  {'Avg ms':>6}  {'Max ms':>6}  {'R/Fire':>6}"
        )
        print(header)
        print("-" * len(header))

        for name in sorted(stats.keys(), key=lambda n: stats[n]["fired"], reverse=True):
            s = stats[name]
            print(
                f"{name:<30}  {s['selected']:>3}  {s['capped_out']:>3}  {s['fired']:>4}  "
                f"{s['success']:>3}  {s['zero_results']:>3}  {s['error']:>3}  {s['timeout']:>3}  "
                f"{s['total_results']:>7}  {s['avg_latency_ms']:>6}  {s['max_latency_ms']:>6}  "
                f"{s['avg_results_per_fire']:>6}"
            )

    # Routing gaps
    gaps = results["routing_gaps"]
    if gaps:
        print(f"\nRouting Gaps ({len(gaps)} issues):")
        for g in gaps:
            print(f"  {g['claim_id']}: {g['detail']}")

    # Cap victims
    victims = results["cap_victims"]
    if victims:
        print(f"\nCap Victims ({len(victims)} truncations):")
        for v in victims:
            print(
                f"  {v['claim_id']}: {v['adapter']} capped out (slots filled by {v['filled_by']})"
            )

    # Summary
    print(f"\nSummary:")
    print(f"  Registered adapters: {len(results['registered_adapters'])}")
    print(
        f"  Adapters that were selected: {sum(1 for s in stats.values() if s['selected'] > 0)}"
    )
    if not dry_run:
        print(
            f"  Adapters that fired: {sum(1 for s in stats.values() if s['fired'] > 0)}"
        )
        print(
            f"  Adapters with >0 success: {sum(1 for s in stats.values() if s['success'] > 0)}"
        )
        total_fired = sum(s["fired"] for s in stats.values())
        total_success = sum(s["success"] for s in stats.values())
        if total_fired > 0:
            print(
                f"  Overall success rate: {total_success}/{total_fired} ({100*total_success/total_fired:.0f}%)"
            )
    print(f"  Routing gaps: {len(gaps)}")
    print(f"  Cap truncations: {len(victims)}")


def main():
    parser = argparse.ArgumentParser(
        description="PQ-06 Adapter Scorecard — measure adapter performance"
    )
    parser.add_argument(
        "--claims",
        type=str,
        default=None,
        help="Comma-separated claim IDs (e.g. sc-01,sc-05,sc-09)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Selection only, no API calls",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Output as JSON",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show per-claim detail",
    )
    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.WARNING
    logging.basicConfig(
        level=log_level,
        format="%(levelname)s %(name)s: %(message)s",
    )
    # Suppress noisy loggers even in verbose mode
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("app.services.cache").setLevel(logging.WARNING)
    logging.getLogger("app.services.circuit_breaker").setLevel(logging.WARNING)

    claim_ids = args.claims.split(",") if args.claims else None
    claims = load_corpus(claim_ids)

    if not claims:
        print("No claims found. Check --claims IDs against data/scorecard_claims.json")
        sys.exit(1)

    print(f"Running scorecard for {len(claims)} claims...")
    results = asyncio.run(
        run_scorecard(claims, dry_run=args.dry_run, verbose=args.verbose)
    )

    if args.json_output:
        # Clean up latencies_ms before JSON output (already consumed by compute_derived_metrics)
        results["adapter_stats"] = compute_derived_metrics(results["adapter_stats"])
        print(json.dumps(results, indent=2, default=str))
    else:
        print_table(results)


if __name__ == "__main__":
    main()
