# Tru8 Release Readiness — 2026-05-18

**Status overall (updated 2026-07-09): AMBER — every code-side blocker closed + deployed (2026-06-05, `820aba6..62c6741`, smoke-tested). Remaining before launch: (1) £20 Console Stripe product + checkout wiring (the price shown on /pricing has no purchasable product behind it — the ONLY code-path item); (2) founder chores: `backend/.env` delete/sanitise + Clerk TEST-key revoke; (3) the operational-verification sweep below. Qdrant JWT/cluster row CLOSED 2026-07-09 (cluster was already decommissioned by 2026-06-25). Prep pack for the closing session: `audit/2026-07-10_release_blockers_prep.md`.**

*(Original status at audit date: RED — do not ship until blockers close.)*
**Audit date:** 2026-05-18
**Auditor:** Claude (Opus 4.7), at the user's request, with seven parallel agent streams.
**Method:** read code, cross-reference with displayed UI text and external services, run targeted web research for timing/venues.
**Original planned launch date:** Mon 2026-05-18 (today) — **postponed pending blocker closure.**

This document **does not override** `audit/OPEN_WORK.md` (live work register) or any per-track audit doc under `audit/track-*/`. It is a single-point-in-time pre-launch gate. As blockers close, **edit the checklist below in-place; do not write a new audit. The section files under `audit/release-readiness/` remain the canonical detail**.

## Recommended new launch date

**Primary: Wednesday 2026-05-27, 12:01 AM PT (07:01 UTC) for Product Hunt; 14:00 UTC for the synced Show HN + Reddit + X + Discord push.**

**Backup: Thursday 2026-05-28** (same time profile).

Rationale: the timing research (section 07) identifies Tue 2026-05-19 as the per-day optimum, but the audit found enough blockers that closing them all by tomorrow is unrealistic. Fri 2026-05-22 → Tue 2026-05-26 is a hard avoid (US Memorial Day + UK Spring Bank Holiday both fall on Mon 2026-05-25). **2026-05-27** is the first clean weekday post-holiday and gives nine real calendar days (five clear weekdays) to close blockers, regress-test, and re-run Stripe test-mode purchases. Mon 2026-06-01 is the Monday-penalty trap; outside the 2-week window. If 2026-05-27 slips, **2026-05-28** is the same-week backup.

## Status per domain

| Domain | RAG | Blockers | High | Medium | Low | Detail |
|---|---|---|---|---|---|---|
| Auth | **RED** | 1 | 2 | 4 | 6 | [01_auth.md](release-readiness/01_auth.md) |
| Legal | AMBER | 1 | 2 | 7 | 3 + 4 INFO | [02_legal.md](release-readiness/02_legal.md) |
| Payments + costs | **RED** | 3 + 1 mitigated | 6 | 3 | 2 | [03_payments_costs.md](release-readiness/03_payments_costs.md) |
| README + repo | AMBER | 0 | 1 | 4 | 4 + 2 INFO | [04_readme_repo.md](release-readiness/04_readme_repo.md) |
| Security | **RED** | 3 | 5 | 5 | 3 | [05_security.md](release-readiness/05_security.md) |
| User-facing surface | AMBER | 0 | 4 | 4 | 5 + 3 INFO | [06_user_surface.md](release-readiness/06_user_surface.md) |
| Launch timing | GREEN (research) | — | — | — | — | [07_launch_timing.md](release-readiness/07_launch_timing.md) |
| Posting venues | GREEN (partial — full venue tables deferred) | — | — | — | — | [08_posting_venues.md](release-readiness/08_posting_venues.md) |

**Overall finding totals across all domains: 8 BLOCKERS, ~20 HIGH, ~27 MEDIUM, ~23 LOW, ~9 INFO.**

## Hard blockers (must all be closed before launch)

