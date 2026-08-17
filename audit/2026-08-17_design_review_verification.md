# Verification of the 2026-08-14 quality-first design review against the working tree

**Date:** 2026-08-17 · **Method:** three independent read-only verification agents, instructed to refute rather than confirm, each claim checked against actual code with quoted evidence. **Scope:** every factual file:line claim in `audit/2026-08-14_quality_first_design_review.md`.

**Headline: 24 of 26 claims stand.** One claim is REFUTED on its core condition (starvation), and one governance premise is contradicted by a signed founder decision (the challenge-lane "trigger"). Neither invalidates the 5-phase plan, but Phase D's justification must change, and several build details below are load-bearing.

---

## 1. The two findings that matter

### 1.1 Phase D re-opens a SIGNED founder decision — the "pull-back trigger has fired" framing is wrong

The review (§1.1) says the challenge lane's "pre-agreed pull-back trigger has fired." Verified against `audit/2026-07-15_decoupling_build_plan.md`:

- The trigger (`:273`) required pools coming back "systematically supports-only", and pulled the lane in **scoped to normative claims only**.
- **§15.8 records the probe RAN and the trigger did NOT fire as written** — P1 was an existence proof that retrieval is not structurally challenge-blind, and P4 partially invalidated the readout instrument.
- **"✅ D1 SIGNED BY FOUNDER 2026-07-16: OPTION A"** — reactive Phase 2 with three hard commitments; Option B ("the scoped challenge lane enters Phase 1") was explicitly not chosen.

So Phase D is a **new decision on new evidence** (the Scotland/dairy re-grades of 2026-08-12/13, which post-date the probe), re-opening a signed one — not the execution of a standing trigger. The evidence for re-opening is real and recorded; the justification just has to be stated honestly, and the founder should confirm Phase D knowing it reverses their own 2026-07-16 call. Note also the review's lane is universal (factual claims included), broader than even the rejected Option B (normative-only).

### 1.2 `_element_is_starved` — REFUTED as characterised

`runner.py:425-443`: an element with **no refs at all returns False** ("the unresolved trigger owns it, so it is deliberately NOT counted as starved"). Starvation = has mapped refs, none directional. Zero-ref elements still reach recovery via the unresolved branch (`runner.py:2508`: `(needs/total) > 0.4 or any_starved`).

Also drifted: recovery does not re-issue "claim-direction" queries — `retrieve_for_elements` plans per-ELEMENT queries (≤2 each, hardcoded at `retrieve.py:1341`) with claim text only as planner context and a 100-char suffix on the naive fallback (`:1363`, `:1297`). The §1.1 conclusion (recovery re-searches the same phrasing and needs the challenge treatment too) still holds; the mechanism description does not.

---

## 2. Corrections that change build details (claims otherwise CONFIRMED)

