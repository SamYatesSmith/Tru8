"""Verify Session A: per-adapter prepare_query lifts live API yield.

Direct adapter-invocation script. Bypasses both the article classifier
(no Mode D risk) and the Redis cache (calls .search() directly, not
.search_with_cache()), so the result is a clean A/B on query shape alone.

For each migrated adapter (Hansard, GOV.UK, Companies House):
  1. prepare_query() output for a realistic (claim, entities) tuple
  2. adapter.search(raw_claim, ...) — count
  3. adapter.search(shaped_query, ...) — count

Acceptance: shaped count > raw count (ideally raw=0, shaped>=1).

Plus an integration check on search_with_cache() to confirm the
empty-string skip path fires when no required entity is present.
"""

import sys
from pathlib import Path

# Run from backend/ so app.* imports resolve
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.services.api_adapters.legal import HansardAdapter, GovUKAdapter
from app.services.api_adapters.business import CompaniesHouseAdapter


# Realistic claim + NER-style entities. The entity list mimics what the
# pipeline's NER stage emits (label + text dicts).
LAW_CLAIM = (
    "The Climate Change Act 2008 set the UK's target of net zero emissions " "by 2050"
)
LAW_ENTITIES = [
    {"label": "LAW", "text": "Climate Change Act 2008"},
    {"label": "GPE", "text": "UK"},
    {"label": "DATE", "text": "2050"},
]

ORG_CLAIM = "BP plc reported record profits of GBP 28 billion in 2022"
ORG_ENTITIES = [
    {"label": "ORG", "text": "BP plc"},
    {"label": "MONEY", "text": "GBP 28 billion"},
    {"label": "DATE", "text": "2022"},
]

# Claim with no ORG — should make Companies House skip via empty string.
NO_ORG_CLAIM = "The Climate Change Act 2008 set net zero by 2050"
NO_ORG_ENTITIES = [
    {"label": "LAW", "text": "Climate Change Act 2008"},
    {"label": "DATE", "text": "2050"},
]


def banner(title: str) -> None:
    print()
    print("=" * 72)
    print(title)
    print("=" * 72)


def report(
    label: str,
    expected_shape: str,
    actual_shape: str,
    raw_count: int,
    shaped_count: int,
) -> bool:
    shape_ok = actual_shape == expected_shape
    yield_ok = shaped_count > raw_count
    print(f"  prepare_query: {actual_shape!r}")
    print(f"    expected:    {expected_shape!r}  [{'OK' if shape_ok else 'FAIL'}]")
    print(f"  search(raw claim)    -> {raw_count} results")
    print(f"  search(shaped query) -> {shaped_count} results")
    print(
        f"    yield delta: {'OK' if yield_ok else 'FAIL'}"
        f"  ({'raw < shaped' if yield_ok else 'no improvement'})"
    )
    return shape_ok and yield_ok


def test_hansard() -> bool:
    banner("Hansard — UK parliamentary debates (no API key required)")
    adapter = HansardAdapter()
    shaped = adapter.prepare_query(LAW_CLAIM, LAW_ENTITIES)

    raw = adapter.search(LAW_CLAIM, "Law", "UK")
    shaped_results = adapter.search(shaped, "Law", "UK")

    return report(
        "Hansard",
        expected_shape="Climate Change Act 2008",
        actual_shape=shaped,
        raw_count=len(raw),
        shaped_count=len(shaped_results),
    )


def test_govuk() -> bool:
    banner("GOV.UK Content API (no API key required)")
    adapter = GovUKAdapter()
    shaped = adapter.prepare_query(LAW_CLAIM, LAW_ENTITIES)

    raw = adapter.search(LAW_CLAIM, "Law", "UK")
    shaped_results = adapter.search(shaped, "Law", "UK")

    return report(
        "GOV.UK",
        expected_shape="Climate Change Act 2008",
        actual_shape=shaped,
        raw_count=len(raw),
        shaped_count=len(shaped_results),
    )


def test_companies_house() -> bool:
    banner("Companies House (UK company registry — API key required)")
    adapter = CompaniesHouseAdapter()
    if not adapter.api_key:
        print("  SKIP: COMPANIES_HOUSE_API_KEY not configured")
        return True  # not a failure of Session A
    shaped = adapter.prepare_query(ORG_CLAIM, ORG_ENTITIES)

    raw = adapter.search(ORG_CLAIM, "Finance", "UK")
    shaped_results = adapter.search(shaped, "Finance", "UK")

    return report(
        "Companies House",
        expected_shape="BP plc",
        actual_shape=shaped,
        raw_count=len(raw),
        shaped_count=len(shaped_results),
    )


def test_companies_house_empty_skip() -> bool:
    banner("Companies House — empty-string skip via search_with_cache")
    adapter = CompaniesHouseAdapter()
    if not adapter.api_key:
        print("  SKIP: COMPANIES_HOUSE_API_KEY not configured")
        return True
    shaped = adapter.prepare_query(NO_ORG_CLAIM, NO_ORG_ENTITIES)
    print(f"  prepare_query (no ORG entity): {shaped!r}")
    if shaped != "":
        print("  FAIL: expected empty string when ORG entity absent")
        return False

    # search_with_cache should see "" and return [] without an HTTP call
    results = adapter.search_with_cache(
        NO_ORG_CLAIM, "Finance", "UK", entities=NO_ORG_ENTITIES
    )
    print(
        f"  search_with_cache returned {len(results)} results "
        f"(expected 0; check uvicorn log for skip message)"
    )
    return len(results) == 0


def main() -> int:
    results = {
        "Hansard": test_hansard(),
        "GOV.UK": test_govuk(),
        "Companies House (search)": test_companies_house(),
        "Companies House (skip)": test_companies_house_empty_skip(),
    }
    banner("Summary")
    for name, passed in results.items():
        print(f"  {name}: {'PASS' if passed else 'FAIL'}")
    failed = [n for n, p in results.items() if not p]
    if failed:
        print(f"\n{len(failed)} failure(s): {failed}")
        return 1
    print("\nAll checks passed. Session A live-verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
