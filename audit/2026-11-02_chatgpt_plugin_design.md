# ChatGPT Plugin: design (rev 2, after review round 1)

2026-11-02 · Status: **DESIGN, not built.** Research: `audit/2026-11-02_chatgpt_plugins_research.md`.
The project rule requires a design review at difficulty ≥3, and this is 4: auth plus a protocol change on a paid tool.

## Goal
List Tru8 in the ChatGPT Directory as a plugin backed by the hosted MCP server (`https://api.trueight.com/mcp/`).
A ChatGPT user links their Tru8 account once (OAuth through Clerk) and then runs checks paid from their existing credits.
Nothing is sold inside ChatGPT (OpenAI rule).

## Non-goals
- No purchase, upgrade or pricing prompts in ChatGPT responses.
- No change to the stdio package, API-key callers, Smithery, or the dashboard.
- No widget/UI in v1. Text tool results only.

## Constraints (from research; ⚠ = unconfirmed, settled by P0)
- Auth must be none or OAuth 2.1 with PKCE S256. ChatGPT registers itself by CIMD or DCR, and needs `/.well-known/oauth-protected-resource`.
- ⚠ A tool call is cut off after about 60 s in ChatGPT (forum reports only). A full check takes 60–120 s.
- ⚠ Whether Clerk access tokens carry our resource URL in `aud`.
- ⚠ Whether Clerk's OAuth provider is on our plan.
- ⚠ How ChatGPT learns a tool needs linking. Expected: `securitySchemes` on each tool, plus an auth-challenge `_meta` on an unauthenticated call. Read OpenAI's auth page in P0.
- Smithery's scanner lists tools with no credentials (2026-08-05). **Listing must stay open; only tool calls need auth.**

## Current state (code read 2026-11-02)
- **Hosted `/mcp`:** stateless streamable HTTP (`main.py:491-563`). Each tool builds a `Tru8APIClient` per request (`tru8_mcp/server.py:_get_client`).
  - The client calls OUR OWN public API over HTTP, sending the caller's key as `X-API-Key`.
  - `_request_api_key` already accepts `Authorization: Bearer <api key>` as a courtesy and forwards it as `X-API-Key`.
- **`/agent/*` identity** (`agent_auth.get_agent_identity` / `get_agent_payment`): Skyfire JWT or `X-API-Key` only. The credit rail debits `User.credit_balance_pence`.
- **`/checks/{id}`** (used by `tru8_get_result`): `auth.get_current_user_or_api_key` takes a Bearer **Clerk session JWT** or an API key.
- **Session JWT check** (`auth._verify_jwt_token`): RS256 against the instance JWKS plus the issuer. **`aud` is enforced only if `CLERK_JWT_AUDIENCE` is set** ("legacy permissive").

## ⚠ Security hazard H1: token confusion (must close before anything ships)
Clerk OAuth access tokens, when issued as JWTs, are probably signed by the same instance keys with the same issuer as session tokens. If so:
- **Today, unchanged:** an OAuth token minted for ChatGPT could pass `_verify_jwt_token`. It would get full dashboard power over the user's account (keys, billing, deletion), not just "run checks".
- **The reverse:** a dashboard session token must never pass the new OAuth check.

**Rule:** each check accepts exactly one token type, decided by claims, not by which header carried it.
- Session tokens carry Clerk's session claims (`sid`). OAuth access tokens carry `client_id`/`scope` and possibly a `typ` of `at+jwt`. P0 records the real claims.
- Both checks reject the other type, and a negative test pins each direction.
- If Clerk issues **opaque** OAuth tokens instead, H1 cannot happen. Verification then goes through Clerk's verify endpoint, adding one network call per tool call (cache by token hash for its lifetime).

## Design

