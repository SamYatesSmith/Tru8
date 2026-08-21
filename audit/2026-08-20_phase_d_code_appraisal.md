# Phase D (challenge lane) — code appraisal before build

**Date:** 2026-08-20
**Scope:** verify the Phase D build spec (`2026-08-14_quality_first_design_review.md` §1.1,
corrected by `2026-08-17_design_review_verification.md` §2) against the code as it stands at
`1ff7cc4`, before any of it is built.
**Method:** read the seam end-to-end, then *run* the real augmenter and the real merge over
synthetic plans (`scratchpad/phase_d_probe.py`) rather than reason about the arithmetic.

**Headline: the spec's placement rule — "appended LAST, claim lane 3→4" — does not fire on the
claims Phase D exists to fix.** Proven, not inferred. Two independent truncation collisions kill
it, and a third defect (dead since it shipped) sits in the same slice.

---

## 1. What the spec gets right (verified, no change needed)

| Spec claim | Verdict | Evidence |
|---|---|---|
| Mechanical templates, not a planner-prompt edit | ✅ correct, and the precedent exists | `app/utils/query_class_augmentation.py` is the exact shape: pure function, mutates `plan["queries"]`, returns for chaining, no LLM, no prompt touch |
| F1-D3 hedge keys on positional index 1 | ✅ correct | `_hedged_query_freshness`, `retrieve.py:425-427`; position is *within the lane*, applied after truncation at `:478-481` |
| `runner.py:54` is what makes the cap 3 real | ✅ correct | `EvidenceRetriever.__init__` sets `self.max_queries_per_element = 5` (`:526`); the worker overrides it from `PipelineConfig` (`workers/pipeline.py:180-181`). **Unit tests that construct `EvidenceRetriever()` directly run at cap 5 and cannot see cap-3 behaviour** — this is why §3 below has been invisible |
| A 4th claim-lane query drops per-query depth 13→10 | ✅ correct in effect | `:2033-2039`; `max_sources` is 40 on the main path (`:1665` passes `max_sources_per_claim * 2`). Mechanism description is slightly off — `CLAIM_LANE_MAX_RESULTS_PER_QUERY` is a literal `13` (`:195`) min'd against `40 // n`, not "40//3 by construction". Aggregate c0 candidates are flat (3×13=39 → 4×10=40), so this is a diversity change, not a loss. Re-pin `test_element_retrieval_seam.py` deliberately |
| `retrieve_for_elements` bypasses the lane seam | ✅ correct | `:1274-1466`; hand-built plans, hardcoded `plan.get("queries", [])[:2]` at `:1341`, no augmenter call, no hedge. Needs its own edit — confirmed |
| Yield is unmeasurable on `_query_index` | ✅ correct, and worse than stated — see §4 | `:2091-2102` first-writer-wins |

The fetch-budget worry does **not** apply: `_allocate_fetch_budget` (`:331-339`) buckets per
**query index**, not per lane, so a challenge variant gets its own round-robin bucket at claim-lane
weight 2. It will be fetched, not starved. (Second-order effect the spec misses: because the 2:1
weight is per *query*, adding a 4th c0 query raises the claim lane's aggregate fetch share from
6:10 to 8:10 per round — element lanes lose ~2 slots. Acceptable, but name it.)

---

## 2. 🔴 Defect A — "appended last" is truncated away on Politics / Finance / Health / Law

The claim lane's query list is built by three writers and then sliced:

1. planner — hard-capped at **2** (`query_planner.py:571`, `validated_plan["queries"][:2]`)
2. `augment_plans_with_date_anchor` — rewrites in place, **adds nothing** (`query_date_anchor.py:141-156`)
3. `augment_plans_with_class_queries` — appends **1**, or **2** when
   `domain ∈ {Politics, Finance, Health, Law}` **and** `jurisdiction ∈ {UK, US, EU}`
   (`query_class_augmentation.py:145-161`)
4. `_merge_element_plans` slices `[:lane_cap]` (`retrieve.py:477`)

So the claim lane offers up to **5** queries into a **4**-slot cap under the spec. Probe output,
real functions, planner at its normal output of 2:

| Article class | cap 3 (today) | cap 4 (spec) | challenge survives? |
|---|---|---|---|
| Politics/UK · Health/UK · Law/US … | 5 built → 3 kept | 5 built → 4 kept | **❌ NO** |
| Health/Global, Sports/Global, General | 4 built → 3 kept | 4 built → 4 kept | ✅ yes |

`jurisdiction` defaults to `"Global"` but is actively derived to UK/US/EU from LOCATION entities
(`article_classifier.py:390-396`), so the failing row is the common one for our corpus.