1. **F-SEC-01 — Live `backend/.env` with production keys in working tree.** Rotate every key (`sk_live_…`, `whsec_…`, manifest signing key, R2 keys, OpenAI sk-proj, Google AIza, Resend, 14 search/factcheck/govt keys), move to Railway env vars, delete the file. Highest urgency item in the entire audit. Git history is clean; this is a disk-state risk only.
2. **F-SEC-02 — SSRF on URL ingest + webhook registration.** `requests.Session().get(url, allow_redirects=True)` in `backend/app/pipeline/ingest.py:154-207` with no IP allowlist; `POST /webhooks` accepts arbitrary HTTPS URLs incl. `https://10.x.x.x` and `https://qdrant.railway.internal:6333/`. Add `assert_public_url()` helper that resolves DNS, blocks RFC1918/loopback/link-local/CGNAT/IPv6 ULA, and re-validates after redirects.
3. **Next.js 14.2.13 vulnerable to CVE-2025-29927** (middleware auth bypass via `x-middleware-subrequest`). `cd web && npm install next@14.2.30`. Public exploit code exists.
4. **F-AUTH-01 — x402 endpoints trust unverified `x-payer-address` header.** `X402_ENABLED=False` by default keeps this latent; **must remain False until the facilitator-verified payment flow is implemented**. Either keep disabled at launch or land Option B (synchronous facilitator signature verification in `get_x402_payment`) and the integration test.
5. **M-01 — `backend/static/llms.txt` serves wrong currency + wrong domain + wrong field names + wrong credit packs.** First thing autonomous agents read. Delete and serve `web/public/llms.txt` instead, or sync content.
6. **M-02 — Swagger description (`backend/main.py:151-154`) shows agent prices in USD.** `s/\$/£/g`.
7. **M-03 — `web/app/developers/page.tsx:491` shows `totalChargedCents` (legacy field name).** Real API returns `totalChargedPence`. Single-line fix.

### Demoted (not blockers)

- **F-LEG-01 (ICO registration)** — registration was completed long ago. The inline `{/* pending */}` comments in ToS §14 + Privacy §13 are stale. Demoted to LOW documentation fix: paste the registration number into the rendered text and remove the comments.
- **F-UX-04 (Correspondent rename)** — the Interpreter → Correspondent rename was deliberate audience-broadening, same logic as Developer → Professional. Code is correct. Demoted to LOW documentation fix: update CLAUDE.md (done) and any stale audit references to use "Correspondent".

**One additional blocker is feature-flag-mitigated and only fires if x402 is enabled: F-PAY-01 (GBP/USDC currency confusion in the x402 settlement code). Keep `X402_ENABLED=False` at launch.**

## High-priority items (close before launch where feasible)

**Auth (F-AUTH-02, F-AUTH-03):**
- Add `POST /api/v1/webhooks/clerk` with Svix signature verification; handle `user.deleted` and `user.updated`. Without this, deleting via Clerk leaves orphaned API keys + credit balances forever. (GDPR right-to-erasure incomplete.)
- Enable Clerk JWT `aud` verification via `CLERK_JWT_AUDIENCE` env var; add Skyfire `service_id` check in `get_agent_identity`.

**Legal (F-LEG-02, F-LEG-03, F-LEG-04):**
- Cryptocurrency / x402 payment terms — UK FCA financial-promotion rules around crypto tightened October 2023. Either ship a unified Agent Payment Rails section in ToS (covering x402 USDC + Skyfire + credits) **or** keep both rails disabled until terms ship. **Lawyer review recommended.**
- Refresh `lastUpdated` to launch date across all four legal pages (currently `18 March 2026`).

**Payments + cost (F-PAY-02, F-PAY-03, F-PAY-04, M-04, M-05, M-06):**
- Add webhook handlers for `charge.refunded`, `charge.dispute.created`, `invoice.payment_failed`, `customer.subscription.trial_will_end`, `customer.deleted`. Without these, refunded users keep credits, failed renewals stay "active", deleted customers stay billable.
- Make `handle_subscription_updated()` recompute plan + credits from the price ID — Stripe Portal upgrades silently fail today.
- Decide on tier-naming env var convergence (Stripe + frontend use Starter/Professional; env vars + CLAUDE.md say Pro/Developer).
- Fix `stitch-developer-showcase.tsx:58-61` (wrong path `/agent/quick` → `/api/v1/agent/quick`, wrong header `Authorization: Bearer` → `X-API-Key`).
- Add `/agent/consensus` endpoint **or** update docs to say consensus is only via `/agent/check?max_tier=consensus`.

