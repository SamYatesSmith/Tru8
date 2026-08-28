# Rigour and Refutation — scoping design review (OPEN_WORK items 7 + 8)

**Date:** 2026-08-28 · **Status: item 7 stage 1 (Option 7-A) BUILT + FLIPPED ON same day** (`20a6da8`, `2612a3e` — measured first: 0 false positives / 200 stored URLs, Carbon Brief flags and lands at reporting on the `fa08cff7` probe; bench re-recorded, pass state 121/5/11/5). **Item 7 stage 2 (7-B) and item 8 Option A remain scoped, NOT built.** The rest of this doc is the scoping review as written before the build.
Everything below was re-derived from code and from the LIVE public record
(`GET /api/v1/checks/public/fa08cff7-…?detailed=true`, fetched today), never from the
OPEN_WORK prose alone. Where the prose and the record disagree, this doc says so.

---

## 0. Verdict summary

| | Finding | Recommended direction (founder decides) |
|---|---|---|
| **Item 7** (tier sets weight, rigour has no channel) | **Real.** One constant, one consumer — but its arithmetic couples to the support floors and the anti-sycophancy ceiling, so any number change is a package, never a one-liner. Two dead channels found: `is_factcheck` can only ever fire on Google Fact-Check API hits (the domain-marking parser is **unwired**), and the LLM classifier never sees the flag at all. | Stage 1: repair the `is_factcheck` channel (content-derived, not outlet-list). Stage 2 (only after measuring): let `evidence_type` modulate weight within tier, **floors moved in the same commit**. Do not touch retrieval. |
| **Item 8** (vocabulary cannot say "refuted") | **Real at the vocabulary/aggregate layer — but the stated premise is PARTIALLY WRONG.** The element badges a reader scans on `/r/fa08cff7` already read **"− Challenged"**, not "± Disputed" (§4d fix 3, `29c5149`, 2026-07-21 — verified live: both elements carry `rule_applied: all_challenges` and every badge surface that receives `basis` renders the refinement). What still flattens: the raw `state` value every machine consumer reads, the dashboard/history aggregates, and arguably the strength of the word "Challenged" for 0-vs-13. | Complete the presentation layer (Option A) + expose a **derived** `challengesOnly` field in API payloads. **Defer the enum extension**; if ever taken, the value must be descriptive ("challenged"), never verdicty ("refuted"), derived-only, forward-only. |

Neither item's fix unblocks Viglione — her hold is the tier *labelling* her own outlet
receives, and that stands until item 7 is actually decided and shipped. **No weight patch
to unblock a send** (founder, 2026-08-27, reaffirmed here).

---

## 1. What the record actually shows (fetched 2026-08-28)

Claim: *"2026 is the quietest year for wildfires in Europe"* (the "by some distance"
truncation is already logged in item 7).

| Element | state | rule_applied | supports | challenges | context | weighted s/c |
|---|---|---|---|---|---|---|
| e1 (number of wildfires) | disputed | `all_challenges` | 0 | 4 | 2 | 0 / 8 |
| e2 (intensity / area burned) | disputed | `all_challenges` | 0 | 9 | 3 | 0 / 17 |

Orientation: *"Of 2 elements examined, retrieved evidence challenges all 2, with none
supporting."* `orientation_basis`: `{disputed: 2, supported: 0, …}`.

Evidence classification (all 13 items):
- **Carbon Brief → commentary/analysis, `classification_method: llm`.** The LLM filed it,
  not the heuristic — though it would have landed the same either way, because
  **`carbonbrief.org` is hardcoded in `_THINK_TANKS`** (`evidence_classifier.py:190`,
  → commentary/analysis on the heuristic path). It is double-pinned.
- **hannahritchie.substack.com → commentary/opinion, `blog_platform_floor`** — confirmed;
  the hard override, content never assessed.
- **`is_factcheck: False` on every item** — confirmed.
- x.com (Ridley) → commentary/opinion, mapped `context` — contributes zero. Working as
  designed; do not "fix".

