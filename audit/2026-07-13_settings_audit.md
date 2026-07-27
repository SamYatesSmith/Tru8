# Dashboard Settings Area — Audit (assessment only)

**Date:** 2026-07-13
**Scope:** `web/app/dashboard/settings/` — `page.tsx`, `components/settings-tabs.tsx`, `account-tab.tsx`, `subscription-tab.tsx`, `notifications-tab.tsx`, `developer-tab.tsx`.
**Trigger:** Founder, during the Stripe test-payment walkthrough — "lots of dated elements that have either changed, are not relevant, or are just wrong; all tabs require assessment … we cannot release a haphazard, sub-standard customer-facing area." (`audit/OPEN_WORK.md`, 2026-07-13 entry.)
**Method:** every visible element walked and traced to its live backend source; each claim called right/wrong against product truth for 2026-07-13. **No code was changed — this is the assessment phase.**

**Severity key:** **P0** = wrong (a paying customer sees a false statement or a control that does nothing) · **P1** = dated (was true once, now misleading) · **P2** = polish (inconsistency / redundancy / dead code).

---

## Ground truth used (2026-07-13)

- **Lineup:** Free trial (3 checks) / **Console £20/mo · £200/yr, 200 checks/month hard cap** / Teams from £75 (sales-led, `/contact`). **Starter £7 / Professional £29 are RETIRED** — render only for their existing subscribers, never sold (`web/lib/tiers.ts`, `retired: true`).
- **Usage truth = the `usage_events` ledger** (`backend/app/services/usage_ledger.py`); re-searches/top-ups cost 1 credit each; legacy counters are back-compat only.
- **Agent API credits = a separate prepaid pence balance** (`User.credit_balance_pence`, per-call £0.02–£0.15) — distinct from subscription checks (`User.credits`).
- Currency GBP; UK English; "analysis"/"evidence research", never "verification"/"fact-checking"; six views named by ACTION; no verdict colours.

---

## Backend facts established (load-bearing for the findings)

1. **`GET /api/v1/payments/subscription-status`** returns `plan`, `creditsPerMonth`, `currentPeriodStart/End`, `cancelAtPeriodEnd`, `subscriptionsEnabled` (`backend/app/api/v1/payments.py:785-796`). **It carries NO billing-interval field.** A monthly and an annual Console subscriber are *identical* in the response: both `plan == "console"`, both `creditsPerMonth == 200` (webhook maps both price IDs to `("console", 200)` — `payments.py:319-320`). The **only** signal of annual billing is that `currentPeriodEnd` is ~12 months out, not ~1 month.
2. **`GET /api/v1/users/usage`** reads the ledger (`users.py:302` → `get_usage_snapshot`). For Console: `creditsPerPeriod == 200`, `isTrial == False`. **The 200 cap is enforced across the whole subscription period window** (`current_period_start`→now). For an *annual* subscriber that window is a **year**, so at the gate an annual subscriber effectively gets **200 checks per YEAR**, not per month, until the annual renewal resets it (`payments.py:687-689`). ⚠️ This is a billing-correctness question, not just copy.
3. **Email:** only two emails are ever sent — check-completed and check-failed — both via `backend/app/services/email_notifications.py`, both preference-gated, wired only in `runner.py`. **No weekly-digest sender and no scheduler (no Celery beat/cron) exist anywhere; no marketing-email sender exists.**
4. **API keys:** 5-active-key cap (`api_keys.py:92-101`), prefix `tru8_sk_` (`core/auth.py:30`). UI matches exactly.
5. **Agent prepaid rail is real and separate** (`User.credit_balance_pence`; top-up `POST /agent/credits/purchase`; balance `GET /agent/credits/balance`). The Developer settings tab references none of it.

---

## ACCOUNT TAB — `account-tab.tsx`

