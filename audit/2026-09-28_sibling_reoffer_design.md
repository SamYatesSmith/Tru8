# Sibling re-offer: design (A− H1, family B)

**Date:** 2026-09-28. **Status:** DRAFT for independent review, then founder approval, then a paid eval. Difficulty 3, because it changes element states.
**Problem record:** `audit/2026-09-28_mapping_failures_review.md`, § "Family B: root cause found".

## 1. The fault
A source whose text states element B's assertion is filed only under sibling element A, so B reads unresolved or contextual. Three coupled causes:
1. **The prompt forbids it.** `MAPPING_PROMPT`, `BATCH_MAPPING_PROMPT` and `COMPLETION_PROMPT` all say "Map each item to the SINGLE element it most directly addresses; do NOT duplicate". This is the NF-12 anti-collapse rule, kept deliberately in NF-19 (`a903729`).
2. **The completion backstop** (`_complete_unmapped_sources`) offers only wholly unmapped items.
3. **Coverage recovery** misses a lone weak element (the trigger is >40% of elements, and 1/3 does not pass it). When it does fire, it maps only newly retrieved items.

**Measured on the 18 re-run records:** 13 weak (unresolved or contextual) elements with 61 sibling-directional candidates.
- The graders named the fault on three of them:
  - #1 e3: 9 outlets state "Harborne £36m", all filed under e1.
  - #12 e3: Statista gives 427 ppm (2025) and 323–325 (1968–70), filed under e1 and e2 only.
  - #15 e2: every "29% fall" source is under e1 or e3.
- #1 would reach A− with this fixed; it is the only record on the set that mapping alone lifts to A−.

## 2. Design
**New pass `_reoffer_sibling_sources(claim_map, evidence_list)`**, behind flag `ENABLE_SIBLING_REOFFER` (default **False** until the eval passes).

**Where it runs:** at the end of `_complete_unmapped_evidence`. That is after the main mapping (with its gates) and after completion, and before the relationship review (flag off) and `apply_orientation`. The main path only in v1; the coverage-recovery path is named in §6.

