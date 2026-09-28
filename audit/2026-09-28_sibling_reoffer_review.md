# Sibling re-offer: independent design review

**Date:** 2026-09-28. **Reviews:** `audit/2026-09-28_sibling_reoffer_design.md` (DRAFT).
**Method:** read-only. The code was read at `b7a3d8f`, and the 18 stored re-run payloads (`scratchpad/rerun/r<n>.json`) were re-analysed with local scripts. No model calls, no checks.

## Verdict: **APPROVE WITH CHANGES**

The idea is right: add by model, on one element, with the gates re-run, and never copy by rule. The seam is close to right. As written, though, the design has problems in four places:
- **Two production hazards.** An exception wipes the whole claim's mapping. A timeout can fail the whole check.
- **One model-routing error.** The pass would run on the lite model that the codebase itself records as breaching #7 on thin support.
- **Three receipt and display defects.** One of them is already live in completion.
- **An eval that cannot gate the flag.** It measures the wrong input, has almost no challenge cases, and has no held-out set.

All of these can be fixed without changing the idea. Do the required changes before the paid eval, not after.

---

## Findings

### F1. Root cause: right for #1 and #15, only partly right for #12
- **#1 e3: confirmed.** Eight sibling-directional items state Harborne's £36m outright and are filed only on e1 or e2. Examples: `ev-e3b15cecbc81` "Christopher Harborne has given £36m to Reform UK", `ev-86a53193d1b1`, `ev-daae2922e638`, `ev-c0b5e2e9df6a`, `ev-af15c09aeeb4`. e3 has only Al Jazeera (ws=2, rule `support_floor`). Recovery did not fire (0 `ev-rec` items). 1/3 is not above 40%, and e3 is not starved (`runner.py:2517-2519`, `_element_is_starved` at `:395-411`).
- **#15 e2: confirmed.** Every "29%" source is on e1 or e3 (`ev-4c7b95336d3d`, `ev-ede3290cd1a3`, `ev-77d1ec69fcc0`, …). e2 has one commentary support (ws=1, `support_floor`). Recovery did not fire (0 items).
  - Caveat: e2 ("the number … **changed**") is a trivially-true prerequisite element. The 2026-09-09 decomposition rule was meant to prevent those. The mapper filing "29%" under the causal e3 is the SINGLE rule doing its job, so part of the fault is upstream.
- **#12 e3: partly wrong.** The SINGLE rule did not bind here: the mapper put Statista (`ev-15c97bdc6e6e`) on **two** elements (e1 and e2). It left e3 off by judgement. e3's own mapper uncertainty says: "Evidence provides historical records … but lacks a direct comparative statement." e3 is a *derived comparison* (Build D's restated element). Statista lists 427.49 and 322.89 but never states the comparison.
  - A prompt that returns only a source "whose own text **states** this element's specific assertion" should decline Statista again.
  - A prompt that accepts it is doing the mapper arithmetic the figure gate was built to stop (`claim_map_analyzer.py:2871-2874`: "the mapper did the arithmetic").
  - So #12 must not be a **mandatory** positive in the pass bar (see F13).
- **Recovery's pool claim:** confirmed. `map_evidence_to_specific_elements` maps only `new_evidence` (`:3763-3774`). Its gate index covers new evidence only (`:3804`).

### F2. Hazard: an exception in the pass wipes the claim's whole mapping
`map_evidence_to_elements` awaits `_complete_unmapped_evidence` inside the `try` whose `except` calls `self._fallback_mapping(claim_map)` (`claim_map_analyzer.py:1819-1852`). That sets every element to `unresolved` with no refs.
- Every single-claim check reaches this path (`map_evidence_batch` → `len(with_evidence) == 1` → `:1999-2002`). So do grounds claims and batch retries.
- The design says "on failure: no change", but covers only a failed call. A `KeyError` in the merge (Enum vs str relationship, a missing basis key) would blank the whole report.
- `_complete_unmapped_sources` protects itself with its own try/except (`:3581`, `:3713`). The pass needs the same.

### F3. Hazard: time budgets
- **Single-claim path:** there is no inner timeout. The runner wraps the whole mapping stage in `analyze_timeout = 120` and **fails the check** on breach (`runner.py:2435-2465`, `PipelineError`). Worst case today is mapping 55+5 s, then completion 30+5 s, each followed by an OpenAI fallback. Adding another Google timeout plus an OpenAI fallback can cross 120 s.
- **Batch path (article checks):** completion runs under `_COMPLETION_TIMEOUT = 25` s (`:2088-2106`). A pass placed inside `_complete_unmapped_evidence` shares that 25 s. It would be cancelled silently on most multi-claim checks: completion alone plus a 20 s call leaves nothing. The code's comment says the same about the relationship review.
- **Latency evidence:** "per-call timeout 20 s" does not match any code path. `_call_llm` has no per-call timeout parameter: non-mapping labels get `self.timeout = 30` and mapping labels get 55. The only measurement on this model, M1 round 2 on gemini-3.7-flash, had p90 25.0 s and 11/33 timeouts (`2026-09-24_a_minus_mapping_design.md:236`).