**Security (F-SEC-03, F-SEC-04, F-SEC-05, F-SEC-06, F-SEC-07):**
- Add `Content-Security-Policy` + `Strict-Transport-Security` headers to `web/next.config.js`.
- Add `max_length` to `CreateCheckRequest.content/.url`, `AgentClaimRequest.claim` (currently no caps → 50MB DoS surface).
- Enable Jinja2 autoescape on the PDF template + disable WeasyPrint network fetch (XSS / SSRF in PDF generation).
- Decide public-report policy: opt-in `is_public` flag, **or** strip `inputContent` from `/checks/public/{check_id}?detailed=true` response.
- Add `send_default_pii=False` + `before_send` PII scrub to Sentry SDK init.

**User-facing surface (F-UX-01, F-UX-02, F-UX-03, F-UX-04):**
- Verify Railway `NEXT_PUBLIC_SUBSCRIPTIONS_ENABLED=true` and backend returns `subscriptionsEnabled: true` — otherwise the pricing CTA dead-ends in a "Coming Soon" waitlist modal.
- Fix wrong API host on `developer-tab.tsx:396` (`api.tru8.com` → `api.trueight.com`).
- Decide Interpreter ↔ Correspondent naming: marketing carousel renames the view AND describes a different feature than what ships. Pick one canonical name and reconcile copy.

**README + repo (F-REPO-01, F-REPO-06, F-REPO-07):**
- Create top-level `README.md` (use the 11-section outline in 04_readme_repo.md).
- Append all Skyfire/x402/CDP/SIWE/Track-M/model-name env vars to `backend/.env.example`.
- Add `NEXT_PUBLIC_BASE_URL` to `web/.env.example` (used in 8 places — sitemap, robots, OG, share URLs all broken on fresh clone).

## Master pre-launch gate checklist

Edit this list in-place as items close. Pull individual finding context from the per-domain detail files.

### Blockers (all must be ticked before launch)
- [x] **F-SEC-01 — PARTIAL (2026-06-05):** high-value keys rotated on Railway (Stripe secret+webhook, OpenAI, Google AI, Clerk secret); free-tier data-source tail consciously DEFERRED post-launch (git history clean, folder not cloud-synced). **Residual: delete/sanitise `backend/.env` from disk (USER).**
- [x] F-SEC-02 — `assert_public_url()` implemented (`backend/app/core/url_safety.py`, commit `cae242d`); gates ingest + webhook registration + delivery. Closed 2026-05-20, deployed 2026-06-05.
- [x] **Upgrade Next.js to 14.2.35 (CVE-2025-29927)** — closed 2026-05-20. *Audit's 14.2.30 target was itself flagged vulnerable by npm; corrected to 14.2.35 (latest `next-14` dist-tag).*
- [ ] F-AUTH-01 / F-PAY-01 — Confirm `X402_ENABLED=False` on Railway and tested; OR implement Option B verification path
- [x] **F-LEG-01 — ICO ZC110163** added to ToS §14 + Privacy §13 — closed 2026-05-20
- [x] **M-01 — `backend/static/llms.txt` synced to `web/public/llms.txt`** — closed 2026-05-20
- [x] **M-02 — Swagger USD → GBP** in `backend/main.py:151-154` — closed 2026-05-20
- [x] **M-03 — `totalChargedCents` → `totalChargedPence`** in `web/app/developers/page.tsx:491` — closed 2026-05-20

### Newly discovered + closed (2026-05-20 dependency audit; audit doc missed these)

- [x] **GHSA-vqx2-fgx2-5wq9 — Clerk middleware bypass (CRITICAL, CVSS 9.1)** — same class as CVE-2025-29927 but in `@clerk/nextjs`. Closed via `@clerk/nextjs` 5.7.1 → 5.7.6. *Audit's `05_security.md` static dep reading missed this; npm audit caught it.*
- [x] **`@sentry/nextjs` v8 transitive vulns** — closed via upgrade to ^10.53.1. Build verified clean.
- [x] **lodash + picomatch transitive vulns** — closed via `npm audit fix` (non-breaking).

