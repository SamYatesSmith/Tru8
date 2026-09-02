# Build A — the claim lane's unwindowed twin (design review, 2026-09-02)

**Status:** REVIEWED → BUILDING (founder: "lets give it a go … scoped properly, and design reviewed").
**Evidence it rests on:** `audit/2026-09-02_dissent_discovery_probe.md` §1 — with the pipeline's exact
parameters the plain claim text finds the TTE rebuttal at rank 3 and the Scotland rebuttal at rank 3
**unwindowed**; with the past-month window the claim lane actually runs, Google returns only
facebook/instagram/linkedin (all blocklisted) — the lane contributes nothing.
**Companion (NOT built here):** Build B, the Brave generic-goggle lane — §6.

## 1. The defect, precisely

- `_synthesise_claim_lane_plan` (and the planner, when it does emit `c0`) gives the claim lane ONE
  query: the claim text. Its freshness is inherited from the first element plan (`pm` on both TTE runs).
- The F1-D3 hedge (`_hedged_query_freshness`) unwindows **position 1** of each lane. A one-query lane
  has no position 1. When the planner emits site: variants, position 1 is a *variant*, not the claim
  text. Either way **the claim's own words never run without a window.**
- Element lanes DO get the hedge, but they search the decomposed vocabulary ("NHS App AI triage Sussex
  GP pilot deployment"), which is not what a critic's headline matches.
- Net: on a thin claim whose critics published >1 month ago (or whose month-window results are all
  social), the record's dissent depends on run-to-run churn in the element lanes. `11f54993` had the
  critic; `b0398fca` did not; same input.

## 2. The change (mechanical, flag-gated)

`ENABLE_CLAIM_LANE_UNWINDOWED_TWIN` (default True; False = today, byte-for-byte).

In `_merge_element_plans`, for a **wired** claim lane whose freshness is not `pd`/`pw` (the F1-D3
breaking-news exemption, founder decision #2): if the lane's **lead query** (`queries[0]`) is not
already emitted with freshness `none`, insert a copy of it at **lane position 1** with freshness
`none`. A new parallel array `query_twin_of` marks it (`[None, 0, None, …]`); everything else is
`None`, so every existing consumer and the Seeker's self-supplied plans are untouched.

Why position 1 and not the end: `unique_search_results` is in query order and the allocator walks it;
the twin's top results should sit beside the lead's, not behind the site: variants.

In `execute_planned_queries`:
- **Depth:** twins are excluded from the claim-lane depth divisor, so the lead keeps exactly the depth
  it has today (13 alone, 6 beside two variants). The twin asks for a fixed `CLAIM_LANE_TWIN_RESULTS = 10`
  (both known rebuttals sit at rank 3; results cost nothing — providers bill per call).
- **Fetch weight:** `_allocate_fetch_budget` already round-robins **per query**, each claim-lane query
  at weight 2. A twin at weight 2 would move the claim lane from 2/7 to 4/9 of the 40 fetch slots
  (≈11 → ≈18) and starve the element lanes — the opposite of "add, don't replace". So the twin takes
  **`ELEMENT_LANE_FETCH_WEIGHT` (1)**: the lane goes 2/7 → 3/8 (≈11 → ≈15 slots), and the twin's rank-3
  hit is fetched in its third round. Element lanes keep ≈25 of 40.
- Nothing else changes: dedupe is global (invariant #1), the mapper decides direction, quick tier gets
  the same twin (one extra Serper call, ~$0.001; not a tier limitation because both tiers get it).

Cost: **+1 Serper query per wired claim** (~0.1p on a 1-claim check, ≤0.5p on a 5-claim article).

## 3. What this is NOT
- Not Phase D. No new wording, no counter-frames, no platform targeting. The query is the claim text,
  which the design has always said the claim lane searches — only the window changes.
- Not a "challenge lane". It is direction-neutral; it widens the pool the mapper judges.
- Not a fix for framing-mismatch rebuttals (dairy). Probe §2: unreachable by any query on any engine.

## 4. Verification (the 20 Aug rules)
1. **Unit, at the wired seam** (`tests/unit/pipeline/test_claim_lane_unwindowed_twin.py`): twin present
   at position 1 with `none` for synthesised and planner-emitted lanes; absent for `pd`/`pw`, for an
   already-unwindowed lead, for unwired plans, and with the flag off; the four arrays stay
   index-parallel; site: variants shift to positions 2+; existing hedge positions unchanged; depth:
   twin 10, lead unchanged; allocator: twin weight 1.
2. **Existing pins** (`test_element_retrieval_seam.py`, `test_f1_recency_hedge.py`) that assert exact
   query lists on wired plans are updated to the new shape with a dated note — they pin behaviour that
   is changing on purpose.
3. **Bench:** the twin is a new request signature on every wired corpus claim → **cassette drift on
   all of them until re-recorded** (`--all --update-golden`, never per-claim; ~£0.80, ~10 min, docker
   up). The bench cannot judge the change itself (25/40 URL churn); it only guards later drift.
   Re-record on the founder's go (money).
4. **Live control arm** (founder's go, 2 × 15p): re-run the TTE and Scotland claims after deploy and
   read the pool — the critic's presence is the pass/fail, not the badges. Run each twice if the first
   pair disagrees (churn).

## 5. Rollback
Env `ENABLE_CLAIM_LANE_UNWINDOWED_TWIN=False` on Railway — no deploy.

## 6. Build B (designed, NOT built) — the independent-publishing lane on Brave
One Brave query per wired claim with a **generic** inline goggle (boost `substack.com`, `ghost.io`,
`medium.com`; downrank `facebook.com`, `instagram.com`), results appended as a claim-lane sibling
query at weight 1 with a hard cap of **2 fetch slots** (commentary weight 1 vs support floor 3 — a
lane that could badge alone is a sycophancy hazard). Direction-neutral; name it for what it does.
Measured 2/3 on the known cases. Cost: free tier 2,000/month covers today's volume; Base plan ≈0.4p
per query at scale, sharing the quota with Brave's fallback role (the circuit breaker must protect
the fallback). Gate: after A ships and the control arm reads, decide whether the extra pence buy
enough. Not before.
