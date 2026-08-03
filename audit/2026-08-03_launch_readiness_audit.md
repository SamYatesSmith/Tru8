# Launch readiness audit — 2026-08-03

**Question put:** we think we are ready to push this live, spend money and time on
outreach, and start earning. Pressure-test that, the way a professional operator
would for a first-time solo founder.

**Method.** Nothing in this document is taken from an audit doc on trust. Every
claim below was re-derived from one of: the current working tree, the live
production site over HTTP, the production Sentry org, Companies House, or a test
run performed today. Where something could not be verified without an interactive
login (Railway), it is marked UNVERIFIED and not counted either way. Doc-only
claims were treated as leads, not evidence — several turned out to be stale in
both directions.

---

## 1. The short answer

**The product is live and genuinely built. The launch is not blocked by the
pipeline. It is blocked by six things that sit between a stranger and a paid
subscription — and by the fact that you currently cannot measure whether a
subscription makes or loses money.**

The order matters. Spending money on outreach right now would send traffic to a
page whose main demo link is broken, through a funnel you can read, into a product
whose unit cost you cannot. The fix list is short and mostly not code.

One thing to name plainly, because it is the real constraint and it is not a
defect: **production has almost no traffic.** Every Sentry issue in the last 30
days shows `Users: 0`, and total error volume across both projects is roughly 60
events in a month. That is consistent with what the existing docs already say —
distribution is the bottleneck, not the build. The work below is about making sure
the traffic you are about to pay for does not leak.

---

## 2. What is genuinely ready (verified today)

| Area | Evidence |
|---|---|
| Site availability | All 18 public routes return 200; unknown routes correctly 404. Swept over HTTP 2026-08-03. |
| Legal entity | **TRUEIGHT LTD, company number 17090683** — Active, incorporated 13 Mar 2026, registered office 115a Queensway, Petts Wood, Orpington BR5 1DG. Verified at Companies House. Accounts due 13 Dec 2027; confirmation statement due 26 Mar 2027. |
| Legal pages | Substantive, not placeholders (ToS 296 lines, privacy 221, cookie 178, refund 86). Company number, ICO registration (ZC110163), governing law (England & Wales), and an explicit "not VAT-registered" statement all present, sourced from one file (`web/lib/legal.ts`). |
| Email infrastructure | `trueight.com` MX → Zoho (EU). SPF `v=spf1 include:zohomail.eu include:resend.com ~all`. DMARC present at `p=quarantine`. Transactional and inbound mail are both properly set up. |
| Secret hygiene in git | Clean. Scan of all tracked files found no live key. Only `.env.example` files are tracked; `backend/.env` has never been committed. |
| Test suite | 3,055 collected, **2,985 pass / 1 fail / 69 skip** in 85s (run today). The single failure is caused by uncommitted work — see F-03. |
| Error monitoring | Sentry live on both `python-fastapi` and `javascript-nextjs`, and demonstrably capturing real production exceptions. |
| Product analytics | PostHog **is live in production** (key `phc_CdYijMo4…` present in the shipped `app/layout` chunk). Cookieless-first init, so it captures without a consent banner. Funnel taxonomy is well designed — signup, check_submitted, paywall_hit, pricing CTAs, report_viewed, evidence_expanded, export_clicked. |
| Abuse/rate limiting | `slowapi` limiter keyed by API key then IP, Redis-backed outside development. Cost is additionally bounded by the credit ledger. |
| Cost blast radius | `MAX_SELECTED_CLAIMS = 5` enforced at all four call sites. The old "12-claim dashboard hole" is closed. |

This is a real, deployed, legally-constituted business with monitoring and
analytics. That is further than most first launches get.

---

## 3. Findings

Severity is by **effect on revenue**, not by engineering interest.

### F-01 — BLOCKER. The sample report linked from the homepage is dead.

`https://www.trueight.com/r/TRU-8723-1E97` returns **HTTP 200** with the body
`Report Not Found`. Verified twice, over plain HTTP; the string is in the
server-rendered HTML, so this is not a client-side artefact.