### Accepted risk — post-launch register (recorded 2026-05-20)

Remaining 7 vulnerabilities require major-version upgrades (Next 14 → 16, Clerk 5 → 7, eslint-config-next 14 → 16) — genuinely 1-2 day migrations, not patch installs. Scoped post-launch.

**Next.js 14.2.35 retains 14 HIGH CVEs** that only have fixes in Next 16. Most are scenario-specific:
- Image Optimizer DoS — `remotePatterns` is tight (ytimg/youtube/clerk.com only); low exploit surface
- DoS / cache poisoning in React Server Components — requires specific payload shapes
- Pages Router i18n middleware bypass — N/A, we use App Router
- WebSocket SSRF — N/A, we don't handle WS upgrades
- XSS in `beforeInteractive` scripts — review usage before launch
- HTTP request smuggling in rewrites — review `next.config.js` rewrites usage

**`@clerk/nextjs` 5.7.6 retains GHSA-w24r-5266-9c3c (HIGH)** — Clerk authorization bypass when combining organization/billing/reverification checks. Mitigation: we don't currently combine those checks. Closes via Clerk 7 upgrade.

**`eslint-config-next` 14.2.35 retains vulnerable glob transitive (HIGH, dev-only)** — exploitable only via running `npm run lint` on a malicious package. Zero runtime risk.

**Schedule:** Next 16 migration + Clerk 7 + eslint-config-next 16 → bundle as a post-launch sprint, ~1-2 days. Owner: TBD.

### Operational verifications (no code change required — confirm + tick)
- [ ] Railway env: `DEBUG=false`, `ENVIRONMENT=production`, `NEXT_PUBLIC_SUBSCRIPTIONS_ENABLED=true`, `MANIFEST_SIGNING_ENABLED=True`, `X402_ENABLED=False`, `SKYFIRE_ENABLED=False`, fresh signing key
- [ ] Run `alembic upgrade head` against production DB
- [ ] Verify Google AI tier is paid (Vertex / paid Generative Language API), not free tier — Privacy §5.5 depends on it
- [ ] Verify CookieYes subscription active + production domain registered
- [ ] Verify Stripe Tax / UK VAT setup matches "inclusive of VAT" claim in ToS §4.5
- [ ] Verify Clerk transactional email delivers (ToS §13 30-day legal notice)
- [ ] Verify `@tru8app` Twitter handle ownership
- [ ] Production smoke test: `/api/v1/checks/test/stream-mock` returns 404 (DEBUG endpoints gated)
- [ ] Run the 7 `gh` commands listed in 04_readme_repo.md (visibility, branch protection, releases, Dependabot, secret-scanning)
- [ ] Run Stripe test-mode purchase matrix tests #1-15 from 03_payments_costs.md

