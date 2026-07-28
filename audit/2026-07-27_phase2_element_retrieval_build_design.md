# Phase 2 build design — wiring element-level retrieval

**Date:** 2026-07-27 · **Status:** BUILT `36d3f4e` · **independently verified 2026-07-28** (§6b) —
criteria 1–16 + 18 PASS, **criterion 17 (live pair) OWED and blocking deploy**
**Parent (diagnosis, already proven):** `audit/2026-07-27_element_retrieval_design.md`
**Sibling (shipped):** `audit/2026-07-27_phase1_mechanical_honesty_design.md` — its §4a testing
rules apply here · **SOT:** `audit/DECOUPLING_STATE.md`
**Process:** phased-build-loop — criteria frozen in §6 *before* any code.

---

## 1. Scope

Wire the seam the parent doc proved dead: `retrieve.py:292` reads `claim["elements"]`,
decompose writes `claim["claim_map"]["elements"]`, nothing writes the key that is read, so
the query planner has only ever seen one synthetic element made of the raw claim text.

Diagnosis is **not re-derived here**. This document is the build: exact changes, the budget
rule, the guards, and what "done" means.

---

## 2. Three things the code read changed about the plan

The parent design was written from the defect. Reading the execution path end-to-end surfaced
three consequences of wiring it that the parent doc does not cover. All three are load-bearing.

### 2a. Sequential slicing would starve the very lanes we are adding

`_execute_planned_queries` appends results **in query order** and then truncates:
`unique_search_results[:max_sources]` (`:1800`, `max_sources = 40`). With 3 queries × 13
results that slice never bites. With ~11 queries it bites hard, and it bites the **tail** —
the last elements' lanes get dropped wholesale before a single URL is fetched. Wiring the
seam without fixing the allocation would give the last element of every claim nothing, and
the logs would still say its queries ran.

Fix: allocate the fetch budget by **weighted round-robin across lanes** instead of list
order. This is invariant #2's principle ("truncation is round-robin, never sequential
slicing") applied at the one truncation point that never needed it before.

### 2b. The planner's token budget is now a silent-truncation risk

`max_tokens=3000` for the whole batch. Today a batch is ≤5 plans (one per claim). After
wiring it is up to 5 claims × (1 claim lane + 5 elements) = **30 plans**, ~100 tokens each.
Gemini's output would truncate mid-array — and `_try_parse_json`'s truncation repair
(`google_ai.py:85-143`) **closes the brackets and returns a short plans list**, so the tail
elements lose their queries with one WARNING line and no failure. Fix: scale `max_tokens`
with element count on both providers.

### 2c. `_validate_plans` maps plans to claims by list position

`element_texts[i]` (`query_planner.py:505`) assumes plan *i* is element *i*. Today
`total_elements == n_claims`, so a positional slip is invisible. After wiring, indices span
elements and any reordering or omission by the LLM mis-attributes the claim text used by
`_fix_hallucinated_years` — i.e. years get rewritten against the wrong claim. Fix: key by
`(claim_index, element_id)`.

---

## 3. Design

### 3.1 The seam (`retrieve.py:289-319`)

```
lanes = [ {element_id: "c0", description: claim["text"]} ]          # claim lane — unchanged behaviour
       + [ {element_id: e.element_id, description: e.description}   # element lanes — new
           for e in (claim["claim_map"]["elements"] or claim["elements"])[:5] if description non-empty ]
```

- **Add, do not replace** (founder decision, parent §4.1). The claim lane is exactly today's
  synthetic element; the element lanes are additive.
- The claim lane's id becomes **`c0`, not `e1`**. Today every claim-level result is stamped
  `element_ids: ["e1"]`, which silently attributes the whole pool to the first real element.
  `c0` cannot collide with a real element id (`e1`…`e5`).
