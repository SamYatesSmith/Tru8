# Cache as a floor, not a ceiling — pool-quality gate (SCOPE, 2026-09-02)

**Status:** SCOPED, NOT BUILT. Founder: *"If we are recycling a bad output, we put reputation on the line."*
**Trigger:** the Build A control arm showed a 24 h per-claim evidence cache replaying a whole pool
(junk included) with zero searches; coverage recovery then re-searched only *thin* elements, inside the
past-month window. A thin, one-sided or junk-heavy pool is recycled unchanged to every later caller.
**Read first:** `2026-09-02_claim_lane_unwindowed_twin_design.md` (Build A), `2026-09-02_dissent_discovery_probe.md`.

## What exists (verified in code today)

| piece | where | what it does now |
|---|---|---|
| evidence cache | `workers/pipeline.py:186-218, 285-300` · `services/cache.py:174-182` | key `tru8:evidence_extract:<md5(claim text)>`, TTL 24 h, stores the FILTERED pool if ≥ `MIN_SOURCES_FOR_CACHE` (2). On a hit, retrieval is skipped entirely. |
| coverage recovery trigger | `runner.py:2504-2532`, predicates `:447-472` | a claim qualifies if >40% of elements are `unresolved` OR any element is *starved* (refs but none directional). **Quantity only.** |
| recovery searches | `retrieve.py:1011` `_recover_evidence_for_claim`, `:1380-1420` | planner ≤2 queries/element at the element's freshness (`pm` on TTE), 8 results, `-site:snopes`; naive fallback `py`. No unwindowed query. Merge/re-score/re-classify/re-map machinery: `runner.py:2560-2800`, capped by `RECOVERY_MAX_CLAIMS` / `RECOVERY_MAX_ELEMENTS_PER_CLAIM`, timed. |
| pool-quality signals | `pipeline/support_structure.py` (`element_is_thin`, `side_quality_note`) · element `basis.support_structure/challenge_structure` (`derivation.originals`, `derivative_count`, `distinct_domains`, `tier_counts`) | already computed after classification; rendered as the grey △ notes. **Not read by any trigger.** |

So the shape the founder described — reuse the pool, re-search what is weak — already exists for *empty*
elements. The change is to make it fire on *weak* ones, search properly when it does, and stop the cache
from outliving the code that filled it.

## The change — three pieces, in build order

### Piece 3 first (1 h) — the cache must not outlive its retrieval code
- `config.py`: `RETRIEVAL_CACHE_VERSION: str = "2026-09-02a"` — **bumped in the same commit as any retrieval change** (add to the ship checklist in CLAUDE.md).
- `cache.py:176,181`: identifier `f"{settings.RETRIEVAL_CACHE_VERSION}:{md5}"`.
- `workers/pipeline.py:295`: pass `ttl=3600` when the claim's plan freshness is `pd`/`pw` (breaking news is not frozen for a day); default TTL unchanged.
- Tests: key changes with version; TTL by freshness. ~10 lines + 2 tests. No behaviour change for callers.

### Piece 2 (2 h) — recovery searches the claim's own words, unwindowed
- `retrieve.py::_recover_evidence_for_claim` ~1405: when the claim was triggered for *pool quality* (Piece 1 passes a `reason`), add one search pair `(claim_text, "none")`, 10 results, deduped against `existing_urls` (already passed in). Mirror of Build A one stage later.
- Apply the F1-D3 hedge to recovery's element queries (position 1 → `"none"`), which it never had. ~3 lines.
- Tests at the wired seam (the recovery search loop is driven in `test_coverage_recovery*`; add the twin pair + hedge pins). ~15 lines + 2 tests. Cost: +1 Serper query per triggered claim.

### Piece 1 (half a day) — the trigger reads quality, not just quantity
- `runner.py:447-472`: two new predicates beside `_element_is_starved`:
  - `_element_is_one_sided_thin(elem)`: all directional refs on ONE side **and** that side's `support_structure`/`challenge_structure` has `derivation.originals ≤ 1` **and** `distinct_domains ≤ 2` (reuse `element_is_thin`). **One-sided alone must NOT trigger** — a well-evidenced grave claim should look one-sided (invariant #7; Viglione `441144ac`: 10 challenges across 8 domains → no trigger). TTE `11f54993` (1 original + 6 derivatives) and Tapper `5d69fc71` (Neidle + 4 recitals) → trigger.
  - `_claim_pool_is_junk_heavy(claim)`: scorer excluded > 50% of the reviewed pool, or < 4 distinct domains after filtering (from the `raw_evidence` filter metadata the runner already holds).
- `runner.py:2520-2532`: candidates also qualify on either predicate; each candidate carries `reason ∈ {unresolved, starved, one_sided_thin, junk_heavy}` — logged, and written into the element `basis` as a receipt (`recovery_reason`) so the page can say why more was fetched (no hidden curation).
- Caps, timeout, merge and re-map untouched. ~40 lines + tests: the four fixture shapes above, pinned from stored records (tolerance 0).
- **Measure before flipping:** run the predicates over every stored check's basis (`scripts/`, read-only, no spend) and report the trigger rate by claim shape. Expect: fires on thin/niche claims (TTE, Tapper, McSweeney e1), never on big-outlet claims (Viglione, Seymour).

## What does not change
The cache stays (a viral claim must not cost a thousand searches; a fresh run is not automatically better — 25/40 URL churn). The cached pool is still the starting point; good items are kept by URL dedupe; only the weak parts are searched again. Recovery's existing caps bound cost and time.

## Cost and risk
- Per triggered claim: recovery already spends ~4 queries + fetches (~0.3p); Piece 2 adds ~0.1p. Untriggered claims: nothing.
- **Sycophancy arithmetic:** recovery can add commentary at weight 1 on a pool whose support floor is 3; the trigger fires on one-sided-thin pools where adding independent sources is the point, and the originals/domains guard stops echoes re-qualifying the pool. Re-check the `2026-08-20` ceiling rule (≤2 commentary items per lane) in the merge.
- Any query change re-keys bench cassettes — already owed for Build A; **re-record once, after Pieces 2+3 land.**
- Flags: one per piece (`ENABLE_RECOVERY_POOL_QUALITY_TRIGGER`, `ENABLE_RECOVERY_UNWINDOWED_TWIN`); Piece 3 has no flag (a version string).

## Estimate
~1 day of build + tests, then the measurement script, then a live control arm: TTE (after purging its cache key) and Tapper, 2 × 15p. **Order: 3 → 2 → 1.**

## Not in scope
Rewriting cached pools on read; a "who has disputed this?" reasoning step; Build B (Brave goggle lane, `…twin_design.md` §6) — separate decision.