**Consequence:** Trump/wars (Politics·US), NHS (Health·UK), Scotland (Politics·UK) — three of the
four Phase E re-grade records — would issue **zero** challenge queries. The Phase D acceptance
criterion ("lane yield non-zero in the histogram; Macfarlane 589 in pool") would read as a miss and
be misattributed to Serper ranking. That is precisely the F1 "never fired live" ambiguity the spec
was written to avoid, at 45p a probe.

**Root cause of the spec error:** it conflated *"do not take index 1"* (the real hedge invariant)
with *"be last"*. The invariant is `index >= 2`, and last is merely one way to satisfy it — the one
way that also loses the truncation race.

---

## 3. 🔴 Defect B — the element-lane half of Phase D can never work as specced

`lane_cap = min(max_queries_per_element, ELEMENT_LANE_MAX_QUERIES)` = **2** (`:474-476`), and the
planner emits 2. Probe, both cap 3 and cap 4, every domain:

- planner emits 2 → element lane `[elem_q0, elem_q1, CHALLENGE][:2]` → **challenge dropped, always**
- planner emits 1 → `[elem_q0, CHALLENGE][:2]` → challenge survives **at index 1 and takes the
  F1-D3 hedge slot** (probe prints `e1 freshness=none CHALLENGE:…`)

There is no case where "the first element lane gets the variant" behaves as intended. It either
does not exist or it eats the historical-retrieval slot. Raising `max_queries_per_element` to 4 does
**not** help — the `min()` pins element lanes at 2 regardless.

---

## 4. 🟠 Defect C — the proposed yield tag cannot distinguish the challenge query

The spec says ride the `_element_ids` accumulating pattern (`:2093`). But `_element_ids` accumulates
the **lane id**, and a challenge variant *inside* lane c0 carries `element_id == "c0"` — identical to
the base query. `_lane_histogram` (`:301-308`) resolves `_query_index → query_element_ids[i]`, so a
challenge hit renders as plain `c0`.

The pattern is right; the array is not. Yield measurement needs a **fourth parallel array**
(`query_is_challenge: List[bool]`) threaded `_merge_element_plans` → `query_plan` →
`execute_planned_queries` → histogram, plus an accumulating `_challenge_hit` on the result that is
set on the dedup path (`:2091-2094`) exactly as `_element_ids.add()` is. Three arrays are built
side-by-side today (`:464-466`); a fourth is a mechanical addition, but it must be *designed in*,
not discovered at acceptance.

---

## 5. 🔴 Defect D — pre-existing: the jurisdiction-official class query is dead at full tier

Not Phase D's doing, found while measuring it. At cap 3 with the planner at 2, the official-sites
variant is built and **immediately truncated away** on every element-wired claim
(probe: `official class offered=True survives=False`). It has therefore never run in production for
Politics/Finance/Health/Law claims — the only domains it targets.

It is invisible because `EvidenceRetriever()` defaults to cap **5** (`:526`), so every unit test that
instantiates the retriever directly keeps all four queries and passes.

Founder rule: dead code is revived or removed when found. Phase D re-records anyway, so this is the
cheap moment to decide — and the decision interacts directly with §6.

---

## 6. Recommendation — one change, one decision

**Place the challenge variant by reserved slot, not by append order: insert at index 2 of the claim
lane, and raise the full-tier claim-lane cap 3 → 5.**

Why this and not a bigger redesign:

- Index 2 satisfies the real hedge invariant (`>= 2`) with no change to `_hedged_query_freshness`.
- Cap 5 makes the claim lane's four writers fit without a race: `[q0, q1(hedge), CHALLENGE,
  class_news, class_official]` — the challenge fires on **every** domain, and §5's dead official
  query is revived in the same stroke rather than left to rot behind a slice.
- Element lanes: `ELEMENT_LANE_MAX_QUERIES` 2 → 3 **only for the challenge-bearing lane**, so the
  variant lands at index 2 there too and never touches the hedge. Fixes §3 without fanning every
  element lane out.
- Cost: **13 → 16 Serper queries per claim** at full tier (+23%). ⚠️ Corrected 2026-08-20 after
  building — the first draft of this doc said "13 → 15 (~+15%)" and undercounted. The claim lane
  takes +2 (one counter-frame, one for the revived official-sites variant) and the first element
  lane +1. Fetch cap unchanged at 40 — this buys *frame diversity within a fixed fetch budget*, it
  does not enlarge the pool. Per-c0-query depth becomes `40//5 = 8`; aggregate c0 candidates stay 40.
