# Echo link confirmation build plan: independent review (2026-10-05)

**Plan reviewed:** `audit/2026-10-05_echo_link_confirmation_build_plan.md`.
**Against:** design rev 2 (`audit/2026-10-01_echo_link_confirmation_design.md` §10–11) and the prior review (`audit/2026-10-01_echo_link_confirmation_review.md`).
**Reviewer:** independent; did not write the plan. No code changed.
**Note:** steps 1–2 are already in the working tree, untracked (`backend/app/services/echo_link_confirmation.py`, `backend/scripts/echo_link_eval.py`, `backend/tests/unit/pipeline/test_echo_link_confirmation.py`). Where they show how the plan will behave, they are cited.

## Verdict: APPROVE WITH CHANGES

The seam is right, and the join inside the analyzer is the right place for it. Every index build, basis build and gate pass runs after the first `_parse_mapping_response` call, so a join in front of those calls covers all of them. But two faults must be fixed first. The join, as worded, has a race that lets a claim be gated without its links. And the paid eval feeds the model text that production cannot produce, so a pass would not show that the shipped stage is precise.

## HIGH

**H1. Two first joins can run at once, and "later calls return at once" lets one parse before the links are written.**
- When the batch call fails or returns a bad shape, every claim is retried at the same time: `asyncio.gather(*[_retry_map(i) ...])` (`claim_map_analyzer.py:2236-2246`). Each retry runs `map_evidence_to_elements`, makes its own mapping call, and reaches the join (`:1910`) whenever its call returns.
- No join has run yet on that path: the batch parse at `:2148` was never reached (`:2158-2163`).
- Plan §3.3: "the first call awaits the task … Later calls return at once." A second caller that arrives while the first is still waiting returns at once, builds `ev_index` (`:2654`) with no `confirmed_copies`, and gates and bases its claim without links. The first caller then writes `metadata.echo_links` saying "confirmed" for links that claim never used. The receipt misdescribes the report (invariant #5).
- **Required:** the join is one memoised awaitable. The first caller creates it (for example `self._echo_join_future = asyncio.ensure_future(self._do_join())`, under an `asyncio.Lock` or a plain check-and-set with no await in between). Every caller awaits that same future, and none returns before the fields are written. Add a seam test: two concurrent `map_evidence_to_elements` calls on a failed batch both see `confirmed_copies` in their gate pass.

**H2. The eval text is not the production text, so the switch-on gate measures a different input.**
- Re-fetched pairs (173 of 248) get "page opening (900) plus up to two 900-char windows around the pair's shared non-year facts" (`audit/echo_precision/refetch_verbatim.py:28-37`). Those windows are chosen to contain the overlap, which is where a copy cue sits.
- Production cannot build such windows. At the seam, `_full_text` is already gone (distil removes it; `runner.py:2268-2270`, `:2329-2333`). What is left is the 1,200-char opening (`echo_link_confirmation.py:46`, `:136-140`), the search snippet and `text_provenance.passages`. The passages are chosen by **element** terms (`text_provenance.py:29-83`, `selection_method: lexical_element_windows_v1`), not by the pair's facts.
- Production then cuts each side to 2,700 chars (`echo_link_confirmation.py:39`, `:324`) in the order opening → snippet → passages (`:147-156`). So about 1,200 chars of passages survive, from up to 7,200 retained. The eval puts the shared facts inside the window; production mostly cuts them off.
- The harness feeds the labellers' blind text as `original_snippet` with no passages (`scripts/echo_link_eval.py:46-56`). `verbatim_text` then returns that text unchanged. The production composition is never exercised, although plan §1.2 says "the eval tests the production code".
- The 75 stored pairs are closer (stored snippet + element passages) but lack the page opening, which production adds first.
- Effect: recall is overstated, and precision is measured on richer text than the model will see. A pass does not show the shipped stage meets 90%.
- **Required:** score the model on production-shaped text and keep the labels as they are. Labels made on richer text are a better reference for truth; the model must see only what production shows it. For each re-fetched side, build the item as production would: put the re-fetched text in `_full_text`, run `copy_page_opening` and `capture_text_provenance(item, <pool claim text>, <pool elements>)` from the stored claim map, then call `verbatim_text` and `build_prompt` unchanged. For stored sides, use the stored `text_provenance` as it is, and add a re-fetched opening where one exists (or report that stratum without one). State in the report that trafilatura is not the production extractor. Either way, no paid run until the harness feeds `verbatim_text` real production-shaped items. Optionally, a cheap production gain: within the 2,700 cap, put retained passages that contain the pair's strong shared facts first. It is mechanical and claim-independent at selection time, and it narrows the gap honestly.

## MEDIUM

**M1. Clean-up is planned in a method that does not exist, and a deadline cancel loses finished calls.**
- Plan §3.5 puts `try/finally: echo_join.cancel()` in `analyze`. There is no `analyze` method. The runner calls `asyncio.wait_for(analyzer.map_evidence_batch(...), timeout=120)` (`runner.py:2475-2478`).
- The task is created at `runner.py:2342`. Between there and the mapping `try` (`:2457`) there are awaits (`_log_stage_transition`, `:2349`), and a watchdog cancel can land there (`watchdog.py:55-56`). Tasks made with `create_task` are not children: cancelling the pipeline does not cancel them.
- If `wait_for(120)` fires during the join, it cancels the `shield` wrapper, not the task.
- `confirm_pairs` gathers every chunk and builds records only at the end (`echo_link_confirmation.py:388-420`). Cancelling it at the deadline loses the calls that had finished, against plan §3.4 ("finished calls keep their results").
- If mapping returns `None` for every claim (`claim_map_analyzer.py:1943-1944`, `_fallback_mapping`), no join ever runs and no record says why.
- **Required:** a `try/finally` in the runner from task creation to the end of mapping. It cancels the task and clears `analyzer.echo_join`. Run the chunks as separate tasks, and at the deadline use `asyncio.wait(timeout=...)`: keep the done ones and mark the rest `not_inspected` (`detail: deadline`). Add a done-callback that retrieves the exception. If the join never ran, write totals with `detail: mapping_failed` on each claim map.

**M2. The join wait counts against a 120 s budget that is already tight, and overrunning it fails the check.**
- `analyze_timeout = 120` (`runner.py:2461`). On a timeout the whole check fails (`:2480-2485`).
- With the relationship review on, the batch completion timeout is `max(50, 25 + 2×40 + 5)` = 110 s (`claim_map_analyzer.py:2186-2198`; `config.py:858-859`). Batch mapping alone is budgeted at ~55 s (`runner.py:2455-2460`). The worst case already exceeds 120 s.
- The join can add up to 45 s minus the time from task start to the join. That time is spent inside the same 120 s.
- **Required:** cap the join wait separately (for example `min(remaining, 15 s)`, then `detail: deadline`), or raise `analyze_timeout` by the join cap in the same commit. Report the `echo_link_wait` p90 from the live checks in step 4.

**M3. "First confirmed original, in §2 order" is not what `_index_evidence` computes, and Strengthen reorders the pool.**
- `_index_evidence` keeps the first original in **pool** order (`claim_map_analyzer.py:1703-1710`).
- Strengthen's pool is sorted by database id (`report_revisions.py:66-69`, `sorted(evidence, key=lambda e: e.id)`; `re_search.py:128-132`). So the same records rebuilt there can pick a different original for a copy with two confirmed originals. Then the gate scopes it differently and the `echo_scope` cue names a different pair.
- The citation path rebuilds an `_IndexedEvidence` and carries only `original_id` across (`:3443-3445`). A new `cue` field on the index would be dropped there.
- **Required:** store records in §2 order and give each confirmed copy an explicit rank (for example `confirmed_copies: [{"id", "rank"}]`). `_index_evidence` keeps the lowest rank, not the first in the list. The `echo_scope` entry takes `cue`/`cue_kind` from that record, and `_replace` carries them. Test: the same records over two pool orders give the same `original_id` and cue.

**M4. The frozen-replay rebuild has nothing to rebuild from.**
- Frozen items are rebuilt from a fixed field list (`retrieve.py:1811-1840`): no `tier`, no `text_provenance`, no claim-map metadata. Classify is skipped (`runner.py:2144`). The claim map is decomposed afresh, so there are no stored `echo_links` in reach.
- **Required:** under `_is_frozen_evidence_replay`, the stage does not run and writes totals with `detail: frozen_replay`. Drop "rebuilds from stored `echo_links`" from §5 (and design M5), or extend the freeze format. That is a separate piece of work.

**M5. The note can still misfire across two originals.**
- `derivative_ids` is every derivative in the pool (`claim_map_analyzer.py:1437-1441`). `originals` counts any primary with a chain on the side (`:1369-1370`).
- Case: A (chain B1, B2) and B1 on the supports side, plus C, a copy of D (chain C, E), where D sits on the other side. That gives `originals=1, derivative_count=2`, and the note says "Several of these sources repeat a single original report". False. It makes the element toppable via Strengthen (paid).
- The prior review's H2 test (two originals, one copy each) does not catch this.
- **Required:** count, per side, only copies whose original is counted on that same side. This is a backend-only change: `support-structure.ts:40` and `support_structure.py:85-87` read the numbers alone, so there is no parity change. Add this case as a test.

**M6. The attribution check is looser than the plan intends.**
- `_names_of_a` (`echo_link_confirmation.py:175-198`) returns the host label, the `source` field and every run of capitalised words in A's title. The check is a plain substring test (`:297-299`).
- `ons` (from `ons.gov.uk`) matches "questi**ons**" and "conditi**ons**". A title "Inflation falls to 2%" makes "inflation" a "body", so any cue containing "inflation" passes as an attribution.
- **Required:** define the check in the plan. Match whole words. A "body" is an acronym or a multi-word proper name, with a stop-list of generic words (the, report, data, survey, new, how, why…). Add a mutant for each, plus a test that a topic word from A's title does not validate.

**M7. Eval candidate and stratum details.**
- `gate_would_scope` reads only `supports`/`challenges` refs (`extract_heldout.py:62-75`; `pairs_from_prod.py`, `sides`). Before 2026-10-01 the echo gate was on, so a copy it scoped is stored as `context` and the pair is marked "would not scope". The harm stratum is undercounted. **Required:** treat refs listed in `basis.echo_scope.scoped` as sitting on their `was` side.
- The local SELECT takes every evidence row with a tier (`extract_heldout.py:49-57`), including coverage-recovery items and excluded rows. Production never inspects those: the seam runs before recovery. **Required:** drop `is_recovery` / `ev-rec-*` and excluded rows, or report them apart.
- Local dev exclusion is by dev pool id (`extract_heldout.py:22-26`), not by dev URL pair as plan §0 says. Only the prod path drops URL pairs (`pairs_from_prod.py:20-24`). **Required:** drop dev URL pairs from the local set too, or correct §0.
- The pooled pass rule is dominated by pairs the gate would never scope. **Required:** the founder audit reads every confirmed pair in the gate-would-scope stratum.

## LOW

**L1.** §2 says "Both sides empty ⇒ `not_inspected`". If B is empty, no cue can ever validate, so the call is wasted. The module already uses "either side empty" (`echo_link_confirmation.py:382`). Fix the plan text.

**L2.** §2 writes `not_inspected: cap`, but does not name the field. The module uses `detail` (`:376`), which keeps the H4 "no `reason` key" test meaningful. Name it in the plan.

**L3.** §8's baseline "158/13/11/5 + 82CF" does not match the README (canonical): `158 ok / 13 warn / 12 fail / 5 unexercised` + 82CF, with 93DD drifting in `--all` only (`tests/replay_corpus/README.md`). With the flags on, gate changes re-key relationship-review requests and can trigger recovery. Budget two `--record-missing` passes, as B4A3/93DD needed on 2026-09-29.

**L4.** §6 says CONF off with a reader on "writes the old unconfirmed chains". But under §4 the gate reads only `confirmed_copies`, so the legacy gate would be silent unless `_index_evidence` falls back to `derivation_chain`. Prefer to drop the legacy path: rollback is all flags off, which is today's state. Keep the startup warning.

**L5.** Multi-claim checks: one URL can sit in up to 3 claims' pools (`runner.py:1814`), so the same pair may be confirmed up to three times, with possibly split verdicts in one report. Deduplicate by (A url, B url) per check and share the verdict. State that the 24-pair cap is per check, and that records go to each claim map by position.

**L6.** Name the caller. The eval uses `call_google_ai_with_usage`. In production, tokens must reach `cost_telemetry` `by_stage` (V1 lost classifier tokens this way). If it goes through `analyzer._call_llm`, give it its own label branch (model and timeout, like `scope_review`). Note too that `_last_model_used` is reset at the start of every call (`claim_map_analyzer.py:2262`) and is shared with the concurrent mapping call.

**L7.** Quick tier: decide whether the stage runs under `QUICK_CONFIG` (`runner.py:68-80`). If it is skipped, declare it in `tier_limitations` (drift guard).

**L8.** `_echo_page_opening` (1,200 chars × ~40 items) is copied into the ledger snapshot `dict(ev)` (`runner.py:2408-2413`). Pop it after the join.

**L9.** `re_search` builds a fresh analyzer (`re_search.py:134`). State that `echo_join` defaults to `None` and the join is then a no-op, and test it.

## Checks that pass

- `_parse_mapping_response` has exactly three callers: `:1910`, `:1925`, `:2148`. No other code path calls it.
- Grounds claims are mapped one by one through `map_evidence_to_elements` (`claim_map_analyzer.py:2079-2084`), so `:1910` covers them.
- Every `ev_index` and basis build runs after the first parse: the main pass `:2654`, the completion census `:3736` (called after the parse, at `:1937` / `:2222`), recovery `:3958` (runner, after `map_evidence_batch` returns), passage mapping `passage_mapping.py:377-380` (inside completion, flag only), the relationship review basis (`relationship_scope_review.py:728`) and `_restore_orphaned_echoes` (`:1604`).
- Before the join, nothing reads a chain field. The batch prompt, `claim_map_input_hash` and the ledger snapshot (a copy) do not. `_fallback_mapping` (`:4085-4090`) reads none.
- The analyzer is per check (`runner.py:1475`), so an attribute on it cannot cross checks.
- The evidence dicts are the same objects from the seam to mapping (`runner.py:2466-2468`), as the prior review found.
- Strengthen has its data: `claimMap` in the snapshot is the raw snake_case claim map (`report_revisions.py:61`), so `metadata.echo_links` survives, and Evidence rows keep `evidence_id` (`models/check.py:333`).
- Records never carry `reason` (`echo_link_confirmation.py:356-364`). Metadata keys are camelCased on output (`response_builder.py:69-70`), so the test on `echoLinks` targets the right key.
- The order of work (module, then eval, then wiring) means a failed eval costs no pipeline change.
- Echo stays the last gate. No new gate is added, and `echo_scope` is already in `_SCOPE_RECEIPT_KEYS` (`:1648`).

## Answers to §10

1. **A join inside the analyzer, or a runner callback?** Inside the analyzer, in front of each `_parse_mapping_response` call. It is sound once H1 and M1 are fixed: one memoised join future, the clean-up `finally` in the runner from task creation, and a record when no join ran. A runner-level await cannot reach the point between the mapping call and the parse without a callback, which would be the same thing, less direct. Prefer passing the join in explicitly (a constructor or `map_evidence_batch` argument, default `None`) over setting an attribute from outside. Either works, because the analyzer is per check.

2. **Does any path read `ev_index` before the join?** No path reads it before the first join completes, with one exception: the concurrent retry path (H1), where a second caller can arrive while the first join is still waiting. Grounds claims are covered at `:1910`. Completion, recovery, passage mapping, the relationship review and the echo restore all run after it. The ledger snapshot is taken before the join, but it is a copy and reads no chain field.

3. **Is re-fetched text a fair stand-in?** Not as built. It is a fair source of **labels**, and arguably better than production text for judging truth. It is not a fair **model input**. Its windows are centred on the pair's shared facts, which production cannot reproduce after distil. Production uses element-chosen passages cut at 2,700 chars behind a 1,200-char opening. Pages also change between the check and the re-fetch, and the ~130 sites that refused a fetch are the ones production also mostly sees as snippet-only. Keep the labels and rebuild the model input in production shape (H2). Report the re-fetched and stored strata apart, as planned, and report how many production pairs fall to `no_verbatim_text`, so the recall figure is honest.
