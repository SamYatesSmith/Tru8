# Launch fix plan — 2026-08-03

Resolution plan for `audit/2026-08-03_launch_readiness_audit.md`. Ordered so that
nothing later is blocked by something earlier being half-done.

**Correction carried into this plan:** the audit said "no Sentry alert rule exists:
a production error reaches nobody." That was wrong — it was inferred from the
untriaged backlog, not verified. Alerting works. The real defect is the opposite
and is diagnosed in W3 below.

---

## W0 — Commit hygiene. Do this FIRST, before any fix work.

**Why first.** The tree currently mixes an unrelated pipeline fix, an unmeasured
prompt rewrite, ~30 untracked eval artefacts and three doc edits. The project runs
trunk-based on `main` with the single commit as the rollback unit
(`feedback_git_workflow`). Starting six fix workstreams on top of that makes every
subsequent diff unreadable and forfeits the ability to roll back any one change.

**Split into four commits, and one deliberate non-commit:**

| # | Contents | Gate |
|---|---|---|
| 1 | `query_planner.py` gate fix **+ the test fix it requires** | Unit tests. Behaviour-neutral wherever both provider keys are set, which prod is. |
| 2 | Untracked eval scripts (`causal_specificity_eval.py`, `f1_recency_eval.py`, `f3_scope_eval.py`, `f4_repetition_sweep.py`, `mapping_budget_sweep.py`, `repro_focused_text.py`, `verify_m1_d1_prod.py`) + `.gitignore` rule for `backend/scripts/.*.json` | None — additive. |
| 3 | Repo hygiene: delete untracked junk (`nul`, `backend/NUL`, `MODULE_RELOADED.txt`, `replay_bench_*.log`, `web/web-dev.log`); assess **tracked** cruft `backend/scorecard_2026-04-24.json`, `backend/test_pdf_v4.py`, `web/CLEANUP_AUTH.md` for deletion | None. |
| 4 | Docs: `.claude/CLAUDE.md`, `audit/OPEN_WORK.md`, the two new audit docs | None. |
| — | **`claim_map_analyzer.py` mapping-prompt reframe — HOLD, do not commit** | Needs replay-bench re-record + re-gold. Its own session. |

**On the held prompt change.** It is a reasoned change (ForceBench-backed) but an
*unmeasured* one, and it invalidates every mapping cassette because the request
body is part of the cassette key. Committing it alongside launch fixes would mean
that if report quality changes next week, you cannot tell which change did it.
Park it on a branch or leave it in the tree, but keep it out of commits 1–4.

**Note on commit 1.** The gate fix only changes behaviour where `OPENAI_API_KEY` is
*absent or empty*. Production has one set, so this is almost certainly a no-op in
prod today — it is a **safety fix for the Gemini migration**, when provider keys
will change. Worth saying so in the commit message.

---

## W1 — The sample report, screenshots, and staleness

### W1a — Produce a report worth showing

Do not hunt for an existing check to salvage. Run new ones deliberately. You are
in `ADMIN_EMAILS`, so checks cost you nothing but upstream API spend (~a few pence
each), and that spend doubles as the cost data W2 needs.

**What makes a great demo report** — the brief to select against:

1. **Genuinely multi-element.** A claim that decomposes into 4–5 real sub-questions, so the Cartographer has a shape and isn't a stub.
2. **Tier spread.** Evidence pulling government/academic primary sources *and* reporting, so the Librarian heatmap is populated rather than one hot cell.
3. **Mixed states.** Not all `supported`. This is the differentiator — a fact-checker returns a verdict, Tru8 returns a landscape. A report where every element is green looks like a rubber stamp and undersells the product.
4. **Temporal spread.** Evidence across several years so the Chronologist is a timeline, not a dot.
5. **Real known unknowns**, so the Seeker has content.
6. **Interesting but not tribal.** A stranger evaluating the tool should be admiring the machinery, not arguing with the topic.
7. **UK-anchored**, which plays to the source stack — GOV.UK, Hansard, ONS, legislation.gov.uk, Companies House.

**Method:** run **three** candidates, then pick on the evidence of what actually
came back — not on which topic sounded best beforehand. Suggested spread:

- A **data claim** with hard official numbers (e.g. UK renewable vs gas generation share; NHS England waiting-list trend). Strong on tier spread and timeline; risks being all-green.
- A **policy-effect claim** where the honest answer is mixed (e.g. whether a named Act achieved a stated aim). Strongest showcase of mixed states + Seeker.
- An **article URL** rather than a bare claim, so the multi-claim selection gate and the Cartographer both get exercised.

**Then:** pin the winner's ID in `web/lib/marketing.ts`, and add an assertion so it
can never silently rot again — a CI or cron check that `SAMPLE_REPORT_PATH` returns
a real report body, not just a 200.

**Separately:** make a missing report return a real **404**, not a 200 with
"Report Not Found". This is what let the current breakage hide.

### W1b — The letterboxing. Diagnosed; here are the numbers.

The container is `aspect-[4/3]` (`stitch-product-preview.tsx:263`) with
`object-contain`. The screenshots are not 4:3 and are not even consistent with each
other:

| Screenshot | Pixels | Ratio | Empty space in a 4:3 box |
|---|---|---|---|
| `librarian-landscape` | 1254 × 454 | **2.76 : 1** | **~52%** |
| `cartographer-network` | 1252 × 562 | **2.23 : 1** | ~40% |
| `chronologist-timeline` | 1248 × 680 | **1.84 : 1** | ~28% |
| `summary-digest` | 1239 × 848 | **1.46 : 1** | ~9% |

`object-contain` is doing exactly what it was asked to: preserving the image and
padding the rest. With a 2.76:1 image in a 1.33:1 box, over half the card is empty
— that is the "widescreen bars" you are seeing. And because all four ratios differ,
**no single container ratio fixes it.**

**Recommended fix — recapture, don't re-crop.** You will be re-screenshotting
anyway once the new sample report exists (W1a). Capture all four at one fixed
viewport, set the container to that ratio, and the bars disappear structurally
rather than being tuned away. A 16:10 viewport (e.g. 1440 × 900) suits these
dashboard views better than 4:3.

**Also found:** the `-full` variants are **byte-identical duplicates** of the
non-full files — all four pairs. Dead weight and a maintenance trap. Consolidate.

**Also worth a look while in there:** `logo.proper.png` (1.5 MB) and
`favicon.proper.png` (1.3 MB) are referenced. Million-pixel PNGs serving as a logo
and a favicon is a real page-weight cost on the page you are about to buy traffic
for.

### W1c — Staleness sweep

Confirmed so far, low severity each:

- **`sitemap.ts` breaks its own rule.** The file's comment explains that `lastmod` is pinned to real content dates so it stays "an honest signal instead of 'everything changed today'" — then uses `new Date()` for `/blog` (line 48) and `/contact` (line 66), which republishes them as changed on every deploy.
- **Duplicated title suffixes** — `Refund Policy | Tru8 | Tru8`, `Cookie Policy | Tru8 | Tru8`. The page metadata already carries the suffix the layout appends.
- **`/compare` carries competitor claims with no "as of" date.** Comparative claims about named third parties should be dated and re-verified periodically — both for accuracy and because an undated comparison ages into a liability.
- **Blog** is two posts, the newest dated March. Not a defect; just note that a stale blog is a weak signal on a page you are about to drive traffic to.

---

## W2 — Cost, with no customers

**The premise is wrong in a useful way: you do not need customers to measure cost.**
Revenue needs customers. Cost does not — it is a property of the pipeline, and it
is *already fully observable today*.

Three steps, in increasing order of effort:

### Step 1 — Read your invoices. Available right now, retrospectively, for free.

Serper, Google AI (and OpenAI) all report actual spend per month. Divide last
month's spend by the number of checks run last month and you have a **real,
ground-truth cost-per-check today**, with no code changes and no customers. Do this
first — it is an afternoon's work at most, and it will either calm the F-02 concern
or confirm it.

This also cross-checks the telemetry, which is the thing the telemetry most needs:
`cost_constants.py` is explicitly self-described as unverified placeholders.

### Step 2 — Make the meter honest. Half a day of code.

