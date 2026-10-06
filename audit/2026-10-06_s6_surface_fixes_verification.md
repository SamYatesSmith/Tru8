# S6 surface fixes — independent verification (2026-10-06)

Verifier: independent agent (did not build). Scope: the four uncommitted S6 fixes
(video entities, cumulative scope-review receipt, breadcrumb titles, stale futurity).
Nothing fixed, nothing committed, nothing paid run, replay bench not run.

## Verdict: PASS WITH FIXES

Fixes 1, 2 and 3 are sound enough to ship. **Fix 4 should be narrowed before it
ships.** As written it drops genuine caveats (HIGH-1, HIGH-2), and its only record
of a drop is a log line (MEDIUM-1).

## Findings

### HIGH-1: Fix 4 drops a caveat when the futurity cue and the past date are about different things
`backend/app/utils/stale_futurity.py:116-121` (`asserts_past_as_future`). The rule
is "any futurity cue anywhere, and every date in the note is past". The cue is
never tied to the date. Checked on 2026-09-30, each of these real-shaped
evidential-limit caveats is **dropped**:
- "Evidence covers 2024; forthcoming ONS revisions may change this."
- "The 2025 figures may be revised in an upcoming review."
- "Data runs to 2025; the next census will take place later."

The same helper filters `scope_caveat` → `scope_reach` (`claim_map_analyzer.py:2821`),
which feeds the F3-B2 reach caveat. A reach caveat such as "covers England and
Wales in 2025; upcoming 2026 data …" disappears the same way. This removes
honest uncertainty from the report, the opposite of what S6 intends.

### HIGH-2: Fix 4 treats a bare current-year date as past
`stale_futurity.py:107-108` (`return year <= ref.year`). The docstring calls this
"the rule asked for", but here is what it does. The following are **dropped** although each event is
genuinely in the future:
- "The upcoming 2026 US midterm elections have not yet occurred.", checked 2026-03-01.
- "The election is a future event scheduled for later in 2026.", checked 2026-06-01.
- "The upcoming Q4 2026 results." / "The upcoming winter 2026 figures.", checked 2026-09-30. Quarter and season words are not parsed, so only the bare year is seen.
- "Budget for fiscal year 2026-27 is upcoming." / "The upcoming 2026/27 season.". `_YEAR` reads only `2026`; the `-27`/`/27` end year is ignored.

The S6 trigger case ("a future date in 2026" on an 8–11 Sept poll) is caught only
because the year is treated as over. For roughly the first eleven months of each
year, this throws away correct caveats about the rest of that year. Suggested
direction (not applied): drop on a bare year only when it is strictly before the
check year, and drop on a current-year date only when month and day are stated.

### MEDIUM-1: Fix 4's drop leaves only a log line, not a receipt (invariant #5)
`claim_map_analyzer.py:135-149`. The dropped text goes to `logger.info` and
nowhere else. Every other mechanical removal of mapper output in this pipeline
leaves a receipt in the element's `basis` (scope gates, `precision_stripped`,
`grounds.specificity`). A reader of the record or an auditor cannot see that a
note was removed. Railway log retention is the only trace. A drop should leave a
basis key, e.g. `basis.stale_futurity = {field, dropped_text, reference_date}`.
That key would then enter the signed basis for new checks.

### MEDIUM-2: Fix 3's `<h1>` fallback can promote non-headline `<h1>`s
`backend/app/utils/page_title.py:136-146`. The only checks on the first `<h1>` are: not junk
(bot-wall markers only), not a breadcrumb, and not exactly equal to the
title's site suffix. Observed results when `<title>` is a breadcrumb:
- `<title>News | Acme</title>` + `<h1>Page not found</h1>` → title **"Page not found"** (a soft 404).
- `<title>Media | Ofcom</title>` + `<h1>Cookies on this site</h1>` → **"Cookies on this site"**.
- `<title>News | Example</title>` + logo `<h1>Example News</h1>` → **"Example News"** (logo variant ≠ suffix).

