# Idempotency replay failure — root cause (2026-09-11)

**Status:** DIAGNOSED, code-only, no fix applied. Companion to `2026-09-02_fetch_deadline_and_mcp_idempotency.md`.
**Observed:** hosted MCP `tru8_check` (heatwave claim, max_tier full, max_age_hours 0, compact true) →
check `a093c7d2` 09:58:40 UTC, client saw a Cloudflare 502; resend 10:04:20 → NEW check `bebfa026`, NEW 15p charge.
Second pair (wildfire): 09:47:13 → `580fd5b4`, resend 10:00:36 → `12f607d1`.

## 1. Mechanism — the client key is a fixed clock bucket, not a window

`backend/tru8_mcp/tools.py:59-63`:
```python
bucket = int((time.time() if now is None else now) // IDEMPOTENCY_WINDOW_S)   # 600
raw = json.dumps({"e": endpoint, "p": payload, "b": bucket}, sort_keys=True, default=str)
```
`floor(epoch / 600)` is a **fixed bucket aligned to :00/:10/:20…** of every UTC hour, not a sliding
ten-minute window from the first call. Reproduced with the real timestamps and payload:

| pair | first call → bucket | resend → bucket | same key | gap |
|---|---|---|---|---|
| heatwave | 09:58:40 → 2981867 | 10:04:20 → 2981868 | **no** | 340 s |
| wildfire | 09:47:13 → 2981866 | 10:00:36 → 2981868 | no | 803 s |

The heatwave resend therefore carried a **different `Idempotency-Key`**. Server side:
`app/core/agent_auth.py:70-82` looks a transaction up by key alone; no row → fresh debit (`:85-93`) →
new `AgentTransaction` (`:95-108`) → `agent.py:836` sees no `check_id` → new Check + full pipeline.
Every server layer behaved as designed; the retry never presented the first call's key.

**Why the 502 did not matter.** The origin kept running after Cloudflare cut the client off: the tx is
linked to its check at `agent.py:866-867` before the pipeline starts, the check completed ~09:59 and
`tx.status` was set `completed` at `:965`. Had the key matched, `_idempotent_replay` (`:1040-1110`)
would have returned `a093c7d2` at `chargedPence 0`. Same process, same clock — the hosted stateless
path builds the client per request (`server.py:125-142`) and calls the same `submit_with_fallback` →
`submit_smart` (`tools.py:185`) that sets the header. `/agent/check` honours it exactly like
`/agent/full` (`agent.py:388-403` vs `:734-748`, both into `_run_agent_pipeline`).

**Probability.** A retry after gap *g* straddles a boundary with probability *g/600*: 23% for the
~140 s stream death the 2026-09-02 fix was built for, 57% for this morning's 340 s. The design note's
residual — "a retry that straddles a window boundary is still a duplicate — rare, and now harmless on
the server side" — is wrong on both counts: the server cannot see a duplicate it was given a new key
for, so a straddle is a **full second charge**.

**Wildfire pair: expected.** 803 s apart is outside any ten-minute window (bucketed or sliding), so a
re-run and second charge is the documented behaviour. The retrieval pool replay is unrelated: the
per-claim evidence cache (`RETRIEVAL_CACHE_VERSION`, 24 h TTL) served the pool; classify/map re-ran.

## 2. Minimal fix — key without time; window enforced server-side from first-seen

**Client — `tru8_mcp/tools.py:59-63`.** Drop the bucket. Salt with the caller instead:
`raw = {"e": endpoint, "p": payload, "k": sha256(api_key)[:16]}` (make `idempotency_key_for` a method
or pass the key in). `IDEMPOTENCY_WINDOW_S` moves to the server as `AGENT_IDEMPOTENCY_TTL_S = 600`
(`config.py`). Update the docstring at `server.py:223-224` only if wording changes.

**Server — `app/core/agent_auth.py::charge` (`:70-82`).** After the existing-key lookup:
1. `existing_tx.payer_id != self.payer_id` → **409** (never a replay across payers; see §3a).
2. `request_hash` mismatch → 409 (unchanged).
3. `existing_tx.status` non-terminal (`pending`) → return it (a resend while the original is still
   running is replayed and waits — `_idempotent_replay` polls up to `max_wall_time_seconds`, 180 s
   full / 30 s quick, `runner.py`; past that it is a 504, and the caller can resend again).
4. Terminal and `now - existing_tx.created_at <= TTL` → return it (replay).
5. Terminal and older than TTL → retire the old key in the same transaction
   (`existing_tx.idempotency_key = f"{key}#{existing_tx.id}"; flush`) and fall through to a fresh
   debit + insert. The unique index (`ix_agent_transaction_idempotency_key`) stays as the race guard;
   wrap the insert's flush in `except IntegrityError: rollback; re-select; return existing`.

Window semantics become **[first_seen, first_seen + 600 s]** wherever the boundary falls; a retry at
any gap under ten minutes maps onto the first call, a deliberate identical call later is new.

**Tests.** `tests/unit/test_mcp_idempotency_key.py`: key equal at `now=590` and `now=930` (straddles
a 600 boundary — the case that failed today); key differs across API keys; the 150 s retry test
unchanged. `tests/unit/agent/test_idempotency.py`: existing terminal tx aged 599 s → returned,
`session.add` not called; aged 601 s → old key retired, new tx added; aged 601 s but `pending` →
returned; other `payer_id` → 409. `test_agent_idempotent_replay.py` stays green as is.

## 3. Second defects seen on the way

**(a) Cross-user collision — the key carries no caller identity.** The client key is endpoint + payload
only (`tools.py:62`); the server lookup is by key alone (`agent_auth.py:70-73`), `request_hash` is
tier + claim + compact (`:112-115`), and `_idempotent_replay` / `build_agent_response` never check
ownership. Two hosted-MCP users submitting the identical claim in the same bucket: the second gets the
first user's check back, uncharged. Closed by the salt (client) + payer check (server) in §2.

**(b) Smart endpoint replays fail as 409 for the default `max_age_hours=None`.** A retry after the
original completed hits Step 1 lookup (`agent.py:196-227`): the original check is now a cache hit,
`charge()` is called with `request_hash("lookup", …)` (`:231-238`) against a row stored with
`request_hash("full", …)` → 409 "already used with different parameters". Today's calls escaped only
because `max_age_hours=0` invalidates the lookup (`:219-225`). Fix: when `idempotency_key` is set,
select the existing tx first and, if it owns a check, go straight to `_idempotent_replay` before the
lookup branch.

**(c) Link-before-visibility race.** `charge()` flushes without committing; the tx first becomes visible
at the commit on `agent.py:862` with `check_id` still NULL, and is linked at `:866-867`. A resend in
that gap sees `tx.check_id` None and takes the old double-run path (`:845-867`, re-link included). Set
`tx.check_id = check.id` before the first commit (one-line reorder). Milliseconds wide; not today's cause.

**(d) x402 route lacks the replay guard.** `agent_x402.py:151-159` calls `charge()` with the header but
has no `tx.check_id` short-circuit — the pre-2026-09-02 behaviour (second Check, re-link). x402 is OFF
in prod; fix when it is switched on.
