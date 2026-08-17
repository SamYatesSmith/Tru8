# Quality-first design review — the pre-send fix package

**Date:** 2026-08-14 · **Status:** DESIGN REVIEW (founder-commissioned; sends held for quality by founder decision 2026-08-14, superseding the 2026-08-13 "sends start in the morning" call)
**Scope:** every open pipeline-quality item that touches the outreach records, reviewed **together** so cross-effects are named before any build starts.
**Inputs:** `2026-08-13_assertion_evidence_design.md` (§9–§11), `OUTREACH.md` (three grade tables), `2026-07-14_non_sycophancy_invariant.md` §3a (prior challenge-lane design), plus a same-day code survey of `retrieve.py`, `query_planner.py`, `claim_map_analyzer.py`, `runner.py`, `interested_party.py`, `recital_scope.py`, `corroboration.py`, `support_structure.py`, and the replay-bench cassette layer. File:line cites are working-tree (the held reframe shifts `claim_map_analyzer.py` by +42 below ~line 700 vs HEAD).

---

## 0. The problem, restated precisely

The founder's standard: nothing goes to high-quality potential customers while known systematic distortions are live — because recipients will not only read the curated record, they will **run their own checks** through today's pipeline.

The re-grades (2026-08-13, two rounds) established there are **FOUR issue classes**, not three — the docs name the fourth explicitly but it was absorbed into "implicit-claimant arming" in conversation:

| # | Class | Records hit | One-line mechanism |
|---|-------|-------------|--------------------|
| 1 | **Rebuttal retrieval** | Scotland C+, dairy C− (wildfire A escaped "only because Carbon Brief indexes well") | Every query string in the system derives from the claim/element wording — confirmed by survey: no counter-direction phrasing exists anywhere. Named Substack/small-site rebuttals (Macfarlane 589, Gid M-K) never enter the pool. |
| 2 | **Implicit-claimant arming** | NHS (subjects=`["gp practices"]`, NHS England typed PRODUCT-adjacent, not ORG), dairy (`subjects: []`) | The interested-party + recital gates arm off `key_entities` PERSON/ORG only (`interested_party.claim_subjects`). No claimant in `key_entities` → gates structurally silent. Phase 2's prompt rule covers unanchored *recitals*; the mechanical half stays blind. |
| 3 | **Echo not state-bearing** | NHS residual (1 original / 6 derivatives, all counted as 6 supports) — the reason its Phase-2 re-run stopped at B− | `annotate_derivation_chains` / `annotate_repetition_clusters` measure it; `_derive_element_state_with_authority` reads only `relationship` + `tier` and never consults them. Five copies of one wire story = five weighted supports. Presentation note only. |
| 4 | **Run-variance** | NHS re-run lost the A−'s virtues (TTE critique flipped, uncertainty note vanished) | Inherent model variance. Mitigated procedurally: **a send names a frozen check id**. No build. |

Plus the **§10 smalls** from the assertion-evidence design that interact with the above: the `supports_dominant_2x` `>=` tie boundary (overrode an LLM `disputed` in TRU-018F-44AA), the `all_supports` single-ref floor (e3 `supported` off one BBC ref), print-only `uncertainty`, decompose duplicate/presupposition guards, and the recovery-path stale basis blocks.

**And one latent bug found by this survey, previously unrecorded:** `retrieve.py:2144` calls `seen_urls.add(result.url)` but `seen_urls` is a **dict** (`:2070`) — every BALANCED FRESHNESS FALLBACK query raises `AttributeError`, swallowed by the bare `except` at `:2153-2154`. The zero-results freshness-relaxation path in the planned-query route has been dead since it shipped.

---

## 1. Fix designs, per class

### 1.1 Challenge lane (rebuttal retrieval) — resurrect the 2026-07-14 §3a design

**Prior art exists and was never built:** `2026-07-14_non_sycophancy_invariant.md` §3a specifies `app/utils/query_challenge_augmentation.py` at the same mechanical-augmentation seam as the class/site augmenter, flag `ENABLE_CHALLENGE_QUERIES`, provenance via a parallel lane-tag array. `2026-07-15_decoupling_build_plan.md:265-273` demoted it to a reactive backstop on the bet that "neutrally-phrased two-directional routes yield balanced pools" — **the Scotland/dairy records are the recorded evidence that bet failed for factual claims with named disputants.** The pre-agreed pull-back trigger has fired.

