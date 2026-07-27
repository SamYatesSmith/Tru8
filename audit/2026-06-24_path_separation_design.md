# Design Review — Path-Separation Wall (2026-06-24)

**Phase:** design only (no code). Frozen acceptance criteria below for founder approval before any build (phased-build-loop).

## Problem (the leak, confirmed in code)
`POST /checks/stream` and `POST /checks/run` accept **either** a Clerk JWT **or** an API key (`get_current_user_or_api_key`). Both resolve to the same user, and `_validate_and_create_check` (`checks.py:107-131`) then bills against the **subscription/free-trial quota** with no check on *how* the caller authenticated. → an API key on a £20 fair-use sub can submit unlimited programmatic checks for £20. The channel (`via = "api_key"|"dashboard"`) is already computed at `checks.py:638` / `:899` but only logged.

`/agent/*` is **not** leaked — it already debits the prepaid `credit_balance_pence` per call.

## Confirmed safe to close cleanly
- MCP submits via `/agent` (`tru8_mcp/server.py:99` → `submit_with_fallback` → `/agent/*`). The `/checks` submit helpers in `tools.py` are vestigial/unused by the exposed tools.
- Developer docs don't document `/checks` submission.
- → No real client submits checks via `/checks` with an API key.

## Recommended design — "Console submit is sign-in only"
Make the two **submit** endpoints reject API-key auth; programmatic submission already lives at the metered `/agent`.
- `POST /checks/stream` + `POST /checks/run`: if authenticated by API key (`via == "api_key"`, already computed) → **403** with a clear message: *"Programmatic check submission uses the metered /agent endpoints — see /developers. The /checks submission endpoints are for signed-in Console users."* Clerk JWT + the SSE stream-token path unchanged.
- All **read** endpoints (`GET /checks/{id}`, `/progress`, `/public/...`, `/export/...`) keep accepting API keys — MCP/API users read results there. Unaffected.

**Why this over metering `/checks` per call:** less code, no refund-on-failure branching, no duplicated pricing logic; closes the leak *by construction* (an API key never reaches the subscription billing path); and it makes the product boundary crisp — **Console = `/checks` = sign-in; API = `/agent` = metered.**

## Touch points (surgical)
1. A 2-line guard at the top of each submit handler (`checks.py` ~638 and ~899) where `via` is already computed: `if via == "api_key": raise HTTPException(403, ...)`.
2. `_validate_and_create_check` — **no change** (never sees api-key submits anymore).
3. `/agent/*` — **no change** (already correct).

## Explicitly OUT of scope (later, if/when needed)
- Personal-API allowance (£20 includes ~50–100 calls/mo) — a generosity feature, additive later; the wall doesn't need it.
- Trimming `/agent` full price vs Webcite — separate pricing tweak.
- `REPO-STRIPE` credit-pack purchase blocker — only when a real API buyer appears.

## Frozen acceptance criteria
1. `POST /checks/stream` and `/checks/run` with `X-API-Key` (no JWT) → **403** pointing to `/agent` / `/developers`.
2. Same endpoints with a valid Clerk JWT → **unchanged** (create check, enforce sub/trial quota).
3. SSE **stream-token** path still streams progress.
4. `GET /checks/*` (result, progress, public, export) with an API key → **still works**.
5. `/agent/*` submission with an API key → **unchanged** (metered against `credit_balance_pence`).
6. **No path remains** by which an API key debits `Subscription.credits_per_month` or `user.credits` (grep/trace proof).
7. Backend suite green; new unit tests for criteria 1–2.
8. Single, reversible commit.

## Verification (independent, not the builder)
Fresh reviewer confirms 1–6 with evidence (403 on api-key submit; JWT still creates checks; read endpoints still accept keys; trace proving no api-key→subscription billing path) + `pytest` green.

---

## ADDENDUM — Stricter version: reject on resolved auth method (design 2026-06-24)

**Why:** the header-only guard keys off `X-API-Key` *presence*, not whether the resolved principal authenticated as an API key. Faithful today (keys only arrive via that header) but brittle if a future auth channel resolves an api-key principal differently. The stricter version records the auth method at the point of resolution and the guard keys off that (header kept as a fallback).

**Change 1 — `auth.py` (additive only; no return value or error behaviour changes):** set `request.state.auth_method` in each resolution branch of the two dual-auth dependencies the submit endpoints use:
- `get_current_user_or_api_key` (`auth.py:275-303`): JWT branch (~293) → `"jwt"`; API-key branch (~298) → `"api_key"`.
- `get_current_user_or_api_key_sse` (`auth.py:347-398`): stream-token branch (~367) → `"stream_token"`; deprecated JWT-query branch (~378) → `"jwt"`; Bearer-JWT branch (~388) → `"jwt"`; API-key branch (~393) → `"api_key"`.
- (Out of scope: `get_current_user` JWT-only dep — submit endpoints don't use it; the guard's header fallback covers any gap. Could add `"jwt"` there later for consistency.)

