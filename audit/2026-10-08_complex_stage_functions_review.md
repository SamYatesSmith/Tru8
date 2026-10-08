# Complex stage functions — review before any change (2026-10-08)

**Status:** read-only review. Nothing below has been changed. Founder asked for a strong understanding first.
**Scope:** the seven stage functions S7 left at complexity C–E in `backend/app/pipeline/runner.py` (commit `4b34ef6`, live).
**Verified:** an independent agent checked every finding against the code (same day): F1 and F4 were UNDERSTATED, F5 was WRONG (removed), and three things were missed (F9–F11). Corrections are folded in below.
**Method:** read each body and its callees; line coverage from the unit suite (4,648 tests) AND from the replay bench (`--all`, 10 corpus claims) on `runner.py`; settings and tier config read from `config.py` / `PipelineConfig`.

## 1. Summary

| Function | CC | Statements | Run by unit tests | Run by bench | Never run by either |
|---|---|---|---|---|---|
| `_post_filter_recovery` | 34 | 57 | 35 | 34 | the lines that ADD an item, the blocklist drop, the ledger |
| `_retrieve_stage` | 33 | 81 | 30 | 31 | frozen bypass, timeout recovery, exception path, legacy shape, ledger |
| `_map_evidence` | 30 | 77 | 48 | 48 | ledger diagnostics, timeout + error paths |
| `_dedup_urls_across_claims` | 29 | 59 | 28 | 31 | **the capping itself** (any URL on >2 claims), ledger |
| `_coverage_recovery` | 27 | 117 | 16 | 95 | small branches only — bench covers it well |
| `_classify_and_distil` | 24 | 110 | 81 | 82 | heuristic (quick-tier) classify, ledger, no-classify cleanup |
| `_score_relevance` | 16 | 27 | 4 | 20 | frozen skip, exception path |

**What drives the complexity is mostly not the stage logic.** Three things recur:
1. **Debug ledger code** — 32 `ledger` sites in `runner.py`. The ledger exists only when the env var `DEBUG_EVIDENCE_LEDGER=1` (read directly from `os.environ` in `evidence_ledger.py:19`, so it is NOT in `audit/FLAGS.md`). Its only documented user is the February `harness/run_golden_dataset.py`. Neither the unit suite nor the bench ever sets it, so **every ledger line is untested**. Whether production sets it is unknown (needs a read-only Railway variable read).
2. **Frozen-evidence replay branches** — every stage has a "skip for deterministic replay" branch. See finding F1: the input that drives them is reachable from the public API.
3. **Defensive branches that cannot fire** — see F3/F4.

## 2. Findings (ranked)

**F1 — HIGH (integrity of public records), not a refactor matter.** `POST /checks/stream` and `POST /checks/run` accept `frozen_evidence` from any authenticated console user (`app/api/v1/checks.py:280`, passed through at `:400` and `:671`). The field is described "internal use only", but nothing enforces that: no admin check, no environment check (searched `app/api`, `app/core`, `app/middleware`). With it, a user supplies the evidence items themselves — URL, text, and `tier` — and the pipeline then **skips retrieval, URL dedup, relevance scoring and classification** (`[CLASSIFY] SKIPPED — V2 frozen evidence replay`), maps the supplied items, and produces a normal record. **There is no publish step:** `GET /checks/public/{id}` serves any completed check to anyone with its ID (`checks.py:2469-2490`), and the record is signed whenever `MANIFEST_SIGNING_ENABLED` is on (`runner.py:3913`). Details (verified): no claim hash is needed — key `"0"` (the claim position) matches (`runner.py:1122`); it works only on focused (single-claim) checks, because article-mode Phase 2 reloads with `frozen_evidence: None`; fact-check, retrieval, dedup, scoring, post-filter recovery and classify are all skipped and the caller's `tier` survives. Even a NON-matching `frozen_evidence` sets the replay flag (`:1152`): real retrieval then runs but with no dedup, no scoring, no classify (items get no tier) and temperature 0. The agent API and MCP do not accept the field. The only consumer is the February golden-dataset harness. **FIXED 2026-10-08:** `_require_frozen_evidence_permission` (`checks.py`) refuses any non-None `frozen_evidence` with 403 unless the backend is `ENVIRONMENT=development` or the user is an admin (`is_admin_email`, the same test as the usage-limit bypass); it runs before the usage gate, so a refusal costs no credit and creates no Check. 10 tests (6 fail on the old code; mutation-checked). Independent verification: the only two paths in (`/checks/stream`, `/checks/run`) both go through the guard; the Dockerfile bakes `ENVIRONMENT=production`; the harness defaults to localhost. **Carried-over weakness (pre-existing, not introduced here):** admin identity is the stored email, copied from Clerk without a verified-address check (`auth.py:92-108`), and `get_or_create_user` resolves an email clash by moving the existing row to the NEW Clerk ID (`users.py:50-69`). If Clerk ever admits an unverified email, a new sign-in with an existing user's address takes over that user's row (admin included). Depends on the Clerk dashboard's email-verification setting — founder to check.

