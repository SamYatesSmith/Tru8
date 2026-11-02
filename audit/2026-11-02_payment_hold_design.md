# Payment hold on dispute (security sweep #1): rev 2, BUILT. Rev 1 below is superseded

2026-11-02 · Status: DESIGN, for independent review before build.

**Founder decision (2026-11-02): A.** When Stripe reports a dispute, or a full refund, pause the account's checks until it is resolved, and freeze prepaid credits too.

## Problem (confirmed in code)
- `payments._revoke_credits_for_charge` (`payments.py:526-567`, called by `charge.refunded` and `charge.dispute.created`) zeroes `Subscription.credits_remaining` and `User.credits`.
- The dashboard gate reads neither for a subscriber. `usage_ledger._active_subscription` requires `status in (active, trialing)`, then sums `usage_events` against `credits_per_month`.
- The subscription stays `active` through a dispute, so a disputer keeps 200 checks/month.
- Agent prepaid credits (`User.credit_balance_pence`) are untouched by design (docstring), so the agent rail keeps working.

## Design
**State.** Three nullable columns on `User`:
- `payment_hold_reason`: `dispute` | `refund`
- `payment_hold_at`
- `payment_hold_charge_id`

Null means no hold.
- The migration revises the current head. The model already lives in `app/models/user.py`, which `app/models/__init__.py` exports, so the `create_all` + `stamp head` bootstrap cannot skip it (the M-06 failure mode).
- Verify after deploy:
  - `alembic current` is the new head;
  - the columns exist (`information_schema`);
  - one webhook replay sets them.

**Set** (webhooks, idempotent, same customer→user lookup as today):
- `charge.dispute.created` → hold `dispute`, recording the charge id.
- `charge.refunded` where `amount_refunded >= amount` (a FULL refund) → hold `refund`. A partial refund keeps today's behaviour only.
- The existing revoke logic stays.

**Lift:**
- `charge.dispute.closed` with `status in ("won", "warning_closed")` and the same charge id → clear the hold.
- `lost` → keep it (founder reviews).
- A refund hold → cleared by the next successful payment from that customer: `invoice.paid` or a completed credit-pack checkout, after `payment_hold_at`. A dispute hold is NOT cleared by a new payment; only a won dispute clears it.
- Founder override: `python -m scripts.payment_hold lift <user_id>` / `show <user_id>`.

**Enforce:** a single helper `assert_no_payment_hold(user)` raises 402 with a neutral detail: "This account is paused while a payment is reviewed. Contact support@trueight.com." It is called:
1. in `usage_ledger.enforce_usage_limit`, which covers dashboard checks, re-search/strengthening and top-ups, all routed through it;
2. in the agent credit rail's charge path (`services/payments/credit_provider.py`), before the atomic debit, so prepaid credits are frozen;
3. **NOT** for Skyfire/x402, whose payer is not our Stripe customer;
4. **NOT** for reading existing checks, public reports or account/export pages. A hold stops spending, not access to data already paid for.
- **Admins:** a hold applies to admins too (no bypass). Holds are rare and deliberate.