The old title was already a bad breadcrumb in each case, so the user is no worse
off for the logo case. "Page not found" is worse: it misdescribes a live source.
Note that `evidence.py:556` uses the page title **instead of** the search
provider's title whenever one is returned. Returning `None` on an all-breadcrumb
page, so the search title survives, may be the better fallback.

### MEDIUM-3: Fix 3's hidden-child stripping drops visible text
`page_title.py:94-104` (`_visible_text`). Two patterns are stripped even though they are visible:
- The class `hidden` is used for Tailwind responsive patterns. `<h1><span class="hidden md:inline">Acme wins </span>contract for harbour bridge</h1>` → **"contract for harbour bridge"** (visible on desktop).
- `aria-hidden="true"` hides from screen readers, not from the screen. `<h1>Storm <span aria-hidden="true">Eunice</span> closes schools across Wales</h1>` → **"Storm closes schools across Wales"**.

Exposure is limited because this runs only when every meta/`<title>` candidate is a
breadcrumb. Suggested fix: drop `aria-hidden` from the rule, and treat `hidden`
as hidden only when the element has no responsive `*:inline`/`*:block`-style class.

### LOW-1: Fix 1 decodes video text twice on new rows
`checks.py:2660-2663` (`_unescape`) plus `youtube.py:83-85`. The code comment says "Idempotent here". It is not: a
title that literally contains entity text ("Use &lt; in HTML"; the API sends
`&amp;lt;`) is decoded to `&lt;` at ingest and to `<` when served. This is rare and
cosmetic.

### LOW-2: Fix 2 has an untested branch (mutant 2b survived)
`relationship_scope_review.py:400-402`. Failures are read from `current` (all
runs since the last full run). The tests would also pass if failures were read
only from the newest run. One case is not covered: a failed `restored_only` run followed by a
second empty run (for example [full ok, echo failed, echo not_run]).

### LOW-3: Fix 2 roughly doubles the stored receipt size
`relationship_scope_review.py:410-428`. Every pair record is stored in the top-level `pairs` and
again in `latest_run`/`prior_runs`. A pair record carries `original_ref`, a quote of
up to 600 characters and reasoning. This rides in `claim_map` on every owner and public payload.

### LOW-4: Fix 2 reads v3 echo runs as full-scope runs
`relationship_scope_review.py:388-391`. A stored v3 history entry has no `scope` key, so a v3 echo run
counts as `all` and its leftovers supersede the main run's. This affects only
pre-2026-10-06 claim maps that are re-mapped, and the count it skews is `uninspected_pairs`.

### LOW-5: Fix 4 depends on the wall clock
`claim_map_analyzer.py:134`. `reference` defaults to `datetime.now(utc)`, so a
cassette replay of the same mapping response can keep or drop a note depending on
the run date. No current corpus note is known to sit on that edge. This is a slow
nondeterminism source for the bench.

### LOW-6: Fix 3 can re-key bench cassettes (not verified)
Evidence titles enter mapping and classification prompts, and the prompts are
cassette keys. Any corpus page whose `<title>`/`og:title` is a breadcrumb now gets
a different title. If the bench replays fetched HTML through
`_extract_title_from_html`, those claims will show `cassette_drift`. Read the
running bench's drift lines with this in mind before blaming other changes.

## Correctness checks that passed