**Design deltas vs the July sketch (from this survey):**

- **Placement inside existing lanes, appended last.** A challenge variant appended at the END of the c0/element lane inherits that lane's per-query sizing and fetch weight automatically (`retrieve.py:2032-2047`) and — critically — does not steal the F1-D3 hedge slot, which keys on **positional index 1** within the lane (`_hedged_query_freshness`, `:410-427`). Inserting anywhere but the end silently kills the hedge. A genuinely new lane id would instead need a third branch in the sizing code, a third weight class in `_allocate_fetch_budget` (`:351-355` is a two-way if), and a decision about the 2:1 round-robin — more machinery for no clear gain. **Recommendation: variant-within-lane, appended last.**
- **Budget:** claim lane is capped at 3 queries *including* site: variants (`_merge_element_plans` slice at `:477`, cap from `runner.py:54`). A challenge query does not fit without either raising `max_queries_per_element` to 4 for the claim lane (full tier only) or displacing a class-site variant. This is a real trade the July design didn't have to face (it predates the lane system). Element lanes (cap 2) have the same squeeze. **Decision needed at build design; provisional: claim lane 3→4, element lanes keep 2 with the challenge variant only on the FIRST element lane** — cost ≤2 extra Serper queries/claim.
- **Dedup attribution trap:** cross-lane dedup is first-writer-wins on `_query_index` (`:2091-2102`), so a challenge-query URL already returned by the claim lane is credited to the claim lane — **the challenge lane will look like it yielded nothing in the histogram.** Yield measurement must ride an accumulating tag (the `_element_ids` pattern, `:2093`), not `_query_index`. Without this, we cannot tell whether the lane works — the exact "zero firings has two causes" trap from F1.
- **Coverage recovery is the sharper case and must not be skipped:** `_element_is_starved` (`runner.py:425-442`) fires on elements with zero supports AND zero challenges, then stage 5.1 re-issues **claim-direction** queries via `retrieve_for_elements` (`retrieve.py:1274-1466`, which bypasses the lane system entirely — hand-built plans, hardcoded `[:2]`, no augmenters, no hedge). A loop that detects one-sidedness and searches the same side again. The challenge treatment must land there too (the July design already flagged this as the follow-up phase; do it in the same phase this time — it is ~the same augmentation call).
- **Phrasing:** mechanical templates off the element/claim text ("criticism of …", "rebuttal …", "'X' disputed", "'X' wrong") per the July design — NOT a planner-prompt edit. This keeps `query_planner.SYSTEM_PROMPT` untouched, which matters for cassette scope (§3) and keeps the change flag-rollbackable (prompts are not flagged).
- **Quick tier:** `QUICK_CONFIG` sets `max_queries_per_element=1` — a challenge variant cannot fit. Leave quick without it, and **declare the omission in `app/core/tier_limitations.py`** or the drift guard fails (`test_tier_limitations.py:39`).
- **Honest limits, stated now:** counter-direction queries raise the *chance* of fetching a named rebuttal; they do not guarantee any specific document surfaces (Serper ranking is not ours). Acceptance is therefore empirical: the two known cases (§5).

### 1.2 Implicit-claimant arming (mechanical half)

Three options surveyed; the gates themselves need **no change** — `claim_subjects` already accepts bare strings, so anything that lands claimant strings in `metadata["subjects"]` (written only at `runner.py:2417`) arms both gates.

| Option | Mechanism | Cost | Verdict |
|--------|-----------|------|---------|
| **(a) `claimant` field in extract** | Add `claimant`/`attributed_to` to `ExtractedClaim` + the OUTPUT FORMAT block; extract LLM already reads the full text and can name "NHS England" where entity typing dropped it. Merge into subjects at `runner.py:197-199`. | Extract prompt change → **extract-stage cassette re-record**; carry-through at ~4 persistence sites. | **Recommended.** It is the honest fix: the claimant is a property of the claim, extracted where the claim is extracted. |
| (b) Seed from `subject_context` | `ExtractedClaim.subject_context` (already persisted, used by retrieval) merged into subjects. Zero prompt/cassette churn. | It yields *topic phrases* ("gp practices"-like), not claimants — would arm the recital gate on generic nouns; needs stop-listing beyond `_STOP_TOKENS` and still fails the dairy class. | Rejected as primary; over-arming a scope gate is worse than under-arming (false context demotions have no receipt-reader who can catch them). |
| (c) Mechanical extractor at gate time | Regex/lexicon in `_armed_scope_gates`. | Violates the one-writer-in-runner pattern (`runner.py:165-171`) — the exact reader-without-writer hazard the codebase spent July learning. Nothing to anchor on for dairy anyway. | Rejected. |

