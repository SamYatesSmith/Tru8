# Architecture review: why the faults persist, and what to change (2026-10-06)

Read-only review requested by the founder after a week of patches without an A− gain. Four independent mappings fed it:
- **Correction layers:** the full mapping→state path, traced in code.
- **Default-off features:** the seven built-but-off quality features, plus a dead-code scan.
- **Independence:** every mechanism that judges whether a source is independent.
- **Fault ranking:** fault classes across all 60 blind grades (24 Sep, 28 Sep, 30 Sep, 6 Oct).

No code changed.

## 1. The answer in brief
1. **The pipeline corrects the model after the fact, layer upon layer.** There are **10 corrective layers** between the first mapping call and the final state, including a **13-gate** driver (CLAUDE.md lists 6–8). Most faults found in the last two months were handled by adding a layer or a gate, not by fixing the judgement that produced them. Some layers now exist only to manage others: echo restore exists to undo a relationship-review demotion that orphans an echo-scoped copy.
2. **"Is this source independent?" is answered by 14 separate mechanisms.** Each has its own identity signal and a narrow trigger. None asks the whole question, and state derivation sums every ref as if independent. **This is the one fault class that is not falling** (11 → 7 → 11 fails across rounds, and 3 of 3 records on 6 Oct). It is also the cheapest route from 1 A− to 4.
3. **The code is carrying weight it does not use.** Seven quality features are built and off. Of these:
   - three can be deleted;
   - three, the echo trio, only work together;
   - one, the gap note, is nearly ready but has a newly found false positive.

   There are also roughly 1,500 lines of dead modules and functions.
4. **Progress was real but measured badly.** Total fails fell 115 → 82 → 59 across the three full rounds. Six classes are falling or gone. Single-record re-runs move a notch from pool churn (about 60% of URLs change per run) and grader judgement alone. Fixes were chosen from a few records and judged by re-running them, so real gains looked like none.

## 2. Evidence

### 2.1 The correction layers, in run order (full tier)
```
CLASSIFY (+ originator review: lowers primary → reporting; feeds weights)
1  mapping call [model] → per element: validate → 13 GATES (3 sub-passes) → basis → STATE (+floor)
2  completion census [model] → GATES on merged refs → basis → STATE
3  passage review [model, OFF] → GATES (passage text) → STATE
4  relationship review run 1 [model, supports only] → demote → STATE
5  reconcile echoes → restore copies → review run 2 → STATE        (no-op while echo off)
6  apply_orientation
7  COVERAGE RECOVERY: retrieve → classify (no originator review) → recovery map [model]
   → GATES (new-evidence index only) → STATE (target elements only) → review run 3 (+run 4) → orientation
```
- **Gates (default on unless marked):** temporal, readable_text, jurisdiction, measure, date_scope, range_period, figure_scope, interested_party, recital, absence_of_evidence, same_study, echo (**off**), fact_applicability (**off**).
- **State derivation runs from 6 call sites**, and the basis is rebuilt up to 5 times per element.
- **The "save receipts → rebuild basis → restore receipts → re-derive" sequence is copied in 5 places.** Only 3 of them use the shared merge helper.
- **Largest functions:**

  | Function | Lines |
  |---|---|
  | `run_pipeline_phase2` | 1,856 |
  | `_armed_scope_gates` | 671 |
  | `_review_run` | 391 |
  | `_complete_unmapped_sources` | 277 |
  | `_derive_element_state_with_authority` | 249 |

  `claim_map_analyzer.py` is 4,231 lines in total.

**Defects the mapping found (not yet graded, but real):**
- **D1, stale states after recovery.** Coverage recovery adds refs to non-target elements and rebuilds their basis, but keeps their old state. The counts on the card and the badge can disagree.
- **D2, a narrow gate index in recovery.** Recovery gates against an index of *new* evidence only. So same-study cannot match a recovery copy to a main-pass original.
- **D3, unreviewed tiers in recovery.** Recovery items skip the originator review, so they keep primary tiers that the main pass would have lowered.
- **D4, `llm_state` dropped in three places.** It is preserved only in completion; relationship review, echo restore and passage review drop it.
- **D5, a timeout can leave recovery half-done.** Target states are rewritten, orientation is skipped, and refs can point at items never added to the pool. This was inferred from the code, not observed.

**Logic duplicated between a gate and the model review:**
- period/place/measure: the gates vs the review prompt;
- figures: `figure_scope` vs the review's figure guard;
- absence of evidence: the gate vs a prompt rule;
- count-once: same_study vs echo;
- self-interest: interested_party vs recital.

### 2.2 Independence: 14 mechanisms, no shared identity model

| Mechanism | Signal | Effect |
|---|---|---|
| Copy dedup (pre-fetch) | URL key, slug, title | drop |
| UrlKeySet | canonical URL | drop |
| Deduplicator | text similarity ≥ 0.95 | drop (rewrites never reach it) |
| Corroboration groups | ownership + similarity | note (runs before tiers exist) |
| Echo stack (off) | detector + model + cue | context relabel / note |
| F4 repetition | shingles, clusters with no primary | note |
| Same-study gate | DOI/PMID in URL or snippet | context relabel (**fired 0 times on the bench**) |
| Interested-party, recital | host / attribution phrasing | context relabel |
| Originator review | model role + cue | tier lowered |
| Tier weights + floors | none: every ref summed as independent | state |
| Relationship review | model applicability | demote |
| Source concentration | domain | description only |
| same_domain_as_source | domain | tag nobody reads |

**Why nothing caught the graded failures:**
- **#8**, press-release rewrites: different hosts and titles; under the 0.95 similarity cut; echo off; F4 skips clusters that contain a primary; no DOI.
- **#13**, a GRL study plus two write-ups: the DOI appears only in the study's own URL; echo off. Even with echo on, the cues name the journal and institutions, not the host.

