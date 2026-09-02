# Two defects from the Build A control arm — fetch-phase deadline, MCP idempotency (2026-09-02)

**Status:** BUILT the same evening (founder: "Proceed with recommendation").
**Found by:** `audit/OPEN_WORK.md` 2026-09-02, control arm item 1 — the TTE run `dd2ca726` and its retry `c8dd4886`.

## Defect 1 — the 45 s per-claim deadline discarded the whole web lane

**What happened.** `retrieve.py:1751` waits on the web task (search + fetch + extract of all 40 URLs)
and the API task together with `RETRIEVE_CLAIM_TIMEOUT_S = 45`. The comment says partial results are
preserved — true between the two tasks, false inside the web task. On `dd2ca726`: `Fetch budget
candidates=48 fetched=40`, `[DOMAIN_TRACKER] trusttheevidence.substack.com -> accessible`, then
`[CLAIM 0] Tasks timed out after 45s: ['web_search']` → `0 web snippets + 1 API snippets`. Every
fetched page, the critic's among them, was thrown away; post-filter recovery and coverage recovery
rebuilt a thin pool from month-windowed, 8-result queries. Any claim whose pages are slow (Substack,
PDFs, journal DOIs, with the pypdf parse serialised) loses its web lane the same way. Scotland's run
finished inside 45 s (30 candidates) and passed.

**The change.** `ENABLE_FETCH_PHASE_DEADLINE` (default True) + `RETRIEVE_FETCH_PHASE_TIMEOUT_S`
(30). `_execute_planned_queries` now calls `_extract_all_within_deadline`: every fetch runs as its own
task, `asyncio.wait(timeout=30)` returns what has finished, the stragglers are cancelled, and each
dropped page gets a URL-ledger receipt (`stage=fetch_deadline`) plus one summary line
(`[RETRIEVE] Fetch deadline | kept=N dropped_by_deadline=M`). The result list keeps the
`gather(return_exceptions=True)` shape and order, so nothing downstream changes. 30 s leaves the outer
45 s room for search (~3 s) and post-processing, so the all-or-nothing cut should not fire in practice.
Flag off = today, byte-for-byte. Bench: no request-signature change; replayed fetches are instant, so
the deadline never fires under the bench. `RETRIEVAL_CACHE_VERSION` bumped to `2026-09-02b` because the
pool a repeated claim gets is different now.

**Tests:** `tests/unit/pipeline/test_fetch_phase_deadline.py` (5) on the real retriever with a
URL-keyed fake extractor: finished kept / stragglers cancelled, alignment and the exception/None shape,
flag-off waits for everything, ledger receipts, empty set.

## Defect 2 — one hosted-MCP tool call ran, and charged, twice

**What happened.** The hosted MCP's streamable-HTTP `GET /mcp/` stream dies at ~140 s; the client's
next `POST /mcp/` gets `400` (session gone), it re-initialises and re-sends the pending tool call, and
the server executes it again. HTTP log 15:38–15:42: bursts of `400 → 200/202/200` bracket the two
checks. `tru8_mcp/tools.py` sent no `Idempotency-Key`, so the retry was a new check and a new charge
(30p for one call). Worse, once the key IS sent: `agent_auth.charge()` returned the existing
transaction (no second debit) but `_run_agent_pipeline` went on to create a second Check, run the
pipeline again and **re-point the transaction at the new check**.

**The change, both ends.**
- **Client** (`tru8_mcp/tools.py`): `idempotency_key_for(endpoint, payload)` — `mcp-` + sha256 of the
  endpoint, the payload and a ten-minute window; sent as `Idempotency-Key` on `/agent/check` and
  `/agent/{tier}`. A transport retry (observed gap ~150 s) maps onto the first call; an identical
  deliberate call ten minutes later is new. Residual: a retry that straddles a window boundary is
  still a duplicate — rare, and now harmless on the server side.
- **Server** (`app/api/v1/agent.py`): a fresh transaction has no check when `charge()` returns it, so
  `tx.check_id` is the exact signature of a replay. `_run_agent_pipeline` now returns
  `_idempotent_replay(...)` in that case: it waits (up to the tier's wall-time budget) while the
  original is still running, then builds the normal agent response for the ORIGINAL check with
  `chargedPence 0` and `X-Tru8-Idempotent-Replay: 1`; a failed original is a 502 (it was refunded
  then); a still-running original past the budget is a 504. No new Check, no run, no re-link.

**Tests:** `tests/unit/test_mcp_idempotency_key.py` (6): key stable in-window, changes with payload /
endpoint / window, reaches the headers of both POSTs, a 150 s retry sends the same key.
`tests/unit/agent/test_agent_idempotent_replay.py` (5): completed original returned at zero charge,
in-flight original waited for, failed → 502, over-budget → 504, and the wired seam —
`_run_agent_pipeline` with a replayed transaction never touches the session or the pipeline.

## Not changed
- The ~140 s stream death itself (transport / proxy idle). Idempotency makes the retry harmless; a
  keepalive is a separate, later item.
- Coverage recovery still windows every query to the past month with no unwindowed twin (Piece 2 of
  `2026-09-02_pool_quality_gate_scope.md`, held behind the sends).

## Rollback
`ENABLE_FETCH_PHASE_DEADLINE=False` on Railway (no deploy). The idempotency changes have no flag —
they only ever return a check that already exists.