**Structural honesty about the dairy class:** a claim with NO person/org claimant ("full-fat dairy causes no weight gain" — sources report a *finding*) cannot be handled by anchored gates at all, and the survey confirms `recital_scope` rejects unanchored matching by design (`:172-173`). The dairy record's fix is class 1 (fetch the teardown) + class 3 (discount the 9 echoes), **not** class 2. Option (a) fixes NHS-class; dairy-class is out of its reach and that is fine.

### 1.3 Echo state-bearing — two shapes, decision required

The survey confirms the state function never reads derivation data, and maps two shapes:

- **Shape A — weight discount in `_ref_weight`:** derivative items weigh less/0. Simple, but: derivative membership lives pool-wide on the *primary* (`derivation_chain`), so the union must be computed before state (shared helper); it silently perturbs `supports_dominant_2x` / grounds-floor arithmetic; **no receipt** — it is a hidden discount, brushing invariant #5, and arguably a credibility score in disguise (invariant #6).
- **Shape B — sixth scope gate `echo_scope`:** a directional ref whose evidence is a derivative of an original **already counted on the same side of the same element** is re-labelled `context` with a receipt (`{evidence_id, was, original_id}`). Fits the codebase's established idiom (re-label + receipt + flag + symmetric), and the reader sees exactly why. Costs: `_IndexedEvidence` must carry pool-level derivative membership (three `_index_evidence` build sites — and the **recovery index covers `new_evidence` only** (`:2966`), so the gate is blind to chains spanning main-pass + recovery evidence there: fires less, safe direction); the gate's `fires` signature is per-item, but "original already counted" is a per-element set property — needs either the element's refs passed in or an index-time precomputation; and the presentation note (`support_structure.side_quality_note`) must be re-aligned or it double-reports a weakness the state has already absorbed.
- **Either shape must keep independent corroboration meaningful:** the FIRST derivative when the original is absent from the element's refs is the only carrier of that content and should stay directional; only *redundant* copies scope down. (Shape B expresses this naturally: "original already counted" is the condition.)

**Recommendation: Shape B.** It is more work, but every distortion fix this codebase has shipped is a re-label-with-receipt, and the NHS record's failure is precisely a receipt-less inflation. A silent weight discount would fix the number while abandoning the principle that makes the product defensible to exactly the customers we're courting.