**Hazard:** scoping an original as interested party *releases* its copies, because echo only fires when the original is still counted.

### 2.3 Fault classes, ranked (blind grades, fail counts per round)

| Class | 24 Sep | 28 Sep | 30 Sep | 6 Oct (3) | Trend |
|---|---|---|---|---|---|
| Source independence | 11 | 7 | 11 | 3 | **flat** |
| Surface warts (S6) | 15 | 13 | 9 | 1 | falling |
| Off-topic rows | 15 | 13 | 7 | 1 | falling |
| Original not retrieved or disclosed (H3) | 6 | 7 | 6 | 0 | flat |
| Wrong Notables headline | 11 | 12 | 6 | n/a | falling |
| Wrong directional ref | 14 | 6 | 5 | 0 | falling, then flat |
| Wrong tier/type | 10 | 10 | 4 | 0 | falling |
| Card reason missing or false | 11 | 1 | 2 | 1 | fell sharply |
| Gate demotes the authority | 4 | 3 | 0 | 0 | gone |
| Headline contradicts badges | 3 | 0 | 0 | 0 | gone |

**Counterfactual on 30 Sep** (baseline 1 A−):
- fix independence alone → **4**;
- plus off-topic rows → **6**;
- plus H3 (original present or disclosed) → **9**;
- plus wrong directional refs → **12**;
- plus wrong tier → **15**.

**Variance:** #16 and #17 are the same input, yet they graded B and B− on 30 Sep (part run variance, part grader). H3 on #1 flipped on the same facts. **Treat one-notch moves on single records as noise; judge by class counts across all records.**

### 2.4 The seven default-off features

| Feature | Approx. prod LoC | Evidence | Recommendation |
|---|---|---|---|
| Cited-source lane (search half) | ~550 | retrieval 9.5% vs 60% | **Delete** the search half; keep the names call |
| Cited-source gap note | ~600 + web | 4/4 correct live; **false positive on #13**: a journal hosted on a publisher site was listed "missing" | **Finish:** fix the publisher-host blind spot, then switch on |
| Echo link confirmation | ~1,030 | precision clean (0/137), recall 27% | **Merge** the three flags into one |
| Derivation chains (note) | ~60 (+80 dead) | reads confirmation only | Merge (as above) |
| Echo scope gate | ~150 | scoped nothing on live checks | Superseded by §3 Phase 1; delete when that lands |
| Passage mapping | ~620 + web + 867 eval | "NOT ready" (Bank Rate, JWST); parts already moved to default | **Delete** (first confirm no production record carries `citations`) |
| Structured extraction | ~120 | 1 of 5 pages gained text | **Delete** |

**Other dead code:**
- **Unused modules:** `factcheck_parser.py` (474), `source_monitor.py` (226).
- **Uncalled functions:**
  - `_filter_results_by_relevance` (121);
  - the push and email notification senders;
  - three embedding helpers;
  - about ten cache helpers;
  - the copy-dedup shadow path;
  - the retrieve-time chain step whose output `clear_links` deletes.

## 3. Recommended plan
Each phase needs founder approval before it starts.

**Phase 0: clean up (no spend, low risk, about a day).**
- Delete passage mapping, structured extraction, the lane's search half, and the dead modules and functions listed in §2.4.
- Merge the echo trio into one flag.
- Fix the gap note's publisher-host blind spot.
- Correct CLAUDE.md (13 gates).
- Gate: unit suite and flags-off bench equal before and after; verified by an independent verifier.

**Phase 1: one Independence component (difficulty ≥ 3: design → review → offline eval → build).**
- **Question:** "On each side of each element, which refs are distinct observations?"
- **Evidence, strongest first:** URL identity; persistent IDs (DOI/PMID) read from the URL and the **full text**; verbatim copied runs; wire and press-release markers; model-confirmed attribution (any tier of original; the cue may name the journal or institution); title match.
- **Mechanics:** a typed union-find over the pool. State derivation sums **clusters**, not refs.
- **Replaces:** same_study, echo, the corroboration groups, F4's unanchored case and the unused `is_syndicated` field. Pre-fetch dedup calls the same identity function.
- **Must hold:** treats supports and challenges symmetrically; fails closed (unclear → independent); a copy of a scoped original inherits the scoping; receipts name the edge.
- **Eval:** offline, on stored checks and held-out labels; then measured as class counts across all 19 records, with a control arm.

**Phase 2: correctness of the existing layers (no new features).**
- Fix D1–D5 (recovery states, recovery index, recovery tiers, `llm_state`, half-done recovery).
- Replace the 5 copies of the receipt/basis/state sequence with one function.

**Phase 3: reduce overlap.**
- Decide whether the relationship review or the gates own period/place/measure/figure checks, and remove the other's duplicate.
- Split `_armed_scope_gates` into one module per gate behind a registry, so order and ownership are explicit rather than implied.

**Then:** off-topic rows (S5) and H3. H3's hard bucket is mostly "the pool names the original but did not fetch it". The search lane failed, so this needs a different approach (fetch by name from the citing page's own outbound link). Design only after Phase 1.

**Measurement change for all phases:**
- No more judging by single-record re-runs.
- Each change is measured as class counts over all 19 records (one grading round after each phase), with a control arm for anything retrieval-touching.

## 4. What I got wrong
- **I chose fixes from a few records' symptoms and measured them by re-running those records.** That added narrow layers and hid real gains in noise. The founder's standing rule ([general quality, not the outreach set]) says to use the records to find classes and to judge on held-out claims. I drifted from it.
- **I added correction layers without stepping back to the architecture.** This review is the step back that should have come earlier.
