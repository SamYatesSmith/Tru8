# Echo link confirmation: build plan (2026-10-05)

**Design:** `audit/2026-10-01_echo_link_confirmation_design.md`, rev 2 (§10–11). Where this plan and the design disagree, the design wins unless this plan names the change and why.
**Review:** `audit/2026-10-01_echo_link_confirmation_review.md`. M4 asked for the join with mapping to be planned and reviewed before any build. §3 below is that plan.
**Status:** plan only. Needs an independent review before any code.

## 0. Evaluation data (done 2026-10-05, free)
- Candidates: the detector at ≥ 1 derivative over local pools (317, excluding 47 dev pools) and production pools since 2026-09-09 (41 distinct claims, read-only export, founder-approved). Pools holding any dev-set URL pair are excluded. URL pairs are deduplicated.
- 378 candidate pairs. **248 usable:** 75 with stored verbatim text and 173 re-fetched from the live page (plain fetch, then Chromium for 403s, PDFs parsed). The other ~130 sites refuse automated fetches. One captcha page was caught and removed.
- 87 pools; **56 pairs the gate would scope**; rule mix 130 facts / 118 text.
- **Departure from M3 (founder-approved 2026-10-05):** 248 pairs, not ≥ 300. Reaching 300 meant ~£2 of new checks. The pass rule is a Wilson lower bound, so a smaller sample makes passing harder, not easier.
- Re-fetched text is the page opening plus up to two windows around the pair's shared non-year facts. In production the confirmer reads the stored page opening, `original_snippet` and passages. That is close, but it is not the same text, and the eval report must say so.
- Blind labels are being produced by six fresh labellers (`audit/echo_precision/heldout_batches/`, rubric `RUBRIC.md`). The founder audit (≥ 40, weighted to model-confirmed pairs) follows the paid run.
- Scripts: `audit/echo_precision/extract_heldout.py`, `pairs_from_prod.py`, `refetch_verbatim.py`, `refetch_browser.mjs`, `prep_blind_heldout.py`.

## 1. Order of work
1. **Module only, not wired** (`app/services/echo_link_confirmation.py`): candidates, prompt, call, mechanical guards, records. Unit tests and mutants.
2. **Eval harness** (`scripts/echo_link_eval.py`): runs the module's own `build_prompt` / `call` / `validate` over `heldout_all.json` twice. The eval tests the production code, not a copy.
3. **Paid eval** (ask first; quote the cost after the first 6 calls). Score against the blind labels. **Fail ⇒ stop here.** Nothing is wired.
4. Wire it in (§3–§7), the bench, the state replay, two local live checks (each paid step asked first), then switch on.

The wiring is built only after the eval passes, so a failed eval costs no pipeline change.

## 2. The module
- `candidates(ev_list) -> list[Pair]`: `find_corroborating_sources` + tier filter (primary A, reporting/commentary B). Pairs are ordered by (strong shared facts desc, text similarity desc, original_id, derivative_id) (M5), capped at `ECHO_LINK_MAX_PAIRS` = 24. Pairs over the cap get `not_inspected: cap`.
- `verbatim_text(item) -> str`: `_echo_page_opening` (a new key, copied beside `copy_page_opening` and not gated on the originator flag; H1) + `text_provenance.original_snippet` + passages. Never `text`/`snippet` on a distilled item. Both sides empty ⇒ `not_inspected: no_verbatim_text`.
- **Date check (L1):** if both dates are on the trusted `date_basis` allowlist and B predates A by > 1 day ⇒ `rejected: predates`. No call.
- `build_prompt(pairs)`: ≤ 6 pairs per call. Each side gets its host, URL, title, date and verbatim text (≤ 2,700 chars), marked as untrusted data. No claim text. The rubric is the labellers' rubric, compressed.
- Call: `ECHO_LINK_MODEL` = `gemini-3.7-flash`, output cap 8192, 40 s per call, calls concurrent, a 45 s stage deadline (M4).
- Output per pair: `verdict`, `extent`, `cue_kind`, `cue`, `reason`.
- `validate(pair, out)` (M2, fail closed): cue ≥ 12 chars and verbatim in B. `attribution` must name A's host label, publisher or a body in A's title. `copied_text` must be ≥ 40 normalised chars and also verbatim in A. `named_document` must appear in A's title or text. Any failure ⇒ `cue_not_found`.
- A link exists only for `relay` + a validated cue. `extent=whole` feeds the gate; both extents feed the note.
- Records: `{original_id, derivative_id, status, extent, cue_kind, cue}`. **No `reason`** (H4); the reason is logged only. Run totals: `{pairs, calls, confirmed, rejected, unclear, cue_not_found, not_inspected, failed, seconds}`.