- Element cap 5 (the Claim Map contract's own ceiling), empty descriptions skipped.
- `claim["elements"]` is still honoured as a fallback so any caller that does populate it
  keeps working; the pre-decomposition path (no claim_map) is byte-identical to today.

### 3.2 Query counts — deterministic, not emergent

| Lane | LLM queries | Class augmentation | Cap | Result |
|---|---|---|---|---|
| Claim (`c0`) | ≤2 (`_validate_plans:512`) | +1–2 (`query_class_augmentation`) | `max_queries_per_element` = 3 | **3** — identical to today |
| Each element | ≤2 | **none** | `ELEMENT_LANE_MAX_QUERIES` = 2 | **2** |

Class-targeted `site:` augmentation stays **claim-lane only**: it is derived from the
article's domain/jurisdiction, it exists to fix *pool-wide* outlet diversity, and confining
it keeps the count deterministic.

**Per claim: ≤3 + 5×2 = 13 queries** (today 3). Per check (≤5 selected claims): **≤65 Serper
calls**, today ≤15. At Serper rates that is tenths of a penny per check. Fetch and every LLM
stage stay behind their existing caps, so COGS is dominated by unchanged stages.

### 3.3 Fetch budget — parent §4.3 option (c), made concrete

The fetch cap stays **40** (`max_sources_per_claim * 2`). Two rules, both active only when a
claim lane *and* ≥1 element lane exist (`merged_plan["element_wired"] = True`):

1. **Results requested per query, by lane.** Claim lane keeps today's depth
   `max(3, 40 // n_claim_queries)` = **13**; element lanes request
   `ELEMENT_RESULTS_PER_QUERY` = **5**. Requesting more results costs nothing extra — search
   providers bill per *call*, and `num` is capped at 20 (`search.py:495`).
2. **Fetch slots allocated by weighted round-robin.** Claim lane weight **2**, element lanes
   weight **1**, per round, in lane order, until 40 URLs. Expected split on a 4-element claim:
   claim lane ≈17 URLs, element lanes ≈23.

Why not raise the cap to hold claim-lane depth at 13 (parent option (a)): every extra fetch
runs inside `CLAIM_TIMEOUT = 45s`, and that timeout's failure mode is **total loss of the
claim's web evidence** (`retrieve.py:1376-1425` keeps only completed tasks). Trading a known
depth reduction for an unbounded risk of losing everything is the wrong way round. Decision
D1 in §5 puts the alternative to the founder anyway.

**Honest statement of the trade:** claim-lane depth falls from ~13 URLs/query to ~5. That is
a real reduction on the factual path, which is why `TRU-C681-2E38` (Grenfell) is a frozen
criterion rather than an assumption.

### 3.4 Guards and telemetry

- `ENABLE_ELEMENT_RETRIEVAL` (default `True`). **Off = today, byte-for-byte** — one synthetic
  `e1` lane, uniform `sources_per_query`, sequential slicing. Rollback without a deploy.
- Planner `max_tokens` scales: `min(8000, max(3000, 220 × total_elements))`. 1 element → 3000
  (unchanged); 30 → 6600.
- `_validate_plans` keys `element_texts` by `(claim_index, element_id)`.
- New log lines — this is how the before/after in parent §6 gets measured, and how "the seam
  is live" stops being an inference: element/lane/query counts per claim, per-lane URL counts
  actually fetched, and the count of candidates dropped by the fetch budget (today invisible,
  and about to become non-zero).

### 3.5 Files touched

`backend/app/pipeline/retrieve.py` (seam, lane merge, per-lane request sizes, round-robin
allocation, telemetry) · `backend/app/utils/query_planner.py` (token scaling, plan→element
keying) · `backend/app/core/config.py` (one flag, three constants) ·
`backend/tests/unit/pipeline/` (new pins).

**Zero prompt bytes.** The planner's `SYSTEM_PROMPT`, the decompose prompts and the mapping
prompts are untouched — but unlike Phase 1 this does **not** leave cassettes intact, because
cassette keys are request signatures and the query strings change (§7).

---

## 4. Out of scope — deliberately

Mapper answeredness threshold · `_grounds_applied` precision · compound-question atomicity ·
Seeker wording · `F-MMR-POOL` · pool balance/MMR. **All Phase 3, all to be tuned against the
post-Phase-2 pool, never today's.** Nothing in this phase changes how evidence is mapped,
stated, or summarised — only which evidence is gathered.

---

## 5. Decisions needed before build

| # | Decision | Options | Recommendation |
|---|---|---|---|
| **D1** | Fetch budget | (i) hold 40, weighted round-robin — claim-lane depth 13→~5 · (ii) raise to 60 so claim-lane depth holds, ~50% more fetches inside the 45s claim timeout | **(i)** — the timeout's failure mode is losing the claim's entire web pool; depth is measurable after, risk is not |
| **D2** | Quick tier (£0.07) | (i) element retrieval ON, capped at 3 element lanes × 1 query · (ii) claim-level only | **(i)** — +3 Serper calls, ~£0.001. Honesty should not be tier-gated |
| — | *(D2 answered wider than asked)* | Founder: *"we can afford the Serper calls… take what you need"* | **Built without the 3-lane trim**: quick gets all its element lanes at its own `max_queries_per_element=1`, so ≤6 queries/claim instead of ≤4. No other lane was widened, because past that point extra queries do not buy evidence — the FETCH cap binds, so more queries only thin each lane's share |
| **D3** | Grounds-routed claims | (i) claim lane keeps weight 2 like every other route · (ii) drop it to 1, so an opinion's own valence cannot take a third of the pool | **(i) for Phase 2** — one variable at a time; the lanes already cut the valence lane from 100% to ~⅓. Revisit in Phase 3 with measurements |

Settled by the handoff, restated so it is not re-opened: the **F7 bench re-gold happens once,
after Phase 2**, not before.

---

## 6. Acceptance criteria — FROZEN

Every criterion is verified by an agent that did not build. Phase 1's §4a rules apply:
mutate each guard and confirm the pin fires on its semantically correct assertion; the
mutation must be asserted to have applied; restore in `finally`; hash-verify after.

| # | Criterion | Evidence required |
|---|---|---|
| 1 | Decomposed claim → planner receives 1 claim lane + N element lanes; claim lane first, id `c0`, description == claim text | unit test on the wiring, asserting the exact list |
| 2 | Element descriptions reach the planner **verbatim** — a question-shaped grounds element arrives unaltered | positive assertion on the exact string (fails loudly on an emptied fixture) |
| 3 | No claim_map (pre-decomposition / re_search callers) → **byte-identical to today**: single `e1` lane, uniform `sources_per_query`, sequential ordering | regression test |
| 4 | `ENABLE_ELEMENT_RETRIEVAL=False` → byte-identical to today on a **decomposed** claim, all three behaviours (lanes, request sizes, ordering) | regression test |
| 5 | Element cap: 7 elements → 5 element lanes + claim lane; empty-description elements skipped | unit test |
| 6 | Query counts deterministic: claim lane ≤3 (class-augmented), each element lane ≤2 (never class-augmented) | unit test on merged plan |
| 7 | `query_element_ids` stays index-parallel with `queries` after merge, and each id is the lane that produced it | unit test — the attribution pin |
| 8 | Fetch allocation: with 1 claim lane (3 q) + 4 element lanes (2 q each) and 40 slots, **every lane contributes ≥1 URL**; reverting to sequential slicing makes it fail | unit test + mutation |
| 9 | Claim lane is weighted 2:1 — it receives strictly more slots than any single element lane | unit test on the allocation |
| 10 | Per-lane request sizes: claim-lane calls request 13, element-lane calls 5 | assert `max_results` per mocked search call |
| 11 | F1-D3 recency hedge intact per lane: position 1 unwindowed unless the planner chose pd/pw | existing `test_f1_recency_hedge.py` extended to multi-lane, still green |
| 12 | Planner `max_tokens` scales with element count (30 elements → >3000; 1 element → exactly 3000) | unit test on call args, both providers |
| 13 | `_validate_plans` attributes plans by `(claim_index, element_id)` — shuffled plan order still year-fixes against the right claim | unit test + mutation (restore positional → fails) |
| 14 | Telemetry proves the seam is live: a log line carrying elements/lanes/queries per claim, and the budget-drop count | assertion on captured log records |
| 15 | Full backend suite: **no new failures** vs baseline 2893 passed / 11 failed (Redis-only) / 69 skipped; `tests/unit/pipeline/` 1002 passed | captured pytest output |
| 16 | Zero prompt bytes changed (`SYSTEM_PROMPT`, decompose, mapping) | `git diff` |
| 17 | **Live pair, networked** — T4 paraphrase: the 4 questions are searched and no query mirrors the claim's valence · T2 paraphrase: e03 (alternative NHS treatments) is searched · T3 Grenfell paraphrase: pool size, tier mix and element states do not regress | prod run + logs; **owed, not skippable — see §8** |
| 18 | **Added 2026-07-28 by the independent pass** — `ENABLE_ELEMENT_RETRIEVAL=False` **still honours caller-supplied `claim["elements"]`**. Criterion 3 pins that caller, criterion 4 pins the flag; neither pinned the *intersection*, and that is exactly where the build broke | unit test + mutation M9 (restore the flag check above the branch → fails) |

---

## 6a. Build notes — drift from the approved design, declared

Two things exist in the build that the approved design did not spell out. Both are
additive; neither changes an acceptance criterion.

1. **`[RETRIEVE] Lane shortfall` warning.** If the planner is handed a lane and returns no
   queries for it, that element is never searched — the exact defect this phase exists to
   kill, arriving by a different route. The planner's own shortfall warning is batch-level
   (*"only N plans for M elements"*); this one names the element and the claim. Falls under
   §3.4 telemetry, pinned and mutation-proven like the rest.
2. **Assertions written against literals, not the constants they pin.** `assert
   per_query == ELEMENT_RESULTS_PER_QUERY` passes under any mutation of that constant —
   it asserts a tautology. The request-size pin asserts `13` and `5` directly. This is the
   same class of defect as Phase 1's vacuous fixture, caught here by the matrix rather than
   by the verifier.

3. **Criterion 11's stated evidence was not produced** (found by the independent pass, not
   declared here at build time). The criterion required the *existing*
   `test_f1_recency_hedge.py` to be **extended** to multi-lane; that file was never touched.
   Multi-lane hedging is pinned instead by
   `test_hedge_applies_per_lane_not_across_the_merged_list` in the new file, and the original
   13 tests still pass. Behaviour covered, criterion satisfied by a different route — recorded
   because "evidence or it didn't happen" applies to *which* evidence, not just whether some
   exists.

