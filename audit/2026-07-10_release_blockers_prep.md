# Release-blocker closing session — prep pack (written 2026-07-09 evening, for the morning of 2026-07-10)

**Context:** code-side release readiness is CLEAR (all 2026-05-18 audit blockers closed + deployed 2026-06-05; F8 clarity pass C1–C4 complete 2026-07-09; retrieval quality fixed + verified `c61d9a5`). This pack preps the final three buckets so the morning session executes rather than investigates. Gate doc: `audit/2026-05-18_release_readiness.md` (header updated to AMBER, 2026-07-09).

---

## Blocker 1 — £20/£200 Console Stripe checkout (the only code-path item)

**Problem:** `/pricing` advertises Console £20/mo (£200/yr) and Teams from £75/mo, but Stripe only has the legacy £7 (`STRIPE_PRICE_ID_PRO`) and £29 (`STRIPE_PRICE_ID_DEVELOPER`) products. The pricing card CTAs route to the app/contact, not a checkout (`stitch-pricing.tsx` header comment: "a real £20 Stripe checkout needs a new Stripe product + price-id env — deferred to P4/deploy"). A visitor who decides to pay the advertised price cannot.

**Founder actions (Stripe dashboard, ~10 min, FIRST thing — code work is blocked on the IDs):**
1. Create product **"Tru8 Console"** with two prices: **£20/month** and **£200/year** (recurring, GBP, tax behaviour per the Stripe Tax decision in the ops sweep below).
2. Copy both price IDs (`price_…`).
3. Decide the legacy question (see Decisions below) — takes 1 minute, shapes the wiring.

**Code inventory (wiring plan):** see the "Stripe plumbing map" section below — env vars to add, endpoint changes, tiers.ts, CTA wiring, webhook mapping, and the test plan.

**Decisions to make before wiring:**
- **D1 — Legacy tiers:** what happens to £7 Starter / £29 Professional? Options: (a) keep both purchasable in the dashboard for existing users, Console becomes the only marketed tier; (b) retire from sale, grandfather existing subscribers. Recommendation: (b) — the site no longer displays them anywhere.
- **D2 — Console entitlements:** the card says "fair-use unlimited evidence research in the browser". The plan-derivation code assigns credits/limits per tier — Console needs an explicit expression of "fair-use unlimited" (a high ceiling + monitoring beats literal unlimited).
- **D3 — Annual toggle:** one CTA with a monthly/annual switch, or monthly-only checkout with annual via contact? Recommendation: both price IDs wired from day one; the card already names both figures.

---

## Blocker 2 — founder security chores (~15 min, no code)

**2a. `backend/.env` on disk.** High-value keys were rotated onto Railway on 2026-06-05; the file itself was left pending a decision. Options:
- **Sanitise (recommended):** replace every live value with a placeholder / `sk_test_…` dev key so local dev still boots. Note the local OpenAI key is already dead (401) and the local stack mostly runs against dev services.
- **Delete:** cleanest, but local backend runs will need a fresh `.env` built from `.env.example` when next needed.
Either way: confirm afterwards that no other live secrets sit in the working tree (`rg "sk_live|whsec_" --no-ignore` over the repo, excluding node_modules).

**2b. Revoke the leaked Clerk TEST key.** `sk_test_7jxii…` was committed historically in `docs/integration/frontend-backend-integration.md` (scrubbed from the doc in `6d394ba`, but the git history copy survives). Clerk dashboard → **Development instance** → API keys → revoke/rotate that secret key. Low severity (test instance), one minute.

**2c. ~~Qdrant JWT + cluster~~ — CLOSED 2026-07-09.** Already decommissioned (corroborated by the 2026-06-25 Sentry session); register row updated.

---

## Bucket 3 — operational verification sweep (founder, ~1 hr, can interleave with code work)

From the 2026-05-18 gate (§ operational verifications), current state annotated:

| # | Check | How to verify | Notes |
|---|-------|---------------|-------|
| 1 | Stripe Tax / UK VAT configured | Stripe dashboard → Tax settings | Decide tax-inclusive vs -exclusive BEFORE creating the Console prices (Blocker 1) |
| 2 | Stripe test-mode purchase matrix | Test-mode checkout for each purchasable tier after Blocker 1 wiring | Was blocked on the Console product existing |
| 3 | Clerk transactional email sending | Trigger a real password-reset/magic-link on prod | |
| 4 | Google AI on paid tier | Google AI Studio billing page | Pipeline runs on Gemini — quota exhaustion mid-launch would be public-facing |
| 5 | Cookie-consent position | Confirm intended: CookieYes was REMOVED (`c947eff`, hydration crash) — verify the current no-banner state matches the privacy policy's cookie claims | If analytics are cookieless (PostHog EU cookieless mode) a banner may genuinely be unnecessary — confirm and note in the legal file |
| 6 | `NEXT_PUBLIC_SUBSCRIPTIONS_ENABLED=true` on Railway | Confirmed live long ago (2026-05-01) | ✓ done |
| 7 | `alembic upgrade head` on prod | Verified via `client_origin` head 2026-06-11 | ✓ done — re-confirm only if new migrations land |
| 8 | DEBUG endpoint gating | `/checks/test/stream-mock` → 404 verified 2026-06-05 | ✓ done |
| 9 | GitHub repo settings (visibility, secrets scanning) | gh repo settings page | |
| 10 | @tru8app handle | Check availability/ownership | Marketing, not launch-gating |