### F4. Model routing: the pass would run on the lite model that is documented to breach #7
`_call_llm` sends only `label in ("mapping", "batch_mapping")` to `MAPPING_GOOGLE_MODEL` (`:2190`, `:2213-2215`). A new label `sibling_reoffer` would run on `GOOGLE_LLM_MODEL` (default `gemini-3.5-flash-lite`, `config.py:117-118`). It would also get no thinking config and no response schema.
- `config.py:675-692` records that 3.5-flash-lite labels a recital of the claim as **SUPPORTS 10/10**. It adds that this "only surfaces when the support side is thin — which is exactly when it does the most damage". Thin-support elements are exactly the pass's target set.
- The design's "Model: the mapping model" therefore needs a code change at `:2190`, pinned by a test on the request.
- Separately, the design and the brief say "flash" or "gemini-2.5-flash". Production maps on **gemini-3.7-flash**: all 18 payloads have `metadata.mappingModel = gemini-3.7-flash`.

### F5. The OpenAI fallback is an unevaluated state-changing model
On a Google timeout or exception, `_call_llm` falls back to OpenAI `ANALYZER_MODEL` (`:2286-2302`). Its additions would change states with zero eval coverage, and the prod OpenAI key is unverified (CLAUDE.md). This pass is optional, so it should **fail closed**: on Google failure, make no change and record `status: failed`. The fallback should never answer for it.

### F6. The receipt `basis.sibling_reoffer` is destroyed by three later rebuilds
Each of these rebuilds `elem["basis"]` from scratch and carries forward only `_SCOPE_RECEIPT_KEYS` (plus `state_derivation` in recovery):
- coverage recovery: `claim_map_analyzer.py:3850-3867`
- relationship review: `relationship_scope_review.py:579-585`
- passage review: `passage_mapping.py:372-381`