- **Fix 1 coverage.** All five video serialisers in `checks.py` now go through `_video_to_dict`: `GET /{id}/videos` (2656), `/videos/recover` both returns (2728, 2768), public `/r/` payload `get_public_check` (2995), and `GET /public/{id}/videos` (3024). No backend PDF/export path prints videos. Grep of `app/` found no other reader of `VideoRecommendation`, and `response_builder`/agent/MCP payloads carry no videos. The VARCHAR(500)/(200) limits are safe because unescaping only shortens strings.
- **Fix 2 counts.** `assessed_pairs` sums per-run counts. Only decided pairs (compatible/scoped/unknown_kept) count, and `plan_review` (`:262`) never re-draws one, so the sum is distinct pairs. A pair that is invalid in run 1 and decided in run 2 appears twice in `pairs` but is counted once. `PassageReviewNotice.tsx` lists only `status === 'scoped'`, and a scoped pair cannot be scoped twice. The notice now shows "N of M directional relationships inspected" from the cumulative counts, a failure line when a failure is among the current runs, and every run's scoped rows.
- **Fix 2 failure paths.** Cancellation sets `interrupted` and re-raises, and `finally` publishes the cumulative receipt (mutant 2c caught). When all calls fail, the run reports `failed` and keeps `uninspected = total`. A partial failure leaves the missing pairs as `not_returned` (uninspected) and the run reads `needs_review`. If `plan_review` raises before `holder["run"]` is set, the old receipt is left untouched.
- **Fix 2 signing and hashing.** `manifest_signer.py:142-176` canonicalises element `state` + `basis` + evidence ids, not `claim_map.metadata`, so the receipt shape is outside the signature. `report_revisions.snapshot_from_rows` hashes the **stored** claimMap with no read-time transform, so existing snapshots, `identify_snapshot` and the strengthen `baseline_hash` (`research_operations.py:143,227`) are unchanged for stored rows. `claim_map_input_hash` (`runner.py:2471`) covers element ids/descriptions and evidence ids/urls only. Fix 1's read-time unescape touches video rows, which are not in any snapshot.
- **Fix 3 good titles.** Short real headlines are kept ("Inflation hits 10% - ONS", "May resigns | BBC", "Brexit"). Non-English breadcrumbs ("Septembre - Université de Galway", "Nachrichten | Spiegel") are not detected, so behaviour is unchanged (no harm, no coverage). Bot walls still return `None` (junk `<title>` → no fallback → `<h1>` never consulted). Wikipedia year and section pages ("2016 - Wikipedia" with `<h1>2016`, "Events - Wikipedia") keep their title because the `<h1>` is itself a breadcrumb.
- **Fix 4 kept cases.** "upcoming 2027 election" on a 2026 check: kept. "The future of the NHS … 2025": kept (the regex does not match "the future of"). Next-month "1 October 2026" checked 30 Sept: kept. Same month with no day stated: kept. A day equal to the check day: kept. Missing year ("The upcoming 11 September poll"): kept. A note with no futurity cue: kept.
- **Fit.** No verdict language was introduced. UK English is used and the code is formatted with black. Fix 4 is mechanical, not a prompt change, which matches the project rule that a prompt-only fix failed for NF-11. Fix 2's receipt keeps every run (invariant #5) and says plainly that this is "not entailment proof".

## Mutant table

Each mutant was applied in place, the fix's test file run with `-x`, and the
original bytes restored in a `finally`. Script: scratchpad `mutants.py`.