**Mutation matrix: 15/15 fired**, each on a semantically correct assertion. Two rounds were
needed — the first showed `M7 (revert to sequential slicing)` firing *only* on a telemetry
assertion, because the allocation was pinned through the helper in isolation while nothing
proved `_execute_planned_queries` still called it. A behavioural pin
(`test_wired_path_actually_fetches_from_every_lane`, driving the real method with a pool
that overflows the budget and asserting on the URLs that reach the fetcher) now covers it.
That is the NF-18 lesson again: **test the wired seam, not the halves.**

---

## 6b. Independent verification — 2026-07-28

Run by a pass that did **not** build this, re-deriving PASS/FAIL from §6 rather than
inheriting §6a's claims. The build's own evidence was entirely builder-run; two earlier
delegated verifiers ran long and returned nothing.

**Result: criteria 1–16 and 18 PASS. Criterion 17 remains OWED and blocks deploy.**

Evidence captured:

- **Full suite: 2922 passed / 11 failed / 69 skipped** (979s). All 11 failures are
  `tests/performance/test_cache_monitoring.py` — Redis not running, matching the recorded
  baseline exactly. 2922 = baseline 2893 + the 29 tests added. Criterion 15 confirmed.
- **Mutation matrix re-run independently: 10/10 fired**, each on a semantically correct
  assertion, every mutation asserted to have applied before running, all files restored and
  SHA-256-verified after. Covers C1, C3, C5, C6, C8, C9, C10, C12, C13, C18.