**Weights never touched this record's outcome.** With 0 supports on both elements, the
count-based `all_challenges` rule fires before any weight is consulted
(`claim_map_analyzer.py:1051`). Item 7 is about *labelling* and about *marginal
mixed-evidence cases* — not about this record's answer. That matters for prioritisation.

---

## 2. Item 7 — verified mechanism inventory

### 2.1 The weight constant and its one consumer

`_STATE_TIER_WEIGHTS = {"primary": 3, "reporting": 2, "commentary": 1}`
(`claim_map_analyzer.py:873`). **Single definition, single consumer**: `_ref_weight`
inside `_derive_element_state_with_authority` (`:1029`). Three call sites, all passing
`_state_floor_for(claim_map)`:

1. Main mapping pass (`:2337`)
2. Completion pass (`:2963`)
3. Coverage recovery (`:3195` — since 2026-08-17 receives the *merged* pool, so
   pre-existing refs no longer fall to weight 1)

Unresolvable evidence_ids and unknown tiers default to weight 1.

`factual_weight_share` (the bench metric) is **type-based** — (academic + official +
data) / mapped, computed in `runner.py` — and does NOT read `_STATE_TIER_WEIGHTS`. A
weight change moves no bench quality signal directly; only state flips would show, via
`element_resolution`.

### 2.2 What the weights decide — and what they don't

Weight-free (count-based): `no_evidence`, `context_only`, `all_challenges`,
`all_supports`. Weight-dependent: the two strict-`>` 2× dominance rules, `close_split`,
and both support floors. So the weights only ever decide **mixed-evidence elements near
the dominance boundary** and **whether thin support clears the floor**.

### 2.3 The arithmetic the weights are load-bearing for (change = package)

- `FACTUAL_MIN_WEIGHTED_SUPPORT = 3` and `GROUNDS_MIN_WEIGHTED_SUPPORT = 3`
  (`config.py:651-667`) are calibrated to "**one primary (weight 3) alone suffices; a
  lone reporting (2) or commentary (1) ref does not**". Any weight change silently
  re-derives what the floor means.
- **The anti-sycophancy ceiling** (Phase D abandonment record, 2026-08-20): with floor 3
  and commentary at weight 1, THREE independent commentary items are needed to badge a
  factual element `supported`. Raise any commentary-tier class to weight 2 and TWO
  suffice — *the exact hazard already documented at item 5 #3 when promoting Substack
  was considered and closed.* **Any weight raise for a commentary-tier class must move
  the floors in the same commit or state the halved bar as an accepted decision.**
- The strict-`>` tie semantics (2026-08-17, commit `d1d4bd9`): an exact 2×
  tie is `close_split` → `disputed`, pinned by
  `tests/unit/pipeline/test_state_behaviour_phase_b.py`. New weight values create new
  exact-tie points; the tests' worked examples must be re-derived, not just re-run.