1. **`seen_urls` bug (`retrieve.py:2070`/`:2144`) — real, but narrower and younger than stated.** Not "dead since it shipped": `.add()` predates the dict; the init became a dict in `6e8a344` (2026-02-12, PR-B03) which converted the main loop but missed this call — worked ~10 weeks, dead six months. And the path is only reachable for `pw`/`pm` plans (`:1992` default `py` + guard `:2115-2119`), so it never bites the planner's default. Bonus find: `test_element_retrieval_seam.py:595` covers this path with an empty-results stub and asserts before the fault — green and structurally incapable of failing. Phase C should fix the test too.
2. **Query-cap footgun:** `runner.py:54` (3) / QUICK (1) are correct, but `EvidenceRetriever.__init__` defaults `max_queries_per_element = 5` (`retrieve.py:526`); the 3 only arrives via the worker override (`workers/pipeline.py:180-181`). Any new call site constructing a retriever directly slices at 5. Quick tier's claim lane holds ONE query — nothing appended survives the slice, so the tier_limitations declaration (I-9) is mandatory, not belt-and-braces.
3. **4th claim-lane query side effect:** `CLAIM_LANE_MAX_RESULTS_PER_QUERY=13` is `40//3` by construction; a 4th query drops claim-lane depth to 10 and breaks the assertion at `test_element_retrieval_seam.py:592`. Budget decision 4 carries a test re-baseline.
4. **Hedge (`retrieve.py:425-427`) — confirmed positional-index-1, with a new edge:** on a lane the planner gave only ONE query, an appended challenge variant becomes position 1 and silently takes the F1-D3 hedge slot. The append-last rule is safe only for lanes with ≥2 planner queries.
5. **Two-way lane branching is FOUR sites, not one:** `== CLAIM_LANE_ELEMENT_ID` recurs at fetch weight (`:350-355`), query cap (`:475`), sizing (`:2040-2047`), and `_class_augmentation_targets` (`:284-289`). Reinforces variant-within-lane over a third lane id.
6. **Phase A is cheaper than the review implies:** all five gates ALREADY emit an identically-shaped, label-distinguished INFO line from the shared driver (`claim_map_analyzer.py:2556-2559`; labels TEMPORAL SCOPE / JURISDICTION SCOPE / MEASURE SCOPE / INTERESTED PARTY / RECITAL). The bench gap is matcher + golden fields only (`capture.py` has 20 matchers, one gate matcher, `:154-157`).
7. **`_SCOPE_RECEIPT_KEYS` trap is WORSE than stated:** `_merge_scope_receipts` (`:1423`) iterates the constant, not the union of keys — an unlisted gate loses its FRESH receipts too on the completion path (basis rebuilt `:2827`), and fresh entries are dropped on the recovery path. I-5's checklist stands, with sharper teeth.
8. **Recovery staleness surface is bigger:** recovery never calls `_compute_element_basis` (call sites `:2230`, `:2264`, `:2827` only) — stale are FOUR breakdown dicts + `support_structure` + `challenge_structure` + `evidence_count` (`:1344-1356`), not "three blocks". The B-phase fix should enumerate all seven.
9. **Claimant arming, option (a) mechanics:** `ExtractedClaim` (`extract.py:48-75`) confirmed to have no claimant field. The merge point is `runner.py:197-198` (inside `attach_claim_subjects`, sole writer, call site `:2417` — the review's line cites were mislabelled but the substance holds). Useful: `claim_subjects` accepts bare strings with NO type filter (`interested_party.py:200-201`), so a claimant string can merge into subjects directly without faking a key_entity. Also: `subject_context` is persisted but effectively DEAD in retrieval whenever the planner is live (only the fallback branch `retrieve.py:1673-1687` uses it) — do not lean on it.
10. **`>=`→`>` scope, precise:** on the challenges side the comparator changes only `rule_applied` (close_split also yields `disputed`, `:1036-1037`); only the supports side changes state. Known test breakage is THREE files: `test_coverage_recovery.py:1371ff` (four assertions), `test_claim_map_analyzer.py:1015`, `test_map_completion.py:589`.
11. **Echo/derivation storage confirmed** (chains keyed on the PRIMARY, `corroboration.py:242-282`; repetition marks members directly `:512`) with one Shape-B design input: a derivative whose primary is absent from the pool is invisible as a derivative — the "original already counted" condition degrades safely (fires less).
12. **Recital anchor lines are `recital_scope.py:171-172`** (not 172-173); the gate cannot arm without subjects AND non-empty distinctive tokens (`claim_map_analyzer.py:2460-2466`).

## 3. Fully confirmed without qualification

State derivation's input surface (no derivation data read; five wire copies = five supports) · `>=` at `:1029`/`:1032` with mechanical override of `llm_state` (`:2280`) · `_state_floor_for` three call sites, factual floor 0 · gate order + the `break` (`:2549`) · `_index_evidence` three build sites, recovery indexes `new_evidence` only (`:2966`) · first-writer `_query_index` dedup vs accumulating `_element_ids` (`:2090-2102`) · per-lane sizing inheritance (13/5) · `retrieve_for_elements` bypasses every lane-seam mechanism (`:1274-1466`) · zero counter-direction query generation anywhere (grep-proved across planner, augmenters, prompts) · `query_challenge_augmentation.py` never existed on any branch · tier-limitations drift guard both directions · the 2v1 tie arithmetic (2 >= 2·1) · `side_quality_note` parity twin · subjects writer uniqueness.

## 4. Consequences for the plan

- **Phases A, B, C, E: proceed as designed** (with the enumerated detail corrections folded into build design — notably §2.6 makes Phase A smaller and §2.7/§2.8 make Phase B's checklist stricter).
- **Phase D: needs an explicit founder decision acknowledging it reverses signed D1 Option A (2026-07-16)** on the strength of the Scotland/dairy evidence — and a scope choice: universal lane (review's design) vs normative-only (the old Option B). The review's §5 decision 4 should absorb this.
