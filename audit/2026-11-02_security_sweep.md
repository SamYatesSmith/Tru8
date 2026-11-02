# Security sweep 2026-11-02

Independent read-only review of auth, payment, fetch and output surfaces (agent), triggered by the ChatGPT-plugin P0 finding. No production calls.
✔ = the author confirmed the finding against the code before recording it.

## Already in hand
- **H1 (HIGH, latent):** `_verify_jwt_token` accepted Clerk OAuth access tokens and ID tokens as sessions (shown in practice on the dev instance). **P1 fix built**: `_require_session_shape`, 22 tests, independently verified safe. Deploy pending a founder check of the production "Customize session token" claims.

## New findings, most severe first
1. **MEDIUM ✔: a chargeback does not stop a subscriber.**
   - `payments.py:521-561 _revoke_credits_for_charge` zeroes the legacy counters only.
   - The gate (`usage_ledger._active_subscription`) reads `Subscription.status in (active, trialing)` plus `usage_events`.
   - Buy Console, dispute the charge, keep 200 checks/month until Stripe deletes the subscription.
   - Fix: on a dispute or full refund, set a status the gate refuses, or write a negative ledger adjustment. **Founder: the behaviour on dispute.**
2. **MEDIUM ✔: readable SSRF through redirects.**
   - `services/evidence.py:483-488` (the stored snippet appears publicly on `/r/`), `services/article_reader.py:70-75` (Compare), `title_recovery.py:210` and `government_api_client.py:192` fetch search-result URLs with `follow_redirects=True` and no `url_safety` check.
   - Only ingest (`safe_get`) and webhooks are guarded.
   - Also: `safe_get` and the webhook POST resolve DNS twice, so DNS rebinding can slip in.
   - Fix: an async `safe_async_get` that checks every hop and pins the checked IP, used for every outbound GET.
3. **MEDIUM ✔: HTML injection in the waitlist/feedback emails, with no login needed.**
   - `feedback.py:139` and around it interpolate `pageUrl`/`message`/`claimText`/`userEmail`/`checkId` unescaped into the founder's email HTML. `reply_to` is attacker-set. Phishing arrives from Tru8's own domain.
   - Fix: `html.escape` every field, allowlist `source`, no `reply_to` on the unauthenticated route.
4. **MEDIUM (conditional) ✔: the hosted `/mcp` can fall back to a server key.**
   - `tools.py:132`: `api_key or os.environ["TRU8_API_KEY"]`, and the hosted route runs in the API process.
   - If `TRU8_API_KEY` is set on Railway, anonymous `/mcp` callers spend that account's money.
   - Fix (code, regardless of env): the HTTP transport never falls back to the environment. Also check Railway variables.
5. **LOW: image `file_path` is not validated** (`checks.py:298`, `ingest.py:394-399`). Any local image can be OCR'd, existence leaks, and other users' S3 keys are readable if guessed. Fix: accept only keys issued by `/upload`, bound to the owner.
6. **LOW ✔: `/mcp?apiKey=` reaches Sentry.** The scrubber (`main.py:424`) only matches `token=`. Fix: also match `apikey`/`api_key`/`tru8_api_key`.
7. **LOW: unauthenticated `/metrics`;** public PDF export is a cheap CPU drain. Fix: restrict `/metrics`; tighter limit or caching on the PDF route.
8. **LOW: internal errors echoed to clients:** `payments.py:89,141`, `auth.py:71`.

## Checked and found sound (per the sweep)
- Ownership on every route that takes an id.
- Admin gating.
- Stripe/svix signatures.
- Atomic credit debit and refund locking.
- Payer-scoped idempotency.
- No stored XSS.
- CORS.
- Models have no tools.

Noted, not exploitable: Stripe event dedupe is written before the handler, so a failed handler's retry is skipped (an integrity issue, not a security one).

## Plan
- **Batch A (small, no behaviour change for honest users):** #4, #3, #6, #8, plus #2's DNS pinning, alongside P1.
- **Batch B:** #2 safe fetch for all outbound GETs. This touches retrieval, so it gets its own commit, tests and a bench control arm.
- **Batch C:** #1, after the founder decides the dispute behaviour. Then #5, #7.

## Progress
- **P1 (H1) + Batch A, built 2026-11-02, with all verifier follow-ups:**
  - **Session-token shape check:** 22 tests. Verifier nits applied: `application/at+jwt`, list `azp`, and `PyJWTError` so an unknown kid gives 401 not 500.
  - **#4 hosted `/mcp`:** never uses the server environment key. Fail-closed `HOSTED_TRANSPORT` flag set at the mount, plus a request check.
  - **#3 emails:** every field escaped, `fullmatch` on the email, links to trueight.com, waitlist 5/min, field length caps, log values as repr.
  - **#6 Sentry:** credential redaction across the query string, breadcrumbs (httpx `http.query`, log messages), exception values, `logentry` and `message`. Covers `key=`, `apikey=`, `api_key=`, `token=`, `tru8_sk_…` and Google `AIza…` keys.
  - **#8 error text:** 13 response sites no longer echo exception text (payments ×6, users ×3, checks ×2, agent ×2 + webhook payload, x402 ×2). Pipeline failures use `get_user_friendly_error`.
  - **Each fix has tests that fail on the old code.**
- **Production pre-check (founder screenshot):** the Production "Customize session token" claims are `{}`, so there is no lockout risk from the shape check.
- **Open:** Batch B (#2 safe fetch + DNS pinning), Batch C (#1 dispute behaviour — founder; #5 upload keys; #7 `/metrics` + PDF limit). `ENABLE_CLERK_AZP_ENFORCEMENT` stays off until production logs show the real `azp` values ("Clerk session azp not allowlisted").