- Symmetry: weights apply identically to supports and challenges. Any modulation must
  stay side-blind (invariant #7 — both sides in one commit, always).

### 2.4 The `is_factcheck` channel is structurally dead (two mechanisms)

Verified end-to-end:

1. **Only the Google Fact-Check API stage can set it** (`factcheck_api.py:242`, invoked
   from the runner's FACTCHECK stage). A factcheck arriving through *web search* — which
   is how Carbon Brief arrived — is never flagged.
2. **`factcheck_parser.py` (domain marking for snopes/politifact/factcheck.org/fullfact
   + rating extraction) is NOT wired into the live pipeline.** Zero references from
   `app/pipeline/`; its only caller is the legacy `workers/pipeline.py`, which is not
   the live path (runner is). So even the four hardcoded factcheck domains go unflagged
   on the search path, and `factcheckRating`/`factcheckPublisher` (`response_builder.py:119`,
   gated on `factcheck_parse_success`) can effectively never render for searched items.
3. **The LLM classifier never sees the flag.** The one classification consequence —
   `is_factcheck → ("reporting", "analysis")` — lives in `_classify_heuristic`
   (`evidence_classifier.py:325`), the *fallback* path. A flagged item classified by the
   LLM can still land commentary.

So the existing design already contains a decided answer to "what tier is a factcheck":
**reporting/analysis, weight 2** — equal to a news write-up, not half. It just never
executes. That is the narrowest honest repair available.

### 2.5 The tier philosophy is not the defect

Tier = distance from the underlying data (fireside lock). Carbon Brief reading
Copernicus/EFFIS data it did not produce IS secondary analysis; filing it commentary is
*consistent* with the philosophy. The defect is exactly as item 7 states it: **weight
derives from distance alone**, so the philosophy's honest label gets an arithmetic
penalty it never asked for.

---

## 3. Item 7 — options

### Option 7-A: repair `is_factcheck` (recommended stage 1)

Make the flag content-derived and live on the search path, then let the already-decided
consequence execute.

- **How it fires:** the batched tier/type LLM classifier already reads title+snippet per
  item; add "is this article a verification exercise of a specific claim?" to its output
  schema (a genre judgement — a content property like `evidence_type`, NOT an outlet
  list). Keep the four-domain heuristic as fallback. **An IFCN/outlet roster is the wrong
  shape** — that is a curated credibility list, the thing invariant #6 exists to forbid.
- **What it does:** flagged items classify reporting/analysis (weight 2) — the
  heuristic's existing rule, promoted to both paths. Carbon Brief would count equal to
  the Guardian, not half. It does NOT outweigh it — see 7-B for that question.
- **Receipts:** `classification_method` must say so (e.g. `factcheck_promotion`), and it
  is already in the signed manifest — forward-only, no backfill.
- **Blast radius:** classifier prompt + schema, `_classify_heuristic` unchanged,
  `tier_breakdown`/`support_structure` displays unchanged (they read tier). The
  `factcheckRating` surface (#14) stays gated on the parser, which remains unwired —
  wiring it is separate, optional work; do not conflate.
- **Hazard:** a false-positive flag promotes an opinion column to weight 2. Mitigate by
  requiring the type to also come out `analysis` (both signals agree) before promotion.
- **Measure first** (COMPARE lesson — firing rates before surfaces): run the classifier
  question over the stored evidence ledger and count how often it fires and on what.
  Pence, minutes, direct.

### Option 7-B: type-modulated weights within tier

A (tier × type) matrix instead of tier-only — e.g. commentary/analysis and
commentary/academic sit above commentary/opinion.

- **Invariant #6 reading:** defensible — it weighs *classes* the pipeline already
  assigns mechanically, not outlets. It is "classify, don't score" applied twice, not a
  credibility number.
- **The arithmetic package (§2.3) binds hardest here.** Commentary/analysis at weight 2
  → two Substack-adjacent analyses badge `supported` under floor 3 — unless the
  `blog_platform_floor` keeps open-platform items at opinion (it does — Hannah Ritchie
  stays weight-min under this option, which is *coherent policy* but must be stated as a
  decision: the floor now sets weight, not just label).
- **Prompt-sensitivity enters the weight path:** `evidence_type` is LLM-assigned, so
  weight becomes prompt-movable in a way tier-only mostly wasn't. The mapper is
  unaffected, but classification drift now moves states. The corpus tolerance-0 pins
  give partial cover; classification is exactly what the 2026-08-25 model migration
  churned.
- **Half-weights or a wider integer scale** (e.g. ×2 everything, modulate ±1) avoid new
  exact-tie points landing on old worked examples; either way `test_state_behaviour_phase_b`
  examples are re-derived by hand.

### Option 7-C: a third axis (rigour/method classification)

Honest, and the only option that gives rigour a channel *without* touching tier or type
semantics — but it is a new classification stage, new manifest field, new UI vocabulary,
and a new drift surface, for a defect currently evidenced by one record. **Not now.**
Park until 7-A + 7-B measurements say the smaller shapes can't carry it.

### Option 7-D: label reframe only

Rename the commentary tier's display (e.g. "Analysis & commentary") without touching
weights. Addresses the *perceived* insult (an editor seeing her outlet filed as
"commentary"), not the 2:1 arithmetic. Cheap; compatible with everything above; on its
own it does not answer the founder's finding.

### Recommendation

**7-A first** (it executes a decision the codebase already made, is content-derived, and
is the exact mechanism that failed on this record), with the firing-rate measurement
before the prompt ships. **7-B only after** measuring type distributions over stored
evidence and with floors re-derived in the same commit. 7-D as a free rider if the
founder wants it. 7-C parked. **None of this is send-week work.**

---

## 4. Item 8 — the corrected premise, then the real gap

### 4.1 What already exists (and works — verified against the live payload)

- **Prose:** `challenged_only` has been a mechanical, prose-level refinement of
  `disputed` since 2026-07-09 (`claim_map_analyzer.py:705-753`) — the orientation line
  on this record is exactly right.
- **Badges:** §4d fix 3 (`29c5149`, 2026-07-21) renders **"− Challenged"** instead of
  "± Disputed" whenever `basis.state_derivation.rule_applied == "all_challenges"` —
  keyed by the shared `isChallengesOnly` (`shared/constants:90`). Both badge components,
  and the PDF template.
- **This record qualifies:** both elements carry `rule_applied: all_challenges` in the
  public payload fetched today, and `basis` is threaded on the surfaces that matter:
  `evidence-views/ElementList` (the `/r/` + dashboard roster), `ClaimSectionCard`,
  `claim-map/element-list`, `UnknownElementCard`.
- **The first-glance summary surface is honest too:** `ClaimSummaryPanel` leads with the
  stance bars (supports/context/challenges = 0/5/13 here, from `e6f9ad4`) and the
  orientation sentence — relationship counts, not state labels.

So the item-8 sentence "the badges a reader scans flatten it" **does not hold for the
roster badges on this record**. The register entry is corrected alongside this review.

### 4.2 Where the flattening is real (complete inventory)

**Surfaces that still read raw `disputed`:**

| Surface | What it does | File |
|---|---|---|
| Dashboard check-card | counts states, colour-dot per bucket (`bg-state-disputed`), `else → unresolved++` | `check-card.tsx:42-60` |
| Recent-checks list | same pattern | `recent-checks-list.tsx` |
| History filters | `has_disputed` / `all_supported` filter logic | `history-content.tsx:102-112` |
| Overview card | `stateCounts.disputed` counter | `ClaimOverviewCard.tsx:27-33` |
| Seeker RelatedClaimCard | badge WITHOUT `basis` prop — renders "± Disputed" even when challenges-only | `RelatedClaimCard.tsx:47` |

**Machine consumers that read the raw value** (the vocabulary criticism proper):

- Agent API / MCP / public JSON: `state: "disputed"` with the receipts *available* in
  `basis` but the headline value flattened.
- `orientation_basis.state_distribution` — **fixed four-key dict**
  (`compute_orientation_basis:823`) in the signed manifest.
- Consensus votes: `element_state_distribution` keyed by state string
  (`consensus.py:144-146`).
- `computed_analytics` Counters; `response_builder.py:432` state logic.
- `support-structure.ts:125` / `support_structure.py:156`: `disputed` → "evidence-rich,
  contested — not thin" (correct for challenges-only too, but by coincidence of wording).

### 4.3 Option 8-A — complete the presentation layer + a derived API field (recommended)

1. **Thread the refinement to the surfaces missing it:** pass `basis` in
   `RelatedClaimCard`; split the dashboard/overview/history aggregates' disputed bucket
   into *challenged* vs *disputed* using the same `isChallengesOnly` helper (data is
   already in every payload). The `else → unresolved++` buckets stay correct because no
   new state value exists.
2. **Consider strengthening the badge/label wording** where counts are stark — e.g.
   "Challenged — none supporting" is already the orientation's own phrasing; a badge
   cannot hold a sentence, but the roster row's `EvidenceQualityNote` idiom could carry
   it. Founder call on wording; no mechanism question.
3. **Expose `challengesOnly: true` as a DERIVED field** in the API/agent/MCP element
   payload — computed on read from `rule_applied`, exactly like the COMPARE collision
   table (computed on read, never stored). **No storage, no migration, no manifest
   impact, historical checks get it for free.**

Cost: small, frontend + response_builder only. Risk: near zero. This is the send-week-
compatible option, though nothing here is send-blocking (TTE/Seymour notes cite the
orientation sentence, which is already honest).

### 4.4 Option 8-B — extend the enum (`challenged`) — DEFER

If the vocabulary itself must one day say it, the containment that makes it survivable:

- **Derived-only, never LLM-emitted.** The mapper prompts embed the state vocabulary
  (`claim_map_analyzer.py:285-327, 553-595`); leave them untouched. The mechanical
  override (`all_challenges` rule) is the only writer of the new value — so prompt
  behaviour, cassettes, and the mapping contract stay still.
- **Name it descriptively.** "Refuted" is a verdict word — it collides with the
  terminology lock ("analysis not verification", "we organise; you decide") and with
  what the evidence actually licenses (13 challenges is a one-sided *retrieved pool*,
  not a proof). "Challenged" is the word the badge already uses.
- **Forward-only, never backfill.** Element `state` is in the signed canonical payload
  (`manifest_signer.py` — read back from stored data on verify, so old checks stay
  green *only* if their stored states are never rewritten).
- **Blast radius to audit, every site** (this is the real cost): the four-key
  `state_distribution` dict (silently drops unknown keys today — a new state would
  vanish from the signed distribution, a receipt-integrity bug); every `=== 'disputed'`
  and every `else`-bucket in §4.2; `support-structure` thin filters both sides
  (parity-locked pair); Seeker `isAssessed`/`isKnown` lists; TS union + backend enum;
  consensus **cross-version vote mixing** — old checks vote `disputed`, new vote
  `challenged` on the same claim hash, so a genuinely stable claim reads unstable until
  votes are normalised (k≥3 makes this rare today, but it is a correctness bug by
  design if unhandled); PDF; goldens (none pin states directly — verified — so unit
  tests are the guard).
- **Symmetry duty (the 2026-08-17 lesson):** the supports side's counterpart
  (`all_supports` vs `supports_dominant_2x`) is currently also un-distinguished — but
  "supported" carries no two-sidedness connotation, so leaving it alone does not
  manufacture balance. That asymmetry-of-connotation argument must be *written into the
  change*, in the same commit, the way the strict-`>` commit documented both sides — not
  assumed silently.

**Recommendation: 8-A now (or at leisure), 8-B only when a consumer actually needs the
vocabulary at the source** — e.g. agent API users making decisions on `state` without
reading `basis`. The derived field in 8-A largely removes that pressure.

---

## 5. Interaction between the two items

Clean separation, verified: `all_challenges` is **count-based and weight-free**, so
every item-8 option is invariant to every item-7 outcome. Conversely, item-7 weight
changes can flip *mixed* elements across the dominance boundary but can never create or
destroy a challenges-only element. The two can be sequenced independently and in either
order. The one shared rule: both must write receipts (`state_derivation` /
`classification_method`) — invariant #5 — and both are manifest-forward-only.

---

## 6. Verification constraints (for whichever build is chosen)

- State derivation is deterministic post-pool → **exhaustive unit rule-tables are the
  real guard** (extend `test_state_behaviour_phase_b.py`; its worked examples must be
  re-derived by hand under any new weights, including new exact-tie points).
- Corpus goldens do not pin element states directly (verified by grep) — corpus movement
  from a weight change shows only indirectly (`element_resolution`). Do not read the
  bench as proof either way; it also cannot verify retrieval (62% churn) — irrelevant
  here since nothing proposed touches retrieval.
- Classifier changes (7-A/7-B) re-key nothing in cassettes (classification is replayed),
  but a classifier PROMPT change is a cassette-key change — budget a bench re-record or
  hold the prompt exactly as the mapping reframe is held. **This is the same trap as the
  held mapping reframe; do not ship a classifier prompt edit casually.**
- Firing-rate measurements (7-A flag, 7-B type distribution) run over stored evidence
  rows — SQL over the ledger/prod, pence and minutes, before any number is chosen.

## 7. Out of scope, noted

`total_search_results: 17` on this full-tier check remains undiagnosed and is NOT
addressed by anything above; one record is not evidence of a systematic shortfall
(~62% churn). Measure with a control arm before concluding anything.