**F2 — MEDIUM (quality, live path).** Post-filter recovery (`_post_filter_recovery`) adds raw search **snippets** with `relevance_score: 0.0` and they are **never relevance-scored** — nothing downstream scores `ev-rpf-*` items (searched `app/`). It runs exactly when the scorer has thinned a claim below `MIN_EVIDENCE_POST_FILTER` (5), i.e. when the scorer judged much of the pool off-topic. Coverage recovery had the same gap and was fixed on 2026-07-22 (score recovery items, same receipt shape); post-filter recovery was not. The items are classified later (good), so they get a tier, but not a relevance gate.

**F3 — LOW (dead code).** In `_retrieve_stage`, two branches cannot fire: `retrieve_evidence_with_cache` (`app/workers/pipeline.py:161-338`) catches every exception and always returns a dict carrying `evidence_by_claim`. So (a) the legacy "non-dict result" branch is unreachable, and (b) the `except Exception` branch — including its "raise `PipelineError` in production" — is unreachable. **Consequence worth knowing:** a total retrieval failure in production does NOT fail the check; it logs `critical` and proceeds with an empty pool. The comment-level intent ("raise in production") is not what happens.

**F4 — LOW (edge path).** On the outer 180 s retrieval timeout, `_progressive_results` holds only claims that finished; unfinished claims get **no key** in `evidence`. Post-filter recovery iterates `evidence.items()`, so it never sees those claims — it skips exactly the claims that most need backfill. If no claim finished, `evidence` is `{}` and post-filter recovery is skipped entirely. Worse (verified): progressive results hold only `retrieve.py`'s own accumulators (`retrieve.py:962-965`), so on that timeout **cache-hit claims and all fact-check evidence are lost too** — they live in the wrapper's local variables. (Inner deadlines — 45 s per claim, 30 s fetch phase — make the 180 s timeout rare. Never exercised by tests or bench.) See also F11.

**F5 — withdrawn (verifier: WRONG).** `score_evidence_batch` checks `settings.ENABLE_LLM_RELEVANCE_SCORER` itself (`relevance_scorer.py:604`), so the env kill switch does stop recovery scoring.

**F6 — LOW (misleading default).** `_dedup_urls_across_claims` reads `getattr(settings, "MAX_CLAIMS_PER_URL", 3)`; the setting always exists and is **2** (`config.py:339`). The `3` never applies.

**F7 — note.** Dedup runs before LLM scoring, so its `llm_relevance_score or relevance_score` tiebreak is in practice always the retrieval `relevance_score` (the cache is written before scoring too).

**F8 — test gap.** The dedup capping logic (a URL wanted by more than `MAX_CLAIMS_PER_URL` claims) has never run under test or bench. It only triggers on multi-claim article checks that share sources. The bench corpus has none. `tests/unit/pipeline/test_double_cap_dedup.py` tests a COPY of the logic (`_run_dedup`), not the runner, so drift would not be caught.

