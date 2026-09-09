# Track Q takeover and stabilise — 9 September 2026

The founder handed the `codex/evidence-quality` branch (27 commits by Codex implementing OpenAI "Astra"'s 6→8/10 plan, `tmp/tru8-hands-on/tru8-route-to-eight.md`) to Claude with three instructions: assess it, keep the documents current before every commit, and bring it to a merge that works. This record holds the audit findings, the founder's decisions, what was fixed today, and the evidence.

## Audit at handover

Three parallel reviewers (backend step 4; backend steps 5–6 and the scope review; frontend and steps 1–3) plus the whole backend suite, which Codex had never run — every checkpoint reports "N focused tests".

| # | Severity | Finding | Evidence |
|---|---|---|---|
| 1 | HIGH | Strengthening refund written as `kind=refund` per check. `ux_usage_events_check_kind` (migration `2026_07_10_usage_events`) allows ONE such row per check, so the second failed operation on a check raised `IntegrityError` inside `fail_operation`, left it `running`, the 30 s reconciliation loop re-failed forever, `uq_research_active_check` blocked new admissions, and the second debit was never refunded. | `research_operations.py::_fail_locked`; fixture used `create_all`, which does not create the partial index, so no test could see it |
| 2 | HIGH (suite) | 21 existing tests red: `response_builder.py` read `ev.text_provenance` unguarded; every serialisation test with a plain test double broke. Runtime unaffected (ORM rows carry the column). | whole-suite run: 3,814 passed / 23 failed (21 this cause, 2 order-dependent Sentry tests that pass alone) |
| 3 | MEDIUM | `capture_report` hashed every Evidence column incl. `archived_url`, which the fire-and-forget Wayback task writes row-by-row (~15/min) after completion. Any strengthening started in that window failed its baseline-hash check ("report changed") and refunded; `identify_snapshot` also stopped matching a retained revision once the column moved. | `report_revisions.py::snapshot_from_rows`; `wayback_archive.py:160` |
| 4 | MEDIUM | `/verify/{id}/revisions/{rev}` returned only `{valid}` while the page copy promised signed-at, key id, tier and fingerprint rows. | `verify.py`, `web/app/verify/[id]/page.tsx:100-116` |
| 5 | MEDIUM | New public rendering of model free text: per-reference `reasoning` ("System interpretation") and scope-review `reasoning` on `/r/`, never read for verdict language — the Fix 1 (2026-09-02) trap. | `ReadingTable.tsx`, `PassageReviewNotice.tsx` |
| 6 | DEFAULT-PATH | Codex deleted the domain concentration cap (`6958152`): over-concentrated primary/reporting items were relabelled commentary for pool share alone (sqlite.org's WAL page became `commentary/analysis`), and tier feeds `_STATE_TIER_WEIGHTS`. Documented in `2026-09-08_source_roles.md`, absent from the status doc, invisible to the bench. | `runner.py`, `source_concentration.py` |
| 7 | LOW | Seeker treated any passage-review status other than `complete` as unknowns, including `not_run` (the default-off candidate), so the empty state never showed. | `SeekerView.tsx:75` |
| 8 | MEDIUM (suite) | `scripts/run_passage_evaluation.py` called `logging.disable(logging.CRITICAL)` at module level, and `test_passage_factorial_evaluation.py` imports that module — so every test after it in the process ran with logging off. The two Sentry behavioural tests (which log CRITICAL and expect one event) failed only in a whole-suite run and passed alone. Confirmed against a detached `main` checkout (unit tree green there). | branch-only; fixed by moving the switch under `__main__` and pinning `logging.root.manager.disable == NOTSET` after import |
| 9 | LOW | Register said "no application code changed on 9 September"; five files were edited 10:46–11:06 that morning — the result-fidelity step was done (38/38) and uncommitted. | file mtimes; `2026-09-09_result_fidelity.md` |

Also recorded, not acted on today: `identify_snapshot` runs a JSONB equality query per completed GET; `ReportRevisionHistory` refetches on every report update; dead `status` dep in `use-research-poll`; `fact_applicability` gate sits AFTER echo (flag-only, additive, invariants intact); free text now enters the signed `basis` via receipt entries (design deviation, not a break).

What the reviewers verified as sound: one operation per check with admission before debit under real PostgreSQL concurrency; before/after signed snapshots; quote-in-passage validation before any relationship is accepted; conflicts recorded, never overwritten; both candidate flags OFF with byte-identical default prompts, schema, gate order and receipts (pinned); `RETRIEVAL_CACHE_VERSION` correctly unchanged; owner-only revision endpoints; generation guards in both web hooks; tests that would fail with the feature deleted.

## Founder decisions (2026-09-09)

1. **Keep the concentration-cap deletion.** Recorded in CLAUDE.md; pinned by `test_runner_no_longer_relabels_sources_by_domain_share`.
2. **Ask before every paid model run**, with the estimated cost. No standing spend authority.
3. **Gate public "System interpretation" fail-closed.** Owner sees the sentence unchanged.

## Fixed today

- `KIND_RESEARCH_REFUND = "research_refund"` (`usage_event.py`), used by `_fail_locked`; `comparison.py`'s re-search budget counts both refund kinds. Every meter sums credits regardless of kind, so it nets like any refund. The integration fixture now creates `ux_usage_events_check_kind` after `create_all`, and `test_second_failed_strengthening_on_one_check_still_refunds` fails on the old code.
- `response_builder.py`: `getattr(ev, "text_provenance", None)`.
- `report_revisions.py`: `archived_url` excluded from the snapshot; `test_archiving_during_research_does_not_fail_commit` writes the column mid-research and asserts completion AND that the retained revision is still identified.
- `verify.py`: revision verify returns `signedAt`, `kid`, `executedTier`, `pipelineFingerprint`; asserted in `test_completion_preserves_both_signed_revisions`.
- `web/lib/system-interpretation.ts`: shares Fix 1's verdict test (`containsVerdictLanguage` exported from `element-caveat.ts`). On `readOnly` surfaces an adjudicating sentence renders as "withheld from the public record (adjudicating wording)" — never as "no explanation was saved". `readOnly` threaded `public-report-client → LibrarianView → EvidenceLedger/ReadingTable` and `→ PassageReviewNotice`; Seeker passes its own. Tests: `system-interpretation.test.ts`, `reading-explanation.test.tsx`.
- `SeekerView.tsx`: unknowns from review only for `needs_review | partial | failed | interrupted | invalid_response`. Test in `seeker-honesty.test.tsx`.
- `scripts/run_passage_evaluation.py`: logging switch moved under `__main__`; `test_importing_the_script_leaves_logging_enabled` pins it.
- Docs: CLAUDE.md (Track Q row, cap deletion, seventh flag-only gate + scope review, `research_operations.py` row), `OPEN_WORK.md` START HERE, status doc latest checkpoint, this record.

## Evidence

Figures are from the runs on this working tree before the two commits (the whole backend suite runs in the scratch venv `tmp/quality-venv`, which needed `prometheus_client` and `mcp` installed to collect the MCP tests — an environment gap, not a code one).

| Check | Result |
|---|---|
| Backend whole suite (`pytest tests/ --ignore=tests/replay_corpus`) | **3,902 passed, 0 failed, 69 skipped** (118 s). Before the fixes: 3,814 passed / 23 failed |
| Web suite (vitest 4.1) | 32 files, 195 tests passed (190 before) |
| TypeScript | `tsc --noEmit` exit 0 |
| Default replay bench (`tmp/quality-replay-stabilise-2026-09-09.log`) | **185 ok / 1 warn / 13 known fail / 2 unexercised, zero cassette drift** — the 13 are the attributed set (3 × 018F interested-party, 2 × must-have URL, 8 × thin-pool floors) |
| `alembic heads` | `text_provenance (head)` |

## Commits

1. Codex's result-fidelity step, committed as Codex left it (recital exemption under the flag, scope review v2, passage fingerprint v10, `evaluate_result_fidelity.py`, frozen fixtures, its doc, `.gitignore` for test-account briefings).
2. The stabilise fixes and documents above.

The two commercial-assessment documents stay untracked until the founder has read them.