- ⚠️ **Second-order effect, measured after building:** `_allocate_fetch_budget` weights per QUERY,
  not per lane, so raising the claim lane's query count also raises its aggregate fetch share —
  from 6:10 to 10:11 per round, i.e. roughly 15 → 19 of the 40 fetch slots, with element lanes
  losing ~4. Part of that shift funds the counter-frame (which lives in the claim lane), but not
  all of it. Fixing it properly would need a third weight class in `_allocate_fetch_budget`, which
  the design review explicitly ruled out as machinery for no clear gain. Recorded rather than
  fixed: the golden diffs at re-record #2 will show it, and it is a deliberate, known trade.
- Quick tier: cap 1, nothing appended survives — unchanged and correct.

**The cheaper alternative**, if +2 queries/claim is unwanted: cap 3 → 4, insert at index 2, and
*delete* the official-sites branch of the class augmenter for wired claims — which documents §5's
death rather than reviving it. One extra query instead of two, at the price of permanently losing
gov.uk/sec.gov targeting on political and health claims.

### Correction to a spec line, for the register

> "Quick tier gets NOTHING … and **must be declared in `app/core/tier_limitations.py`** or the drift
> guard fails."

Not as written. `max_queries_per_element` is **already** mapped to slug `reduced_query_breadth`
(`tier_limitations.py:43`), so raising the full-tier cap changes the numeric diff that is already
declared and the guard stays green with no new work. A declaration is required only if Phase D adds
a **new `PipelineConfig` field**. ⚠️ And the converse is the real trap: `undeclared_reductions()`
iterates `vars(DEFAULT_CONFIG)` (`:62-68`), so if `ENABLE_CHALLENGE_QUERIES` lands as a bare
`settings.` env flag — the idiom every scope gate uses — the guard **cannot see it at all**, quick
tier silently withholds an undeclared reduction, and invariant #5 is breached with a green CI.
Ship it as a `PipelineConfig` field *and* a slug, not as a settings flag alone.

---

## 7. Build order this implies (unchanged elsewhere)

1. `app/utils/query_challenge_augmentation.py` — mirror `query_class_augmentation.py`'s shape.
2. Slot-aware insertion + caps (§6) — this is the load-bearing edit, and it is in
   `_merge_element_plans`, not in the new module.
3. Fourth parallel array + `_challenge_hit` accumulation + histogram (§4) — **same commit**.
4. `retrieve_for_elements` counter-frame (`:1341`) — its own edit, same phase.
5. `PipelineConfig.enable_challenge_queries` + `_FIELD_SLUGS` slug.
6. Re-pin `test_element_retrieval_seam.py`; add a cap-3/cap-4/cap-5 truncation test that
   constructs the retriever **at the worker's cap**, not the constructor default (§2, §5 were both
   invisible for want of exactly this).
7. Re-record #2 (~25p, reframe patched out first), replay-verify, review golden diffs.

**Acceptance must include a truncation assertion, not only a live probe:** "the challenge variant
survives the merge for a Politics/UK claim at the production cap". A live-yield check alone cannot
distinguish "the lane fired and Serper ranked it low" from "the lane was sliced off before it ran" —
and this appraisal exists because those two look identical from the outside.

---

## 8. BUILT 2026-08-20 — what shipped, and what the build itself taught

Built to §6's recommendation. Flag-gated both ways: `settings.ENABLE_CHALLENGE_QUERIES`
(global kill-switch, no deploy) and `PipelineConfig.enable_challenge_queries` (per-tier, and the
thing the drift guard can actually see).

| # | Change | File |
|---|---|---|
| 1 | New module — `counter_frame_query`, `augment_plans_with_challenge_queries`, `challenge_augmentation_targets` | `app/utils/query_challenge_augmentation.py` |
| 2 | Reserved-slot insertion at index 2, element-lane cap 2→3 when carrying a variant, fourth parallel array | `retrieve.py::_merge_element_plans` |
| 3 | Counter-frame never claims the F1-D3 hedge slot | `retrieve.py::_hedged_query_freshness` |
| 4 | `_challenge_hit` accumulating tag on both the main and the revived freshness-fallback dedup paths; `[CHALLENGE LANE]` yield line | `retrieve.py::execute_planned_queries` |
| 5 | Counter-frame on BOTH recovery branches (planned + naive) | `retrieve.py::retrieve_for_elements` |
| 6 | Cap 3→5, `enable_challenge_queries`, quick tier off | `runner.py` |
| 7 | Slug `no_challenge_queries` | `tier_limitations.py` |
| 8 | Threading | `workers/pipeline.py` |