| ID | File | Mutation | Result | Killing test |
|----|------|----------|--------|--------------|
| 1a | checks.py | `title` served without `_unescape` | CAUGHT | test_served_video_text_is_unescaped |
| 1b | youtube.py | ingest title not unescaped | CAUGHT | test_adapter_decodes_snippet_text_at_ingest |
| 1c | checks.py | `channelName` served raw | CAUGHT | test_served_video_text_is_unescaped |
| 2a | relationship_scope_review.py | uninspected summed over all runs, not `current` | CAUGHT | test_a_full_rerun_supersedes_earlier_leftovers_but_an_echo_run_adds |
| 2b | relationship_scope_review.py | failures read from newest run only | **SURVIVED** | — (LOW-2) |
| 2c | relationship_scope_review.py | `finally` → `else` (no publish on cancel) | CAUGHT | test_a_cancelled_run_publishes_interrupted_over_the_earlier_runs |
| 2d | relationship_scope_review.py | v3 receipt not read as history | CAUGHT | test_a_stored_version_3_receipt_is_read_as_the_latest_run |
| 3a | page_title.py | hidden children not stripped | CAUGHT | test_breadcrumb_title_gives_way_to_the_visible_h1 |
| 3b | page_title.py | site-name `<h1>` guard removed | CAUGHT | test_breadcrumb_kept_when_no_better_candidate_exists |
| 3c | page_title.py | no early `None` when all candidates junk | CAUGHT | test_a_bot_wall_h1_never_becomes_the_title |
| 3d | page_title.py | breadcrumb check disabled | CAUGHT | test_breadcrumb_title_gives_way_to_the_visible_h1 |
| 4a | stale_futurity.py | bare year `<=` → `<` | CAUGHT | test_a_past_date_called_future_is_flagged[...2026.] |
| 4b | stale_futurity.py | same month, no day → past | CAUGHT | test_genuine_or_undatable_notes_are_kept[September 2026...] |
| 4c | stale_futurity.py | `all` → `any` | CAUGHT | test_genuine_or_undatable_notes_are_kept[...2027 census...] |
| 4d | claim_map_analyzer.py | `field="scope_caveat"` label removed at parse | **SURVIVED** | — (log label only; the parse test checks the drop, not the label) |

Tree restoration: sha256 of `git diff -- backend` + both new util files was
`186683407519afbfd564a8e70abd20745ae14187cfbb15ccd0c6a1ba8e91b95b` before the
mutant run and the identical hash after it.

## Test output

Targeted (the four fixes + passage-mapping integration; Docker Postgres/Redis up):

```
$ python -m pytest tests/unit/test_video_entities.py tests/unit/test_relationship_scope_review.py tests/unit/test_evidence_title_extraction.py tests/unit/test_stale_futurity.py tests/integration/test_passage_mapping.py -q --no-cov
tests\unit\test_video_entities.py ....                                   [  3%]
tests\unit\test_relationship_scope_review.py ........................... [ 27%]
...............................................                          [ 70%]
tests\unit\test_evidence_title_extraction.py .............               [ 81%]
tests\unit\test_stale_futurity.py ...................                    [ 99%]
tests\integration\test_passage_mapping.py .                              [100%]
====================== 111 passed, 210 warnings in 3.29s ======================
```

Full unit suite (regression sweep):

```
$ python -m pytest tests/unit -q --no-cov
========== 4631 passed, 44 skipped, 388 warnings in 82.90s (0:01:22) ==========
```


---

## Re-verification (2026-10-06, after the coordinator's repairs)

### Verdict: PASS

Every HIGH and MEDIUM finding is closed. Four LOW items remain, and none of them blocks shipping.

### Earlier findings, closed with evidence

