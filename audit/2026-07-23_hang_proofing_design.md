# Hang-proofing design — no check may ever be left hanging (2026-07-23)

**Status: APPROVED (founder, 2026-07-23 — 300s/150s ceilings, sweep includes
'pending') → BUILT + SHIPPED `c7b4d4d` + DEPLOYED same day (prod healthy).
Gates: test_hang_proofing.py 12/12 · neighbouring suites 305 · full pipeline
suite 974/44 identical to reference · single alembic head · tsc clean.
Owed: founder dashboard eyeball that the first boot sweep auto-healed the two
stranded checks (T7 attempt 1 + 46406547).** Build deviations from this design, both
improvements found during implementation:
1. The pipeline supervisor RE-RAISES PipelineError after failure handling — a
   clean finish would make an attached `events()` stream announce "completed"
   for a check that just failed. A done-callback retrieves the exception so
   detached tasks don't log GC noise.
2. Re-search tasks are NOT inflight-registered (design said register them):
   the shutdown guard only acts on 'processing'/'pending' checks, and a
   re-search's parent check is COMPLETED — registration would be dead code.
   The re-search watchdog terminates the Redis status channel instead, which
   is what the Seeker UI polls.
Also shipped: `processing_started_at` column + migration (the design's sweep
needed a clock; created_at mis-ages paused-then-resumed article checks).
Trigger: T7 ("Immigration policy is a disaster") sat on "gathering evidence"
with a healthy backend; founder line: *"We cannot have a claim just being left
hanging — not a good user experience."* Second incident class today after the
T2 OOM stranding (check `46406547`, still stuck 'processing').

## 1. Problem

A check must always reach a terminal state the user can see — `completed`, or
`failed` with an honest message and a refund. Today three gaps allow a check to
sit in `processing` forever:

| # | Gap | Code evidence |
|---|---|---|
| G1 | **The pipeline watchdog is attached to the SSE connection, not the task.** `events(pipeline_task, max_duration_seconds=300)` cancels the pipeline only while the *original* stream generator is being consumed. Client disconnect/reconnect/navigation tears down the generator — and the watchdog with it. The reconnect endpoint (`stream_check_progress`) has no task reference, so a reconnected stream re-arms nothing. | `checks.py:827,839-840`; `progress.py:265-314` |
| G2 | **Phase 2 and re-search tasks have no watchdog at all** — fire-and-forget `create_task` with no ceiling anywhere. Re-search tasks are also unregistered in the inflight registry (the 2026-07-21 watch item). | `checks.py:1429` (phase2), `1662/1766/1866` (re-search ×3) |
| G3 | **Kills bypass everything.** The inflight guard runs only in the SIGTERM lifespan window; OOM/SIGKILL strands rows, and there is **no boot-time sweep**, so a stranded row stays `processing` forever with the credit burned. | `inflight.py:1-17,44+`; `main.py` lifespan (shutdown only) |

Plus one honesty defect found during this review:

| # | Defect | Code evidence |
|---|---|---|
| D3 | The SSE-side timeout emits *"Pipeline timed out. **Your credit has been returned.**"* — but that path performs **no refund**. It cancels the task; `CancelledError` (BaseException) skips the `except Exception` failure handlers, so no `handle_pipeline_failure`, no refund, no `failed` status. The message can lie to the user. | `progress.py:300-314`; `checks.py:562-583` |

## 2. Design — four small layers, one watchdog owner

Principle: **exactly one owner of the pipeline's lifetime — the task itself.**
Streams only ever *report*; they never control.

### W1 — Task-level watchdog (the core)

New helper (suggest `app/core/watchdog.py`, ~30 lines):

```python
def supervised_task(coro_fn, *, check_id, user_id, ceiling_s, label):
    async def _run():
        try:
            await asyncio.wait_for(coro_fn(), timeout=ceiling_s)
        except asyncio.TimeoutError:
            logger.error(f"[WATCHDOG] {label} exceeded {ceiling_s}s — failing {check_id}")
            await handle_pipeline_failure(check_id, user_id,
                PipelineError("This check took too long and was stopped. "
                              "Your credit has been refunded — please submit it again."))
    return asyncio.create_task(_run())
```

Applied at **all six** task-creation sites: the two submission paths
(`checks.py:586, 827`), phase 2 (`:1429`), and the three re-search sites
(`:1662, 1766, 1866`). Re-search sites also gain `inflight_register/unregister`
(closes the 07-21 exposure watch).

