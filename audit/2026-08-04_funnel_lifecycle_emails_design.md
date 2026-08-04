# Funnel lifecycle emails — welcome + trial exhausted

**Date:** 2026-08-04
**Status:** DESIGN — founder-agreed on the two forks, not built
**Why now:** the MCP registry listing will start sending developers. A user signs up,
spends 3 free checks and hears nothing. That silence sits between traffic and revenue,
and it is the cheapest gap on the board to close.

---

## 1. What already exists (verified, not assumed)

| Thing | State | Evidence |
|---|---|---|
| Resend integration | **LIVE in production** | `GET /api/v1/health/email-config` → `status: "ready"`, key `re_Hdyrx…`, package installed |
| Sending service | Built | `app/services/email_notifications.py` — `_send_email` + two templates |
| Transactional emails | 2 | check completed, check failed (both fired from `pipeline/runner.py`) |
| Per-user preferences | 5 fields | `email_notifications_enabled`, `_check_completion`, `_check_failure`, `_weekly_digest`, `_marketing` |
| Preferences UI | Built | `web/app/dashboard/settings/components/notifications-tab.tsx` |
| Clerk webhook | **LIVE, Svix-verified** | bare POST to `/webhooks/clerk` → **403**, not 503, so `CLERK_WEBHOOK_SECRET` is set. Handles `user.deleted` / `user.updated` only |
| Usage gate | Canonical | `services/usage_ledger.py::get_usage_snapshot` → `{usage, limit, limit_type}` |

**Gap:** no welcome email, no trial-exhausted email, and **zero tests for the email
service** — `find tests -iname "*email*"` returns nothing. The service has never been
covered.

**No new vendor, no new dependency, no domain verification.** Both emails are new
templates and new triggers on the existing Resend path.

---

## 2. Founder decisions (locked 2026-08-04)

1. **Welcome fires on first arrival in the app**, not the Clerk `user.created` webhook.
   Rationale: no external config to forget, testable locally, and guaranteed to fire for
   everyone who actually reaches the product. Accepted cost: someone who signs up and
   bounces before the dashboard loads gets nothing.
2. **Trial-exhausted fires when the 3rd check finishes**, not when a 4th is blocked.
   Rationale: reaches 100% of exhausted users rather than only those who return, and lands
   at the moment a finished evidence landscape is on screen.
3. **Scope: the two emails done properly** — preference toggle, unsubscribe, and the test
   coverage the service currently lacks.

---

## 3. Design

### 3.1 Schema — one migration, three columns on `user`

| Column | Type | Default | Purpose |
|---|---|---|---|
| `email_lifecycle` | bool | `True` | Opt-out for this class of email |
| `welcome_email_sent_at` | timestamp, null | — | Exactly-once marker |
| `trial_exhausted_email_sent_at` | timestamp, null | — | Exactly-once marker |

**Backfill is load-bearing, not cosmetic.**
- `welcome_email_sent_at := created_at` for every existing row. Without this, every
  existing user gets a "welcome" the first time they load the dashboard after deploy.
- `trial_exhausted_email_sent_at := now()` for every existing user already at or over
  their trial limit. Without this, the deploy blasts the historical exhausted cohort with
  an upgrade pitch they did not ask for.

A deliberate reactivation campaign to that historical cohort is a **separate, opt-in
decision** — not a side effect of shipping this.

### 3.2 Exactly-once: claim the row, then send

Both triggers use a conditional update as the lock:

```
UPDATE "user" SET <marker> = now()
 WHERE id = :id AND <marker> IS NULL
RETURNING id
```

Send **only if a row comes back**. This is race-safe across concurrent requests and
across pipeline workers, and it needs no new locking. Marker is set *before* the send:
if Resend fails we lose one email, which is strictly better than a retry loop mailing
someone repeatedly.

### 3.3 Welcome — trigger

Hook the create path of `api/v1/users.py::get_or_create_user` (line 75-80).