| # | Element (file:line) | What it says | What's true | Sev | Action |
|---|---|---|---|---|---|
| A1 | `account-tab.tsx:382` `PlanUsageSection` | `{currentTier.name} (£{currentTier.price}/month)` → **"Tru8 Console (£20/month)"** for *every* Console subscriber | An **annual** Console subscriber pays £200/yr, not £20/month. `currentTier.price` is the flat `20` from `tiers.ts`; there is no interval awareness. Wrong for annual buyers. | **P0** | Reword — infer interval from the `currentPeriodStart→End` delta (the only backend signal) and show "£200/year" or "£20/month" accordingly; or drop the price from this summary line and keep it only on the Subscription tab. |
| A2 | `account-tab.tsx:397-402` | "Checks — **{creditsPerMonth} per month**" → "200 per month" | Number (200) is right; the **word "month" is wrong for annual** subscribers, whose gate window is the full year (backend fact #2). | **P1** | Reword to match resolved interval, or neutral "200 per billing period". Underlying gate behaviour = founder decision (see decisions table). |
| A3 | `account-tab.tsx:362` | `creditsPerMonth = subscriptionData?.creditsPerMonth \|\| 3` | `/payments/subscription-status` does return `creditsPerMonth`; on the page-level API-error fallback (`page.tsx:62-66`) only `creditsPerPeriod` is set, so this silently defaults to 3. Cosmetic on the error path only. | P2 | Leave, or align the fallback object's field name. |
| A4 | `account-tab.tsx:93-111` delete flow | `confirm()` → `confirm("…Type DELETE in the next prompt…")` → `prompt("Type DELETE…")` | Functional, but the middle step is a plain OK/Cancel `confirm()` whose text promises a prompt — mild UX confusion. Browser-native dialogs also clash with the app's design language. | P2 | Optional: replace with an in-page typed-confirmation modal. Not release-blocking. |
| A5 | `account-tab.tsx:265-275` Activity stats | "Total Checks / Sources Analysed / Claims Analysed" | Verified against `GET /users/stats` (`totalChecks`, `totalSourcesAnalyzed`, `totalClaimsAnalyzed`, `claimTypeBreakdown`, `memberSince` all exist). UK spelling "Analysed" ✓, en-GB date ✓. | — | Correct — no action. |

**Account tab verdict:** structurally sound. The only real defect is the shared annual-price problem (A1/A2), which it inherits from `tiers.ts` having a single `price` field and the backend exposing no interval.

---

## SUBSCRIPTION TAB — `subscription-tab.tsx`

| # | Element (file:line) | What it says | What's true | Sev | Action |
|---|---|---|---|---|---|
| S1 | `subscription-tab.tsx:176-180` | Current-plan subline: `£{currentTierConfig.price}/month · {creditsPerMonth} checks` → **"£20/month · 200 checks"** for an annual subscriber | Same root cause as A1 — annual Console pays £200/yr. No interval field exists to distinguish (backend fact #1). | **P0** | Same fix as A1 — resolve interval from the period-window delta and render "£200/year" for annual; keep "£20/month" for monthly. |
| S2 | `subscription-tab.tsx:201-203` | Paid usage line: `{periodUsage} of {creditsPerMonth} checks used **this month**` | For **annual** subscribers "this month" is wrong: the ledger counts against the full annual window, so it's really usage-this-year against 200 (backend fact #2). For monthly subscribers it's correct. | **P1** | Reword conditionally ("this period"), and escalate the underlying gate behaviour (200/year for annual) to the founder — see decisions table. |
| S3 | `subscription-tab.tsx:302` | `const canUpgrade = isUpgrade && subscriptionsEnabled;` | **Dead variable** — the Upgrade CTA (`:377`) renders on `isUpgrade` alone and ignores `canUpgrade`, so `subscriptionsEnabled` never gates the button. Harmless today (subs are enabled in prod) but the guard silently does nothing. | P2 | Either wire `canUpgrade` into the CTA condition or delete it. |
| S4 | `subscription-tab.tsx:258-263` "Billing history" | A second button that calls `handleManageSubscription` — i.e. opens the **same** Stripe portal as "Manage subscription" | Not wrong (the portal shows invoices), but two differently-labelled buttons perform one identical action. Note `apiClient.getInvoices()` deliberately throws "not implemented" (`api.ts:485`), so routing to the portal is the correct choice — just don't present it as a distinct feature. | P2 | Merge into one action, or relabel to make the shared destination honest. |
| S5 | `subscription-tab.tsx:296` grid | `grid-cols-… lg:grid-cols-4` for the Compare-Plans cards | `purchasableTiers()` yields **3** cards for a typical user (Free / Console / Teams — Starter & Professional are retired). A 4-column grid leaves a visible empty column on desktop. | P2 | Set the grid to the actual card count (3), or centre. |
| S6 | `tiers.ts:66-71` Console features vs `/pricing` | Settings Console card lists "All six **lenses**", "Signed records + PDF export", "Targeted re-search" | `/pricing` (`stitch-pricing.tsx:23-49`) lists the same product as "All six **views**" + "Full export (PDF/CSV/JSON)" + "Signed record + receipts" + "Personal API allowance". Two surfaces describe one product differently; "lenses" also drifts from the action-names lock (internal term leaking to a customer surface). | P2 | Align feature copy between `tiers.ts` and `stitch-pricing.tsx`; use view/action names, not "lenses". |
| S7 | `subscription-tab.tsx:369-376` Teams card | Name "Teams", CTA "Contact Us" → `tier.contactUrl` (`/contact`) | Matches the lineup (Teams, sales-led, `/contact`). ✓ | — | Correct. |
| S8 | `subscription-tab.tsx:387-395` annual upsell | "or £{tier.annualPrice}/yr — two months free" → **£200/yr** | Correct against `tiers.ts` (`annualPrice: 200`) and `/pricing`. ✓ | — | Correct. |
| S9 | `subscription-tab.tsx:15` `TIER_ORDER` | Array still contains `'starter'`, `'professional'` | Intentional — needed for the upgrade/downgrade index maths; retired tiers are filtered out of display by `purchasableTiers()`. Not customer-visible unless the user *is* a legacy subscriber. | — | No action (correct by design). |

**Subscription tab verdict:** the annual-price line (S1) is the headline defect and is genuinely customer-facing wrong for anyone who buys the annual plan the founder is about to sell. S2 compounds it. The rest is polish.

---

## NOTIFICATIONS TAB — `notifications-tab.tsx`

| # | Element (file:line) | What it says | What's true | Sev | Action |
|---|---|---|---|---|---|
| N1 | `notifications-tab.tsx:250-276` **Weekly Digest** toggle | "Receive a weekly summary of your activity" — a working switch | **Aspirational.** The preference persists (`User.email_weekly_digest`) but **no sender and no scheduler exist** — no Celery beat/cron anywhere in the backend, no digest template, no code path reads the field to send anything (backend fact #3). The switch does nothing a customer will ever experience. | **P0** | **Cut** the toggle, or gate it behind an explicit "Coming soon" disabled state. Shipping a live control that silently never fires is exactly the "just wrong" the founder flagged. |
| N2 | `notifications-tab.tsx:278-304` **Marketing Emails** toggle | "Receive updates about new features and offers" | **Aspirational.** No marketing-email sender exists; the field is only read by the preferences endpoints and the GDPR export. Defensible as forward consent-capture, but as worded it implies active sending. | **P1** | Founder decision: **cut**, or keep as consent capture but reword to "Allow us to email you about new features" (no implied cadence). |
| N3 | `notifications-tab.tsx:194-220` **Check Completion** | "Get notified when your analyses are complete" | **Real** — sent from `runner.py:3172`, gated on `email_check_completion` + master (`email_notifications.py:100-104`). UK term "analyses" ✓. | — | Correct. |
| N4 | `notifications-tab.tsx:222-248` **Check Failures** | "Get notified if an analysis encounters an issue" | **Real** — sent from `runner.py:3118`, gated on `email_check_failure` + master (`email_notifications.py:152`). Terminology ✓. | — | Correct. |
| N5 | `notifications-tab.tsx:170-192` **master toggle** | Disabling it disables all sub-toggles | Enforced both client-side and server-side (`users.py:604-611`); every send double-checks `email_notifications_enabled`. ✓ | — | Correct. |
| N6 | `notifications-tab.tsx:307-311` | "Your notification preferences are synced across all devices." | True — server-stored (`User` columns) with a localStorage backup. Uses an emerald info panel (informational, not a verdict colour). ✓ | — | Correct. |

**Notifications tab verdict:** two of the five switches (Weekly Digest, Marketing) are dead controls. Weekly Digest is the one that most clearly reads as "just wrong" to a paying customer — recommend cutting it before release. The two functional switches and the master cascade are solid and terminology-compliant.

---

## DEVELOPER TAB — `developer-tab.tsx`

| # | Element (file:line) | What it says | What's true | Sev | Action |
|---|---|---|---|---|---|
| D1 | `developer-tab.tsx:215,349` key cap | "New Key" disabled at ≥5; footer "**{n}/5** active keys" | Matches backend cap exactly (`api_keys.py:92-101`, "Maximum 5 active API keys per account"). ✓ | — | Correct. |
| D2 | `developer-tab.tsx:289-291,395` prefix | Shows `{key_prefix}...` and curl `X-API-Key: tru8_sk_...` | Matches `API_KEY_PREFIX = "tru8_sk_"` and the stored 8-char prefix (`api_keys.py:104-107`). ✓ | — | Correct. |
| D3 | `developer-tab.tsx:65-101` create/revoke | Create (shown once), revoke (soft-delete) | Matches `POST ""` / `DELETE "/{key_id}"` (`is_active=False`). Revoked-keys `<details>` and single-view secret handling all correct. ✓ | — | Correct. |
| D4 | Whole tab — **omission** | Tab is **key-management only**; never mentions the agent prepaid balance, credit-pack top-up, or per-call rates | The prepaid rail is real (`credit_balance_pence`; `POST /agent/credits/purchase`; `GET /agent/credits/balance`) but is surfaced **only on `/developers`**, not in Settings. A logged-in developer cannot see or top up their agent balance from Settings. Internally consistent, but a gap if Settings is meant to be the account's control centre. | P2 | Founder decision: surface balance + "Top up" here, or deliberately keep credit management on `/developers` and leave this tab as pure key management. |
| D5 | `developer-tab.tsx:399-414` doc links | Links to `/api/docs` and `/api/redoc` (new tab) | Standard FastAPI doc routes — **verify they resolve in prod** (not traced here). Low risk but worth a click-test before release. | P2 | Verify both routes 200 in prod. |

**Developer tab verdict:** the cleanest tab — every claim it makes is correct. Its only issue is what it *doesn't* say (the agent credit balance), which is a UX-scope decision, not an error.

---

## Cross-tab & cross-surface consistency

| # | Where | Inconsistency | Sev |
|---|---|---|---|
| X1 | Account (A1) ↔ Subscription (S1) | Both render "£20/month" for an annual Console subscriber, from the same interval-blind `tiers.ts` price. One fix (interval resolution) closes both. | **P0** |
| X2 | Account (A2) ↔ Subscription (S2) | Both describe the 200 cap as monthly ("per month" / "this month") while the ledger gate applies it over the full period window — a full **year** for annual subscribers. | **P1** |
| X3 | Subscription `tiers.ts` ↔ `/pricing` `stitch-pricing.tsx` | Same Console product, different feature copy ("lenses" vs "views"; missing receipts / Personal API allowance in Settings). | P2 |
| X4 | Settings area ↔ `/developers` **(adjacent, out of settings scope but flagged)** | `web/app/developers/page.tsx:366` still tells developers: *"Dashboard subscriptions (**Starter, Professional**) give you a monthly check allowance…"* — **stale retired-tier language** naming plans that are no longer sold. Should read Console. | **P1** |
| X5 | `/pricing` `stitch-pricing.tsx:208` **(adjacent)** | API band copy: "metered **verification**, billed per call" — "verification" violates the terminology lock ("analysis"/"evidence research" only). | P1 |

X4 and X5 are outside the settings directory but were surfaced while tracing settings claims; noting them so the retired-tier / terminology sweep is complete. They are **not** part of the settings fix slices.

---

## Founder decision table (judgement calls — not mechanical fixes)

| # | Decision | Why it needs you | Options |
|---|---|---|---|
| DEC-1 | **Annual-Console display (A1/S1).** How should a £200/yr subscriber's plan line read? | The backend exposes **no billing-interval field** — only the period-window length distinguishes annual from monthly. Fixing the copy requires either (a) inferring interval from `currentPeriodStart→End` on the frontend, or (b) adding an `interval` field to `/subscription-status`. | (a) Frontend infers from date delta (no backend change); (b) backend adds `interval`/`billingCycle` (cleaner, small backend slice); (c) drop the price from the settings lines entirely and rely on the Stripe portal. |
| DEC-2 | **200-cap window for annual (A2/S2, backend fact #2).** Is "200 checks/**month**" actually enforced monthly for annual subscribers, or 200 over the whole year? | Today the ledger gate counts against `current_period_start`, which for annual is a **year** — so an annual buyer gets ~200 checks for the year, contradicting the "200 checks a month" marketing on `/pricing` and `tiers.ts`. This is a **billing-correctness** question beyond settings copy. | (a) Intended (annual = 200/yr) → then the marketing "200/month" is the thing to fix; (b) not intended → backend needs a monthly reset within the annual period; either way the settings copy follows the answer. **Recommend resolving before selling annual.** |
| DEC-3 | **Weekly Digest toggle (N1).** | It's a live control that never fires (no sender, no scheduler). | (a) **Cut** (recommended for release); (b) build a digest job + template; (c) keep, disabled, labelled "Coming soon". |
| DEC-4 | **Marketing Emails toggle (N2).** | No marketing sender exists; the switch is currently consent-capture only. | (a) Cut; (b) keep as consent capture with reworded, cadence-free copy. |
| DEC-5 | **Agent credit balance in Settings (D4).** | The prepaid balance + top-up fully exist but live only on `/developers`. | (a) Surface balance + "Top up" in the Developer settings tab; (b) keep credit management on `/developers` by design and leave the tab as key-management only. |

---

## Bottom line

- **Release-blocking (P0):** the annual-Console price line (A1/S1/X1) and the dead Weekly Digest toggle (N1) are the two things that will read as "just wrong" to a paying customer during the imminent Stripe go-live. Both are contained fixes.
- **Escalate:** DEC-2 (annual 200-cap window) is a genuine billing-correctness question, not just copy — worth resolving before the annual price is sold.
- **Dated (P1):** the "per month / this month" wording for annual (A2/S2), the Marketing toggle (N2), and the adjacent stale "Starter, Professional" line on `/developers` (X4) + "verification" on `/pricing` (X5).
- **Clean:** the Developer tab's API-key logic, and the Check-Completion/Failure/master notification switches are all correct and terminology-compliant. No verdict colours anywhere in the settings area.

*Fixes to follow as separate, founder-approved slices — the assessment above is frozen.*

---

## Remediation plan — design-reviewed, decisions locked (2026-07-13)

**Design insight:** the gate (`enforce_usage_limit`) and the usage meter (`/users/usage`) both call **one** function, `get_usage_snapshot`. Fixing the usage window there corrects the lock-out bug *and* the "X of 200 used this month" display in a single place — the change concentrates, it does not scatter.

**Founder decisions locked:**
- **#1 annual allowance** → computed monthly rolling window inside `get_usage_snapshot` (no scheduler; one code path for monthly + annual). Ships with a unit test.
- **Marketing Emails toggle** → **cut** (UI removed; DB column left dormant).
- **Weekly Digest toggle** → **cut** (UI removed; DB column left dormant).
- **Agent credit balance** → **add** a balance + top-up panel to the Developer tab.

**Slices (each: design → build → independent verify → sign-off):**

| Slice | Scope | Files | Verify |
|---|---|---|---|
| **1** (backend, logic) | Monthly rolling allowance window in `get_usage_snapshot`; store `billing_interval` on `Subscription` (from Stripe) and expose it on `/subscription-status` | `usage_ledger.py`, `models/user.py`, migration, `payments.py` | Unit test: annual sub, usage across 3 months, gate counts only current month + month-boundary clamp. No data backfill (annual is test-mode only). |
| **2** (frontend display) | Interval-aware price ("£200/year" vs "£20/month") + "this period" wording on Account + Subscription tabs | `account-tab.tsx`, `subscription-tab.tsx`, `api.ts`, TS types | tsc + visual |
| **3** (frontend cleanup) | Cut Weekly Digest + Marketing; wire `canUpgrade`; merge billing button; fix grid; align Console feature copy ("views") | `notifications-tab.tsx`, `subscription-tab.tsx`, `tiers.ts` | tsc + visual |
| **4** (developer tab) | Agent credit balance + top-up panel | `developer-tab.tsx`, `api.ts` | tsc + purchase-flow check |
| **5** (adjacent copy) | `/developers` "Starter, Professional" → "Console"; `/pricing` "verification" → "analysis" | `developers/page.tsx`, `stitch-pricing.tsx` | tsc + visual |

Slice 1 first (everything visual depends on its `billing_interval` field, and it carries the only real logic/risk).

### Build status (2026-07-13) — ALL FIVE SLICES BUILT + INDEPENDENTLY VERIFIED SOUND (uncommitted)

- **Slice 1** — `usage_ledger.py` monthly rolling window (`_monthly_window_start`); `Subscription.billing_interval` column + migration `2026_07_13_billing_interval` (head off `usage_events`, `server_default="month"`); set from Stripe on all four write paths; exposed as `billingInterval` on `/subscription-status`. Independent verify: **SOUND-WITH-NITS** → the one nit (a pre-existing local-vs-UTC timestamp in the new-sub branch the window math now leans on) **fixed**.
- **Slice 2** — `formatTierPrice(tier, interval)` in `tiers.ts`; Account + Subscription tabs show "£200/year" vs "£20/month" from the real interval. (The "per month / this month" wording — findings A2/S2 — became TRUE once Slice 1 made the annual allowance genuinely monthly, so no wording change was needed.)
- **Slice 3** — Weekly Digest + Marketing toggles cut (DB columns dormant); `canUpgrade` wired into the CTA; duplicate billing button merged; plan grid follows the real card count; "All six lenses" → "All six views".
- **Slice 4** — new Clerk-authed `GET /users/agent-credits` + `POST /users/agent-credits/purchase` (shared webhook fulfilment, metadata byte-identical to the agent rail, dispatch confirmed); balance + top-up panel in the Developer tab.
- **Slice 5** — `/developers` "Starter, Professional" → "Console"; `/pricing` "verification" → "analysis".

Independent verify of Slices 2–5: **SOUND**, no defects. Full matrix green (backend 81 + 144, web 72, tsc clean).

**New out-of-scope finding (verifier):** `web/app/terms-of-service/page.tsx:66,75` still lists Starter £7 / Professional £29 as live plans — stale, untouched here (legal doc), worth a follow-up slice.

**Not committed** — awaiting founder end-to-end test.