**Visibility:**
- Log `[PAYMENT HOLD] set|lift user=… reason=… charge=…`.
- Email the founder via the existing `FEEDBACK_EMAIL`/Resend path, with fields escaped (sweep #3).
- No user-facing banner in v1; the 402 detail is the message.

**Stripe setup (founder, dashboard):** the live webhook endpoint (`we_1TEtiA`) must subscribe to `charge.dispute.closed`, alongside the already-handled `charge.refunded` and `charge.dispute.created`. Without it a won dispute never lifts the hold, and the founder must use the script. Claude cannot see the endpoint's event list from here.

## Tests
- Webhook handlers:
  - dispute.created sets a hold; dispute.closed won lifts it; lost keeps it;
  - full refund sets a hold; partial refund does not;
  - `invoice.paid` after a refund hold lifts it, but after a dispute hold does not;
  - replaying the same event is idempotent;
  - an unknown customer is a no-op.
- Gates:
  - `enforce_usage_limit` raises 402 with the neutral text for a held subscriber, even one with remaining monthly checks;
  - the credit rail refuses before debiting, and the balance is unchanged;
  - Skyfire is unaffected;
  - an un-held user is unaffected.
- Migration: upgrade/downgrade on the test DB; model/columns parity.
- Script: lift/show.

## Risks
- **A webhook arriving before the user row is linked:** no-op plus a log line, the same as today.
- **Wrongly holding a good customer:** only on a FULL refund or a dispute, both deliberate events. Recovery is the founder script.
- **Migration on deploy:** nullable columns, no backfill, so it is fast and safe.

## Founder actions
1. Add `charge.dispute.closed` to the live webhook's events (Stripe dashboard → Developers → Webhooks → the endpoint → events).


## Rev 2 (after review round 1: "not ready" — 1 BLOCKER, 3 HIGH; founder chose A again)
**Founder 2026-11-02:**
- Hold on **disputes only**.
- A **full refund of a subscription payment cancels that subscription** in Stripe. There is no refund hold, which removes review findings 3 (a cheap repurchase clearing a hold) and 8 (a goodwill refund pausing a good customer).

| Review finding | Rev 2 |
|---|---|
| BLOCKER: pack buyers have no Stripe Customer | User resolution: Checkout Session by `payment_intent` → `client_reference_id` (every checkout sets it, so old charges map too) → invoice→subscription→`Subscription` row → customer→`Subscription`. No checkout change needed. Unmapped → ERROR log + Sentry message. |
| HIGH: dedupe written before the handler | The claim is released on handler failure, so Stripe's retry is processed. The dispute handler no longer swallows `Charge.retrieve` errors. |
| HIGH: single charge-id field | State is a `payment_dispute` table keyed by **dispute id**. Held while any row is not in `{won, warning_closed, released}`. Every `charge.dispute.*` event re-reads the CURRENT status from Stripe, so order and escalation are safe. `released` (founder) sticks. |
| MEDIUM: a 402 reads as "buy more" | **403** with plain text that the web client shows verbatim (none of its match words). New purchases are refused while held: subscription checkout and both credit-pack routes. |
| MEDIUM: gate placement | Placed after the `FOR UPDATE` re-read and **before the admin bypass**. Credit rail: `AgentPaymentContext.charge` before `debit_credits` (idempotent replays still return first; nothing new is spent). |
| LOW: comparisons | Gated. |
| LOW: migration | New table, model exported from `app/models/__init__.py` (bootstrap-safe). Verified locally: upgrade → downgrade → upgrade; columns match the model. |

- **Founder tool:** `python -m scripts.payment_hold show <user_id>` / `release <dispute_id>`.
- **Tests:** `tests/unit/test_payment_hold.py`, 17 tests on a real aiosqlite ORM session:
  - pack-only dispute;
  - won, lost;
  - escalation;
  - out-of-order events;
  - second charge;
  - release sticks;
  - invoice mapping;
  - unmapped case;
  - Stripe failure raises;
  - admin gate;
  - credit freeze before debit;
  - message wording;
  - refund cancel and partial-refund no-cancel;
  - dedupe release.

  The gate, credit, refund and dedupe tests were mutation-checked.

**Founder Stripe action:** subscribe the live webhook to `charge.dispute.closed` and `charge.dispute.updated`.


## Verification (2026-11-02): independent verifier, then fixes
The verifier confirmed:
- every spend path is gated, after the lock and before the admin bypass;
- dispute state is right whatever order events arrive in;
- a founder release sticks;
- pack disputes map through Checkout and subscription disputes through the invoice;
- dedupe is released on failure;
- the 403 text is shown verbatim on web, mobile and MCP;
- the migration is bootstrap-safe.

It found, and these are now fixed and mutation-checked:
1. **HIGH:** the refund cancel never fired, because the clover webhook payload has no `charge.invoice`. The charge is now re-read through the SDK, whose requests are pinned to an older API version that includes it.
2. **MEDIUM:** "already cancelled" was decided by error text. It is now decided by `Subscription.retrieve().status`.
3. **MEDIUM:** a held user's checkout returned a 500. `except HTTPException: raise` fixes this; the old "already subscribed" 400 had the same bug.
4. **MEDIUM:** the `prevented` status (refunded before it became a chargeback) is now resolved, per the founder's refund rule.
5. **The 22 older tests:** mocked sessions with fixed result sequences. A `tests/conftest.py` default says nobody is held, and `test_payment_hold.py` opts out of it and uses a real session.

**Deferred (LOW):**
- The Compare UI shows its generic failure text for the hold 403.
- A cached comparison is also refused while held. This is accepted: there is no new spend, but it is a read that is now blocked.

**Deploy safety:** `entrypoint.sh` aborts startup in production if `alembic upgrade` fails, so Railway keeps the old build. A missing table cannot turn into every check failing.

**Out of scope, flagged by the verifier:** `handle_invoice_paid` reads `invoice.subscription` from the clover webhook payload, which removed it. Subscription renewals may not be processed. Investigate next.

Unit suite: 4,627 passed.