- `handle_pipeline_failure` is the existing, tested fail+refund path — no new
  refund logic. `refund_usage`'s `credits_used==0` guard makes double-refund
  impossible.
- `wait_for` cancels at await points; un-cancellable executor threads (pypdf)
  may linger briefly but are bounded by the PDF caps — the *check* still
  reaches `failed` immediately.
- `waiting_for_selection` needs nothing: the phase-1 task *ends* at the pause
  (durable by design), so the ceiling never touches a paused check.

**Ceilings (env-tunable, rollback = env var):**
- `PIPELINE_WATCHDOG_SECONDS = 300` — pipeline phases (slowest observed:
  123.9s; fully-starved estimate +~95s; 300 ≈ 2.4× the worst seen).
- `RESEARCH_WATCHDOG_SECONDS = 150` — single-element re-search/top-up.

### W2 — Boot-time stale sweep (heals every kill class)

In `main.py` lifespan **startup**, one-shot before serving:

```
UPDATE checks stuck in 'processing' (and 'pending' with no progress)
WHERE updated_at < now() - (PIPELINE_WATCHDOG_SECONDS + 120s grace)
→ status='failed', honest message, refund_usage (idempotent)
```

- Explicitly **excludes `waiting_for_selection`** (durable pause, resumes on
  any instance).
- **Deploy-overlap safe by construction**: with W1 live, no legitimate run can
  be older than the ceiling — any row older than ceiling+grace is
  definitionally dead. The old instance's still-running checks are younger
  than the threshold and untouched.
- After an OOM: Railway restarts the container → boot sweep fires → the
  stranded row is failed+refunded within ~a minute of restart. Today's
  `46406547` class becomes self-healing (it still needs one manual cleanup
  now — it predates the sweep).

### W3 — Stream hygiene (fixes D3)

`progress.py::events()` loses its cancel-and-claim-refund branch. The stream's
`max_duration` becomes purely a *connection* bound: on expiry it closes the
stream (client falls back to polling / reconnect). It never cancels the
pipeline and never asserts a refund it didn't make. W1 is the only lifetime
owner.

### W4 — Frontend stall surface (small slice)

On the check progress view:
- No progress event/status change for **45s** → calm notice: research is
  taking longer than usual, still working (no scolding, no spinner-forever).
- `failed` status → render the server's honest message (which now always
  includes the refund fact) instead of a stalled progress bar.
- Because W1+W2 guarantee a terminal state ≤ ceiling, the UI never needs its
  own kill logic — it only has to *render* truthfully and promptly.

## 3. Non-goals
- OOM prevention (shipped separately today, `df0095f`).
- Cancelling executor threads mid-parse (impossible in Python; bounded instead).
- Any queue/Celery migration; any retry-on-timeout logic (user resubmits).

## 4. Tests (gate before ship)
- **W1**: fake pipeline sleeping past a 1s ceiling → check `failed`, refund
  called once, message is the honest timeout copy; a fast pipeline is
  untouched; re-search site registers/unregisters inflight.
- **W2**: seed rows — stale `processing` (swept: failed+refunded),
  fresh `processing` (kept), `waiting_for_selection` stale (kept),
  `completed` (kept). Sweep idempotent on double boot.
- **W3**: stream expiry closes the generator without cancelling the task and
  without emitting the refund claim (update any test locking old behaviour).
- **W4**: `tsc --noEmit` + manual eyeball (per [[feedback_next_cache_churn]] —
  no build against a live dev server).
- Full pipeline unit suite green; no bench interaction (no prompt changes).

## 5. Rollout / rollback
- Two new env vars, defaults baked in code; no migration.
- Rollback: raise the env ceilings (effectively disabling W1) — W2/W3/W4 are
  strictly-safer behaviours with no rollback need.

## 6. Founder decisions requested
1. **Ceiling values** — 300s pipeline / 150s re-search acceptable? (Worst
   honest check so far: 123.9s. A ceiling too low fails real checks; too high
   just delays the honest failure.)
2. **User-facing copy** for the two new strings (watchdog failure message;
   stall notice) — wording is yours to lock; drafts above.
3. **Sweep scope** — also sweep stale `pending` rows (created but task never
   started, e.g. crash between insert and task start)? Recommend yes.
4. Sequencing — build now vs after T7/T8 grading. Recommendation: now; it
   converts both of today's incident classes into non-events.