## 3. The seam: overlapping with mapping (M4)
Today `annotate_post_classify_structure(evidence)` runs synchronously after classify + distil (`runner.py:2342`), then `map_evidence_batch` (`:2482`). The scope gates (echo LAST) run inside the synchronous `_parse_mapping_response` (`claim_map_analyzer.py:2636`, `ev_index` built at `:2654`).

**Plan:**
1. `annotate_post_classify_structure` keeps F4 repetition as it is, clears `derivation_chain` and `confirmed_copies` on every item (L3), and, when the stage should run (§6), returns a **started task**: `asyncio.create_task(confirm_pool(evidence))`. Candidates are computed before the task starts, so the task only does model calls.
2. The runner hands the task to the analyzer: `analyzer.echo_join = EchoJoin(task, deadline)`.
3. **Join point:** a new `await self._join_echo_links()` immediately before each async-path call to `_parse_mapping_response`. There are three sites: `:1910` (single-claim; also the grounds path), `:1925` (null-reasoning retry, a no-op after the first join) and `:2148` (batch). The join is idempotent: the first call awaits the task (bounded by the deadline), writes the fields onto the shared evidence dicts and stores records in each claim map's metadata. Later calls return at once.
4. **Deadline:** the 45 s budget starts when the task starts, so mapping time (≈ 11–15 s, longer on batches) overlaps it. At the join, `asyncio.wait_for(shield(task), remaining)`. On timeout, finished calls keep their results, unfinished pairs get `not_inspected: deadline`, and the task is cancelled.
5. **Cleanup:** `analyze` wraps mapping in `try/finally: echo_join.cancel()`. A mapping timeout or error cannot leave a model call running behind the watchdog.
6. **What sees the fields:** the main gate pass (`:2654`), the completion census (`:3736`) and the recovery index (`:3958`) all build their index after the join, so they all see the confirmed fields. Recovery items carry none, as today.
7. `stage_timings["echo_link_confirmation"]` = the task's own wall time; `stage_timings["echo_link_wait"]` = how long the join actually blocked mapping. The second figure is the latency cost.