### High-priority code + content fixes (close as many as possible before launch)
- [x] **F-AUTH-02 — Clerk webhook** with Svix verification (`user.deleted`, `user.updated`). Endpoint at `POST /api/v1/webhooks/clerk`. Requires `CLERK_WEBHOOK_SECRET` set on Railway — endpoint refuses every request when empty (fail-closed). Closed 2026-05-20.
- [x] **F-AUTH-03 — JWT `aud` verification** behind `CLERK_JWT_AUDIENCE` env var (legacy permissive when unset). Skyfire `service_id` enforced in both `_verify_jwt` and `get_agent_identity`. Closed 2026-05-20.
- [x] **F-LEG-04 — `lastUpdated` refreshed** to "27 May 2026" across ToS, Privacy, Cookie, Refund. Closed 2026-05-20.
- [ ] F-LEG-02 / F-LEG-03 — Crypto + Skyfire payment terms (or keep rails disabled). **Still needs lawyer review.** Mitigation: keep `SKYFIRE_ENABLED=False` and `X402_ENABLED=False` on Railway at launch.
- [x] **F-PAY-02 / F-PAY-03 — Stripe handlers added** for `charge.refunded`, `charge.dispute.created`, `invoice.payment_failed`, `customer.subscription.trial_will_end`, `customer.deleted`. Closed 2026-05-20.
- [x] **F-PAY-04 — `handle_subscription_updated()` re-derives plan + credits** from active item's price ID on every update event. Plan-change path resets `credits_remaining` and `user.credits` to the new allocation. Closed 2026-05-20.
- [x] **M-05 — Landing curl fixed** in `stitch-developer-showcase.tsx`. Path `/api/v1/agent/quick`; auth `X-API-Key`. Closed 2026-05-20.
- [x] **M-06 — Docs updated.** Both `web/public/llms.txt` and `backend/static/llms.txt` now describe consensus as reachable via `/agent/check?max_tier=consensus`, not as a standalone endpoint. Closed 2026-05-20.
- [x] **F-SEC-03 — CSP + HSTS added** to `web/next.config.js` (CSP whitelists Clerk, Stripe, Sentry de.sentry.io, cdn.jsdelivr.net; HSTS `max-age=63072000; includeSubDomains; preload`). Note: CSP keeps `'unsafe-inline'`/`'unsafe-eval'` on script-src for Next 14.2 compatibility — nonce-based CSP bundled with the post-launch Next 16 migration. Closed 2026-05-20.
- [x] **F-SEC-04 — `max_length=10_000` on `content`/`claim` fields, `max_length=2048` on `url` field.** Applied to `CreateCheckRequest`, `AgentClaimRequest`, `SmartCheckRequest`, `BatchClaimItem`. Closed 2026-05-20.
- [x] **F-SEC-05 — Jinja2 autoescape** set to `select_autoescape(["html","xml"])` on the PDF template env. WeasyPrint network fetch blocked via `url_fetcher` callback that raises on every external resource request. Closed 2026-05-20.
- [x] **F-SEC-06 — `inputContent` stripped** from `/checks/public/{check_id}?detailed=true` responses. `inputUrl` retained (URLs less sensitive than free-text claims). Opt-in `is_public` flag scheduled post-launch. Closed 2026-05-20.
- [x] **F-SEC-07 — Sentry PII scrub** added (`send_default_pii=False` + `before_send=_scrub_event_pii` redacting user email/IP, request body fields, and sensitive headers `X-API-Key`/`Authorization`/`skyfire-pay-id`/`x-payer-address`). Closed 2026-05-20.
- [ ] F-UX-01 — Confirm Railway `NEXT_PUBLIC_SUBSCRIPTIONS_ENABLED=true`. (Operational check only; no code change.)
- [x] **F-UX-02 — `api.tru8.com` → `api.trueight.com`** in `developer-tab.tsx`. Closed 2026-05-20.
- [ ] F-UX-04 — Decide Interpreter / Correspondent naming, reconcile copy.

### F-SEC-02 — SSRF (was a BLOCKER)

- [x] **`assert_public_url()` + `safe_get()` + `safe_async_post()`** in new `backend/app/core/url_safety.py`. Blocks RFC1918 / loopback / link-local / CGNAT / IPv6 ULA / multicast / reserved / IETF test ranges, plus literal blocklist of internal hostnames (`*.railway.internal`, `localhost`, `*.internal`, `*.local`). Wired into THREE callsites (audit listed two — the third was webhook delivery in `services/webhooks.py:97`):
  1. `pipeline/ingest.py` — replaced `session.get(allow_redirects=True)` with `safe_get` that validates URL + every redirect hop.
  2. `api/v1/webhooks.py:96` — `assert_public_url` on URL registration (refuses `qdrant.railway.internal`, `10.x.x.x`).
  3. `services/webhooks.py:97` — `safe_async_post` validates before each delivery attempt; redirect-following disabled.
