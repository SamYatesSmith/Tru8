# Echo link confirmation wiring: independent verification (2026-10-05)

**Change verified:** the uncommitted echo link confirmation wiring in the working tree (`app/services/echo_link_confirmation.py`, `runner.py`, `claim_map_analyzer.py`, `re_search.py`, `config.py`, `models/claim_map.py`, `main.py`, the new seam and module tests, the edited echo tests, `audit/FLAGS.md`).
**Against:** build plan rev 2 (§11) and §12, the plan review, design rev 2 §10.
**Verifier:** independent; did not write the code. Nothing in the repo was changed apart from this file.
**Run:** `pytest tests/unit` = 4,457 passed, 44 skipped. The five echo test files = 108 passed. Probes were run from a scratch script, not from the repo.

## Verdict: PASS WITH FIXES

The seam is sound. With all three flags off, behaviour on the main pipeline is identical to before. The shared join, the deadline, the clean-up and the ranks all behave as rev 2 asks. Echo is still the last gate, and `_SCOPE_RECEIPT_KEYS` has not changed.

One HIGH: the seam that the whole feature depends on has no test. Fix it before the flags go on. Four MEDIUMs follow: a casing hole in the cue guard, the quick-tier deviation, a residual note misfire, and records that were wired despite the failed eval (the founder's decision, so this one is about the record only).

## HIGH

**H1. The join call sites and the runner clean-up have no test. One "cancel" assertion passes vacuously.**
- Rev 2 H1 asks for this seam test: "a failed batch → two concurrent `map_evidence_to_elements` retries → both gate passes see `confirmed_copies`". Plan §8 also asks for "cancel on a mapping failure" and "the fields seen by all three index sites".
- No test calls `map_evidence_to_elements` or `map_evidence_batch` with an `echo_join` set. `test_echo_link_seam.py` is the only test file that mentions `echo_join` or `EchoJoin`, and it calls `_join_echo_links()` directly.
- So any of these mutants leaves all 4,457 tests green:
  - deleting `await self._join_echo_links()` at `claim_map_analyzer.py:1943` or `:2173`;
  - deleting `echo_join.close()` at `runner.py:2523`;
  - deleting the `+15` at `runner.py:2482`.
- `test_close_without_a_join_says_mapping_failed_and_cancels` (`test_echo_link_seam.py:215-230`) checks `join._task.cancelled() or join._task.done()` after `asyncio.run` returns. `asyncio.run` cancels every task still running at shutdown, so the check passes whether `close()` cancels or not. Verified: a `close()` mutant that never cancels survives that test.
- Fix: add (a) an analyzer test that maps a pool with a gate-on `echo_join` through `map_evidence_to_elements` and through `map_evidence_batch` (including the failed-batch retry path), and asserts the `echo_scope` receipt; (b) a runner test (or a narrow helper extracted from the runner) proving `close()` runs when mapping raises or times out; (c) in the cancel test, assert `_task.cancelled()` inside the coroutine, after one `await asyncio.sleep(0)`, before `asyncio.run` returns.

## MEDIUM

**M1. The attribution guard checks the model's casing, not the source's. A common word can pass as an acronym, and the stored cue need not be verbatim.**
- `validate` checks that the cue is in B after `_norm` (casefold plus whitespace) (`echo_link_confirmation.py:357`). Then it runs the case-sensitive name patterns on the model's own `cue` (`:360-361`). It stores `cue.strip()`, which is the model's text, not B's (`:373`).
- Probe: A = `who.int`, B = "Experts who said the malaria figures…", model cue "Experts WHO said the malaria figures" → `confirmed`. Rev 2 M6 says "WHO, never who". The same applies to "Ons" inside "the ons questions".
- The stored cue then goes into `basis.echo_scope.scoped[*].cue` and `metadata.echo_links`, which are public on `/r/`, in a form that is not in the source.
- Fix: find the cue's span in B's actual text (case-insensitive, whitespace-tolerant). Run the name patterns on that span and store it. Add the "who" → "WHO" case as a mutant test.

**M2. Running in the quick tier (the deliberate deviation) is not sound as built.**
- Quick checks run under a hard `asyncio.wait_for(..., timeout=config.max_wall_time_seconds)` = **30 s** (`agent.py:925-933`, `:965-973`; `runner.py:72`). The join can add up to 15 s (`JOIN_WAIT_S`), and the eval's call max was 24 s. One slow echo call can push a quick check past 30 s, and then the paid agent call fails.
- Quick uses heuristic tiers (`enable_llm_classifier=False`, `runner.py:2199-2208`). The eval ran only on LLM-classified pools, where A was a primary by the classifier's judgement. The prompt tells the model that "A is a primary source". In quick tier that input has not been measured.
- Cost: $0.0019 per pair. At 8 sources per claim this is a few pence per check, against a $0.07 price. That is material.
- Not declaring it in `tier_limitations` is right as far as it goes: quick gets the stage, so nothing is withheld. But the question L7 asked was whether quick *should* get it.
- Fix: skip the stage under `config.mode == "quick"` and write a `detail: quick_tier` totals receipt. Because no `PipelineConfig` field changes, the drift guard does not need a new slug. Alternatively, give quick a join cap of 2–3 s. Either way, state the choice in the plan.

**M3. The note can still say "repeat a single original" when there are two originals.**
- The M5 change counts a copy only when one of its originals is on the same side (`claim_map_analyzer.py:1373-1384`). But the note fires on `originals ≥ 1 and derivative_count ≥ 2` (`support_structure.py:86-88`), and `originals` counts every on-side primary that has a chain.
- Probe: A has chain [B1, B2] and D has chain [C1, C2]. A, B1, D and C1 all support. Result: `{"originals": 2, "derivative_count": 2}`, so the note says "Several of these sources repeat a single original report." That is false, and it makes the element a candidate for a paid Strengthen.
- The plan §4 / design H2 test, "two originals, each with one confirmed copy on the same side ⇒ no echo note", only passes in its trivial form: one confirmed copy writes no chain at all (`test_one_confirmed_copy_writes_no_note_chain`).
- Fix: in the backend only, set `derivative_count` to the largest number of on-side copies of any one on-side original. The TS reader reads only the numbers, so parity is unchanged. Add the probe above as a test.

**M4. The wiring went in after a failed eval. The plan does not record why.**
- Plan §1.3: "Fail ⇒ stop here. Nothing is wired." §12: "FAILS … fail ⇒ stays off." The founder's "build the wiring anyway" decision is recorded only in `audit/OPEN_WORK.md` (2026-10-05 entry). The module docstring still says "This module is not wired into the pipeline until the held-out eval passes" (`echo_link_confirmation.py:17`). The `config.py` comment does give the eval numbers.
- Switching the flags on goes against the pre-registered rule. That is a founder call, separate from merging the code with the flags off.
- Fix: add a §13 to the build plan recording the founder's decision, and that switch-on is a separate decision. Correct the docstring.

## LOW

**L1. `prepare` and `EchoJoin.start` are not guarded.** They run synchronously in the runner (`runner.py:2344`, `:2475`). An exception in the candidate or triage code would fail the whole check, although the stage is meant to fail closed. The same applies to `rebuild_after_research` in Strengthen (`re_search.py:139`). No input that raises was found. Fix: wrap each in `try/except Exception` → `skip(..., "failed")` (or clear the links), and log.

**L2. `stage_timings["echo_link_confirmation"]` is not the task's own wall time.** `run_seconds` is measured from the task's start to the end of the join (`echo_link_confirmation.py:817`), so it includes the time the finished task sat waiting for mapping. Plan §3.7 asks for the task's own time. Fix: use `result["stats"]["seconds"]`.

**L3. Echo tokens land in `by_stage["analyzer"]` and cannot be separated from mapping.** `call_echo_link` accumulates into the analyzer's usage (`claim_map_analyzer.py:2487-2489`), which is good enough for the total. The live-check step must report the "real cost per check" (plan §9), and that needs the echo tokens on their own. Fix: keep a separate `_echo_usage` counter and add it as `by_stage["echo_link"]`.

**L4. Stale text.** The `ENABLE_DERIVATION_CHAINS` comment (`config.py:764-769`, and therefore `audit/FLAGS.md`) still names `annotate_derivation_chains` as the writer. That function now has no caller (`corroboration.py:524`). Fix: reword the comment, regenerate FLAGS.md, and delete the function or mark it unused.

**L5. `named_document` accepts generic phrases.** "the annual report said" validates when it also appears in A's text (probe). That matches the design's rule ("present in A's title or text"), so this is a design limit, not a build fault. Report it with the founder label audit.

## Checks that pass

- **Rev 2 items, code-relevant:**
  - **H1 shared future:** check-and-set with no await between (`echo_link_confirmation.py:798-802`). Every caller awaits `shield` of the same future. `apply_records` runs once (`test_the_join_runs_once_for_every_caller`).
  - **M1:** the `try/finally` runs from task creation to the end of mapping, with no await between `EchoJoin.start` and `try` (`runner.py:2475-2526`). Chunks run as separate tasks, and `asyncio.wait` keeps finished chunks (`:473-503`; `test_finished_calls_survive_the_deadline`). The done-callback retrieves exceptions (`:785`). If no join ran, the totals say `mapping_failed` (`:849-857`).
  - **M2:** the join wait is capped at 15 s, and the stage deadline is 45 s from task start. `analyze_timeout` gains 15 s only when a join exists.
  - **M3:** records are ranked. `_index_evidence` keeps the lowest `(rank, id)` (`claim_map_analyzer.py:1730-1737`). The citation-path `_replace` carries the cue (`:3534-3538`). There is a test over two pool orders.
  - **M4:** frozen replay skips and writes a `frozen_replay` receipt (`runner.py:2471-2473`).
  - **M6:** whole-word matching and acronym-only matching for common words are implemented, apart from the casing hole in M1 above.
  - **L1:** either side empty ⇒ `not_inspected`. **L2:** the field is `detail`. **L4:** the legacy path is gone and the startup warning is in place (`main.py:78-87`). **L5:** pairs are deduplicated per check by URL, the cap is per check, and records go to each claim by its own ids (`test_a_pair_shared_by_two_claims_is_judged_once`). **L6:** `call_echo_link` has its own model, schema and timeout, has no OpenAI fallback, and does not touch `_last_model_used`. **L8:** the page opening is popped in `prepare`, before the ledger snapshot at `runner.py:~2408`. **L9:** `echo_join` defaults to `None`, and the join is then a no-op (test).
- **Async seam:**
  - Every `_parse_mapping_response` call, and every gate `_index_evidence` build, runs after the join. The three parse sites follow a join at `:1943` or `:2173`. The batch path joins before its retries, so the H1 race cannot happen there. Grounds claims are mapped one at a time through `:1943`. Completion (`:3831`), passage mapping and the relationship review run inside completion, after the join. Recovery (`:4053`) runs after mapping and indexes only new items. In Strengthen and recovery, `echo_join` is `None` after the `finally`.
  - The join also runs when the mapping call returns `None`, so the fallback path still writes records.
  - Probe: a mapping caller cancelled mid-join, then `close()` → both tasks done, no pending tasks, no "never retrieved" errors from the loop's exception handler.
- **Flags off (the defaults):**
  - `should_run()` is False. No page-opening copy, no `prepare`, no join, `analyze_timeout` stays 120, and no `echo_links` metadata is written.
  - `clear_links` pops the same `derivation_chain` as before, plus a `confirmed_copies` key that never exists when off.
  - `_index_evidence` gives `original_id=None` as before.
  - `derivative_ids` is `{}`, so the basis output is unchanged.
  - The echo receipt entry adds `cue` only when there is a cue.
  - Prompts and `_call_llm` change only in formatting, so cassette keys do not move.
  - One deliberate difference: Strengthen now clears any retrieve-time `derivation_chain` on new items. It is the safe direction and matches the flags-off intent.
- **Invariants:**
  - Echo is still the last of the default gates; only the flag-only `fact_applicability` comes after it, as before.
  - `_SCOPE_RECEIPT_KEYS` is unchanged (`:1651`).
  - The gate logic is unchanged and reads `was` / the side, so it treats supports and challenges alike.
  - Every inspected or uninspected pair gets a record (`cap`, `predates`, `no_verbatim_text`, `deadline`, `failed`, `re_search`).
  - Records never carry `reason`. Totals hold only counts and seconds (`test_public_payload_has_no_model_reason`).
  - The claim text never enters the prompt.
- **Production shape:**
  - `runner.py` and `re_search.py` use CRLF throughout, with no mixed endings. `core.autocrlf=true` stores them as LF, as `HEAD` is.
  - Evidence ids are URL+text hashes, so multi-claim fan-out by member ids is safe.
  - Items without `evidence_id` are never candidates. Items without `url` key on `evidence_id`.
  - Strengthen `existing` items without `tier` simply produce no candidates.
  - A check that predates the feature has no `echo_links`, so Strengthen writes no links. That matches the old behaviour: chains were never persisted on Evidence rows.
  - `ClaimMapAnalyzer` is per check, so `echo_join` cannot cross checks.
