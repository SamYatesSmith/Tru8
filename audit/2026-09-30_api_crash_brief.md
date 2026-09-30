# Brief for the next session: the API process dies during bursts of checks

**Written:** 2026-09-30, end of session, for a fresh session. **Status (updated 2026-09-30, later session): CAUSE CONFIRMED AND FIXED locally, see §8. Deploy pending.** Original status: diagnosed as far as logs allow; cause NOT confirmed; nothing built. **Priority:** above all A− work (founder, 2026-09-30: "we absolutely must resolve the issues found with the crashes").

## 1. What happens
The production API process (Railway service `backend`, project `tru8`) dies and cold-starts partway through a run of checks. Any check running at that moment fails and is refunded by the stale sweep ("This check was interrupted and could not complete. Your credit has been refunded"). Requests in flight get 502s for about a minute.

| When (UTC) | Deployment | Checks since last start | What was running |
|---|---|---|---|
| 2026-09-28 ~08:59 | pre-`9aff4ea` | ~8 (the 28 Sep A− run) | #9's retrieve, just after two 250+ page PDFs (then blamed on PDF memory; `b50672e` fixed that leak) |
| 2026-09-30 13:48:28 | `23228095` (`ffe31b0`) | ~5, two overlapping | #3/#4 A− re-run, retrieve (check `ff462ddc`, Cook poll) |
| 2026-09-30 14:23:11 | same | ~15, strictly one at a time | #8 A− re-run, retrieve (check `0d87654a`, Galway reef) |
| (a third restart on the same deployment; time not yet read) | same | | |

## 2. The signature (from `railway logs --deployment`)
Both 30 Sep crashes end identically, in RETRIEVE, within about 1 second:
```
app.services.embeddings - ERROR - Embedding generation failed: unknown parameter type
app.services.embeddings - ERROR - Embedding generation failed:  (): argument ' ' (position 1) must be Tensor, not bool
app.services.embeddings - ERROR - Batch embedding generation failed: (): argument '' (position 1) must be Tensor, not bool
```
Then silence, then `Running database migrations…` / `Started server process [1]`: a cold start with **no shutdown log and no Sentry event** (Sentry shows nothing for the window). That is a SIGKILL or a segfault, not a Python exception.
- These embedding errors appear in the logs ONLY at the crash moments (13:48:28 ×11, 14:23:10–11 ×6); never on a healthy run.
- Earlier deployments (29–30 Sep, light traffic) show one start each and no embedding errors.

## 3. Hypotheses (ranked; none proven)
1. **Memory growth across checks → OOM kill.** Fits: the crash comes after N checks even when they are sequential (14:23), and the 28 Sep crash also came mid-burst. Torch errors like the above are what a process emits while allocations start failing. **Test:** memory per check (see §5).
2. **Thread-unsafe embedding calls.** `app/services/embeddings.py` (unchanged since Feb 2026) runs `self.model.encode(...)` via `loop.run_in_executor(None, …)` with no lock around the call (only model LOADING is locked). Concurrent `encode` calls on one SentenceTransformer / fast tokenizer can corrupt state; "unknown parameter type" / "must be Tensor, not bool" fit that too. Would explain a crash without memory growth.
3. Something else in retrieve holding memory (page text, PDFs, caches) with the embedding errors only a symptom.

## 4. What is NOT the cause (checked)
- Today's deploy (`ed83167`, the originator review) runs after classify, never touches embeddings, and holds ~1.2 KB per candidate transiently. The crash is in retrieve. The 28 Sep crash predates it.
- The PDF page leak (fixed `b50672e`, 28 Sep).

## 5. Plan (founder to approve each paid step; measured costs below)
1. **Read the Railway memory graph** for the backend service around 13:48 and 14:23 UTC (dashboard Metrics tab; the CLI does not show metrics). A sawtooth that climbs per check and drops at each crash confirms H1.
2. **Reproduce locally**, cheap: `audit/originator_eval/run_fresh_harvest.py` runs the real pipeline up to classify (includes retrieve + embeddings) for ~1.5p per claim (measured today: Gemini ~$0.010 + ~7 Serper requests). Adapt it to log process RSS (`psutil`) after each claim and run ~15–20 claims in one process: ~20–30p. Add `tracemalloc` snapshots (top allocations) between claims if RSS climbs. To test H2, fire two claims concurrently and look for the same errors.
3. **Fix the proven cause, with a test** (a leak test that runs the stage N times and asserts bounded growth, or a concurrency test on `embed_batch`). If H2: serialise `encode` behind a `threading.Lock` (cheap, no behaviour change).
4. **Verify:** the same local burst with flat memory / no errors; then deploy; then a production burst.
5. **Then finish the A− re-measure:** #8 and #9 (below).