**Target elements:** state `unresolved` or `contextual` after completion. That includes `unresolved` from the support floor (#1 e3 has one reporting support).

**Candidates for target element T:**
- Items holding a **supports or challenges** ref on any sibling, and no ref on T.
- Context-only and unmapped items are excluded: completion already saw the unmapped ones, and context-on-a-sibling is weak signal.
- Capped at `SIBLING_REOFFER_MAX_CANDIDATES = 20` per element, filled **round-robin across siblings** (invariant #2), not by slicing.

**Call:** one model call per target element, all targets in parallel.
- Model: the mapping model (`MAPPING_GOOGLE_MODEL`), label `sibling_reoffer`, per-call timeout 20 s.
- On failure or timeout: no change and a receipt recording `status: failed`.

**Prompt `SIBLING_REOFFER_PROMPT`:** a single-element question.
> "These sources were already matched to OTHER parts of this claim. A source can bear on more than one part. For THIS element only, return each candidate whose own text states this element's specific assertion (supports) or contradicts it (challenges). Omit the rest; do not use context."

It carries the shared rules **verbatim** from `COMPLETION_PROMPT`: supports-means-warrants, CAUSAL LINK specificity, recital, modality, and topic-vs-figure. It also states the symmetry sentence: challenges are returned exactly as readily as supports.
- No "context" output. The pass is for state-bearing relationships only; context would re-open display bloat.
- Every returned ref needs `reasoning` citing the figure or entity.

**Merge (the same seam as completion):**
1. Validate the ids against T's candidate set only.
2. Dedupe.
3. Append to T's `evidence_refs`.
4. Run **`_apply_scope_gates` over T** (all gates, including figure, recital, interested-party and echo), merging prior receipts via `_merge_scope_receipts`.
5. Recompute the basis and re-derive the state with `_derive_element_state_with_authority` and the claim's floor.
6. Preserve the prior `llm_state`.
- Only T changes. Siblings keep their refs.

**Receipt:** `basis.sibling_reoffer = {candidates, added: [{evidence_id, relationship, from_element}], status}`. It is not rendered in v1, but the state's "Why" line already reports its counts.

**NF-12 guard (collapse):**
- Log `sibling_overlap` = the share of T's directional refs that also sit on a sibling.
- The **v1 eval measures it but does not gate on it**: the overlap is expected, since it is the fix.
- A named v2 guard, if the eval shows collapse on distinct elements: skip T when its description token-overlaps a sibling above a threshold. That is Build D's restated-element case, where identical refs are correct anyway.

## 3. Invariants
- **#7 symmetric:** both directions are returned, the gates re-run, and nothing is promoted by rule. The candidate pool can lean in whatever direction the siblings lean; the eval reports additions by direction.
- **#5 receipts:** every addition carries the model's reasoning and a `sibling_reoffer` receipt.
- **Gate ORDER and `_SCOPE_RECEIPT_KEYS`:** this pass adds no gate; it calls the existing driver.
- **Idempotent:** a second run offers only candidates with no ref on T, so an addition is never re-offered.

## 4. Evaluation (paid, founder's go)
**Run:** replay the pass offline on the 18 stored re-run payloads (their claim maps + evidence snippets), 3 repeats.
- 13 targets × 3 = 39 calls on flash, about **10–20p**.
- Script: `backend/scripts/eval_sibling_reoffer.py`. It is free to build, and no pipeline re-run is needed.

**Labels:** a blind adjudicator agent, who does not see the model's output, labels each of the 61 (T, candidate) pairs as `supports` / `challenges` / `none` from the source text and the element.

**Pass bar:**
- ≥70% of adjudicated supports/challenges pairs added with the correct direction, including all named positives on #1, #12 and #15.
- ≤5% of additions wrong (adjudicated `none` or the opposite direction), reported separately for supports and challenges.
- **Zero** wrong additions that change a state (state replay reported per element).
- p90 latency ≤ 10 s per claim (parallel).
- Failed calls ≤ 5%.

**State replay:** report every state change, its direction, and which grader H1 fails clear. The expected clears are #1 e3, #12 e3 and #15 e2. Watch #5 e1: the figure gate should still demote 66% and 68%.

## 5. Risks
- **Over-adding (sycophancy by volume):** a thin element gains supports from sources that only border on it. Mitigations: the gates, the support floor, and the per-direction wrong-rate bar.
- **Collapse (NF-12):** measured; v2 guard named.
- **Latency:** one extra round on about 1 in 3 claims (13 targets over 18 claims), run in parallel.
- **Cassettes:** a new call re-keys corpus claims that have weak elements. Bench re-record (pence, ask) plus a control arm.
- **Cost:** about 0.1–0.3p per target element.

## 6. Out of scope (named)
- Coverage recovery's trigger (>40%) and its new-evidence-only mapping. Recovery does retrieval (cost, latency); re-assess after this pass is measured.
- Family A (gate releases for an org's own publication): a separate design.
- Family C (wrong-scope refs): M1 is a hard stop.
- Relaxing the SINGLE-element rule in the main prompt: it would reopen NF-12.

## Review outcome — 2026-09-28 (`audit/2026-09-28_sibling_reoffer_review.md`)
**APPROVE WITH CHANGES, 13 required changes.**

**Two findings verified first-hand:**
- `_call_llm` routes only `mapping` / `batch_mapping` to the mapping model (`claim_map_analyzer.py:2190`).
- `llm_state` is missing on 9 of 48 elements in the re-run payloads. This is a live completion-seam bug, independent of this design.

**The finding that matters most (invariant #7):**
- The candidate pool is 56 supports to 6 challenges.
- 6 of 13 targets sit just under the support floor.
- The candidates include refs the graders already marked wrong-scope.

The pass therefore leans structurally toward adding supports. The re-priced eval, on 3.7-flash with held-out and falsified-twin arms, is about **£1+**. **Awaiting the founder's decision** on whether to proceed.