That path is `SAMPLE_REPORT_PATH` in `web/lib/marketing.ts`, and it is linked from
**three** conversion surfaces: the homepage hero (`stitch-hero.tsx:74`), the
closing CTA (`stitch-closing-cta.tsx:39`), and the competitor comparison page
(`direct-alternatives.tsx:176`).

Why this is the top item: "See a sample record" is the only way a stranger can
evaluate the product **without signing up**. For a no-verdict evidence tool whose
whole pitch is "look at what comes back", the sample *is* the sales pitch. Every
pound of outreach spend lands on a broken demo.

The 200-instead-of-404 makes it worse in two ways: no uptime monitor will ever
catch it, and search engines will index it as a valid page.

**Fix:** run one good public check, pin its ID, and add a build-time or cron
assertion that `SAMPLE_REPORT_PATH` returns a real report. Separately, make a
missing report return a real 404.

### F-02 — BLOCKER (commercial). You cannot currently tell whether a Console subscription is profitable.

Console is £20/month for 200 checks — **£0.10 of revenue per check** (~$0.128).
Against that:

- `backend/app/core/cost_constants.py` reports `estimated_cost_usd.search = None`.
  Search cost is not computed at all, because per-query counts were never
  instrumented ("result counts, NOT query counts").
- LLM cost is explicitly **partial** — it covers analyzer + classifier + distiller
  only, and excludes extract, the relevance scorer, and the query stage.
- `PRICING_VERSION = "2026-06-15-UNVERIFIED"`. The rate table is self-described as
  placeholders.
- The costing model in `audit/cost_control_plan.md` is dated **2026-04-29**. It
  predates Phase 2 element retrieval (2026-07-27), which took retrieval from one
  synthetic claim-lane query to **a claim lane plus one lane per element**.
- `app/services/search.py` contains **zero** occurrences of cache/Redis. Every
  query is a billed call on every check.

Working the envelope from code constants rather than from the stale doc:

| Lane | Queries/claim | Results/query | Serper credits |
|---|---|---|---|
| Claim lane (`c0`) | 3 | 13 | **2 each** (Serper bills 2 credits for 11–100 results) → 6 |
| Element lanes (≤5) | 2 each = 10 | 5 | 1 each → 10 |
| **Per claim** | **13** | | **16 credits** |
| **Per check (5 claims)** | **65** | | **80 credits** |

At Serper's entry rate (~$1 per 1,000 credits) that is **~$0.08 per check for web
search alone — around 62% of the £0.10 revenue** — before any LLM cost. The
2026-04 model assumed ~2p of search for a 5-claim check; the constants now imply
several times that. Add the previously-modelled ~5p of LLM and a fully-utilised
Console subscriber plausibly costs more than they pay.

Two honest caveats, so this is not overstated. First, that is the **worst case**:
five claims, every lane firing, entry-tier search pricing. Serper drops to ~$0.30
per 1,000 at volume, which restores the margin comfortably. Second, most
subscribers will not use 200 checks. The structural point survives both caveats:
**your heaviest users are your worst margins, and you cannot currently see it
happening.** That is a fine position to launch from and a dangerous one to *scale
spend* from.

**Fix (small):** thread the true per-query count out of `retrieve.py` into
`cost_telemetry`, and set the LLM rate table from the published prices. That turns
an unknown into a dashboard number within a day's work. Do it before you buy
traffic, not after.

### F-03 — HIGH. The working tree is mid-flight, and one test is red because of it.

Uncommitted: `backend/app/utils/query_planner.py` and
`backend/app/pipeline/claim_map_analyzer.py`.

- The query-planner change is **correct and worth keeping**: the method gated on
  `OPENAI_API_KEY` alone, so an empty OpenAI key silently disabled LLM query
  planning pipeline-wide while the primary Google key sat there working. The fix
  gates on both. `self.google_ai_api_key` is confirmed present at
  `query_planner.py:229`.
