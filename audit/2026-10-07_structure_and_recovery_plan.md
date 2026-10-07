# Structure + coverage-recovery correctness: plan (2026-10-07)

**Source:** architecture review 2026-10-06 §2.1 and §3 Phase 2; read-only inventory (2026-10-07) against `98c4f2d`, spot-checked (D5 timings, D1 state put-back, single-claim fallback).
**Status:** plan, for independent review. Nothing built.

## What the inventory established
- **One sequence, five hand-copies.** "Snapshot scope receipts → rebuild basis (`_compute_element_basis`) → restore or merge receipts → derive state (`_derive_element_state_with_authority`)" runs at: A main parse (CMA:2709–2798), B completion census (CMA:3808–3840), C relationship review (RSR:840–857), D echo restore (CMA:1642–1649), E recovery (CMA:3973–4089). Differences: A has no snapshot (first pass, correct); B and E merge, C and D restore (correct: no fresh receipts in C/D); `llm_state` kept only in B (drift); E non-targets keep a stale state (drift = D1); E gates against new evidence only (drift = D2); C relabels with a plain string, the rest with the enum (cosmetic drift).
- **Defects, all confirmed in code:**
  - **D1** recovery rebuilds a non-target element's basis over the new pool but puts back its OLD state and `state_derivation`; a supported element that gains two primary challenges keeps `supported` while its counts show 1 vs 2.
  - **D2** recovery gates against `_index_evidence(new_evidence)`; same-study cannot see a main-pass host of the same DOI, so the study counts twice.
  - **D3** recovery classifies with `review_originators=False` (documented budget choice); a recovery item the main pass would lower to reporting keeps primary weight 3 and can clear the support floor alone.
  - **D4** the relationship review (default-on) and echo restore (latent: echo off) drop `llm_state`.
  - **D5** recovery Phase B has a 25 s grace (`RECOVERY_MAPPING_GRACE_SECONDS`) but contains a review call with a 40 s deadline; cancellation mid-review leaves new refs on elements, target states rewritten, orientation stale, and refs to items never added to `evidence[pos]` (so never stored). `return_exceptions=True` results are never inspected, so a late exception leaves the same state with no log.
  - **D6 (new)** single-claim path (grounds claims always): any exception in completion/review/reconcile reaches `_fallback_mapping`, which wipes every ref (CMA:1997–2002); the batch path keeps the main-pass mapping instead.

## Principle
Separate **refactors** (output byte-identical; proof = suite unchanged + bench equal to control) from **fixes** (output changes on purpose; proof = a failing test written first, then the fix, then the bench diff read claim by claim and every moved number attributed). Never mix the two in one commit.

## Steps

### S1 — one refresh function (REFACTOR, plus D4)
`_refresh_element(elem, pool, claim_map, *, fresh_receipts=None, keep_llm_state=True) -> None` in CMA: snapshot `_SCOPE_RECEIPT_KEYS` + prior `llm_state` → `_compute_element_basis(elem, pool)` → `update(_merge_scope_receipts(prior, fresh or {}))` → derive → write `state`, `state_derivation`, restore `llm_state` unless the caller supplies a new one.
- Replace B, C, D with it. Merge vs restore are the same operation when `fresh` is empty (`_merge_scope_receipts(prior, {})` must equal `prior`; pin with a test first).
- A stays as is (first pass, no snapshot) but calls the same derive/write tail.
- E's target branch uses it with the recovery `llm_state`; E's non-target branch is S3.
- **Only intended change: D4** (`llm_state` survives review and echo restore). Observability only: no reader in app or web. Bench must stay equal.
- C's plain-string relabel becomes the enum (derive accepts both; verify serialisation is identical).

### S2 — D6: single-claim path keeps the main-pass mapping (FIX, narrow)
Wrap `_complete_unmapped_evidence` in the single-claim path exactly as the batch path does (own `_COMPLETION_TIMEOUT`, log, keep main-pass mapping). Test first: a raising completion must not empty the refs.

### S3 — D1: re-derive every element whose refs changed in recovery (FIX)
Non-targets that gained refs go through `_refresh_element` too (state re-derived over the full pool, `llm_state` kept). The docstring's "never change non-target state" intent is replaced by "state always matches its refs" — the card/badge contract.
- Two tests pin the old behaviour (`test_cross_element_ref_merging`, `test_only_targets_unresolved`); rewrite them to the new contract, with the fixture's `ev-existing` added to the pool (its absence is why re-derivation would read `unresolved`).
- **Behaviour change:** a non-target can move state (e.g. supported → disputed). Founder sign-off required before merge (it changes what records say).