- **Criterion 9 measured, not inferred.** The build's pin compares per-*query* counts; the
  criterion is about per-*lane* share. Driving the real allocator gives
  `{c0: 18, e1: 6, e2: 6, e3: 6, e4: 4}` of 40 — claim lane 18 vs largest element lane 6,
  and an 18/22 split against the §3.3 prediction of ~17/~23. The pin has been tightened to
  assert the per-lane form. Note the **last lane systematically takes less** (4 vs 6) because
  the budget runs out mid-round: bounded, not starvation, and C8's ≥1 floor holds.

Three defects in the delivered evidence, all now closed:

| Found | Criterion | Nature | Fix |
|---|---|---|---|
| Flag-off discards caller-supplied elements | 3 / **18** | **Real behaviour defect** | flag check moved *below* the `caller_supplied` branch; criterion 18 + mutation M9 |
| OpenAI provider never pinned | 12 | Evidence gap ("both providers") | `test_openai_fallback_receives_the_scaled_budget` + mutation M10 |
| Hedge file never extended | 11 | Undeclared drift | recorded in §6a item 3 |

**The rollback defect is the one that mattered.** §3.4 and §8 promise
`ENABLE_ELEMENT_RETRIEVAL=False` restores today's behaviour byte-for-byte without a deploy.
It did not: `_build_retrieval_lanes` returned early on the flag and discarded
`claim["elements"]`, which `re_search.py:184-194` populates. Pulling the rollback — the
moment of most pressure and least attention — would have silently re-pointed the Seeker's
targeted re-query at the claim's own text. That is precisely the defect this phase exists to
kill, reappearing on the safety lever. Criterion 3 had already caught the builder once
(adding a claim lane to re-search); it caught the same seam a second time on the flag axis,
which is the argument for freezing criteria that pin **what must not change**.