### Part A: OAuth (Clerk as authorization server)
1. **Clerk dashboard** (founder, or Clerk's management MCP if allowed):
   - Enable OAuth applications. Prefer **CIMD**; turn on DCR only if ChatGPT needs it.
   - Set default scopes (ChatGPT omits `scope`).
   - Use JWT access tokens if offered (no network call per request; H1 rules apply).
2. **`GET /.well-known/oauth-protected-resource`** (and the path-suffixed `/.well-known/oauth-protected-resource/mcp`): `resource = https://api.trueight.com/mcp/`, with `authorization_servers = [Clerk issuer]`.
   - Also publish `/.well-known/oauth-authorization-server`, mirroring Clerk's, for older clients (Clerk's own helper does this).
3. **`verify_oauth_access_token(token)`**, a new function in `app/core/oauth_tokens.py`:
   - Checks signature, issuer, `exp`, the OAuth claims (H1), and the audience/resource (form set by P0).
   - Returns `{user_id: sub, client_id, scopes}`.
4. **Identity:** a third branch in `get_agent_identity` and `get_agent_payment` — a Bearer token that is not a `tru8_sk_` key is verified as OAuth, giving `AgentIdentity(provider="credit", payer_id=user_id, user_id=user_id)`.
   - The same credit rail, idempotency and refunds as an API key. No new money path.
   - Sub→user: the same lookup the dashboard uses for Clerk IDs, without its lazy "create user" side effects, if any. Confirm in build.
5. **`/checks/{id}` read:** `get_current_user_or_api_key` gains the OAuth branch for reads only. Alternatively, switch `tru8_get_result` to `/agent/result/{id}` (see B3), so `/checks` never sees an OAuth token. **Preferred: switch, giving a smaller surface.**
6. **MCP plumbing** (`tru8_mcp/server.py`): `_request_api_key` becomes `_request_credential()`, returning `("api_key", k)` or `("bearer", t)`, split on the `tru8_sk_` prefix.
   - `Tru8APIClient` sends either `X-API-Key` or `Authorization: Bearer`.
   - The idempotency key salt uses the user identity, not the raw token. OAuth tokens rotate, so salting with the raw token would break the ten-minute replay. The client cannot know the user ID, so salt with a hash of the token's `sub` claim, decoded **without** verification (the server verifies). Alternatively, send no key and let the server derive one. Reviewer: pick.
7. **Tool auth declaration:**
   - `tru8_check` gets `securitySchemes = [oauth2]`.
   - The read tools get `[oauth2]` too, since they are per-user.
   - An unauthenticated call returns a tool error carrying the auth challenge in OpenAI's documented form (P0 confirms the exact shape). **Listing stays unauthenticated.**
   - API-key callers are unaffected: the server still accepts `X-API-Key`; the scheme declaration only tells OAuth clients what to do.

### Part B: the ~60 s limit
1. **Budgeted wait:** in hosted mode, `tru8_check` waits at most `MCP_HOSTED_TOOL_BUDGET_S` (default 45). The async route already exists (202 + poll). Past the budget it returns the existing still-running answer (`checkId`, `status`, `chargedPence`, a plain message). The stdio package keeps its long deadline (no limit there).
   - The budget is per transport, not per client: the hosted stream already dies at ~140 s for every client, so a 45 s budget helps Claude.ai and Smithery users too.
   - Reviewer: confirm this behaviour change is acceptable for existing hosted callers. Today they get the result in one call; they would sometimes need a second call.