⚠️ **That function is `INSERT … ON CONFLICT DO UPDATE`, so "returned a user" does not mean
"created a user"** — a returning user whose Clerk ID changed takes the update branch. The
`welcome_email_sent_at IS NULL` claim above is what actually distinguishes them; do not
try to infer it from `created_at == updated_at` (two separate `datetime.now()` calls, so
they can differ by microseconds).

⚠️ **Do not call the Resend SDK inline.** It is synchronous; `get_or_create_user` is on
the async request path for `/profile`, `/stats`, `/usage`, `/checks` and more. A blocking
HTTP call there stalls the event loop and lands on the user's first page load. Dispatch
via `asyncio.to_thread` (or a FastAPI background task) and wrap in `try/except` so a mail
failure can never fail the request.

### 3.4 Trial exhausted — trigger

Extend `pipeline/runner.py::send_success_notifications` (line 3448), which already runs
after a successful check and already owns the completion email.

**Reuse `get_usage_snapshot` — do not re-implement the limit formula.** The trial limit is
`max(3, credits + total_credits_used)`, not a literal 3, and it is deliberately the legacy
allocation invariant. A second copy of that expression will drift from the gate, and then
the email and the paywall will disagree.

Condition: `limit_type == "trial"` **and** `usage >= limit`.

**Standalone email, not a footnote on the completion email.** Reasons: it needs its own
opt-out; a user who has switched completion emails off still needs to know their trial
ended; and an upgrade CTA buried under a results summary converts poorly. Accepted cost:
two emails land within seconds of each other. If that proves irritating in practice, the
fix is to suppress the completion email's CTA on the last check, not to merge the two.

### 3.5 Consent and unsubscribe

- Gate both on `email_notifications_enabled AND email_lifecycle`, matching the existing
  pattern for completion/failure.
- **Do not reuse `email_marketing`** — it defaults to `False`, so the feature would be
  dark for everyone.
- Add a `List-Unsubscribe` header (`mailto:`) to lifecycle sends. Cheap, and it is what
  bulk-sender rules look for.
- Keep the existing logged-in "Manage preferences" link. A one-click unauthenticated
  unsubscribe token is **deliberately deferred** — current volume does not justify a new
  public endpoint, and it can be added without reworking any of this.

### 3.6 Copy

House rules apply: UK English; "evidence research", not "fact-checking"; "analysis", not
"verification"; no verdict language.

- **Welcome** — what Tru8 does ("we organise; you decide"), that 3 free checks are
  waiting, one primary CTA into the app, and a link to the live sample report so they can
  see finished output before spending a credit.
- **Trial exhausted** — plain statement that the 3 free checks are used, what they got
  (checks run, sources organised), Console pricing (£20/mo · £200/yr, 200 checks/month),
  and a single upgrade CTA. No urgency theatre, no fake scarcity.

---

## 4. Work items

| # | Item | Notes |
|---|---|---|
| E-1 | Migration + 3 columns + **both backfills** | Backfills are the risky part — review them, not the DDL |
| E-2 | `send_welcome_email` + template | Reuse the existing card layout |
| E-3 | `send_trial_exhausted_email` + template | Console pricing must match `web/lib/tiers.ts` |
| E-4 | Welcome trigger in `get_or_create_user` | Off the event loop; must never fail the request |
| E-5 | Exhaustion trigger in `send_success_notifications` | Via `get_usage_snapshot`, not a copied formula |
| E-6 | `email_lifecycle` toggle — API + settings tab | `/users/email-preferences` already exists |
| E-7 | Tests | See §5 |

Frontend surface is small: one toggle in an existing tab.

---

## 5. Test plan — the seam, not the halves

The service has **no existing tests**, so this starts from zero.

1. **Both templates render** — no unescaped interpolation, links absolute, pricing matches
   the tiers config.
2. **Preferences honoured** — global off, lifecycle off, both off.
3. **Exactly-once** — calling the trigger twice sends once. Mutate the `IS NULL` guard away
   and this must fail.
4. **Backfill correctness** — an existing user does not receive a welcome; an
   already-exhausted user does not receive an exhaustion email.
5. **Wired seam** — signup path actually reaches a send, and a 3rd completed check actually
   reaches a send. **Both halves green with a dead wire is exactly how NF-18 hid**
   (`feedback_test_wired_prepare_query_path`).