*Also corrected: §6a says 15/15 mutations, the commit message and MEMORY.md say 16/16. The
independent matrix is a separate 10-mutation set and does not resolve which of the two the
build actually ran.*

---

## 7. Blast radius — restated because it lands with this commit

All replay cassettes die: cassette keys are request signatures and every query string
changes. **F7 re-gold becomes blocking for anything bench-gated**, once, after this. Also
invalidated: 2026-07-02 latency baselines and the pending prod `stage_timings_s` read;
`cost_telemetry` per-check baselines; coverage-recovery trigger rate (Stage 5.1 has been
compensating for this defect and should fire markedly less — a behaviour change, not just
volume); agent tier economics (quick most exposed); the consensus layer will mix pre- and
post-wiring element states. Historical checks are not recomputed, so every before/after
comparison is cross-version.

---

## 8. Risks + reversibility

| Risk | Mitigation | Reversible? |
|---|---|---|
| Factual path regresses on shallower claim-lane depth | criterion 17 Grenfell guard; D1 alternative sized and costed | **Yes** — flag off, no deploy |
| Query planner truncates on large batches | §2b token scaling + criterion 12; shortfall already WARNs | Yes |
| More queries → more latency inside `CLAIM_TIMEOUT` | queries are `asyncio.gather`'d (`:1691`); fetch cap unchanged at 40, so the expensive axis does not grow | Yes |
| An element lane returns nothing and its element still reads unanswered | correct behaviour — that is the Seeker's job; Phase 1's floor now routes it there | n/a |
| `c0` surfaces somewhere that expects a real element id | criterion 7 + repo-wide grep in verification | Yes |

**Criterion 17 needs network + a real check run.** *(Corrected 2026-07-28: this line
previously read "no working local LLM key", which is false and was propagated onward.
**Google is the primary provider and `GOOGLE_AI_API_KEY` is set locally**; the dead key is
`OPENAI_API_KEY`, which is only the fallback. What criterion 17 actually needs is a live
networked check with real search providers and a prod check id to compare against — not an
LLM key that was never missing. See CLAUDE.md "LLM providers".)*
Local criteria 1–16 gate the build; 17 gates the *ship*. If it cannot be run at sign-off it
is recorded as **owed and blocking deploy**, in the register, not quietly dropped —
Phase 1's lesson: a mechanism verified is not an outcome verified.

**Rollback unit:** one commit; `ENABLE_ELEMENT_RETRIEVAL=False` restores today's behaviour
without a deploy.