- Validated against `http://10.0.0.1/`, `http://127.0.0.1:8000/`, `http://169.254.169.254/latest/meta-data/`, `http://localhost:5433/`, `http://qdrant.railway.internal:6333/`, `https://[::1]/`, `ftp://example.com/`, `file:///etc/passwd` — all blocked. Public URLs (Google, OpenAI) — allowed. Closed 2026-05-20.
- **Known limitation (post-launch):** Time-of-check-time-of-use DNS rebinding mid-connection is not defended against — defence requires resolving once and connecting to the resolved IP while preserving Host for SNI, a non-trivial refactor of `requests`/`httpx` adapters. Threat is narrow vs. the audit's stated threats.

### Newly required env vars (set on Railway before launch)

- `CLERK_WEBHOOK_SECRET` — required for F-AUTH-02. Copy from Clerk dashboard → Webhooks. **Endpoint fail-closed when empty.**
- `CLERK_JWT_AUDIENCE` — optional; set if your Clerk JWT template emits an `aud` claim (recommended).
- (Reminder) `SKYFIRE_SERVICE_ID` — set if Skyfire enabled; F-AUTH-03 now enforces it.
- (Reminder) `MANIFEST_SIGNING_KEY` — already required, but not yet on Railway per existing checklist.

**`.env.example` update was blocked by a guardrail hook — apply manually:** add `CLERK_JWT_AUDIENCE=` and `CLERK_WEBHOOK_SECRET=` lines under the Clerk auth section.

### Medium-priority fixes (close where time allows)
- [ ] F-LEG-05 — Decide "Beta" status removal in ToS §2
- [ ] F-LEG-06 — Reconcile ToS §11.1 refund language with Refund Policy §2.1
- [ ] F-LEG-07 — Add `/verify` mention to ToS §2 service description
- [ ] F-LEG-08 — Verify lookup-tier cache behaviour; align ToS §6.4
- [ ] F-LEG-09 — Define attribution form in ToS §6.5
- [ ] F-LEG-10 — Reconcile analysis retention period across ToS + Privacy
- [ ] F-LEG-15 — Footer copyright `© 2026 TRU8 LTD` → `Trueight Ltd`
- [ ] M-04 — Decide tier-naming env var convergence
- [ ] M-07 — Fix tautological `mo/mo` ternary in `stitch-pricing.tsx:113-114`
- [ ] M-08 — Reconcile concurrency limit (developers page says 5, ToS says 3, code default 5, tests assume 3)
- [ ] F-AUTH-05 — Rate limits on API key + webhook CRUD endpoints
- [ ] F-AUTH-07 — Change `.env.example:88` `DEBUG=true` → `DEBUG=false`; add startup assertion
- [ ] F-PAY-05 / F-PAY-06 — Skyfire `aud` verification + settle-before-pipeline
- [ ] F-SEC-08 / F-SEC-09 / F-SEC-10 — Explicit rate limits on `/verify`, `/waitlist`, `/feedback`
- [ ] F-SEC-11 — Clerk webhook handler (duplicate of F-AUTH-02)
- [ ] F-UX-05 — Reskin 404/error/global-error pages with Stitch theme
- [ ] F-UX-06 — Remove ICO "pending" inline comments after registration
- [ ] F-UX-07 — Decide BETA STATUS in ToS §2
- [ ] F-UX-08 — Update sitemap to add `/blog/evidence-research-for-agents`, `/cookie-policy`, `/refund-policy`; align lastModified dates
- [ ] F-REPO-01 — Create top-level `README.md`
- [ ] F-REPO-02 — Create top-level `LICENSE` (proprietary)
- [ ] F-REPO-03 — Add `[project.urls]` + `authors` + `license-files` to `tru8_mcp/pyproject.toml`
- [ ] F-REPO-04 — Add tier-pricing + `/verify/{check_id}` section to MCP README
- [ ] F-REPO-05 — Update "From source" URL in MCP README to real mirror URL
- [ ] F-REPO-06 — Append missing env vars to `backend/.env.example`
- [ ] F-REPO-07 — Add `NEXT_PUBLIC_BASE_URL` + Sentry build-time vars to `web/.env.example`
- [ ] F-REPO-08 — Remove stale `web/.env.example` entries