6. **Failure isolation** — Resend raising must not fail the request or the pipeline.

Every guard gets a mutation check. A green test file is not evidence it pins anything.

---

## 6. Risk

| Risk | Handling |
|---|---|
| Deploy mails the entire existing user base | The two backfills in E-1. This is the single highest-consequence item here |
| Blocking the async request path | `asyncio.to_thread`; never call Resend inline |
| Duplicate limit formula drifting from the gate | Reuse `get_usage_snapshot` |
| Two emails arriving together | Accepted; documented alternative in §3.4 |
| Email failure breaking signup or a check | `try/except` on both triggers, matching existing practice |

**No pipeline code is touched**, so the replay bench is not in play and no re-gold is owed.
This work is independent of the two changes currently held in the working tree.

---

## 7. Design review (2026-08-04, self-review — NOT independent)

Reviewed §3 against the code before building. **Four defects in the plan above, all now
corrected in this section.** The plan as originally written would have shipped bugs.

### R-1 — the founder would have been emailed "your free trial is over" ⛔
`_is_admin` bypasses the limit in `enforce_usage_limit`, but **`get_usage_snapshot` still
returns `usage >= limit` for an admin**, because the bypass is in the gate, not the
snapshot. An admin account with hundreds of checks reads as exhausted on every single
check. **Fix: exclude admins from the exhaustion email.**

### R-2 — a trial could be exhausted with no email ever sent ⛔
Re-searches and top-ups debit credits (`kind="re_search"` / `"top_up"`,
`checks.py:1675/1784/1890`) but **do not go through `send_success_notifications`**. Run one
check, then two re-searches, and the trial is gone in silence.

**Fix: a shared helper called from two choke points**, not one:
- `pipeline/runner.py::send_success_notifications` — covers all 4 check-completion sites.
- `api/v1/checks.py::_reserve_re_search_credit` — covers all 3 re-search/top-up sites,
  after its commit.

The exactly-once marker makes double-wiring safe: whichever fires first claims it.

This does **not** re-open the founder's decision. That fork was *proactive vs. reactive
(the 402 block)*; this is the same proactive email reached from a second path. Hooking the
402 itself was rejected on inspection anyway — it raises inside a `FOR UPDATE`
transaction that is about to roll back, so the marker claim would be lost.

### R-3 — lapsed subscribers would get the wrong email ⛔
When a subscription goes inactive, `limit_type` falls back to `"trial"` and the formula
`max(3, credits + total_credits_used)` makes `usage == limit` for anyone who has spent
their allowance. A former paying customer would receive an email about "your 3 free
checks". **Fix: only send when the user has never had a subscription row at all.**

### R-4 — local dev would silently burn the marker ⚠️
The marker is claimed before sending (correct — it prevents a retry loop). But
`_send_email` returns `False` early when email is disabled, so running the flow in dev
with `ENABLE_EMAIL_NOTIFICATIONS=False` would set the marker and permanently suppress the
real email. **Fix: return before claiming when the service is disabled.**

### Confirmed sound on review
- Resend's `Emails.send` **does** accept custom `headers` (SDK 2.19.0, verified in the
  installed package), so `List-Unsubscribe` is available.
- Credits are debited *before* the pipeline runs, so by completion the ledger already
  includes the current check — `usage >= limit` is correct at that moment.
- Agent and API-key users never reach `get_or_create_user`; they construct `User` directly
  (`core/agent_auth.py`, `api/v1/agent_x402.py`), so they cannot receive a welcome email.
- Failed checks refund, and the trigger is on the success path only — no email for a check
  the user was not charged for.
- Timestamps must be **naive UTC** (`_utcnow_naive`) to match every other column here.

---

## 8. Incidental finding (not part of this work)

`GET /api/v1/health/email-config` is **publicly reachable, unauthenticated**, and returns
the sending address and the first 8 characters of the Resend API key. Not a key leak, but
an unauthenticated diagnostic exposing configuration. Low severity; worth closing when
someone is next in that file. Logged here so it is not lost.