Recovery runs on T whenever T is still unresolved or starved after the pass, and on **any** element that receives a recovery ref (`:3833`). So a T that gained refs loses the record of where they came from (invariant #5).
- Do not add `sibling_reoffer` to `_SCOPE_RECEIPT_KEYS`: `_merge_scope_receipts` assumes the `scoped` / `scoped_count` shape.
- Either keep the receipt at claim level (`claim_map.metadata.sibling_reoffer[element_id]`, as `passage_review` does), or add a separate carried-keys tuple honoured by all three rebuilds.

### F7. The completion seam the design copies has a live `llm_state` bug
Completion rebuilds the basis (`:3655`) and **then** reads `prior_basis = elem["basis"].get("state_derivation")` (`:3663-3669`). `_compute_element_basis` never writes `state_derivation` (`:1415-1491`), so `llm_state` is always dropped when completion adds a ref.
- Payload evidence: #12 e2 and #10 e1 both have `llm_state: None`, next to completion-added refs.
- Design step 6 says "Preserve the prior `llm_state`" and "the same seam as completion". Copying the seam copies the bug.
- Fix: capture the prior derivation before the rebuild, as recovery does at `:3856`. Fix completion in the same commit.

### F8. A stale mapper `uncertainty` would contradict a newly supported badge on 8 of 13 targets
- Since 2026-08-17, a `supported` element's `uncertainty` is **appended to the caveat** (`:1274-1276`), and the caveat reaches every surface.
- 8 of the 13 targets carry a main-pass uncertainty that becomes false once the pass adds support. Examples:
  - #12 e3: "…lacks a direct comparative statement"
  - #10 e2: "No provided evidence contains the specific figure of 1.2 per cent…"
  - #2 e2 and e3: "No provided evidence mentions…"
- If a target turns `supported`, the page would show SUPPORTED with a caveat saying there is no evidence. That is the #10 "that is false" defect again (`mapping_failures_review.md:13`).
- `scope_reach` is stale in the same way and feeds the F3-B2 reach caveat (`:1226-1247`).
- The pass must either return a fresh `uncertainty` and `scope_caveat` for T, or clear both on a state change and keep the old values in the receipt.

### F9. A gated addition flips `unresolved` to `contextual` and hides the element from the Seeker
Design step 4 appends the model's refs, then gates them. A gated addition stays on T as `context`. On an element with no other context ref, rule `no_evidence` becomes `context_only`, and the state goes `unresolved` → `contextual`.
- `contextual` is excluded from the Seeker's gap count (`SeekerView.tsx` rule, cited at `:1167-1171`). It also changes the recovery trigger (`_element_is_starved`).
- So a **wrong** addition that the gates correctly catch still changes the state class. The design wanted "no context output", and this path defeats it.
- Fix: stage the additions on a copy, gate them, and append only the survivors. Record the gated ones in the receipt with the gate's entry (invariant #5 is met by the receipt). The bar "zero wrong additions that change a state" must count this flip too.
- Also: `_validate_evidence_refs` accepts `context` (`:3381`, `_VALID_RELATIONSHIPS`). The pass must reject `context` itself, or better, enforce it with a response schema (enum `supports|challenges`, ids restricted to T's candidates). M1 lost 25% of its outputs as invalid.

### F10. Invariant #7: where the pool tilts, and what the eval cannot see
- **Pool direction.** On the 13 targets, the sibling-directional candidates are **56 supports and 6 challenges**. The pool follows the siblings' direction. The "reported separately for supports and challenges" bar therefore has about 6 challenge cases, which gives it no power in that direction.
- **Floor-clearing machine.** 6 of 13 targets are `support_floor` elements (#1 e3, #2 e2, #2 e3, #5 e2, #7 e2, #15 e2). They already have ≥1 support and 0 challenges. One more reporting support clears the floor: 1+2 = 3 (`_state_floor_for`, `:1009-1038`).
  - The additions are clustered. #1 e3's 12 candidates sit in 5 `corroborationGroupId`s. #15 e2's 10 sit in 3, and nearly all recite one unpublished NHS England figure that the OSR ruled non-compliant (`ev-319518c67f5c`).
  - The echo gate needs `derivation_chain` (`:1618`). That field is **absent from the stored payloads**, so the offline replay cannot see echo demotions.
- **Inherited family-C errors.** The pool carries the main mapper's wrong directional refs:
  - #10 e2's candidates are exactly the graders' family-C wrong supports (Franklin Templeton `ev-5a3f43af9b67`, ECB `ev-rec-e2_5_d84422a2`).
  - #12 e3's candidates include Smithsonian's Keeling "~310 ppm" (a family-C wrong support on e2).
  - The pass can copy a known-wrong ref onto a second element, which doubles the damage.
- **The figure gate is SUPPORTS-only** (`:2876-2877`, `:2902`) and depends on the ref's `reasoning` naming the figure (`rests_on_a_figure`, `:2903`).
  - The design's "reasoning citing the figure **or entity**" lets the model cite an entity and slip past the figure gate.
  - A wrong **challenge** built from a nearby figure is not figure-gated. Example on #1 e3: `ev-b28b497407cc` "Harborne gave £9m last year" filed against "£36m".
  - "All gates re-run, symmetric" overstates it.
- **Target selection.** Only `unresolved`/`contextual` elements are targeted. So a supported element never gains its missed sibling-filed challenges (#15 e1, #18 e2/e3, #19 e1 have them), and a disputed element never gains its missed supports (#13 e2, #19 e2/e3). The two omissions mirror each other, so this is defensible for v1. The design should say so rather than claim blanket symmetry.
- **What the eval needs** to measure #7 given this tilt:
  - A **falsified-twin arm**: for each target, perturb T's figure, date or entity (e.g. "Harborne contributed £40 million"), offer the same candidates, and require **zero surviving `supports`**.
  - A recital probe on this label, in the style of `recital_repeat_probe.py`.
- **Prompt framing.**
  - "These sources were already matched to OTHER parts… A source can bear on more than one part" invites additions. Pair it with "most candidates will not state this element; returning none is expected".
  - Never show the sibling relationship or reasoning, since that primes direction.
  - Do show the sibling descriptions, for disambiguation only. Without them, a source stating e1 ("£72m in one weekend") is easier to accept for a near-restated T.

### F11. Placement: roughly right, but underspecified, and it interacts with recovery
- **Gates at the seam.** Main-pass refs are already gated in `_parse_mapping_response` (`:2562`), and completion's additions in `:3643-3658`. So running `_apply_scope_gates` over T again is sound:
  - Already-scoped refs are `context` and skipped (`:3305`).
  - The deterministic gates re-pass survivors without new receipts.
  - `_merge_scope_receipts` stays disjoint.
  - "One gate owns a ref" holds, because the driver's `break` is untouched.
- **Set-dependent gates.** Same-study (`:3138-3159`, tie-break on tier then ref position) and echo (`:3207-3221`) can now demote a **pre-existing** main-pass ref because a newly added original or a higher-tier host has arrived. That is correct behaviour, but it must be reported separately in the state replay ("pre-existing refs newly scoped"). The append order also becomes behaviour and must be deterministic.
- **The words "end of" contradict themselves.** `_complete_unmapped_evidence` *ends* with the relationship review (`:3440-3444`). Say it exactly: after `_complete_unmapped_sources` and the passage review, and **before** `review_relationship_scope`, so that a future review also sees the additions. It must not live inside `_complete_unmapped_sources`, which returns early when there are no leftovers (`:3526-3531`).
- **Recovery's trigger.** The pass runs before Stage 5.1, so it changes recovery's trigger. A T lifted to `supported` on reporting-tier echoes no longer triggers the targeted retrieval that could have found the **primary** source. H3 (authoritative source missing) fails on 7 of 18 records. #12 would lose its recovery run entirely.
  - That trade may be right, but it has to be measured: for each claim, would the trigger have fired at the seam before and after the pass?
  - When recovery later runs `map_evidence_to_specific_elements` on T, the pass's refs are kept (`existing_refs + new_refs`, `:3820-3821`) and not re-gated (they are not in `recovery_ev_index`), which is fine. The receipt is lost (F6).
- **Parallel targets.** Snapshot all candidate sets before any merge, and merge in element order, not completion order. Otherwise results depend on timing, and the bench's cassette replay breaks.

### F12. Paths the design does not name
- **Batch mapping:** covered, because `map_evidence_batch` calls `_complete_unmapped_evidence` for each successfully batch-mapped claim (`:2099-2121`). But it is under the 25 s budget (F3).
- **Grounds (opinion) claims:** they route through `map_evidence_to_elements` (`:1989-1994`), so they **would** get the pass. They have question-shaped elements and a prompt without `GROUNDS_MAPPING_ADDENDUM`, which is the highest #7 risk area. None of the 18 records is grounds-routed, so the eval cannot see it. Skip grounds claims in v1.
- **Quick mode:** `QUICK_CONFIG` has a 30 s wall budget and no recovery (`runner.py:67-80`). Nothing stops the pass running there. Decide explicitly. If quick mode skips it, add a `PipelineConfig` field so the `tier_limitations` drift guard declares it.
- **Manifest fingerprint:** precedent says add a contract key when the flag is on (`manifest_signer.py:46-51`, as the relationship review did).
- **Cassettes:** with the flag off, nothing changes. With it on, the pass adds new request keys rather than re-keying old ones, so `--record-missing` patch mode applies. But changed states change recovery triggers, so expect recovery-key churn as well, and run the control arm as planned.
- **Cost telemetry:** the new label must appear in `by_stage` / `_models_used` (it will, through `_call_llm`). Check that `stage_timings_s` attributes it.
- **Frontend "Why" line:** `elementStateReason` returns `null` for `supported` (`web/lib/element-reason.ts:34`). For the main intended outcome (unresolved → supported) the line shows nothing. The design's "the Why line already reports its counts" holds only when T stays non-supported. Acceptable for v1 if F8 is fixed; otherwise the stale caveat is the only text on the card.

### F13. The eval, as designed, is not a valid gate
- **Wrong input.** The stored payloads are **post-recovery** final maps. 10 of 18 records have `ev-rec`/`ev-rpf` items, and 9 of the 61 candidate pairs are recovery items. The production seam (before recovery) would never offer them. Target states also differ: #5 e1 has 4 recovery refs of its own, and #5 e2, #6 e2 and #12 e3 have one each. Rebuild the seam state (strip the recovery items and their refs, then re-derive) before replaying.
- **Gate fidelity.** Payloads are camelCase and lack `derivation_chain`, so the echo gate is silent offline. Recital, interested-party and date gates need `metadata.subjects`, `subject_kinds`, `claim_text`, `published_date` and `date_basis` mapped back to snake_case. Reuse the loader in `backend/scripts/eval_relationship_review.py`, and **report echo as not measured**.
- **No held-out set.** The 18 records are the set on which the fault was found. The prompt will be tuned on them. M1's review required a held-out set (`2026-09-24…design.md:129`). Use a disjoint set, e.g. replay-corpus claims, labelled **before** any prompt iteration.
- **Too few challenge cases** (6/61; see F10). Add the falsified-twin arm.
- **Mandatory positives.** Drop #12 from "all named positives must be added" (F1). Keep #1 and #15.
- **Pass bar.**
  - Split judgement from outcome: score the model's raw decision (pre-gate) and the post-gate state separately.
  - Count `unresolved → contextual` flips as state changes (F9).
  - Add: "no addition of a ref the graders already marked wrong (family C)".
  - Add: "independence of floor-clearing additions reported (corroboration groups)".
  - Fix NF-12 "collapse" numerically in advance: T shares ≥80% of its directional refs with one sibling **and** the descriptions are not a restatement. Otherwise "measure, don't gate" can never fail.
- **Adjudicator.** Blind to the model's output **and** to the graders' named positives and this design. Use three-way labels, as M1 did. A founder spot-check of the positives is cheap.
- **Cost.** It is priced at "flash, 10–20p". Production is gemini-3.7-flash, about 5× flash-lite per call (`2026-09-24…design.md:243`), with thinking floor "low". Expect roughly 40p–£1.20 for 39 calls, plus the held-out and falsified-twin arms. That is still small, but the founder's "ask before any paid run" rule needs an honest number.
- **Latency bar.** p90 ≤ 10 s per claim has never been met by this model on a comparable call (M1: 25 s). Set the timeout from a measurement, not the other way round.

### F14. NF-12 "measure, don't gate" for v1
This is acceptable, because the pass only adds to weak elements, never touches siblings, and is flagged. Two things are missing:
- A pre-registered collapse threshold (F13).
- A note that when a restated element (#12 e3, #15 e2) is lifted, the claim-level orientation counts the same sources twice ("2 predominantly supported" from one evidence set). That is the real NF-12 harm, and the pass makes it worse precisely on restated elements. Report it in the state replay. v2's token-overlap skip remains the right follow-up.

---

## Required changes (before the paid eval)

1. **Fail-safe wrapper:** the whole pass runs inside its own try/except and never propagates, so `_fallback_mapping` can never fire because of it (F2). Add a test that injects an exception in the merge.
2. **Wall-clock budget:** use one `wait_for` around the whole pass, sized from a measurement. Make sure it fits both `analyze_timeout=120` on the single-claim path and `_COMPLETION_TIMEOUT` on the batch path (raise that under the flag, as the relationship review did) (F3).
3. **Route the label to `MAPPING_GOOGLE_MODEL`** with the mapping thinking config and a response schema (enum `supports|challenges`, ids restricted to candidates). Pin it with a request-body test (F4, F9).
4. **No OpenAI fallback for this label:** on Google failure, make no change and write `status: failed` (F5).
5. **Stage, gate, then commit.** Gate the additions on a copy and append only the survivors. Record gated additions in the receipt. Reject `context` outright (F9).
6. **Keep the receipt alive:** store it at claim-metadata level, or in a carried-keys tuple that recovery, relationship review and passage review all preserve. Add a test that runs recovery after the pass and asserts the receipt survives (F6).
7. **Capture `state_derivation` before the basis rebuild** (keeps `llm_state`), and fix the same bug in completion at `:3655-3669` (F7).
8. **Stale text:** on any state change of T, replace or clear `uncertainty` and `scope_reach`, and keep the old values in the receipt (F8).
9. **Placement:** after `_complete_unmapped_sources` (and the passage review), before `review_relationship_scope`, not inside `_complete_unmapped_sources`. Snapshot the candidates, then merge deterministically in element order (F11).
10. **Skip grounds-routed claims in v1.** Decide quick-mode behaviour explicitly, via a `PipelineConfig` field if it is skipped. Add the manifest contract key under the flag (F12).
11. **Prompt:**
    - Reasoning must quote the **source's figure** whenever T states one ("or entity" is not enough).
    - Show sibling descriptions for disambiguation only, never sibling relationships or reasoning.
    - Add "returning none is the expected outcome for most candidates" (F10).
12. **Rebuild the eval** (F13):
    - Reconstruct the pre-recovery seam.
    - Replay the gates with snake_case fields, and report echo as unmeasured.
    - Label a held-out disjoint set before any prompt iteration.
    - Add the falsified-twin arm (bar: zero surviving `supports`) and a recital probe.
    - Remove #12 from the mandatory positives.
    - Count `unresolved → contextual` flips.
    - Report additions of graders' family-C wrong refs, the independence of floor-clearing additions, pre-existing refs newly scoped by echo or same-study, and before/after recovery-trigger changes per claim.
    - Pre-register the NF-12 collapse threshold.
    - Re-price on gemini-3.7-flash and ask the founder with that number.
13. **Correct the design text:**
    - #7 symmetry is at the relationship level only. Target selection is state-conditioned, and the pool leans with the siblings.
    - The "Why" line shows nothing for `supported`.
    - The model is 3.7-flash, not flash.
    - #12 is a derived-comparison element, not a SINGLE-rule casualty.
