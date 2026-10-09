# Async `/agent/check` + polling MCP client — design (2026-10-09)

**Why:** F11 (`audit/2026-10-08_complex_stage_functions_review.md`). `tru8_check` holds ONE silent POST to `/agent/check` for the whole pipeline. Cloudflare closes an origin that is silent for 125 s (Enterprise-only to raise). Prod worst so far 90 s for MCP, 114 s for web; the tail will cross 125 s, and then the caller loses the result while the server finishes and keeps the charge. Polling keeps every request short.

## Server (`app/api/v1/agent.py`)
1. `POST /agent/check?async=true` (new query param, default False → today's behaviour for every existing caller, including `tru8-mcp` ≤1.0.3).
   - Lookup / consensus hits and the structured misses are instant → returned exactly as today (200).
   - Pipeline escalation → `_run_agent_pipeline(async_mode=True)` → existing 202 `{checkId, status, tier, chargedPence, txId, pollUrl, estimatedSeconds}`.
2. Idempotent replay never holds a silent connection in async mode. `_replay_for_key` and the `tx.check_id` branch of `_run_agent_pipeline` pass `async_mode`; `_idempotent_replay(wait=False)`:
   - completed → full result, 200, `chargedPence 0` (as today);
   - failed/error → 502 (as today);
   - still running → **202** `{checkId, status, tier, chargedPence: 0, txId, pollUrl}` + `X-Tru8-Idempotent-Replay: 1`, no wait.
   Sync mode keeps today's wait (old clients).
3. Async background task held in `_background_tasks` (today a bare `create_task`, collectable by GC mid-run).
4. Docstrings: drop "set your HTTP client timeout to at least 180 seconds"; say "use `?async=true` and poll" (`agent.py` /full + /check, `checks.py` /run, `main.py` OpenAPI text).

## Client (`tru8_mcp/tools.py`)
- `submit_smart` sends `?async=true` when `max_tier` is quick/full. The request timeout stays at the tier timeout, so an OLD server that ignores the param and answers synchronously still works.
- 200 → return as today. 202 → `_await_agent_result(check_id, charged_pence)`:
  - `GET /agent/result/{id}` every 5 s (30/min limit is per API key → 12/min per check; on 429 wait `Retry-After` or 10 s);
  - `completed` (payload has `_meta`/`claims`) → return it with `_meta.chargedPence` restored from the 202 (the result endpoint always reports 0);
  - `failed`/`error` status → raise `RuntimeError("check {id} failed; the charge was refunded")`;
  - overall deadline 330 s (watchdog 300 s + margin) → return `{checkId, status: "processing", message: "still running — call tru8_get_result with this checkId"}`, never an error that invites a re-submit.
- Idempotency key unchanged (query param is not in the payload) → old-sync and new-async calls of the same claim share a key and a request hash.
- Release as `tru8-mcp` 1.0.4 (owed anyway). Hosted `/mcp` picks it up on deploy.

## Not changed
`/agent/quick|full` sync defaults; `/agent/result` itself; charging, refund and idempotency rules; `/checks/run` behaviour (founder tooling already polls).

## Tests (first, seen failing)
Server: `/agent/check?async=true` miss → 202 + task held in `_background_tasks`; lookup hit with `async=true` → 200 unchanged; replay of a running check in async mode → 202 immediately (no sleep), sync mode still waits; completed replay → 200. Client (httpx mock transport): 202→processing→completed returns result with restored `chargedPence`; failed → error; 429 → backs off and continues; deadline → processing message; 200 sync answer → returned unchanged.

## Review resolutions (independent design review, same day)
- **B1 (blocker)** poll failure could trigger the old-server fallback (`"404" in str(e)` matched check ids) → a second charged run. Fixed: `Tru8APIError(status_code)`; fallback only on a SUBMIT 404; `CheckFailedError` is not a `RuntimeError`.
- **B2 (blocker)** outer hosted `/mcp` POST is one long tool call. Verified in the live container (mcp 1.12.4, sse-starlette 3.0.3): the POST answer is an `EventSourceResponse` with the default 15 s ping, which reaches the wire since the gzip fix (`87118a4`). Stateless mode cannot send progress notifications, so pings are the mechanism; guard test pins `json_response is False`.
- S3 `/agent/result?compact=true` added. S4 deadline per tier = 2 phases × wall time + 60 s (full 420 s, quick 120 s) — the agent background task is bounded per phase, not by the 300 s watchdog. S5 any status but completed/failed = running (`waiting_for_selection` occurs between phases). S6 async failure refunds only a `pending` tx under `FOR UPDATE`; the stranded sweep locks too. S7 `refunded`/`failed` tx → idempotency `expired` at once (retry charges afresh, the failed run cost nothing). S8 poll 8 s; fixed 10 s backoff on 429/5xx (no Retry-After is sent). S9 neutral wording (credits refunded, other rails unsettled).
- Nits done: `wait=True` default; batch task held; 202 in OpenAPI; `/full` rate text; `tru8_check` docstring; "180 s" docs (OpenAPI intro also wrongly called `/checks/run` "recommended for agents" — API keys get 403 there).

## Open (separate)
Railway `TRU8_API_URL` for the hosted route (inner calls may loop out through Cloudflare). Still worth reading, but with polling every inner call is short.