**Counter-frame wording:** `"{base} criticism OR rebuttal OR disputed OR limitations"`, base being
the planner's own first query (so it inherits the date anchor). Deliberately not
"debunked"/"hoax": those surface conspiracy content, whereas "rebuttal" and "limitations" surface
the methodological teardowns the two recorded failures actually missed.

### Four things the build corrected in this appraisal

1. **The reserved slot is defence-in-depth; the CAP RAISE does the truncation work.** The first
   mutation run exposed this: reverting to append-last at cap 5 broke only *one* test, because 5
   slots fit all five queries either way. The invariant that actually matters is **which query is
   sacrificed when the cap binds** — and it must never be the counter-frame. A test at cap 4 now
   pins exactly that, and the append-last mutation fails it. A cap-5-only test suite would have
   proved nothing about ordering.
2. **Cost was understated in §6.** Actual: **13 → 16 queries/claim** (+23%), plus a fetch-share
   shift toward the claim lane (~15 → 19 of the 40 slots). Both now recorded in §6.
3. **A synthesised claim lane would never have asked the other side.**
   `_synthesise_claim_lane_plan` fires when the planner returns no `c0` plan — and live that is
   not a rare edge: it happened on **3/3 networked checks on 2026-07-28**, because the planner
   prompt's only JSON example uses an `e1`-shaped id. The lane is built AFTER the augmenter chain
   has run, so the counter-frame silently skipped it — the one lane never asking the other side,
   on exactly the checks where the planner had already misbehaved. Found by reading the diff, not
   by a test. Fixed by re-augmenting the synthesised plan alone (idempotent); pinned by
   `TestSynthesisedClaimLane`, mutation-checked.
4. **`__init__` was the wrong home for the switch.** `retrieve_for_elements` read
   `self.enable_challenge_queries`, but `EvidenceRetriever.__new__(EvidenceRetriever)` is a
   legitimate construction path (used throughout `test_coverage_recovery.py` to skip network
   setup) and skips `__init__` entirely — every recovery call through it raised `AttributeError`.
   Caught only by the FULL suite, not by the targeted runs. It is now a **class** attribute.
   Generalisable: *an instance attribute is not safely readable in a codebase that constructs
   objects with `__new__`.*

### Verification

- **New tests: 37** — 11 augmenter (`test_query_challenge_augmentation.py`), 21 lane-slot
  (`test_challenge_lane.py`), 5 recovery counter-frame (`test_coverage_recovery.py`).
- **Mutation-checked, 6/6 caught:** append-last · no element-lane slot · counter-frame allowed to
  claim the hedge · quick tier silently enabled · omission undeclared · synthesised lane not
  re-augmented. Each names the user's stake in its failure message.
- **Full suite on the final code: 3,534 passed / 69 skipped / 11 failed.** All 11 failures are
  `tests/performance/test_cache_monitoring.py`, every one of them
  `Error 10061 connecting to localhost:6379` — Redis was not up (Docker Desktop not running on
  this machine, `docker-compose up -d` refused the pipe). Documented environment behaviour, and
  the file exercises Redis cache metrics, which this diff does not touch. **Not verified locally,
  and stated as such rather than assumed clean** — re-run with infrastructure up to close it.
  (It also explains the 16-minute suite: each of those tests burns a connection timeout.)
- **Deliberate re-pins, each with a dated in-file note:** `test_element_retrieval_seam.py`'s wired
  assertion (now proves MORE — the counter-frame reaches the wired seam through the real method,
  not just the merge helper); and 22 `test_coverage_recovery.py` blocks set
  `ENABLE_CHALLENGE_QUERIES = False` so they keep pinning recovery's BASE budget, with Phase D
  covered separately. ⚠️ `patch("app.pipeline.retrieve.settings")` yields a MagicMock on which
  **every flag reads truthy** — a new feature switches itself on inside tests that never mention
  it. Worth knowing before adding the next flag.

### Not done, and owed

- **Re-record #2 has NOT been run.** The counter-frame changes query strings, and request
  signatures are cassette keys, so every corpus claim will fail `cassette_drift` until re-recorded.
  A bench run before that would only re-confirm known drift. Held pending founder approval of the
  ~25p spend; the held mapping-prompt reframe must be patched OUT first (protocol in `OPEN_WORK.md`).
- **Live acceptance not run** — Scotland's Macfarlane 589 / dairy's Gid M-K teardown, and a
  non-zero `[CHALLENGE LANE]` line. Costs live checks; not started.