- It breaks `tests/unit/test_query_planner.py::test_plan_queries_batch_no_api_key`,
  which nulls only `openai_api_key` and asserts `None`. With the fix the real
  Google key is still set, so the call falls through to the no-elements guard and
  returns `[]`. **The test is now wrong, not the code** — it needs to null both
  keys. Confirmed by diffing against `HEAD`.
- The `claim_map_analyzer.py` change is a mapping-prompt rewrite (modality match,
  strength-matching, an explicit "not a scepticism dial" counterweight). Prompt
  changes to the mapper are exactly the class of change the replay bench exists to
  gate. **The bench has not been run.** Expected gate: 135 ok / 2 warn / 1 fail,
  and it needs `docker-compose up -d` first.

You should not be doing outreach with the pipeline in this state, because the
first bug report will arrive against a tree you cannot reproduce.

### F-04 — HIGH. Real production defects, none triaged.

**17 unresolved Sentry issues, zero triaged.** The monitoring works; nobody is
reading it. The ones that matter:

| Issue | What it means |
|---|---|
| `IntegrityError … usage_events_check_id_fkey` (2 events) | **A write to the billing ledger failed.** `usage_event.check_id` is an FK to `check.id`; the insert referenced a check row that did not exist. Whichever direction it failed in, a check was mis-metered — either a debit or a refund went unrecorded. This is the append-only ledger that every entitlement gate sums. |
| `Companies House 401 Unauthorized` (2 issues) | **A production API key is dead.** An evidence source is silently degraded — it fails, gets logged, and the check completes looking normal. |
| `Google AI error: 404` (30 events, one day) | Highest-volume issue by far, on `/checks/stream`. Worth understanding given every primary stage runs on Gemini. |
| `NameError: async_session` on `/checks/{id}/progress` | **Appears already fixed** — current code has the local import at `checks.py:2076` with a comment referencing the 2026-07-21 pool-starvation outage. Left unresolved in Sentry, which is the point. |
| `[KEYWORD DRIFT] Adapter 'GovInfo.gov' is keyword-routed but not registered` | Config drift the code itself warns about. |
| `TypeError: … reading 'getReader'` on `/` | Frontend stream failure on the homepage. |

**⚠️ Correction (same day, after founder challenge).** This finding originally
read "no Sentry alert rule exists: a production error reaches nobody." **That was
wrong** — inferred from the untriaged backlog rather than verified. Alerting works
and the founder receives email on essentially every check. The defect is the
opposite, and worse:

`main.py:381` calls `sentry_sdk.init()` **without passing `integrations=`**, so the
SDK's default set is enabled — including `LoggingIntegration`, whose default
`event_level` is `logging.ERROR`. **Every `logger.error()` in the codebase becomes
an issue and an email. There are 282 of them in `app/`.**

That explains the issue titles above: "Library of Congress all 2 attempts failed",
"Transfermarkt club search failed", "empty HTML tree", "Companies House client
error 401". None are exceptions. They are routine, handled evidence-fetch failures
in a system explicitly built to route around a dead source.

**Fix:** pass an explicit `LoggingIntegration(event_level=logging.CRITICAL)` — real
failures still arrive via the direct `capture_exception` calls in `exceptions.py`
and the ASGI middleware — and demote routine adapter failures from `logger.error`
to `logger.warning`. Then triage the 17 so the backlog means something.

**The consequence is not merely noise.** An inbox that cries wolf 282 different
ways is one where the billing-ledger foreign-key violation goes unread. Which is
exactly what happened.

### F-05 — HIGH. Annual subscribers will be told they have no credits (B2).

Confirmed in code at `backend/app/api/v1/users.py:353`: the endpoint returns
`"creditsRemaining": user.credits` — the legacy counter that resets on the Stripe
**billing period**, which for a £200/year plan fires once a year. A subscriber who
spends 200 checks in month 1 reads `creditsRemaining: 0` for the next eleven
months, and `ResearchButton.tsx` disables Seeker re-search on exactly that value —
while the backend ledger gate would have served the request.