2. **`tru8_get_result` waits too:** while the check is running, it polls up to the same budget before returning. A full check therefore completes in 2–3 tool calls, not many.
3. **Read path:** `tru8_get_result` reads `/agent/result/{id}` (running → status; completed → result, with `_computed` if we add `?computed=true`, or keep `/checks` for the computed block). Build decision; A5 prefers `/agent/result`.
4. **Message wording:**
   - The still-running message tells the model the check is not finished and how to fetch it.
   - ⚠ OpenAI's guideline forbids telling the model to call another *plugin or connector*. Naming our own tool is believed fine; P0 reads the exact rule.
   - The 402 wording stays neutral: "Insufficient balance for <tier> tier" (today's text), with no link.

### Part C: listing (founder-owned unless noted)
- OpenAI Platform: identity verification (individual or business), domain verification (`trueight.com`).
- Pages: privacy policy, terms, support (exist? Claude to check the live URLs).
- 5 positive and 3 negative test prompts, plus a demo video.
- A reviewer account with no MFA and some credits.
- Countries: GB (+US?).
- Annotations, with a justification for each:
  - `tru8_check` keeps `readOnlyHint=false` and `openWorldHint=true`.
  - **`destructiveHint`: open.** It charges money but deletes nothing; today it is false. Reviewer: argue it.
- Responses: audit for internal IDs. `checkId` is needed; `txId` and the idempotency headers should not reach the model.

## Phases (each verified independently before the next)
- **P0 spike (free, a Clerk DEV instance, no prod change):**
  - Enable OAuth + CIMD/DCR.
  - Mint a token with MCP Inspector against a local `/mcp`.
  - Record the real claims (`iss`, `aud`, `typ`, `sid`, `client_id`, `scope`) and JWT vs opaque.
  - Read OpenAI's auth + guidelines pages for the challenge shape and the cross-tool rule.
  - **Exit:** H1 rule written as concrete claim checks, the aud/resource answer, and the challenge shape.
- **P1:** `oauth_tokens.py` + the H1 negative tests (session ↛ OAuth, OAuth ↛ session, wrong aud, expired, wrong issuer). Session-check hardening ships in the same commit.
- **P2:** the protected-resource metadata endpoints, the agent identity branch, MCP credential plumbing, securitySchemes and the challenge. Tests at the HTTP seam (tokens minted from a test key pair).
- **P3:** Part B budgets, with tests that use time travel.
- **P4:** end to end on the dev instance — MCP Inspector, then ChatGPT developer mode (⚠ confirm it exists for custom MCP) — before any production Clerk change.
- **P5:** production Clerk settings (founder), deploy, then submission (founder).

## Risks
- **H1:** token confusion (above). Highest severity.
- **Lazy user creation:** if an OAuth `sub` has no Tru8 user row, we must not auto-create a payer silently. Return a neutral "link a Tru8 account at trueight.com" error.
- **Account takeover via email linking** (`get_or_create_user` hands an existing row to a new Clerk ID with the same email; F1 note 2026-10-08). OAuth `sub` is the same Clerk user ID as the dashboard, so no new path, but confirm "Verify at sign-up" stays on in production.
- **DCR opens a public registration endpoint** — CIMD preferred.
- **Cost of mis-scoping:** a ChatGPT user's model could fire repeated checks. The ten-minute idempotency replay and the per-key 10/min rate limit apply. Confirm the limiter keys on user, not API key, for OAuth callers.

## Founder decisions (one at a time, when reached)
1. Run P0 on a Clerk dev instance (free).
2. Countries (GB only, or GB + US).
3. Starter credit for newly linked accounts? An OpenAI rule forbids selling credits inside ChatGPT, not giving them away. Today a new user has 0 pence on the agent rail and every check returns 402.
4. Identity verification as an individual or a business.


## Review round 1 (independent reviewer, 2026-11-02): changes adopted in rev 2
Verdict: *proceed to P0 after fixes*. Blockers 1 and 2 were confirmed against the code by the author before adopting them.

**BLOCKERS**
- **R1. The rate limiter would put every ChatGPT user in one bucket.**
  - `app/core/rate_limit.py:16-22` keys on `X-API-Key`, else on IP.
  - The hosted MCP calls our public API from Railway's egress IP, so all OAuth callers would share `/agent/check` 10/min and `/agent/result` 30/min.
  - **Fix:** identity resolution sets `request.state.rate_key = "user:<id>"` and the key function prefers it; fall back to a sha256 of the whole Bearer token, never an unverified `sub`.
  - P2 must verify that slowapi 0.1.9 reads state after dependencies resolve. If it does not, key in the function from a verified token. Test it.
- **R2. H1 is wider than stated.**
  - Clerk also issues OIDC **ID tokens** (RS256, same JWKS), which `auth.py:62` (the only Clerk `jwt.decode`) would also accept.
  - With CIMD, **any website** can register as a client, so one consent hands that site full dashboard power.
  - **This is live the moment OAuth is switched on in production Clerk, before any Tru8 code changes.**
  - **Fix:** the session check positively identifies a session token: requires `sid` (`sess_…`), requires `azp` in our web-origin allowlist, and rejects `typ: at+jwt` / `id_token`-shaped tokens.
  - Negative tests: an OAuth access token and an ID token are both rejected.
  - **HARD GATE: P1 deployed and verified in production BEFORE the production Clerk OAuth toggle.**

**HIGH**
- **R3. Bind tokens to us.** OpenAI requires `aud == resource` (unconfirmed whether Clerk honours `resource`). Additionally require a custom scope (`tru8:check`) and allowlist `client_id` (ChatGPT's CIMD URL). Scope also separates token types, since session tokens carry none.
- **R4. Subscribers would get 402.** The agent rail debits `credit_balance_pence`; Console subscribers' allowance lives in `usage_events`.
  - **Founder decision:** which ledger an OAuth call draws from.
  - Also bears on OpenAI review, which needs a fully featured demo account and rejects "additional sign-up steps".
- **R5. Re-link challenge.** Verify the token in the MCP layer itself, in process with no network call. A missing, invalid or expired token returns `_meta["mcp/www_authenticate"]` (with `error` + `error_description`). Any downstream 401 maps to the same challenge.

**MEDIUM**
- **R6. Idempotency salt:**
  - Salt with the *verified* `sub` (available once R5 is in place).
  - Better: the server namespaces keys by payer, so the client salt stops mattering.
  - Never salt with the raw token.
- **R7. Make the budget real:**
  - One deadline from tool entry; every sleep and httpx timeout is capped at the time remaining, including the submit POST (today 60/210 s).
  - Test with a slow mock server.
  - The message says a REPHRASED claim is a new, charged check.
- **R8. `securitySchemes`:** register them on the hosted instance only (`main.py`), since `tool(meta=)` may not exist at the package floor. Regression test: an unauthenticated `tools/list` still returns 3 tools (Smithery).
- **R9. Resource URL:** `/mcp` vs `/mcp/` (307). Accept both as `aud`. Update the served card's `authentication` block (apiKey only today) and its test.
- **R10. `destructiveHint=true`** on `tru8_check` (a charge cannot be undone; OpenAI: being able to undo does not justify false). This gives a confirmation prompt in ChatGPT.
- **R11. Revocation:** refresh tokens never expire, so users need an unlink. Either a dashboard "connected apps" revoke, or opaque tokens.

**LOW**
- **R12.** Use the client tag `mcp-oauth` so ChatGPT usage is measurable.
- **R13.** Reject requests carrying Bearer and `X-API-Key` together.
- **R14.** Audit the `tru8_check` description (£ prices versus "no upgrade promotion") and `_meta` for internal IDs.
- **R15.** CORS on `/.well-known/oauth-protected-resource`, for browser clients like MCP Inspector.

**Tests added to P1/P2/P3:**
- ID-token negative, plus client_id/scope negative.
- Rate-limit key per user.
- Expired-token challenge.
- Budget overshoot against a slow server.
- Unauthenticated-listing regression.
- Server-card update.

**Founder decisions, revised order:**
1. ~~Ledger for OAuth calls (R4).~~ **DECIDED 2026-11-02 (founder): A — the user's existing allowance.**
   - An OAuth check draws on the dashboard allowance first, through the `usage_events` gate: Console monthly checks, or remaining trial checks.
   - It then falls back to prepaid `credit_balance_pence` at the agent tier price.
   - Refunds go back to whichever ledger was debited.
   - Design consequence: the OAuth branch must NOT reuse `provider="credit"` blindly. It needs a payment provider that tries `enforce_usage_limit` and then `debit_credits`, recording which ledger it used on the transaction (refunds and the stranded sweep read it).
   - *Assumption, confirm at build: trial checks count as allowance. This is the plain reading of "existing allowance".*
2. Create a Clerk DEV instance for P0 (free, founder's Clerk account).
3. Countries.
4. Starter credit.
5. Individual vs business verification.