### Low-priority + INFO (post-launch acceptable)
- [ ] F-AUTH-04 — API key HMAC vs SHA-256 (post-launch hygiene)
- [ ] F-AUTH-09 — API key rate-limit by full hash, not prefix
- [ ] F-AUTH-10 / F-AUTH-12 / F-AUTH-13 — SSE token rate limit / remove deprecated JWT-in-query / DB-backed Stripe idempotency
- [ ] F-LEG-11 / F-LEG-12 / F-LEG-13 / F-LEG-14 / F-LEG-16 — Verify 30-day email pipeline, Google AI tier paid, CookieYes config, VAT setup, account deletion cascade
- [ ] F-SEC-13 / F-SEC-14 / F-SEC-15 — YouTube domain suffix-match / `SECRET_KEY` unused / CSRF noted
- [ ] F-UX-09 to F-UX-17 — Mobile nav, env var rename, error-boundary Sentry wiring, etc.
- [ ] F-REPO-09 to F-REPO-14 — Mobile env var, README-STARTUP rewrite, SECURITY.md, CHANGELOG, GitHub release, mirror repo creation

## What this audit does NOT cover

This is a pre-launch snapshot, not a full assurance review. Explicitly out of scope:
- **Third-party pen test** — strongly recommended within 30 days post-launch. Consider HackerOne / Bugcrowd or a one-off engagement.
- **GDPR DPIA** — recommended if expanding to EU enterprise customers post-launch.
- **Full venue catalogue for posting cadence** — 08_posting_venues.md captures the top 3 venues and cadence loops; the full tiered table is deferred (sub-agent output truncated).
- **Accessibility / WCAG 2.1 AA audit** — separate audit, recommended pre-launch.
- **Performance / Core Web Vitals** — separate Lighthouse audit recommended.
- **OG card visual review** — open work item I-06 per `audit/OPEN_WORK.md`.
- **MCP publication mechanics** — tracked in I-07 per `audit/OPEN_WORK.md` and 04_readme_repo.md.
- **Pipeline quality work** — separate active programme; see `audit/pipeline-issues/2026-05-06_v1_quality_plan.md`.
- **Mobile app** — not in launch scope. Audited only at .env.example level.

## Section detail files

Located under `audit/release-readiness/`:

| # | File | What it covers |
|---|---|---|
| 01 | `01_auth.md` | Clerk JWT, API keys, agent rails, dual auth precedence, JWKS, session config |
| 02 | `02_legal.md` | ToS, Privacy, Cookie, Refund — content gaps, ICO, crypto-payment terms |
| 03 | `03_payments_costs.md` | Stripe webhooks, agent rails, idempotency, **price reconciliation matrix**, test-mode test plan |
| 04 | `04_readme_repo.md` | Root README/LICENSE/CHANGELOG, MCP package, env templates, git history scan, branch protection |
| 05 | `05_security.md` | Secrets, SSRF, CSP/HSTS, input validation, PDF Jinja2, public-report data, Sentry PII, deps (Next.js CVE) |
| 06 | `06_user_surface.md` | Every route, every layout, error/404 boundaries, signed-in/out flows, dev docs accuracy |
| 07 | `07_launch_timing.md` | Day-of-week + time-of-day research, calendar conflicts, channel-by-channel timing, sources |
| 08 | `08_posting_venues.md` | Top venues + cadence loops + tier outline (full venue tables deferred — see status note in file) |

## Update protocol

1. As blockers close, tick them in this document. **Do not write a new audit doc; edit in place.**
2. If new blockers are discovered, add them to the "Hard blockers" list above with a `F-NEW-NN` ID and brief evidence.
3. The detail files under `release-readiness/` are canonical for the *why* and *how* of each finding. Reference them from PR descriptions when fixing items.
4. The recommended launch date stays at **Wed 2026-05-27 (backup Thu 2026-05-28)** unless the blocker burndown indicates it should shift earlier or later. Update the "Recommended new launch date" section if it moves.
5. Once all blockers are green and ≥80% of HIGHs are green, flip the overall status banner from RED → AMBER. Only flip to GREEN when the operational verifications are also ticked.