The fix is in the same function: `snapshot` already computes `credits_per_period`
(line 305) and `period_credits_used` (line 304). Return
`max(0, credits_per_period - period_credits_used)`. One line, one test.

Monthly plans are unaffected, which is why the July smoke test missed it. If you
sell a single annual plan before fixing this, that customer hits it.

### F-06 — HIGH (operational security). A live Stripe key is in your dev environment.

`backend/.env` — never committed, correctly gitignored, so **this is not a repo
leak**. But its contents are:

```
ENVIRONMENT=development
STRIPE_SECRET_KEY=sk_live_***
STRIPE_WEBHOOK_SECRET=whsec_***
```

The exposure framing in the older docs undersells this. It is not only that a live
key sits on disk — it is that **your local development environment is wired to
live Stripe**. Any local run, test, or script that touches the payments path acts
on real customers and real money. Clerk is correctly on a test key locally; Stripe
is not.

**Fix:** replace with `sk_test_` / the test webhook secret. Local dev should be
incapable of charging anyone.

### F-07 — MEDIUM. The contact page names a company that does not exist.

`web/app/contact/page.tsx` states **"Company: Tru8 Ltd"** and **"Location: London,
UK"**, with no company number.

The real entity is **Trueight Ltd**, number **17090683**, registered at Petts Wood,
Orpington. The legal pages get this right via `lib/legal.ts`; the contact page was
hand-written and drifted.

Under the Companies Act 2006 disclosure rules a UK company's website must show its
registered name, company number, place of registration, and registered office
address. "Tru8 Ltd, London" is neither correct nor sufficient. It is also the page
a cautious first customer checks before paying.

**Fix:** import `LEGAL` on that page like the others do.

### F-08 — MEDIUM. The refund policy cites the wrong jurisdiction's law.

Section 5 is headed "EU Consumer Rights" and cites the EU Consumer Rights
Directive. You are a UK company, your ToS specify England and Wales, and your
consumers' 14-day cancellation right comes from the **Consumer Contracts
(Information, Cancellation and Additional Charges) Regulations 2013**.

The substance is fine and actually more generous than required, so this is a
citation fix, not a rewrite. But a policy citing the wrong statute is the kind of
thing that undermines a buyer's confidence at exactly the wrong moment.

### F-09 — MEDIUM. The site describes a team you do not have.

The contact page promises "our support team", escalation to "a senior team
member", and staffed hours of Mon–Fri 09:00–17:00 GMT.

You are one person. This matters for three reasons: it is a promise you will
personally have to keep at 9am; it is arguably misleading; and — the part founders
underrate — **solo is an advantage with the researcher buyer you have chosen.**
"Built and supported by one person, reply usually same day" outperforms a fake
support desk with this audience. Rewrite it honestly rather than staffing up to
match the copy.

### F-10 — MEDIUM. No subscription has ever renewed.

Payments were smoke-tested end-to-end in July with a real purchase, so *checkout*
works. **Renewal has never been observed.** The webhook API version
(`2025-09-30.clover`) moved `current_period_start` onto subscription items; the
checkout path re-fetches via the SDK and is fine, but the renewal path is
un-eyeballed. Your first renewal will happen roughly 30 days after your first
subscriber, unattended.

**Fix:** trigger a renewal in Stripe test mode against a test-mode backend and
watch the webhook. An hour now, versus a silently-downgraded paying customer later.

### F-11 — MEDIUM. Duplicated page titles.

`Refund Policy | Tru8 | Tru8`, `Cookie Policy | Tru8 | Tru8`, `Report Not Found |
Tru8 | Tru8` — the page metadata already includes the suffix the layout template
appends. Cosmetic, but it is the text Google shows in results.

### F-12 — DATED RISK. Gemini 2.5 retires 16 October 2026 — 74 days away.