## 6. Tools and access that work
- `railway` CLI is logged in (founder's account) and linked to `tru8 / production / backend`. Read-only log commands used today: `railway logs --deployment --since 90m`, `railway logs --deployment --since <ISO> --until <ISO>`, `railway logs --deployment <deployment-id> --lines 500 --filter "<text>"`, `railway deployment list`. Output caps at 500 lines per call; `--lines 20000` is rejected.
- Sentry MCP: org `trueight`, region `https://de.sentry.io`.
- ⚠️ This session may NOT read the API key in `~/.claude.json` (the permission layer blocks it). Scripts that need it are run by the founder with `! python tmp/<script>.py` (forward slashes). The read-only tru8 MCP tools (`tru8_get_result_raw`) work for reading checks by FULL id.
- `POST /api/v1/checks/run` drops the client at ~60 s, but the check continues server-side; `tmp/run_remeasure_missing.py` handles that by waiting on `GET /checks?limit=1`.

## 7. A− re-measure 3: state at hand-off
Plan: `audit/2026-09-30_a_minus_remeasure_plan.md`. Grades: `audit/a_minus/2026-09-30_rerun/` (blind; brief in that folder).
**17 of 19 graded: A− 1 · B+ 3 · B 9 · B− 4 · C 0** (the same 17 on 28 Sep: A− 0 · B+ 3 · B 5 · B− 4 · C 5). 10 up, 4 same, 3 down.
| # | check | 28 Sep | now |
|---|---|---|---|
| 1 | 206199c9 | B | B |
| 2 | f987a0f4 | C | B |
| 3 | 6c6f26fa | B | B |
| 4 | 2e959f07 | B | B |
| 5 | 4dba6ce3 | C | B |
| 6 | 02c8c252 | C | B |
| 7 | 0b2c0c07 | B− | B+ |
| 10 | 0e8e5a72 | C | B |
| 11 | 8c9657d8 | B | B |
| 12 | 997912d7 | C | B− |
| 13 | 59f86abd | B− | B+ |
| 14 | 7e4ddfaa | B+ | B− |
| 15 | 018f9a18 | B− | B |
| 16 | a4b90246 | B+ | B |
| 17 | 802cebc9 | B+ | B− |
| 18 | d0754a0d | B | B+ |
| 19 | da19fb7b | B− | **A−** |
- H4 (weak source in PRIMARY) on these 17: 10 → 3 (#5, #12, #17; #10's is attributed to map).
- Largest remaining hard buckets: map (H1/H2) and retrieve (H3). #16/#17 (same input) graded B and B−: run-to-run noise is real.
- **Owed:** #8 and #9 (`! python tmp/run_remeasure_missing.py` resumes; best AFTER the crash fix), their grades, then the full tally-by-check/stage write-up into `audit/2026-09-24_a_minus_measurement.md`.

## 8. Resolution (2026-09-30, later session)
**Cause: thread exhaustion, not memory.** H1 and H3 are ruled out, H2 was close but wrong.
- The full 14:23 log has one line the earlier read missed, just before the embedding errors: `libgomp: Thread creation failed: Resource temporarily unavailable`.
- Container (read by `railway ssh`): `memory.max` 8 GB, 675 MB in use, `oom_kill 0`; **`pids.max` 1000**; `nproc` 48, `cpu.max` 800000/100000 (an 8-CPU quota); `torch.get_num_threads()` 48.
- Mechanism: libgomp gives each thread that calls torch its own OpenMP team sized to the visible CPUs. `evidence._extract_semantic_snippet` runs per fetched page (up to 25 concurrent), and each `encode` went to the event loop's default executor (up to 32 threads). ~20 concurrent encodes × 47 team threads ≈ 940 threads, plus the process's own ~100, passes 1000. libgomp then fails thread creation, torch's argument parsing reads garbage (the `must be Tensor, not bool` lines), and the process segfaults: no Python exception, no shutdown log, no Sentry event. It depends on how many pages finish together, not on how many checks came before, so sequential checks crash too.
- **Reproduced:** Linux container with prod's versions (torch 2.5.1+cpu, sentence-transformers 2.3.1, transformers 4.57.6, tokenizers 0.22.2), 48 torch threads, 400 concurrent encodes. Without a pid limit: no errors. With `--pids-limit 1000`: the same `libgomp` line, then `Fatal Python error: Segmentation fault`, exit 139.
- **Fix** (`app/services/embeddings.py`): model load and every `encode` run on one module-level single-worker executor (`thread_name_prefix="embed"`), and torch is capped at `EMBEDDING_TORCH_THREADS = 4`. One caller thread means one team. The executor is module-level, so it also covers the per-pipeline event loops (`runner._executor` runs each pipeline under its own `asyncio.run`).
- **Cost of the fix:** none measured. At 8 CPUs, 30 pages × 200 sentences took 16.0 s (1 worker × 4 threads) vs 16.5 s (2 × 4) and 27.8 s (1 × 2). The work is CPU-bound, so the old concurrency bought nothing.
- **Verified:** the same 400-encode burst routed through the fix under `--pids-limit 1000`: no errors, `pids.peak` 80, exit 0. New test `tests/unit/test_embedding_thread_confinement.py` (concurrent calls from 4 event loops all run on the one `embed` thread, never two at once) fails on the old code and passes on the new. Unit suite 4,313 pass, 44 skip.
- The cross-encoder reranker is only downloaded at boot (`scripts/download_models.py`), never used at runtime, so the embedder is the only torch caller.
- **Owed:** deploy; then one production burst of checks and a `railway ssh "cat /sys/fs/cgroup/pids.peak"` read (expect well under 1000); then #8 and #9 of the A− re-measure (§7).
- **Production verification (2026-09-30 ~17:10):** deployed `fe207a0`; A− #8 (`8fefb637`) and #9 (`ccb174bc`) completed on one process, 0 `libgomp` lines, 0 embedding errors, one container start (the deploy). `pids.peak` 146 across both retrieves. Closed.