- Thread the **true per-query count** out of `retrieve.py` into `cost_telemetry`. The code already admits this is missing ("result counts, NOT query counts"), and it is the single reason `estimated_cost_usd.search` is `None`.
- Set the LLM rate table from the published price lists and drop `UNVERIFIED` from `PRICING_VERSION`.
- Extend token capture to the uncounted stages (extract, relevance scorer, query) — or, if that is bigger than it looks, record the known undercount as an explicit multiplier rather than leaving it silent.

### Step 3 — Generate your own cost data. One hour, a few pounds.

Run 8–10 checks across a deliberate spread — short factual claim, long article,
opinion claim, five-claim article, PDF-heavy claim. That **is** your cost dataset,
and it is better than early customer data because you control the spread. The
checks from W1a count toward this.

### Then make one decision in advance

Write down the cost-per-check figure that would change the plan, **before** you
have a reason to argue with it. Something like: *"if measured cost exceeds 7p per
check, the 200-check Console allowance is revisited."* Deciding the threshold now
means it gets decided on the merits rather than in the middle of a bad week.

**One genuinely reassuring finding:** the 200-check hard cap already *is* your risk
control. Unlike an unmetered plan, your worst case per subscriber is bounded and
known. That is the right structure — you just need the number that fills it in.

---

## W3 — Sentry: the real defect is noise, not silence

**Diagnosis, verified in code.** `main.py:381` calls `sentry_sdk.init()` **without
passing `integrations=`**. The Sentry SDK therefore enables its default set,
including `LoggingIntegration`, whose default `event_level` is `logging.ERROR`.

**Consequence: every `logger.error(...)` in the codebase becomes a Sentry issue and
an email. There are 282 of them in `app/`.**

That is exactly the pattern in your inbox. Look at what the issues actually are:

- "Library of Congress all 2 attempts failed"
- "Transfermarkt club search failed for FIFA: Server error '500'"
- "empty HTML tree for URL …"
- "parsed tree length: 1, wrong data type or not valid HTML"
- "Companies House client error 401 (not retrying)"

**None of these are exceptions.** They are routine, expected, *handled* evidence-
fetch failures. The pipeline is explicitly designed to tolerate a source failing —
that is the entire point of 30+ sources behind a fallback cascade. But each one
currently pages the founder.

**Fix — two parts, both small:**

1. **Pass an explicit `LoggingIntegration` with `event_level=logging.CRITICAL`.** Genuine failures still reach Sentry: `exceptions.py` calls `sentry_sdk.capture_exception` directly (lines 176, 261), the ASGI middleware catches unhandled errors, and `claim_map_analyzer.py` has deliberate `capture_message` calls. Those are the signal, and none of them depend on the logging integration.
2. **Demote the routine adapter/fetch failures from `logger.error` to `logger.warning`.** A source being unavailable is not an error in a system built to route around it. This is the more correct fix and improves the logs regardless of Sentry.

Then triage the existing 17 to resolved/ignored so the backlog means something.

**Consequence worth naming:** right now the alerting is worse than useless — it is
*actively harmful*, because an inbox that cries wolf 282 different ways is an inbox
where you will miss the billing-ledger foreign-key violation. Which is exactly what
happened.

**Still do these two, they are real:** re-key **Companies House** (401 in prod — a
source is silently degraded), and investigate the **`usage_events` FK violation** on
the billing ledger.

---

## W4 — Local dev secrets. Agreed: crucial, and do it early.

Current state: `backend/.env` has `ENVIRONMENT=development` sitting alongside a
live `STRIPE_SECRET_KEY=sk_live_` and a live `whsec_`. Clerk is correctly on
`sk_test_`; Stripe is not. **Any local run touching the payments path acts on real
money.**

**Plan:**

1. Replace `STRIPE_SECRET_KEY` and `STRIPE_WEBHOOK_SECRET` with **test-mode** values, and the price IDs with their test-mode equivalents.
2. Add a **boot-time guard**: refuse to start (or loudly refuse to call Stripe) when `ENVIRONMENT=development` and the Stripe key starts `sk_live_`. This is the part that makes it stay fixed — a config convention decays, an assertion does not.
3. Confirm the live values are on Railway before removing them locally, so nothing is lost.
4. Then take the wider sweep: the remaining free-tier data-source keys deferred at the June rotation.

