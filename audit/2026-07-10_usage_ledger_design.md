# Usage ledger — design review (2026-07-10)

**Status: SIGNED OFF 2026-07-10 (D1 = admin sees real usage w/ unlimited limit; D2 = `drew_trial` column, extend existing refund path; D3 = `usage_events`). Phase A BUILT same day + INDEPENDENTLY VERIFIED — verdict SOUND-WITH-NITS: 1 defect found (migration step-2 adjustment stamped at `now` would inflate an active subscriber's current-period meter) → FIXED (adjustment backdated to `user.created_at`, fallback 2000-01-01) → verifier CONFIRMED CLOSED. Nits N1-N5 logged non-blocking (notable: no real-Postgres race test; no endpoint-level B5 ordering test). Targeted suites 103/103 + new seam tests. Phases B (frontend) and C (non-admin meter proof) remain.**

**Trigger:** the Console pricing decision (200 checks/month, hard cap) forced the question "what exactly debits a credit, and is it counted?" — and the answer exposed that subscriber usage accounting is structurally broken. Founder decision 2026-07-10: re-searches/top-ups DO count against the 200; fix designed properly, not patched.

**Scope:** billing/usage seam only (API layer + one runner refund function + frontend gating/copy). No pipeline-stage change, no LLM request change → **replay bench not required** (noted per [[feedback_replay_bench]] — the bench gates pipeline-quality work; this is entitlement accounting).

---

## 1. Current state (verified at file:line, 2026-07-10)

### The four counters

| Counter | Written by | Read by | Semantics |
|---|---|---|---|
| `Check.credits_used` | creation `=1` (`checks.py:242`); refund `=0` (`runner.py:3155`); agent/test `=0` | **Subscriber usage** = `sum()` in period (`checks.py:157,1574`; `users.py:313`) | Per-check debit marker |
| `User.credits` | `-1` on every debit if `>0` (`checks.py:252-253,1595-1596`); `+1` on refund (`runner.py:3154`) | **Trial limit** component (`max(3, credits + total_used)`) | Trial allocation remaining |
| `User.total_credits_used` | `+1` on every debit (`checks.py:254,1594`); never decremented | **Trial usage** (`checks.py:168,1581`; `users.py:321`) | Lifetime debits |
| `Subscription.credits_remaining` | Reset on webhook renewal (`payments.py:339`) | **Nothing** (gates never read it) | Vestigial |

### The defects

- **B1 — subscriber re-searches uncounted.** All three re-search/top-up endpoints (`research-gaps` `checks.py:1619`, `research-thin` `:1723`, single-element `:1899`) debit via `_deduct_credit` (`:1592-1597`), which writes only the User counters. Subscriber usage sums Check rows → **re-search/top-up validate against the 200 but never count toward it.** Trial users ARE counted (their usage reads the User counter). Two ledgers, divergent truth.
- **B2 — Seeker gate blocks paying subscribers.** Frontend re-search gating reads `creditsRemaining` (= `User.credits`, the TRIAL field) from `/users/usage` (`SeekerView.tsx:45-47`, `ResearchButton.tsx:40`). A subscriber who exhausted the 3 trial credits before upgrading has `credits=0` → UI shows "limit reached" and disables re-search while the backend would allow it.
- **B3 — refund grants phantom trial credit to subscribers.** `refund_check_credit_async` (`runner.py:3154`) unconditionally `user.credits += 1`. A subscriber (who never drew from `User.credits` — creation only decrements when `>0`, and theirs is typically 0) gains a trial credit on every timed-out check. If their subscription later lapses, they carry phantom free checks.
- **B4 — gate/debit race.** Limit check and debit are separate statements with no row lock (`checks.py:137-254`, `:1557-1597`). Two concurrent requests at 199/200 both pass. Low stakes at a 200 cap, but wrong.
- **B5 — deduct after fire.** Single-element re-search launches the background task BEFORE deducting (`checks.py:1896-1899`); if the deduct raises, the work runs unbilled.
- **B6 — client-side usage drift.** `web/lib/usage-utils.ts` computes usage from start-of-calendar-month, not the billing period (cosmetic; server is authoritative for gates).
- **Copy drift:** `SeekerProvenanceNote.tsx:6` says "1 credit per element"; the gap re-search endpoint charges 1 credit for ALL gap elements in a claim (`checks.py:1619` docstring). We under-promise in reverse — says more expensive than it is.

### Why the founder has never seen a meter move
`/users/usage` hardcodes admins to `periodCreditsUsed: 0, creditsPerPeriod: 999999` (`users.py:350-365`). All four meter surfaces (dashboard hero, UsageCard, Settings→Subscription bar, new-check gate) read this endpoint — the admin account is structurally incapable of demonstrating them.

---

## 2. Design — single source of truth: `usage_events`

One append-only ledger table; **all usage reads switch to it; legacy counters stay dual-written for API back-compat** (`creditsUsed`/`creditsRemaining` appear in `auth.py:32`, `response_builder.py:350`, check responses) but no gate reads them again.

### 2.1 Schema (new table, Alembic revision on current head)

```
usage_events
  id           varchar(36) PK (uuid4)
  user_id      varchar FK user.id, NOT NULL
  check_id     varchar FK check.id, NULL      -- the check this event concerns
  kind         varchar(16) NOT NULL           -- 'check' | 're_search' | 'top_up' | 'refund' | 'adjustment'
  credits      int NOT NULL                   -- +1 debit, -1 refund, ±n adjustment
  created_at   timestamp NOT NULL default now
INDEX ix_usage_events_user_created (user_id, created_at)
UNIQUE partial ux_usage_events_check_kind ON (check_id, kind) WHERE kind IN ('check','refund')
```

- The partial unique index makes creation-debit and refund **idempotent at the database level** (at most one of each per check). Re-search/top-up events are unbounded per check (correct — each run is a real debit).
- `kind` distinguishes what the user did — feeds future per-action analytics ("how often is re-search used?") for free.

### 2.2 Usage semantics

- **Subscriber usage** = `SELECT coalesce(sum(credits),0) FROM usage_events WHERE user_id=:u AND created_at >= :current_period_start`. Period boundary = `Subscription.current_period_start`, maintained by the existing Stripe webhooks (`payments.py:687` on `invoice.paid`) — renewal "resets" the meter automatically because the window moves; no reset job needed.
- **Trial usage** = same sum, unbounded window (lifetime). Trial limit formula unchanged: `max(3, user.credits + user.total_credits_used)`. Equivalence with today proven: headroom = limit − usage = `user.credits` under both the old counters and the net ledger (a refund is `credits +1` / ledger `−1` → headroom identical).
- Refunds are **compensating events** (`kind='refund', credits=-1`), never deletions — the ledger is append-only, auditable, and sums correctly in any window that contains both the debit and the refund. (Edge: a check debited in period N and refunded in period N+1 gives N+1 a −1. Accepted — it's a real goodwill credit in the period the user experienced the failure, and the alternative — mutating history — breaks auditability.)

### 2.3 One service, one transaction (fixes B1, B4, B5)

New `backend/app/services/usage_ledger.py`:

```python
async def reserve_usage(session, user_id, kind, check_id=None, limit_ctx=...) -> UsageEvent
    # SELECT user FOR UPDATE  → serialises concurrent gates (B4)
    # compute limit (subscription period sum | trial lifetime sum)
    # raise 402 if usage >= limit
    # INSERT usage_event  +  dual-write legacy counters
    # single commit — gate and debit are atomic
async def refund_usage(session, check_id) -> bool
    # idempotent via the partial unique index; writes kind='refund'
    # dual-writes legacy counters WITHOUT the B3 bug (only re-credit
    # User.credits if the original debit actually drew from it — recorded
    # on the event? see D2 below — simplest correct rule: re-credit only
    # when the user has no active subscription at refund time)
```

Call-site changes:
- `_validate_and_create_check` (`checks.py:137-254`): replace inline gate+reserve with `reserve_usage(kind='check')`; Check row creation joins the same transaction.
- `_check_credits` + `_deduct_credit` (`checks.py:1557-1597`): **deleted**, replaced by `reserve_usage(kind='re_search'|'top_up')` called BEFORE `asyncio.create_task` in all three endpoints (fixes B5 ordering).
- `refund_check_credit_async` (`runner.py:3126`): body delegates to `refund_usage` (fixes B3).
- `/users/usage` (`users.py:313-321`): reads the ledger; **response shape unchanged** (all four meters keep working untouched).

### 2.4 Backfill (inside the migration, data volume trivial — ~45 checks in prod)

1. One `kind='check', credits=n` event per existing Check with `credits_used > 0`, `created_at` copied from the check → subscriber-sum parity with today is exact by construction.
2. Per-user trial reconciliation: `delta = user.total_credits_used − sum(that user's backfilled debits)`; if `delta > 0`, one `kind='adjustment', credits=delta` event (timestamped at migration time). This preserves historical re-search debits that only ever lived in the User counter — trial usage numbers do not move.
3. Refunded checks need no event (their `credits_used=0` excludes them from step 1; net contribution today is 0 and stays 0).
4. Downgrade = drop table (legacy counters were dual-written throughout, so rollback loses nothing).

### 2.5 Frontend (fixes B2 + copy + the pricing sentence)

- **Seeker gate:** compute `remaining = creditsPerPeriod − periodCreditsUsed` from the fields `/users/usage` already returns; stop reading `creditsRemaining` (`SeekerView.tsx:45-47`). Admin (999999) and subscriber cases both fall out correctly.
- **Copy:** `SeekerProvenanceNote` + `ViewGuide` → "1 credit per re-search run"; `TopUpButton` already says 1 credit per run (correct).
- **Pricing page:** add the credit-definition sentence under feature row 01: *"Measured in credits: a check is 1 credit; a targeted re-search or evidence top-up is 1 credit."*
- **`usage-utils.ts`:** align the window to the billing period where a period start is available (B6).

### 2.6 Admin visibility (founder decision D1)

Recommended: `/users/usage` admin branch returns **real** `periodCreditsUsed` (computed like any subscriber-less user: lifetime ledger sum) with `creditsPerPeriod: 999999`. The founder's own meters then visibly move — partial self-serve proof — while remaining uncapped. Full proof still wants a non-admin account (Phase C).

---

## 3. What this deliberately does NOT do

- **No removal of `Subscription.credits_remaining`** (vestigial but harmless; removing it touches webhook code that the Stripe Console wiring is about to touch — do it there or never).
- **No refund-on-failed-re-search.** Re-search runs fire-and-forget; a failed run today keeps its credit. Adding refund needs completion-status plumbing back to the ledger — logged as a follow-up, not smuggled in.
- **No change to the agent/prepaid rail** (`credit_balance_pence` is a separate, correct system).
- **No API response-shape changes** — every existing consumer (dashboard, mobile surfaces, MCP) is untouched.

## 4. Test plan

- **Unit (`tests/unit/services/test_usage_ledger.py`):** debit/limit/402 at boundary; refund idempotency (double-refund = one event); B3 regression (subscriber refund does not bump `User.credits`); trial adjustment math; period-window edges (event exactly at `period_start`); dual-write parity.
- **Unit (endpoints):** all three re-search endpoints debit the ledger (regression for B1 — assert a subscriber's period sum includes the re-search); deduct-before-task ordering (B5).
- **Concurrency:** two concurrent `reserve_usage` calls at limit−1 → exactly one succeeds (FOR UPDATE proof; SQLite test fallback: assert the lock is requested, run the real race against Postgres in integration if the harness supports it).
- **Migration:** backfill parity assertions on a seeded fixture (subscriber sum before == after; trial usage before == after).
- **Frontend (vitest):** Seeker remaining-derivation (subscriber with 0 trial credits → button enabled; at limit → disabled); tsc.
- **Existing suites:** `test_users_endpoint.py` + `test_runner.py` (refund) updated, full unit suite green.

## 5. Phasing ([[phased-build-loop]])

- **Phase A — backend ledger:** migration + backfill, `usage_ledger.py` service, call-site switches, refund fix, admin-usage tweak (D1). Independent adversarial verify. **Ships before the Stripe Console wiring** — the 200 cap must be real before the first subscriber can exist.
- **Phase B — frontend:** Seeker gate fix, copy alignment, pricing-page credit sentence, usage-utils window. (The pricing sentence rides with the uncommitted toggle work from this morning.)
- **Phase C — verification:** non-admin test account: run a check + a re-search → Settings→Subscription bar and dashboard meters advance by 2; founder eyeball.

## 6. Decisions for founder

- **D1 — admin meter:** show real usage with unlimited limit (recommended, §2.6) vs keep hardcoded 0.
- **D2 — refund rule for `User.credits`:** recommended rule "re-credit the trial field only when the user has no active subscription at refund time" (simple, closes B3). Alternative: record on the debit event whether it drew from the trial field and mirror exactly on refund (more precise, one more column `drew_trial bool`). Recommendation: **the extra column** — it's the properly hardened form and costs one boolean.
- **D3 — naming:** `usage_events` (recommended — it records usage of all kinds) vs `credit_events`.