| Finding | Status | Evidence |
|---------|--------|----------|
| HIGH-1, HIGH-2, MEDIUM-1, LOW-5 (Fix 4) | CLOSED: Fix 4 removed | `stale_futurity.py` and its test are gone. `git status` no longer lists `claim_map_analyzer.py`. A Grep for `stale_futurity` / `asserts_past_as_future` in `backend/` finds no files. |
| MEDIUM-2 (`<h1>` promotes non-headlines) | CLOSED | With a breadcrumb `<title>`, these probes now keep the old title: "Page not found", "Sorry, the page you requested was not found", "Cookies on this site", "We use cookies to improve your experience", "Example News" (logo), and "Sign in to read the full article today". The bot wall still returns `None`. Galway is still repaired. |
| MEDIUM-3 (hidden strip drops visible text) | CLOSED | `hidden md:inline` gives "Acme wins contract for harbour bridge works". `aria-hidden` gives "Storm Eunice closes schools across Wales". The Galway `class="hidden"` span is still stripped. |
| LOW-1 (double decode) | CLOSED | `_video_to_dict` (`checks.py`) serves the stored text as-is, and all five serialisers still use it. Ingest decodes once. Test `test_served_video_text_is_passed_through_once_decoded`. |
| LOW-2 (mutant 2b survived) | CLOSED | 2b is now caught by `test_a_failed_echo_run_still_reads_failed_after_a_later_empty_echo_run`. |
| LOW-3 (receipt size doubled) | OPEN, accepted | Unchanged. Each pair is still stored at the top level and in `latest_run`/`prior_runs`. |
| LOW-4 (v3 echo runs read as full) | CLOSED, with a known gap | `_run_history` tags a v3 run `restored_only` when every recorded pair is in `basis.echo_scope.restored`, which `_restore_orphaned_echoes` writes at `claim_map_analyzer.py:1613-1619` (the entries carry `evidence_id`). The docstring states the gap: a v3 echo run with no pairs cannot be told apart. |
| LOW-6 (bench re-keying) | UNCHANGED, informational | Not checked, because the bench is running separately. |

### Migration `video_text_unescape`: safe

- **Chain.** `alembic heads` returns `video_text_unescape (head)`, a single head. `down_revision = "heard_about"`. Only `2026_10_01_heard_about.py` and this file mention `heard_about`, so there is no branch. The local DB `alembic current` is `video_text_unescape (head)`. The table name matches `VideoRecommendation.__tablename__`.
- **NULLs.** `description` can be NULL. The guard `isinstance(text, str)` skips it, and the WHERE clause's `LIKE` on NULL is not true, so a row with a NULL description is still selected through its other columns. Tested in an in-memory SQLite harness that loads the migration module: NULL stayed NULL.
- **Length limits.** `html.unescape` never lengthens a string (every entity is at least 3 characters and decodes to 1-2 code points), so the `[:limit]` slice is a no-op safeguard. It cannot truncate real text.
- **Non-entity `&`.** Stored rows are raw API output, and the API always escapes `&` as `&amp;`. Text such as "R&D & more" passes through unchanged (harness).
- **Downgrade.** It is a no-op, so the chain to `heard_about` stays intact.
- **Idempotence on a re-run: not idempotent (LOW-A below).** Harness result: upgrade turned `Use &amp;lt; in HTML` into `Use &lt; in HTML`, which matches the coordinator's local run. Downgrade (no-op) followed by upgrade again gave **`Use < in HTML`**. A normal deploy runs it once (alembic stamps it), so production is fine unless someone runs `downgrade` and then `upgrade`.

### Remaining findings (all LOW)

- **LOW-A. The migration double-decodes after a downgrade and re-upgrade.** `backend/alembic/versions/2026_10_06_video_text_unescape.py:47-49`. Scenario: `alembic downgrade -1 && alembic upgrade head` turns a literal "&lt;" in a title into "<". Fix options: make `downgrade` raise, or record the decoded ids.
- **LOW-B. Rows from the deploy overlap stay escaped.** Fix 1 no longer decodes when serving. Scenario: the old container ingests videos after the migration has run on the new container's boot. Those rows keep `&#39;` permanently. The window is seconds and only affects the fire-and-forget video task.
- **LOW-C. Fix 3 still promotes some long masthead `<h1>`s, and rejects some real headlines.** `page_title.py` `_names_the_site` / `_NOT_A_HEADLINE`.
  - Promoted: on a breadcrumb page, "Example Council Official Website Home Page" and "Welcome to the Example Council website" still replace the breadcrumb, because the word "page" or "welcome" breaks the masthead match. The breadcrumb was already a non-headline, so the user is no worse off.
  - Rejected: real headlines containing a listed word, such as "BBC to cut **500** jobs...", "Government admits **error**..." and "Netflix raises **subscription** prices...". These fall back to the breadcrumb, which is the safe direction: it only loses coverage.
  - Also, `sr-only focus:not-sr-only` is now kept as visible text ("Skip to content Acme wins..."). That pattern is rare inside an `<h1>`.