**F9 — MEDIUM (invariant #5, "every exclusion has a receipt").** `_dedup_urls_across_claims` silently drops every evidence item with no URL (`runner.py:1950-1952`: `continue`, never re-added to the rebuilt dict), with no receipt. No producer that writes an empty URL was found in `app/services` or `app/pipeline`, so how often this happens is unknown — a production read of URL-less evidence would tell.

**F9 FIXED 2026-10-08:** the drop is kept (a `None` URL fails the whole save — `Evidence.url` is a required string; an empty one gives the reader nothing to open) and now leaves an INFO `[URL LEDGER] claim=… dropped stage=url_dedup reason='no_url' source=… title=…` receipt, `str()`-guarded so an odd field cannot fail the stage. Measured first: 0 of 10,366 local pre-dedup rows (adapter sources included) lack a URL, so the gap was latent. New `test_url_dedup_stage.py` (15 tests) characterises the REAL function — cap, tiebreak, same-claim duplicates, reordering, frozen skip, ledger path — closing F8's gap; the receipt and `str()` tests fail on the old code. Independently verified. Remaining note: URL-less drops count in the ledger's `removed` and the "Removed N duplicate URLs" log line, though they are not duplicates.

**F10 — note.** Dedup also reorders each claim's items into first-seen-URL order (`:1995-1998`). Order can matter downstream (round-robin truncation, invariant #2).

**F11 — MEDIUM (timeouts) — REVIEWED 2026-10-08, not changed.**
- `/checks/run` (`checks.py:653`) wraps the pipeline in `asyncio.wait_for(..., 180)`. Focused (single-claim) checks run Phase 1 AND Phase 2 inside that one 180 s; article checks get 180 s for Phase 1 and a fresh 180 s for Phase 2. On expiry it fails honestly: `handle_pipeline_failure` (refund) + 504 "Your credit has been returned". Retrieval's own 180 s timeout can never fire first on `/run`, so its partial-result rescue never applies there — but the inner deadlines (45 s per claim, 30 s fetch phase) keep retrieval far below 180 s anyway, so that part is cosmetic.
- `/checks/stream` has no such cap; only the 300 s watchdog (`PIPELINE_WATCHDOG_SECONDS`).
- Local data (367 completed checks, `tru8_dev`): p50 55-76 s, p90 102-128 s, max 201 s; 2 of 367 over 180 s. Production distribution NOT read (needs a read-only prod query — founder approval).
- **Bigger, likely issue (verify first):** `api.trueight.com` is proxied by Cloudflare (`Server: cloudflare`, `CF-RAY`, then Railway edge). Cloudflare's documented proxy read timeout on non-Enterprise plans is **100 s** with no bytes from the origin → **524** to the client. `/run` sends nothing until the check ends, so a `/run` call longer than ~100 s would 524 at the edge while the server carries on, completes, saves and keeps the credit; the caller sees an error but the result exists (`GET /checks/{id}`). Local p90 is above 100 s. NOT verified live (a verifying call costs a paid check) and the Cloudflare plan was not checked. `/stream` (SSE) sends progress events, so it is not exposed the same way. Possibly related: the hosted MCP stream dying at ~140 s (CLAUDE.md, 2026-09-02).
- Who uses `/run`: signed-in Console users calling programmatically and the admin API-key exemption; the web app uses `/stream`; agents use `/agent/*`.
- Options (founder): (1) verify — Cloudflare plan + one admin `/run` on a slow claim, or a prod log search for 524s; (2) if confirmed, either make `/run` asynchronous (202 + poll `GET /checks/{id}`), or keep the connection alive with periodic whitespace before the JSON body, and align its ceiling with `PIPELINE_WATCHDOG_SECONDS`; (3) at minimum, correct the docs ("Set your HTTP client timeout to at least 180s") which promise more than the edge allows.

## 3. Per function

### `_post_filter_recovery` (CC 34)
- **Does:** for each claim with < 5 items after scoring, one web search (`SearchService.search_for_evidence`, 10 results; unwindowed for historical claims, else past-year), appends snippet items until the claim reaches 5. Skips URLs already pooled (`UrlKeySet`) and runtime-blocked domains (each with a URL-ledger log). Mutates `evidence[pos]` in place.
- **Off in:** quick tier; frozen replay.
- **Searches run one claim at a time** (`await` in the loop), not concurrently.
- **Complexity drivers:** nested try per claim inside an outer try; the blocklist branch; logging; ledger count.
- **Untested:** the add path and blocklist path (both suites stop at "search returned nothing new").
- See F2, F4.

### `_retrieve_stage` (CC 33)
- **Does:** frozen bypass, OR `retrieve_evidence_with_cache` under a 180 s timeout with partial-result rescue; then diagnostic logs and ledger accounting. Returns `(evidence, raw_evidence_rows, raw_sources_count)`.
- **Complexity drivers:** 4 result paths (frozen / ok / timeout-partial / timeout-empty) + 2 dead paths (F3) + ~30 lines of debug-ledger counting.
- **Untested:** everything except the success path.

### `_map_evidence` (CC 30)
- **Does:** analyzer-input diagnostics; per-claim `claim_map_input_hash` + the three `attach_*` writers (recital pin: `attach_claim_subjects` then `attach_claim_text`, 12-space indent); starts the echo-link join; runs `map_with_join`; fails the check (`PipelineError`) on timeout or error.
- **Complexity drivers:** ~30 lines of snippet-fallback reason counting that feed only the debug ledger; the nested hash function.
- `analyze_timeout` is used only in log text; the real timeout is computed again inside `map_with_join`. Same value, two computations.

### `_dedup_urls_across_claims` (CC 29)
- See also F9 (URL-less items dropped without a receipt) and F10 (reordering).
- **Does:** keeps any URL on at most 2 claims; when a third claim wants it, entries are sorted by score then position and the lowest are dropped (logged at DEBUG; ledger casualties). Same-claim duplicates are left alone. Rebuilds and returns a new dict; on exception returns the input.
- **Untested core** (F8). F6, F7.

### `_coverage_recovery` (CC 27)
- Well covered by the bench (95/117). Fixed and verified yesterday (D1–D5, D3). Phase A/B closures and their source order are pinned by tests. **Lowest priority to touch.**

### `_classify_and_distil` (CC 24)
- Two concurrent closures; writes disjoint fields; per-task timing; telemetry components returned. Heuristic (quick-tier) path untested by bench. Source-order pin: must stay below `copy_page_opening(item)`.

### `_score_relevance` (CC 16)
- Small. Bench covers the live path. Fine as is.

## 4. Constraints for any change
- Source-text pins: `test_cited_source_gap_note.py:313-338`, `test_originator_review.py:497-508`, `test_recital_original_wording.py:111-119`, `test_recovery_atomic.py:395-415`.
- Bench equality is weak evidence here: the bench never runs the ledger, the dedup cap, the post-filter add path, timeouts, or quick tier. **Any change to those needs characterisation tests written first** (as S0 did for the refresh sites).
- B4A3 and 82CF cassette hit counts vary on unchanged code — compare to a control run, never to the README.

## 5. Options (for the founder; one decision at a time)
0. Priority order suggested by the findings: F1, then F9, then F11, then the refactor options.
1. **F1 guard** — reject `frozen_evidence` unless the caller is admin (or `ENVIRONMENT=development`). Small, separate from the refactor, highest value.
2. **Ledger decision** — read Railway for `DEBUG_EVIDENCE_LEDGER` (read-only). If unset in production: either keep it (debug value) or remove it (cuts the largest share of complexity across all seven functions; needs the February harness retired too).
3. **Dead-branch removal (F3)** — make the retrieve exception contract explicit (callee never raises) and delete the two unreachable branches; or decide that a total retrieval failure SHOULD fail the check in production (a behaviour change).
4. **F2** — score post-filter recovery items like coverage recovery does (behaviour change; needs a paid bench re-record since it adds model calls).
5. **Characterisation tests** for the untested cores (dedup cap, post-filter add path) before any structural change to them.