### S4 — D2: recovery gates against the full pool (FIX)
`_index_evidence(pool)` instead of `new_evidence`, gating only refs that are new this pass (pre-existing refs keep their main-pass outcome; no double receipts). Test first: main-pass host + recovery host of one DOI on one side → one counted.

### S5 — D5: recovery commits all-or-nothing (FIX)
Run E on a staged deep copy of the claim map; extend `evidence[pos]` and swap the map in one synchronous step after review, reconcile and orientation complete; on timeout or exception keep the pre-recovery map untouched and log once (inspect the gather results). Size the grace like completion: `max(25, mapping + review deadline + slack)`, or keep 25 and skip the review on recovery (decision below). Tests first: cancel during review → map and pool unchanged; exception after parse → unchanged and logged.

### S6 — D3: originator review on recovery items (founder: run it; built 2026-10-07 in Phase B, see Progress)
The skip was a budget choice. Running it costs ~1p and its latency sits inside Phase A's budget. Options for the founder: run it (correctness), or keep the skip and down-weight unreviewed recovery primaries. No build until decided.

### S7 — split `run_pipeline_phase2` (REFACTOR, after S1–S5)
Extract in order, one commit each, each proven by suite + bench equal: load state; decompose+fact-check; retrieve+dedup+scoring (both REBIND `evidence`: functions return the new dict); post-filter recovery; classify+distil; mapping; coverage recovery (Phase A/B closures become functions; counters returned, not `nonlocal`); final build. Constraints: source-text tests pin call order and literals (`test_cited_source_gap_note.py:313–338`, `test_originator_review.py:497–508`, `test_recital_original_wording.py:111–119`) — move the asserted text with its code and keep the order; one `analyzer` instance must flow through (telemetry reads it at the end); `selected_claims` and `claims` share dict objects.

## Measurement
- Refactors (S1 bar D4, S7): unit suite unchanged, bench equal to control claim by claim.
- Fixes (S2–S5): test written first and seen failing; after the fix, bench diff read per claim, every changed number attributed to the fix or to known drift (93DD/B4A3 under `--all`).
- **Not measurable on the bench:** D5 (needs a timeout) and D2 (no corpus claim has a cross-pass same-study pair, unverified) — their proof is the tests. The A− class counts need paid runs: founder approval before any.

## Decisions needed (in order, one at a time)
1. S3 changes element states on records: approve the "state always matches its refs" contract.
2. S5 grace: enlarge recovery's window to hold a review call, or skip the review inside recovery.
3. S6: run the originator review on recovery items or not.