**Change 2 — `_require_console_submission` (`checks.py`):** key off the resolved method, header as belt-and-braces:
```python
auth_method = getattr(request.state, "auth_method", None)
if auth_method == "api_key" or request.headers.get("X-API-Key"):
    raise HTTPException(403, ...)
```
Strictly more rejections than either check alone; **zero false positives** (JWT/stream-token never set `auth_method="api_key"` nor send the header). FastAPI passes one `Request` per request, so the flag set in the dependency is readable in the handler-body guard (which runs after deps resolve).

**Updated/added acceptance criteria (supersede where overlapping):**
- A1. (was) API-key submit *with header* → 403. Still holds.
- A2. **(new)** A caller resolved as api-key (`request.state.auth_method == "api_key"`) → 403 — proves method-based, not header-only.
- A3. **(new)** `auth_method == "jwt"` → `"dashboard"` (allowed).
- A4. **(new)** `auth_method == "stream_token"` → `"dashboard"` (allowed).
- A5. **(new)** `auth.py` edits are additive — every branch still returns the same `{id,email,name}` dict and raises nothing new; `request.state.auth_method` set in all branches of both dual-auth deps.
- A6. No regressions: full `tests/unit/api/` + existing `_validate`/auth suites green.
- A7. Single reversible commit (now `checks.py` + `auth.py` + extended test).

**Verification (independent):** re-run the verifier on the combined diff — confirm auth.py edits are additive (no behaviour change for other dual-auth endpoints), the guard rejects on resolved method (A2) and allows jwt/stream-token (A3/A4), no api-key→billing path remains, and the suites are green. Plus a live ASGI smoke if desired.

**Risk:** `auth.py` is security-critical and widely used. **Mitigation:** edits are strictly additive (set an attribute before existing returns); re-verify with the auth/api suites + independent verifier.

---

## ADDENDUM 2 — Extend the wall to the Seeker re-search endpoints (design 2026-06-24)

**Why:** independent verification of the hardened wall found a *second* subscription-billed path still reachable by API keys: the re-search endpoints `start_gap_research` (`checks.py:1602`) and `start_element_research` (`checks.py:1705`). Both authenticate via `get_current_user_or_api_key` (so `request.state.auth_method` is already set) and bill `user.credits`/subscription via `_check_credits` (`:1672/:1770`) + `_deduct_credit` (`:1679/:1776`) — NOT via `_validate_and_create_check`, so the submission guard doesn't cover them. Re-search is a Console-only feature (no `/agent` re-search exists), so an API key should not trigger billable re-search. Closing this makes the wall's promise — *no API key bills the subscription* — complete.

**Change (same mechanism):** to each of the two re-search handlers:
1. add a `request: Request` parameter, and
2. call `_require_console_submission(request)` as the **first statement** in the handler body (before check-validation, credit check, or the `re_search` import) so an API-key caller 403s before any work or billing.

The helper already works here because these endpoints use the same dual-auth dependency that sets `auth_method`.

**Two minor copy/naming points (low-churn choices):**
- Generalise the guard's 403 message so it fits both submission and re-search, e.g. *"This endpoint is for signed-in Console users; programmatic/agent access uses the metered /agent endpoints (see /developers)."* (Still mentions `/agent`; existing test assertion `"/agent" in detail` still holds.)
- Keep the helper name `_require_console_submission` (a re-search is still a billable Console operation) to avoid churn; OR rename to `_require_console_auth` for accuracy (touches 2 submit sites + test import). **Recommend: keep the name, generalise the message.**

**Frozen acceptance criteria (EX):**
- **EX1** Both re-search handlers call `_require_console_submission(request)` as their first action, with `request: Request` added to each signature.
- **EX2** An API-key caller to either re-search endpoint → **403** (mentions `/agent`) **before** any credit is checked or deducted. Proven by a live ASGI test mounting the real router (guard short-circuits before DB/re_search).
- **EX3** JWT/Console callers unaffected — re-search still works for signed-in users (guard passes; no behaviour change beyond the guard).
- **EX4** Only the `request` param + guard call added to the handlers; no other change to re-search logic.
- **EX5** `_require_console_submission` is now called at EXACTLY four sites (2 submit + 2 re-search), nowhere else.
- **EX6 (completeness):** no remaining billable API-key path — every code path that debits `user.credits`/subscription (`_validate_and_create_check` AND `_check_credits`/`_deduct_credit`) is now guarded against api-key callers. Verifier re-runs the bypass hunt for any THIRD path.
- **EX7** All tests green (existing 10 + 132 + new re-search test); folds into the single P1 commit.

**Verification (independent):** verifier confirms EX1–EX6 with file:line evidence, runs the suites, and re-hunts for any other endpoint that bills `user.credits`/subscription without the guard.

**Risk:** adding `request: Request` to a handler is inert (FastAPI injects it); placing the guard first means api-key callers never reach validation/billing. Low risk; re-verified.