**Why not a separate stage before mapping:** with one call per check at 7–25 s (the relationship review's measured range), a sequential stage adds that much wall time to every check that has a candidate. Overlapping hides most of it behind mapping's own call.

## 4. Fields and readers (H2, L2)
- `confirmed_copies` on A: confirmed `whole` derivatives (≥ 1). `_index_evidence` builds `original_of` from `confirmed_copies` (first confirmed original per copy, ordered as in §2; L2). The `echo_scope` receipt gains `cue` and `cue_kind` from that same pair.
- `derivation_chain` on A: confirmed derivatives (`whole` or `part`), written only when there are ≥ 2. The note reads it unchanged. No frontend or parity change.
- New test: two originals, each with one confirmed copy on the same side ⇒ no echo note.

## 5. Strengthen, replay, stored reports
- **Strengthen (H3):** `research_claim` rebuilds `confirmed_copies` / `derivation_chain` on `existing` from `metadata.echo_links` before re-mapping, with no call. New re-search items get `not_inspected: re_search`. Test: a Strengthen run keeps an echo-scoped copy scoped.
- **Frozen replay (M5):** under `_is_frozen_evidence_replay` the stage makes no call and rebuilds from stored `echo_links`. Bench cassettes take the new requests through `--record-missing` (paid, small; ask first).
- **Stored reports (L5):** not rewritten.

## 6. Flags (L4)
`ENABLE_ECHO_LINK_CONFIRMATION` (new, default False), `ENABLE_DERIVATION_CHAINS`, `ENABLE_ECHO_SCOPE_GATE`. The stage runs only when CONF is on and at least one reader is on. CONF off with a reader on writes the old unconfirmed chains (rollback only) and logs a startup warning. `audit/FLAGS.md` is regenerated in the same commit.

## 7. Public payload (H4)
`metadata.echo_links` holds no `reason`. A test asserts the `/r/` JSON for `echoLinks` has no `reason` key. The existing `scopeReview.pairs[*].reasoning` exposure on `/r/` is still a separate founder item.

## 8. Tests and checks
- Module: the cue validators (each kind, each failure), the date check, the cap order, the deadline, error and invalid-JSON handling (no link), no claim text in the prompt, no `reason` in records.
- Seam: join idempotence, the deadline path, cancel on a mapping failure, the fields seen by all three index sites, the frozen-replay rebuild, the Strengthen rebuild, the flag matrix.
- Mutation run on the validators and the join. An **independent verifier** (not the builder) checks the build against this plan and the design.
- Bench `--all` flags off (must match baseline 158/13/11/5 + 82CF) and flags on (only echo receipts and support counts may move).

## 9. Pass criteria for the paid eval (design §10 M3, unchanged)
On confirmed links: Wilson 95% lower bound ≥ 80% and point estimate ≥ 90% relay. Flip rate ≤ 5% between two runs. Report recall, the cue-not-found rate, failures, p90 seconds, tokens per pair and the real cost per check. Report the gate-would-scope stratum separately. Report stored-text and re-fetched-text pairs separately.

## 10. Questions for the reviewer
1. Is a join inside `map_evidence_to_elements` / `map_evidence_batch` sound, or should the runner await the task between the mapping call and the parse? (The parse is inside the analyzer, so the runner cannot reach that point without a new callback.)
2. Shielding plus a deadline at the join: does any path read `ev_index` before the join? (Grounds claims go through `map_evidence_to_elements`, so `:1910` covers them.)
3. Is re-fetched text a fair stand-in for the production input for the purposes of the eval?

---

## 11. Rev 2: every finding of the plan review taken (`2026-10-05_echo_link_confirmation_build_plan_review.md`, APPROVE WITH CHANGES, 2 HIGH)
Where rev 2 and §§0–10 disagree, rev 2 wins.

**H1, one shared join.** The join is a single memoised future: the first caller creates it with a check-and-set (no await in between), and every caller awaits that same future. No caller returns before the fields are written. Seam test: a failed batch → two concurrent `map_evidence_to_elements` retries → both gate passes see `confirmed_copies`.

**H2, production-shaped model input (DONE, 2026-10-05).** `audit/echo_precision/build_model_inputs.py` builds each side the way production does. A stored side gets its stored text plus a re-fetched page opening where one exists (178 sides; 20 without). A re-fetched side gets its full page text run through `copy_page_opening` + `capture_text_provenance` with the check's own claim and elements (297 sides). The module's `verbatim_text` and `build_prompt` then run unchanged. The labels are unchanged. 247 of 248 pairs; one page has gone. **Caveat for the report:** trafilatura and Chromium are not the production extractor, and pages change between check and re-fetch. Re-fetched sides have no original search snippet (less text than production: the conservative direction). The optional "shared facts first" ordering is NOT built (v1 keeps production's order).

**M1, clean-up.** A `try/finally` in the runner from task creation to the end of mapping cancels the task and clears the join. Chunks run as separate tasks. At the deadline, `asyncio.wait(timeout=…)` keeps the finished ones and marks the rest `not_inspected` (`detail: deadline`). A done-callback retrieves the task's exception. If no join ran (every claim fell back), each claim map gets totals with `detail: mapping_failed`.

**M2, budget.** The join waits at most `min(remaining, 15 s)`, then `detail: deadline`. `analyze_timeout` rises by 15 s in the same commit. `echo_link_wait` p90 is reported from the live checks.

**M3, explicit rank.** Records are stored in §2 order. `confirmed_copies` = `[{"id", "rank", "cue", "cue_kind"}]`. `_index_evidence` keeps the lowest rank, not the first in pool order. `echo_scope` takes `cue`/`cue_kind` from that record, and the citation-path `_replace` carries them. Test: the same records over two pool orders give the same original and cue.

**M4, frozen replay.** The stage does not run under frozen replay; totals carry `detail: frozen_replay`. "Rebuild from stored `echo_links`" is dropped from §5 and from design M5.

**M5, the note.** Per side, only copies whose original is counted on that same side are counted. Backend only (`claim_map_analyzer.py` basis); the TS and Python readers read numbers alone. A test covers the review's two-originals case.

**M6, attribution names (DONE, 2026-10-05).** Names match as whole words, and only names that stand for a body count:
- A host label of ≤ 4 letters matches only as an acronym or a capitalised word (ONS/Ons). A label that is a common word matches only as an acronym (WHO, never "who").
- A compound label also matches when written as words (metoffice → "Met Office").
- A domain-shaped `source` reduces to its label. A single common word is ignored.
- From A's title, only two kinds count: acronyms outside a place/measure list (UK, US, GDP, CPI…), and multi-word proper names containing an organisation word (Office, Bank, Institute, University…).
- 53 unit tests; 19/19 mutants killed.

**M7, eval data (DONE, 2026-10-05).**
- `gate_would_scope_v2` reads refs the old gate scoped back onto their `was` side: 56 → 99 pairs.
- 2 pairs repeating a dev URL pair are dropped.
- Recovery items (`ev-rec`, `ev-rpf`; 66 pairs) never reach the stage. They are scored as a separate stratum, not in the main figure.
- **Main scored set: 179 pairs (33 relay / 137 independent / 9 unclear); gate stratum 82 (16 / 63 / 3).**
- The founder audit reads every confirmed pair in the gate stratum.
- Excluded rows: prod pools carry no `receipt_status`. Tiered rows that were excluded after classify may remain, and that limit is stated in the report.

**L1** either side empty ⇒ `not_inspected` (as built). **L2** the field is `detail`. **L3** the bench baseline is the README's: 158/13/12/5 + 82CF; budget two `--record-missing` passes. **L4** the legacy unconfirmed path is dropped: CONF off ⇒ no chains, no `confirmed_copies`; rollback = all flags off. The startup warning stays for a reader-on/CONF-off configuration. **L5** pairs are deduplicated by (A url, B url) per check, with one shared verdict. The 24-pair cap is per check. Records go to each claim map by position. **L6** the call goes through the analyzer with its own label branch (`echo_link`, its own model and timeout) so tokens reach `by_stage`. `_last_model_used` is not read for it. **L7** quick tier: the stage is skipped under `QUICK_CONFIG` and declared in `tier_limitations` (drift guard). **L8** `_echo_page_opening` is popped after the join. **L9** `echo_join` defaults to `None`, and the join is then a no-op (re_search); a test covers it.

**Guard ceiling (free check, 2026-10-05).** The labellers' own cues for the 35 relays were run through the guards: 13 pass, 22 would be blocked. Most of the blocked cues are copied figures or table rows that are not verbatim in A's shown text, or attributions to a study by name rather than its host. The model chooses its own cue, so this is not the recall figure. But recall may fall short of 60%, and that is a guard cost the eval must report.

## 12. Paid eval result (2026-10-05): FAILS the pre-registered rule. Precision clean, recall low.
Two full runs on production-shaped input (`audit/echo_precision/eval_runs/r1.json`, `r2.json`). Probe + runs cost $0.95 (≈ £0.72); founder-approved.

| | r1 | r2 |
|---|---|---|
| Main set (179 pairs, 33 relay / 137 independent): confirmed | 9, all relay | 9, all relay |
| Wilson 95% lower bound (pass ≥ 0.80) | **0.70** | **0.70** |
| Recall (target ≥ 60%) | **9/33 = 27%** | 9/33 = 27% |
| Gate stratum (82 pairs): confirmed / recall | 4, all relay / 4/16 | 3, all relay / 3/16 |
| Independents confirmed (main) | 0 of 137 | 0 of 137 |
| Flip rate (pass ≤ 5%) | 3/247 = 1.2% | |
| Cost per run / per pair | $0.46 / $0.0019 | $0.48 |
| Call seconds p50 / p90 / max | 4.0 / 6.9 / 14.4 | 3.7 / 7.2 / 23.9 |

**Reading:**
- **Precision: no false confirmation in 19.** Across 274 independent judgements (137 × 2), the stage confirmed none. That is the harm the stage exists to prevent.
- **The lower bound fails on sample size alone.** With 9 confirmations, even 9/9 gives 0.70. A lower bound of 0.80 needs about 16 confirmations with none wrong.
- **Recall is 27%,** and it is lost two ways (r1, the 33 main relays plus 2 recovery):
  - **The mechanical guard blocked 11 relays the model called correctly.** The cue named a body that is not A's host, publisher or title body: Japan's Statistics Bureau for stat.go.jp, a journal for a PubMed page, a report title not in A's title. Or the model chose `copied_text` where the copied words were not in A's shown text.
  - **The model rejected 14.** Several of those labels look wrong on reading the reasons: B forecasting upcoming ONS figures (h137), B reporting a different month (h159), a different Met Office release (h145), A a Wikipedia page (h174), a different judge (h111). The founder label audit is owed and will move the recall figure.
- **Per design §6: fail ⇒ stays off.** No guard or threshold is tuned on this held-out set. Any change needs a fresh draw.
- Rejected cues were not stored on `cue_not_found` records, so the guard misses cannot be re-checked offline. A future eval run should keep them in the eval output only.

## 13. Decision after the failed eval, and the wiring as built (2026-10-05)
**Founder decision: wire it anyway, flag off.** §12 failed the pre-registered rule on two counts: 9 confirmations cannot reach a 0.80 lower bound, and recall was 27% against 60%. The harm the rule guards against never appeared, though: 0 independents confirmed in 274 judgements. Two further facts informed the decision:
- **A− #8** carries the missed copy "According to the University of Galway…", which is an attribution relay of exactly the kind the stage confirms.
- With the gate off since 1 Oct, #8 and #9 count every copy as independent support.

The founder's instruction was "whatever's logical". The logical course is a safe stage that hides about a third of real copies, against a gate that hides none. **This overrides §6 ("fail ⇒ stays off") knowingly.** The switch-on still needs the paid bench `--record-missing` and two live checks.

**Independent verification** (`audit/2026-10-05_echo_link_confirmation_verification.md`, PASS WITH FIXES). Every finding was taken:
- **H1:** no test ran the real mapping paths with a join. They now do: single-claim, batch, and the concurrent per-claim retries after a failed batch reply. The runner step became the tested helpers `plan_for_check` / `start_for_check` / `map_with_join`. The cancel test is no longer vacuous.
- **M1:** the cue must match the source case as well (whitespace only is collapsed), so "WHO" no longer stands for "who". The stored cue is the verbatim form.
- **M2:** the stage is **skipped on the quick tier** with a `quick_tier` receipt: its 30 s wall clock cannot hold the join, and the eval never measured heuristic tiers. `tier_limitations` declares `no_echo_link_confirmation` for quick only while the stage is on.
- **M3:** the note counts copies **per original** (the most any one on-side original has), so two originals with one copy each no longer reads as "repeat a single original".
- **M4:** this section.
- **LOW:**
  - Planning and start faults are guarded and receipted (`planning_failed`, `start_failed`).
  - `run_seconds` is the task's own time.
  - Stale config comments were fixed.
  - Echo tokens share the analyzer's usage and are not split out in `by_stage`; noted, not built.
  - `corroboration.annotate_derivation_chains` no longer has a pipeline caller. Its own tests still pin it.
- **Checks:** unit suite green; module 19/19, seam 22/22 + 1 mutants killed.

## 14. Flag-on verification (2026-10-05): safe, but no visible effect. NOT switched on.
**Bench, flags on** (`--record-missing`, 9 claims; 82CF excluded as known drift): every claim's ok/warn/fail line is identical to the flags-off run. Three cassettes gained a few echo calls (5647, B4A3, 0004), costing a few pence. The flags-off bench on the patched cassettes is unchanged: 158/13/11/5 + 82CF.

**Two local live checks** (`audit/echo_precision/live_checks.py`, payloads in `live_checks/`; 9p and 6p; the echo run took 9.0 s and 2.7 s and fully overlapped mapping, with join wait 0.0 s):
- `676ffb49` (A− #8 input, Galway reefs): 2 pairs.
  - Confirmed, whole: Irish Mirror ← the university release. The cue is an attribution naming Galway, Ifremer and the Sorbonne. Correct.
  - The independent.ie pair had no verbatim text.
- `bea9b8d7` (UK CPI, July 2025): 10 pairs.
  - Confirmed: Trading Economics, whole ("source: Office for National Statistics"), and BBC, part ("tracked by the ONS"). Both correct.
  - 3 were rejected `predates` because the ONS bulletin's stored date is later than its real one; safe, but recall lost.
  - 4 had no verbatim text (FT, BBC live pages).
- **The gate scoped nothing in either check.** It fires only when the original is counted on the same element. In practice the original is often missing or filed as context while its copies support. On Galway, four rewrites of the release support e2 and the release is not on e2. That is A− #8's S4 pattern, and this rule cannot reach it.

**Decision pending (founder):**
1. A counting rule: copies of one confirmed original count once per side, even when the original is not counted. Difficulty 3; design and review first; testable offline on stored checks.
2. Leave echo off and go to the next A− blocker.

**Found on the way (not echo):** `676ffb49` shows a TRUE claim as `disputed`.
- Decomposition made e1 "23 structures at Porcupine Bank" from "23 structures … on the Porcupine Bank … and in the Bay of Biscay" (a shared total split across conjoined places).
- The relationship review then correctly scoped every support (measure mismatch), and one source saying "a total of 23 … across both" became a challenge.
- This is a hard H1-class fault (wrong badge).