## Independent review (2026-10-07) — taken in full; supersedes the steps above where they differ
- **H1 (S4 wrong as worded):** gating only new refs leaves the double count when the recovery host has the HIGHER tier (it becomes the same-study carrier and the main-pass ref is never examined). **Fix as completion does:** `_index_evidence(pool)` and gate ALL refs; already-scoped refs are `context` and skipped (no double receipts); deterministic gates re-run with the same result; only cross-ref gates (same-study, echo) can move. Test with the recovery host at the higher tier. D3 interacts (an unreviewed recovery "primary" wins the carrier slot) — part of decision 3.
- **H2 (S1 not output-identical):** `state_derivation` (with `llm_state`) is inside `basis`, which is in the SIGNED canonical payload — D4 changes manifest bytes. Split: **S1a** pure refactor keeping per-site `llm_state` semantics (B restores only when truthy; C/D drop; E targets set the recovery state); **S1b** D4. The bench never reads `basis`, so "bench equal" is near-vacuous here: **S0** first — a characterisation test snapshotting full claim_map dicts through B, C, D, E (completion; review; echo restore; recovery targets, non-targets, a target with no new refs, and no-`full_evidence`), asserting equality after S1a. Keep E's no-`full_evidence` branch (pinned by a test) and its `new_refs` guard; callers set `uncertainty` before the refresh (the caveat reads it).
- **M1:** `_merge_scope_receipts(prior, {})` drops falsy values and reorders keys (in-memory only: JSONB + `sort_keys` signing); pin with dict equality and realistic non-empty receipts.
- **M2:** only `test_cross_element_ref_merging` needs rewriting for S3, with `ev-existing` given `tier: primary` and passed as `full_evidence`. Non-targets also include unresolved/starved elements beyond `RECOVERY_MAX_ELEMENTS`. The "never change non-target state" contract is already broken by the review re-deriving demoted non-targets. Fix the `state=preserved` log and the `elements_resolved` counter with S3.
- **M3 (S5 timing):** recovery mapping can take 35 s (+ OpenAI fallback), the review 40 s, and reconcile can add a second review: the window is ~35 + 2×40 + slack ≈ 120 s, which nears `PIPELINE_WATCHDOG_SECONDS=300` — decision 2. Phase A already mutates `existing_urls` and scorer-exclusion receipts (the runner docstring "nothing is mutated" is false; scope S5's test to the claim map and pool). Stage a deep copy of the WHOLE claim map; commit in place (`cm.clear(); cm.update(staged)`) to keep the claims/selected_claims aliasing. An interrupted recovery review receipt will no longer be recorded.
- **M4 (S2 wider than stated):** the single-claim path also serves any one-claim check, every batch-parse retry, and EVERY Strengthen run (re_search.py:141) — D6 can wipe a strengthened map. It has no completion timeout at all. Wrap only the completion call; keep the fallback for parse failures; hoist `_COMPLETION_TIMEOUT`.
- **M5 (order):** S0 → S2 → S1a → S1b → S5 → S3 → S4 → S7 (S6 decision only).
- **M6 (S7 constraints):** `@metered` stays on `run_pipeline_phase2` only (`test_derivation_chains_flag.py:110-116`); exact-indent literal (`test_recital_original_wording.py:119`); the `"\n    )"` cut in `test_cited_source_gap_note.py:336`; CMA count pins (`_element_lines(` ×5, `_date_context()` ×5); patch targets live in `app.pipeline.runner`, so extracted helpers stay in that module.

## Progress
- **S2 (D6) done** `f3ebbeb`: `_complete_keeping_main_pass` on both mapping paths; tests written first (2 failed on old code).
- **S0 done** `65c6aff`: `test_refresh_characterisation.py` + golden (sites B, C, D, E; branch guard).
- **S1a done:** `_refresh_element` replaces sites B (completion), C (review) and D (echo restore); golden unchanged; mutation-checked (dropping B's `llm_state` fails the golden). **Site E deliberately NOT folded in here:** its body is rewritten by S5 (staging) and S3/S4 (fixes); folding it now would mix structure with its defects. It moves to `_refresh_element` in S3.
- **S1b (D4) done** `e99abd4`.
- **S5 (D5) done:** `_map_recovery_atomically` (staged deep copy; map swap + pool extension committed together, synchronously); `_await_recovery_mappings` reads every outcome and logs a grace timeout; `_recovery_mapping_grace()` = 85 s with the review on (founder: option 1). Independently verified (no HIGH). Accepted trade-offs: worst-case recovery 60 s → 120 s (watchdog 300 s); the OpenAI fallback inside the mapping call is not budgeted, so when it fires that claim's recovery is discarded whole (safe now). Open LOWs: flag-off grace stays 25 s (the flag is on); a discarded recovery leaves only a claim-level log, not per-item receipts.
- **S3 (D1) done** (founder approved "state always matches its refs"): coverage recovery rebuilds AND re-derives any element that gained refs (target or not) through `_refresh_element`; targets record the recovery model's `llm_state`, non-targets keep the main pass's. The no-pool branch (pinned by a test; the runner always passes the pool) and targets without new refs are unchanged. Golden diff confined to the non-target scenario (supported → disputed, orientation follows). Bench identical; its output prints no recovery logs, so whether the corpus exercises this case is unknown — the proof is the golden + guard.
- **S4 (D2) done:** recovery builds its gate index over the full pool, as completion does; one study is counted once across passes, whichever host has the higher tier (3 tests written first, all failed on the old code). Golden unchanged; bench identical.
- **S6 (D3) done:** founder chose to review recovered items. Correction recorded: the review cannot sit in Phase A (its 35 s budget is nearly spent; overrunning it loses the claim's whole recovery), so it runs at the START of Phase B inside `_map_recovery_atomically`, capped at 20 s (`_RECOVERY_ORIGINATOR_REVIEW_S`), on the page opening kept at enrichment (verification M1: not the claim-selected 500-char snippet). Grace 105 s (founder), worst case 140 s. Overrun -> `recovery_timeout`, fault -> `recovery_review_failed`, both keep tiers and never cost the recovery. Wiring pinned by a source test (mutation-checked). Bench: 93DD gains 2 cassette misses = the new review call (attributed: a control run with only the recovery review off replays clean); clearing them needs a paid `--record-missing` (founder approval). Open: recovery classify + review tokens never reach telemetry (pre-existing gap, verification L2); size the 20 s cap on production `call_seconds`.
- **Remaining:** S7 (`run_pipeline_phase2` split) — refactor only, one extraction per commit.