Item 2 is the one I'd insist on. Without it this recurs the next time someone
copies a `.env` to debug a payment.

---

## W5 — Annual credits: narrower than recorded, and the record should be corrected

Traced every consumer today. **The blast radius is one component, not the dashboard.**

| Surface | Reads | Correct? |
|---|---|---|
| Dashboard hero (`dashboard-hero.tsx:225`) | `periodCreditsUsed` / `creditsPerPeriod` | ✅ already correct |
| New check (`new-check/page.tsx:105`) | `periodCreditsUsed` / `creditsPerPeriod` | ✅ already correct |
| Settings subscription tab | `periodCreditsUsed` / `creditsPerPeriod` | ✅ already correct |
| **Seeker (`SeekerView.tsx:45` → `ResearchButton.tsx:40`)** | **`creditsRemaining`** | ❌ **the only broken reader** |

So `audit/OPEN_WORK.md`'s claim that *"the dashboard credit figure is wrong for the
same reason"* is **stale** — those surfaces were already migrated to the snapshot
fields. Correct that row.

**Mechanism confirmed:** `get_usage_snapshot` is right — it uses
`_monthly_window_start`, so an annual subscriber correctly gets 200/month across
all twelve months. The gate is sound. Only the *display* field is wrong, because
`user.credits` is reset in `handle_invoice_paid` (`payments.py:727`), and for an
annual plan that invoice fires **once a year**.

**Fix — both halves, they are each one line:**

1. `users.py:353` — return `max(0, credits_per_period - period_credits_used)`. Both values are already computed in that function at lines 304–305.
2. `SeekerView.tsx` — read `creditsPerPeriod`/`periodCreditsUsed` from the same payload rather than the legacy field, so the last reader of the legacy counter goes away.

Do both. (1) makes the API self-consistent for any future consumer; (2) removes the
dependency entirely. Add a test with an annual subscription eleven months in — the
case the July smoke test structurally could not catch.

---

## W6 — Contact page and legal copy

Three fixes on one page, plus one elsewhere:

1. **`contact/page.tsx` — import `LEGAL`** like the other legal pages do. It currently hard-codes **"Tru8 Ltd"**, a company that does not exist, at **"London, UK"**, with no company number. The real entity is **TRUEIGHT LTD, 17090683**, registered office **115a Queensway, Petts Wood, Orpington BR5 1DG** (verified at Companies House). Companies Act website disclosure wants registered name, number, place of registration and registered office. This is also the page a cautious first buyer checks before paying.
2. **The team copy.** "Our support team", escalation to "a senior team member", staffed 09:00–17:00. Rewrite honestly. With the researcher buyer you have chosen, *"built and supported by one person; I usually reply the same day"* is a **stronger** sell than a fictional support desk — and it is a promise you can actually keep.
3. **`refund-policy/page.tsx` §5** cites the EU Consumer Rights Directive. You are a UK company under England and Wales law; the right derives from the **Consumer Contracts (Information, Cancellation and Additional Charges) Regulations 2013**. The substance is fine and more generous than required — this is a citation fix.
4. **Add a subprocessor list** to the privacy policy: Clerk, Stripe, Railway, Google, OpenAI, Serper, Sentry, PostHog, Zoho, Resend, Cloudflare. Standard, expected by any business buyer doing diligence, and currently absent.

---

## Suggested order of execution

1. **W0** — commit, so everything after is a clean diff.
2. **W4** — dev secrets. Highest risk-per-minute of anything on the list.
3. **W3** — Sentry noise. Do it early: until the inbox is trustworthy you cannot see the effect of any other change.
4. **W6** — contact/legal. Small, self-contained, no dependencies.
5. **W5** — annual credits. One line each side plus a test.
6. **W1a** — run the candidate checks, pick the sample, pin it, assert it. *This also produces W2's cost data.*
7. **W2 step 1** — read the invoices. Can run in parallel with anything.
8. **W1b** — recapture screenshots from the new report at a fixed ratio; fix the container; drop the duplicates.
9. **W2 steps 2–3** — instrument the meter properly.
10. **W1c** — staleness tidy-up.

Then, as separate sessions: the held mapping-prompt change with a bench re-gold,
and the Gemini migration in September.