- The fetch-share shift (§6) is recorded, not mitigated — deliberately, per the design review's
  ruling against a third weight class in `_allocate_fetch_budget`.

---

## 9. 🔴 RE-RECORD #2 RUN — Phase D IS NOT SHIPPABLE AS WORDED (2026-08-20)

Re-record of all 10 cassettes (~25p, founder-approved) + verification replay.

**Replay result: `131 ok / 19 warn / 13 fail`** against the `175 / 10 / 2` baseline.

### Read the ok-count carefully — most of the drop is UNMEASURED, not failed

Two claims produced cassettes that **do not replay**: `TRU-5647-FA4F` (13 miss / 130 hit) and
`TRU-C1A0-0004` (48 miss / 45 hit). Each contributes `0 ok`, which accounts for most of the
175→131 fall. **The 2026-08-11 lesson repeated: a fresh recording is not a working recording.**
Cause not yet diagnosed; prime suspect is the coverage-recovery counter-frame, whose queries are
built from state (which elements are starved) rather than from the plan, so record and replay can
diverge. That is a defect in the build, separate from the wording problem below.

### The wording problem — mechanistic, and consistent across independent claims

`TRU-C1A0-0005` (UK CPI, September 2024) gained
`actuaries.blog.gov.uk/…/measures-of-price-inflation-rpi-cpi-and-cpih/`,
`obr.uk/box/the-long-run-difference-between-rpi-and-cpi-inflation/`, a tutor2u CPI explainer, a
ScienceDirect paper, and US + Canadian CPI pages — and **lost**
`gianlucabenigno.substack.com/…/uk-september-25-cpi-inflation-report` (a **hard invariant**, and
the off-period source the F1 temporal gate exists to scope), plus `bls.gov`, `cso.ie` and the
period-specific CNBC piece.

**On a statistical claim, "criticism / limitations" retrieves critiques of the METRIC, not
disputes of the CLAIM.** It is the measure-scope confusion reappearing in query form. "limitations"
was chosen deliberately for the dairy study-teardown class and it misfires badly on statistics.

| Claim | Failure |
|---|---|
| `TRU-C1A0-0005` | temporal gate **never fired** · required URL missing · `unique_domains` 3 (floor 5) · `top_domain_share` 0.5 (cap 0.45) |
| `TRU-018F-44AA` | `recital_scoped_refs` drift delta 4, `recital_scoped_elements` delta 1 — **the Phase C tolerance-0 pins** · `factual_weight_share` 0.12 |
| `TRU-B4A3-C42D` | `factual_weight_share` 0.12 (floor 0.15) |
| `TRU-C1A0-0001` | `top_domain_share` 0.6 |

**`factual_weight_share` falls below floor on three independent claims.** That is the systemic
signal and it points one way: the counter-frame displaces data/official evidence with
commentary-and-analysis critique. Pools became **more concentrated and less factual** — the
opposite of Phase D's purpose, and a direct hit on invariant #7 from the other side (a lane meant
to prevent one-sidedness is degrading the evidential base).

⚠️ **Attribution caveat, honoured:** this is one live draw against an older one, and run-variance
is real here. What raises it above variance is (a) the gained URLs are *precisely* what the query
asks for, and (b) the same direction appears on multiple independent claims. A matched pair
(flag off vs on, same session) is still owed before calling it settled.

### State of the tree after this run

- **Corpus RESTORED to the known-good baseline** (`git checkout -- backend/tests/replay_corpus`;
  all 10 cassettes are tracked, so nothing was lost). The Phase D recording is preserved at
  `scratchpad/phaseD_recording/` — it is bad data for shipping but is the raw material for the
  matched-pair attribution.
- **Held reframe RESTORED**, SHA256-verified identical to the pre-work byte copy, diffstat 45/+3.
- **No goldens updated.** The old ones stand.

### What must change before Phase D ships

1. **Re-word the counter-frame.** Drop "limitations" (definitional/methodological magnet). Prefer
   terms that presuppose a dispute *about the assertion* rather than about the instrument, and
   consider making it claim-type aware — the normative case (which the July design was written
   for) and the statistical case want different vocabulary.
2. **Protect period anchoring.** The counter-frame inherits the date anchor from `queries[0]` but
   the counter terms evidently outrank it; a statistical claim must not trade period-specific
   evidence for generic explainers.
3. **Diagnose the replay instability** on the two drifting claims before any further recording —
   otherwise the bench cannot act as a guard at all.
4. **Matched-pair verification** (flag off vs on, one session) before re-recording the corpus
   again. Two independent draws attribute nothing.