**Symmetry note (invariant #7):** echo_scope must scope a challenge-side echo chain exactly as readily — e.g. five outlets reciting one critical report.

### 1.4 State-derivation smalls (ship together, one golden update)

All three live in `_derive_element_state_with_authority` and perturb the same numbers; shipping them separately triples golden churn and destroys attribution.

1. **`>=` → `>` on `supports_dominant_2x` (`:1029`)** — AND on `challenges_dominant_2x` (`:1032`), same commit: changing one side alone builds the asymmetric mechanism invariant #7 forbids. A tie then falls to `close_split` → `disputed`, which is the honest reading of a tie. Known breakage: `test_coverage_recovery.py:1443-1456` pins a 2-vs-1 all-weight-1 tie as `supported` — that test's expectation changes *by design*. Also consider §10's stronger form — never override `llm_state == disputed` downward — recorded as a follow-on decision, not bundled (it changes the mechanical/LLM authority balance and deserves its own fixture).
2. **`all_supports` minimum-evidence floor** — the mechanism exists: `_state_floor_for` already threads a floor into all three call sites; generalise it to return a non-zero floor for factual claims (config sibling of `GROUNDS_MIN_WEIGHTED_SUPPORT`, distinct `rule_applied` string, e.g. `support_floor`). Provisional floor: 2 (one reporting ref no longer suffices; one primary w3 still does — defensible: a single primary source *is* the record for many true claims). ⚠️ Must stay **weight-based, not basis-reading**: recovery never recomputes basis (`:2992-2993`), so a basis-reading floor reads stale structure there — the same §10 staleness defect, which this phase should ALSO fix (recompute basis in the recovery merge, or explicitly re-derive the three breakdown blocks).
3. **Print-only `uncertainty`** — smallest honest step: when the mapper's element-level `uncertainty` is non-empty AND the derived state is `supported`, append it to the state caveat channel (already exists, F3) so it travels to every surface instead of print. Making it state-bearing outright is a bigger authority question — defer with §10's override question.
4. **Decompose guards (presupposition/near-duplicate elements)** — recorded, but **deliberately out of this package**: it is a decompose-prompt change (cassette re-record, held-reframe adjacency) with diffuse benefit. Park unless re-grades show it blocking a grade.

### 1.5 Run-variance — no build

Procedural rule stands: sends name a frozen check id. The one cheap hardening: the re-grade protocol (§5) grades a NAMED new check per record and compares against the named original — never "latest run".

---

## 2. Interaction map (the reason this review exists)

**I-1. The three state-derivation changes and the echo gate all move the same element states.** Echo-as-gate changes ref sets *before* counting; floor and `>` change the rules *after* counting. Shipped separately they would each move corpus goldens and re-grades, making attribution impossible (the 2026-08-11 lesson: unattributed drift blocked work for a week). → Phase them as ONE state-behaviour phase with one golden update (§4 Phase B), gates flag-gated, mutation-checked per the TRU-C1A0-0005 lesson.

**I-2. The challenge lane REDUCES the pressure on the state fixes but replaces neither.** More fetched challenges → fewer `all_supports` elements organically. But single-ref `supported` and echo inflation persist wherever the other side genuinely publishes little. Both are needed; the lane's arrival will however *mask* part of the state fixes' measured effect — one more reason state fixes land and are baselined FIRST (their effect is measured on unchanged pools via replay).

**I-3. Cassette economics dictate the ordering.** From the survey, exactly:
- Replay-CLEAN: state/gate/mapping-logic changes (goldens move, attributably); flag-gated retrieval lane with flag OFF.
- Forces RE-RECORD: any new query string issued (challenge lane ON), any extract/planner/mapping prompt edit (claimant field; recital rule was this), results-per-query or freshness changes.
- The design doc's §8 protocol stands: **sequential, one re-record per query/prompt-affecting phase** — "prompt-change effects on this pipeline have surprised us every single time". Two re-records are owed by this package (Phase C claimant-extract, Phase D challenge lane), ~$0.25 + bench time each.

**I-4. The held reframe.** It edits the three mapping prompts (MODALITY / NOT-A-SCEPTICISM-DIAL bullets + "supports as stated" redefinition). Nothing in this package edits mapping-prompt text (echo is a gate; recital rule already shipped), so **no collision** — but the patch-out/patch-in commit protocol and reframe-stashed bench runs continue for every phase. If the founder ships the reframe mid-package, it must be its own re-record between phases, never combined.

**I-5. New-gate parity checklist is a trap with three teeth** (from the survey): a sixth gate must be (i) appended in `_armed_scope_gates` — order matters, the `break` means position is behaviour; (ii) **added to `_SCOPE_RECEIPT_KEYS`** — omit this and the completion-path snapshot silently drops its receipts on both merge paths while the main pass looks fine (the exact class of the `d39b65d` bug, one layer up); (iii) given a flag. Echo additionally extends `_IndexedEvidence` at all three build sites.

**I-6. Gate/prompt observability is already degrading and this package makes it worse.** The bench parses ONLY `[TEMPORAL SCOPE]` log lines (`capture.py:145-160`); the other four gates — and the new ones — have receipts but no bench signal. And prompt-rule recitals leave NO trace distinguishable from ordinary context, so as prompts improve, gate counts drop, which reads identically to "gate broke". → Phase A adds log-line parsers for all gates + a corpus assertion per new gate (mutation-checked), and the challenge lane gets accumulating yield tags (I-7).

**I-7. Challenge-lane yield is unmeasurable without the dedup fix** (first-writer `_query_index` credits shared URLs to the claim lane). The provenance tag ships IN the lane commit, not after — else we repeat the F1 "never fired live" ambiguity at 45p a probe.

**I-8. Fixing the `seen_urls` bug changes replay behaviour.** Once fixed, the freshness-fallback path can issue queries that no cassette holds → drift on any corpus claim with a zero-result query. Fix it at the START of a re-record phase (Phase C), not in the replay-clean phase.

**I-9. Quick tier + tier_limitations drift guard** — challenge lane absent from quick must be declared (`tier_limitations.py`) or CI fails; conversely declaring it advertises the limitation honestly in `_meta.limitations`, which is correct.

**I-10. Order within `_armed_scope_gates` for echo:** LAST (after recital). Scope-mismatch gates (can this item speak here at all?) should own a ref before independence gates (is it redundant?) — a temporal-scoped whitehouse.gov echo should read `temporal_scope`, the more informative receipt. The `break` makes this choice permanent per ref; changing it later re-attributes existing receipts.

---

## 3. What this package deliberately does NOT do

- No outlet scoring, no tier changes (invariant #6; design §2's PolitiFact observation stays resolved from the demotion side).
- No forced route symmetry — the challenge lane *seeks* the other side; mapping stays free to find nothing (invariant #7 cuts both ways).
- No decompose-prompt work (§1.4.4), no `llm_state`-authority change, no run-variance mechanism.
- No touching the held reframe.
- Does not promise a specific named rebuttal will be fetched — acceptance measures the two known cases and the grade movement, not a guarantee.

---

## 4. Proposed sequence

Each phase: design-confirm → build behind flags → tests → bench (reframe stashed) → live acceptance where stated → OPEN_WORK update. Spends flagged to founder before incurring.

| Phase | Content | Cassettes | Acceptance |
|-------|---------|-----------|------------|
| **A. Observability** | Bench parsers for all five gates (+ future two); corpus assertions for IP/recital receipts on the Trump-adjacent goldens, mutation-checked | Replay-clean | Bench green at current baseline 143/13/5; assertions fail with flags off |
| **B. State behaviour** (one golden update) | `>` both sides · factual support floor via `_state_floor_for` · recovery basis-staleness fix · uncertainty→caveat channel · **echo_scope gate (Shape B)** with `_SCOPE_RECEIPT_KEYS` + parity per I-5 | Replay-clean; goldens move ONCE, attributed | Corpus diff reviewed line-by-line; NHS-class fixture: 1-original/6-derivative element no longer `supported` on echoes alone; Trump fixture regression: still `disputed` on crux |
| **C. Claimant arming** | `claimant` field in extract + merge into subjects; fix `seen_urls` bug same phase | **Re-record #1** | NHS-type claim arms gates (`subjects` contains "nhs england"); dairy still `[]` (expected); Trump regression |
| **D. Challenge lane** | `query_challenge_augmentation.py` + append-last variants (claim lane 3→4) + coverage-recovery counter-frame + yield tags + tier_limitations declaration | **Re-record #2** | Lane yield non-zero in histogram on live checks; Scotland: Macfarlane 589 in pool; dairy: Gid M-K teardown in pool (if still unfetched → investigate ranking, don't force) |
| **E. Re-grade + send** | Re-run wildfire/NHS/Scotland/dairy full-tier (~6p), grade against originals, update send set (named ids), THEN the morning-sequence sends | — | Target: NHS ≥ A− on a NEW record; Scotland ≥ B (challenges present); dairy re-assessed; wildfire holds A |

Estimated spend: 2 bench re-records (~$0.50), ~6–10 live checks across acceptance + re-grades (~10–15p), each flagged before running.

---

## 5. Decisions required from the founder before Phase B

1. **Echo shape:** Shape B (gate + receipts) recommended — confirm, or choose Shape A (silent discount).
2. **Tie boundary:** `>` on BOTH dominant rules (symmetric) — confirm; the "never override LLM `disputed`" stronger form is parked as a separate future decision.
3. **Support floor value:** provisional 2 (one primary passes, one reporting/commentary alone does not) — confirm or set.
4. **Challenge-lane budget:** claim lane 3→4 queries (full tier), first element lane gets the variant — confirm (cost ≤2 Serper queries/claim).
5. **Claimant extraction via extract prompt** (re-record #1 accepted) — confirm.
6. **Sequence + spend envelope** (§4) — approve.