---

## Not blocking (parked, for completeness)
- F-LEG-02/03 crypto + Skyfire terms — only before enabling those rails (both OFF in prod).
- OG-card visual review (I-06), MCP directory submissions (I-07), M1 worktree eyeball, logo polish.
- Agent credit-pack env vars (`STRIPE_PRICE_ID_CREDIT_PACK_*` empty → purchase path 500s) — matters only for the agent-credits rail, not human launch. Could be created in the same Stripe session as Blocker 1 if convenient.
- WHO cache expiry re-check (2026-07-16); F7 replay-bench re-gold (networked env).

---

## Stripe plumbing map (code inventory for Blocker 1 — surveyed 2026-07-09 evening)

**⚠ Load-bearing warning first:** both webhook price→plan maps **fail closed on unknown price IDs**. `handle_successful_payment` (`payments.py:320-328`) logs "Unknown Stripe price ID" and returns **without creating the subscription** — i.e. a Console purchase made before the mapping update would take the customer's money and grant no plan. The mapping edits are mandatory BEFORE any Console checkout link goes live.

### How checkout works today
- `POST /api/v1/payments/create-checkout-session` (`payments.py:54`, `mode="subscription"` at `:117`) — price-agnostic: the **frontend supplies the price_id** in the body.
- Dashboard upgrade UI: `web/app/dashboard/settings/components/subscription-tab.tsx` `handleUpgrade` (`:69-89`) → `getTierPriceId(tier)` → `apiClient.createCheckoutSession` (`web/lib/api.ts:438-445`). Upgrades gated on `subscriptionsEnabled` (`:299` ← backend `SUBSCRIPTIONS_ENABLED`).
- Marketing CTAs today: Console card → `/dashboard` (`stitch-pricing.tsx:111`), Teams → `/contact` (`:153`) — no checkout.
- Backend tier names: `free` (3 credits) / `starter` (env `_PRO`, 40) / `professional` (env `_DEVELOPER`, 200). Env names are legacy; no live tier named pro/developer.
- Credits source of truth = the tuples in the webhook maps (`payments.py:316-317`, `:390-391`); `tiers.ts` credits are display-only. Enforcement is numeric (`checks.py:155,174`; duplicated `:1573,1583`). "Unlimited" has an existing sentinel pattern: admins get `999999` (`users.py:356`) — Console fair-use = a large integer, no boolean flag exists.

### Wiring sequence (tomorrow, after founder supplies the two price IDs)
1. **Backend env + config:** add `STRIPE_PRICE_ID_CONSOLE` + `STRIPE_PRICE_ID_CONSOLE_ANNUAL` to `config.py` (~`:112`); set both on Railway.
2. **Both webhook maps:** add both new IDs → `("console", <credits — D2 decision>)` in `PRICE_TO_PLAN` (`payments.py:315-318`) AND `_plan_from_price_id` (`payments.py:389-393`). (F-PAY-04 portal upgrades re-derive through the second map.)
3. **Frontend env:** `NEXT_PUBLIC_STRIPE_PRICE_ID_CONSOLE{,_ANNUAL}` → `web/.env.example:16-17`, `web/Dockerfile:27-28,37-38` (build args!), `scripts/stripe-setup.sh:130-139`, Railway web service.
4. **`web/lib/tiers.ts`:** add `console` TierConfig + literal `case` in `getTierPriceId()` (`:70-79` — Next inlines env at build; dynamic reads don't work).
5. **`subscription-tab.tsx`:** add `console` to `TIER_ORDER` (`:15`) for upgrade-ordering logic.
6. **CTA decision:** point the Console card CTA (`stitch-pricing.tsx:111`) at a checkout trigger (needs auth → probably `/dashboard/settings?upgrade=console` deep link) or keep routing to `/dashboard` and let the paywall/settings sell the upgrade — decide with D3.
7. **Legacy tiers per D1:** if retiring from sale, remove starter/professional from the upgrade UI while keeping both webhook-map entries (existing subscribers keep re-deriving correctly).

### Test plan (Stripe test mode, before flipping anything live)
- Test-mode Console product mirroring the live one; run checkout end-to-end → assert webhook creates subscription with plan `console` and the intended credits; portal upgrade/downgrade path re-derives via `_plan_from_price_id`; `invoice.paid`, `subscription.deleted` paths sane.
- Negative test: checkout with an unmapped price id → confirm the fail-closed log fires and no plan is granted (this is the pre-fix trap; prove it's closed).
- The ops-sweep "purchase matrix" (bucket 3 #2) becomes runnable at this point.

### Related plan-doc anchors
- `audit/2026-06-24_p3_pricing_design.md:49,61,66` — P3 deliberately deferred the checkout to P4; PC7 wants tiers.ts reconciled to free/console/teams.
- `audit/2026-06-24_item3_packaging_plan.md:28-29,44` — P4 = first-run funnel + soft paywall at export/share/volume; release gate "P4 live". Personal-API allowance = P5, not tomorrow.
- Note: full P4 (soft paywall UX) is a BIGGER slice than the checkout wiring. Tomorrow's blocker is the checkout; the paywall UX can follow separately if the founder wants to stage it.