Every primary pipeline stage runs on it, and two stages (`evidence_distiller.py`,
`extract.py` claim synthesis) have **no fallback at all**. This is not a
model-string swap: thinking cannot be disabled on Gemini 3, and a lone
`thinkingBudget` is a hard 400 on 3.x, so every mapping call breaks the day the
string changes unless `google_ai.py:333` gains a `thinking_level` branch in the
same commit.

It does not block launch. It does mean you have a fixed-date engineering
obligation landing in the middle of your first growth push, and Google's own
guidance implies a cost increase. Plan the migration for September, not October.

### UNVERIFIED (needs your Railway login)

- **Database backup policy.** Whether Railway Postgres has automated backups
  enabled, and whether a restore has ever been tested. For a paid product holding
  customer records this is a genuine gap if absent — untested backups are not
  backups.
- Whether the `usage_events` and `client_origin` migrations are at head in
  production (`railway run python -m alembic current`).
- Whether the production `OPENAI_API_KEY` (the fallback) is alive. The local one is
  dead, which removes only the safety net — Google is primary — but the prod state
  was never confirmed.

---

## 4. The operator checklist — what is missing that is not code

These are the items a first-time founder reliably misses. Not defects; absences.

**Money**
- No unit-cost dashboard. See F-02. Until this exists, every growth decision is blind.
- No pricing-vs-cost trigger. Decide *now* what COGS-per-check figure would make you change the plan, so the decision is not made emotionally later.
- Stripe is not funded for refunds/chargebacks (carried over from the July session and still owed).

**Customers**
- No onboarding email. A user signs up, spends 3 free checks, and hears nothing.
- No lifecycle email at all — no trial-exhausted prompt, which is the single highest-intent moment in the funnel and currently silent.
- No cancellation reason capture.
- Support is one address with no ticketing. Fine at ten customers, painful at fifty.

**Trust**
- No status page. When the pipeline is down, users see a spinner and infer the product is broken.
- No uptime monitoring pinging the API health endpoint from outside Railway. If the backend dies at 3am you find out from a customer.
- Sentry alerting exists but is unusable (F-04) — it fires on all 282 `logger.error` sites, so the signal is buried rather than absent.

**Data protection**
- ICO registration is in place. But there is no list of subprocessors (Clerk, Stripe, Railway, Google, OpenAI, Serper, Sentry, PostHog, Zoho, Resend, Cloudflare) and no documented process for a deletion request. The privacy policy promises 30 days; make sure you can actually do it.

**You**
- No decision about what you will do when it does not work in month one. Write down now what "keep going" looks like versus "stop", because that judgement is much harder to make once you are tired and have spent money.

---

## 5. Recommended sequence

**Before spending a single pound on outreach — roughly one focused day**

1. Fix the sample report (F-01) and make missing reports 404.
2. Fix the annual-credits line in `users.py` (F-05).
3. Swap the local Stripe key to test mode (F-06).
4. Point the contact page at `LEGAL` (F-07); fix the refund-policy citation (F-08); rewrite the team copy honestly (F-09).
5. Triage the 17 Sentry issues and add an email alert rule (F-04). Re-key Companies House.
6. Fix the query-planner test, run the replay bench, commit and push the pipeline work (F-03).

**Before scaling spend — the following week**

7. Instrument true search-query counts and set the real LLM rates, so cost-per-check becomes a number you can look at (F-02).
8. Test a renewal in Stripe test mode (F-10).
9. Confirm Railway backups exist and restore one.
10. External uptime monitor on `/api/v1/health/` and on the sample report URL.
11. Two lifecycle emails: welcome, and trial-exhausted.

**September**

12. Gemini 3 migration (F-12), before the October deadline collides with growth work.

---

## 6. The honest summary

You have built more than you think and shipped less than you need to. The pipeline
work of the last six weeks — element retrieval, atomicity, the honesty phases — is
serious engineering and it is not what is standing between you and revenue.

What stands between you and revenue is a broken demo link, a funnel with no
lifecycle email, an unread error inbox, and a cost model you cannot see. All of
it is a few days of unglamorous work, and none of it is the kind of work that
feels like progress while you are doing it. Do it anyway, then spend the money.