- **LOW-D. Gaps in test coverage.**
  - Mutant 2f survived: switching the v3 tag rule from a subset match (`keys <= restored`) to any overlap (`keys & restored`) passes every test. No test covers a v3 run that mixes restored and non-restored pairs.
  - The data migration has no test in the suite. It was verified only by the harness above.

### Mutant table, round 2

| ID | Mutation | Result | Killing test |
|----|----------|--------|--------------|
| 1a | ingest title not unescaped | CAUGHT | test_adapter_decodes_snippet_text_at_ingest |
| 1b | ingest channel not unescaped | CAUGHT | test_adapter_decodes_snippet_text_at_ingest |
| 1c | serve-time unescape re-added (double decode) | CAUGHT | test_served_video_text_is_passed_through_once_decoded |
| 2a | uninspected summed over all runs | CAUGHT | test_a_full_rerun_supersedes_earlier_leftovers_but_an_echo_run_adds |
| 2b | failures read from newest run only | CAUGHT | test_a_failed_echo_run_still_reads_failed_after_a_later_empty_echo_run |
| 2c | `finally` -> `else` | CAUGHT | test_a_cancelled_run_publishes_interrupted_over_the_earlier_runs |
| 2d | v3 receipt not read as history | CAUGHT | test_a_stored_version_3_receipt_is_read_as_the_latest_run |
| 2e | v3 echo tagging disabled | CAUGHT | test_a_stored_version_3_echo_run_is_read_as_restored_only |
| 2f | v3 tag: subset -> intersection | **SURVIVED** | - (LOW-D) |
| 3a | hidden children not stripped | CAUGHT | test_breadcrumb_title_gives_way_to_the_visible_h1 |
| 3b | `_names_the_site` -> False | CAUGHT | test_a_masthead_variant_of_the_site_name_is_not_promoted |
| 3c | no early `None` when all junk | CAUGHT | test_a_bot_wall_h1_never_becomes_the_title |
| 3d | breadcrumb check disabled | CAUGHT | test_breadcrumb_title_gives_way_to_the_visible_h1 |
| 3e | `_MIN_H1_WORDS` 5 -> 1 | CAUGHT | test_a_short_h1_is_not_promoted |
| 3f | `_NOT_A_HEADLINE` check removed | CAUGHT | test_an_error_heading_is_not_promoted |
| 3g | responsive `:` exemption removed | CAUGHT | test_a_responsive_hidden_span_is_visible_text |
| 3h | `aria-hidden` re-added | CAUGHT | test_aria_hidden_text_is_visible_text |
| 3i | host label dropped from `sites` | CAUGHT | test_a_masthead_variant_of_the_site_name_is_not_promoted |
| 3j | site match direction reversed | CAUGHT | test_breadcrumb_title_gives_way_to_the_visible_h1 |

19 run, 18 caught. Tree restoration: sha256 of `git diff -- backend` + `page_title.py` + the migration + `test_video_entities.py` was `e9c2ae952ff172cda6e6fca874622b5fd53820cf8aac3b1ca41c67d370c58f4a` before and after both mutant passes. A first attempt hit a script error partway through; the hash was confirmed restored after it as well.

### Test output, round 2

```
$ python -m pytest tests/unit/test_video_entities.py tests/unit/test_relationship_scope_review.py tests/unit/test_evidence_title_extraction.py tests/integration/test_passage_mapping.py -q --no-cov
====================== 99 passed, 210 warnings in 3.29s =======================

$ python -m pytest tests/unit -q --no-cov
========== 4619 passed, 44 skipped, 388 warnings in 91.36s (0:01:31) ==========
```

The unit count moved from 4631 to 4619. That matches the 19 deleted stale-futurity tests and the 7 net new tests.
