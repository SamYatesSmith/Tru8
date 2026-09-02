# Should the claim field be the front door? — scoped review (2026-09-01)

> Founder's question, verbatim: *"Should the ENTRY to the site be the claim
> field? Should I finally realise that THIS IS A SEARCH ENGINE. One way or
> another… it looks more and more like a tailored search engine."*
> Status: **REVIEW — nothing built.** Every fact below was read from code or
> the register today, not from memory. Decision owed by the founder (§7).

---

## 0. The answer, short

**Yes to the claim field as the front door. No to calling it a search engine.**

The instinct is right about the *mechanism* — the pipeline is literally a
meta-search (Serper → fetch → classify → map) — and wrong about the
*economics*. A search engine builds an index once and answers in 200 ms at
near-zero marginal cost. Tru8 computes every answer on demand, in 60–180 s,
for ~1.2p. That is a **research engine** (Perplexity / Elicit / Consensus /
deep-research shape), and every product of that shape *also* puts a box on
the front door. So the box is the correct entry regardless of the label; the
label "search engine" would set an expectation — instant, free, yes/no — that
the product cannot and should not meet.

Do it in phases. Phase 1 is a day's work, reversible, spends nothing, and can
ship this week without touching the pipeline or the outreach plan. Phase 2 (a
signed-out run) is the one that actually removes the email gate and is gated on
what Phase 1 measures.

---

## 1. Three things "search engine" can mean — and which one is true

| Sense | What it claims | True of Tru8? |
|---|---|---|
| **(a) UI metaphor** | One box on the front page; type, submit, get a page | **Should be.** The hero already says *"Paste a claim or a question"* — and there is nowhere on `/` to paste it (`stitch-hero.tsx:63`). The copy describes a box that is not there. |
| **(b) Economic model** | Index precomputed; serve millions of queries against it; marginal cost ≈ 0; free at the point of use | **No — structurally.** `search.py` has zero caching (launch audit F-02); every query is a billed Serper call on every check; median **1.18p/check** (measured 2026-08-12); 60–180 s. The user-scoped claim-hash cache in `/agent/check` is the only re-use that exists, and it is per-user. |
| **(c) Product identity** | The thing you get back is a ranked list of documents | **Half.** Retrieval is the engine; the *product* is the organised record — tiers, types, elements, states, receipts, signed manifest. A ranked list is what Google already gives; nobody would pay 1.2p for it. |

**What follows:** own (a) in the UI, own the *mechanism* in engineering (the
search-caching layer F-02 already owes is now doubly justified), and keep the
category word as *evidence research*. A "tailored search engine" is exactly
what Perplexity calls itself an "answer engine" to avoid — because "search"
promises Google's speed and price.

---

## 2. What the front door is today (verified)

```
/                      hero copy + [Start a check] + [See a sample record]
  └─ click ──────────► /dashboard/new-check   (middleware: signed-out → back to / with auth modal)
        └─ sign in ──► form: TEXT tab default (since 2026-08-11 audit), URL, IMAGE
              └─ submit ► 1 claim → "focused" (straight through, runner.py:747)
                          ≥2 claims / article → waiting_for_selection (pause)
                    ► ~60–180 s ► /dashboard/check/[id] ► optional public /r/[id]
```

- The **only** no-sign-up evaluation path is the sample record (launch audit F-01).
- `new-check` already accepts `?url=` prefill (`page.tsx:57`); it does **not**
  accept `?text=`.
- Trial = 3 checks (`usage_ledger.py`, `max(3, …)`); Console £20 / 200.
- Input triage (`web/lib/input-triage.ts`) already refuses the inputs that
  reliably fail — it can sit behind a hero box unchanged.
- `/r/` records are crawlable (robots allows `/`) but **not in the sitemap**.

**Every stranger the outreach sends produces will arrive by `/r/[id]`, not `/`.**
The front door they meet is the record page's own call-to-action, and only
*then* `/`. Whatever is decided here applies to that footer as much as the hero.

---

## 3. What the box would change

**For the better**
1. **Copy and page agree.** Today the hero promises a paste target and offers a button.
2. **It fits the best-performing input.** The 2026-08-11 usage audit: typed
   claims produced the best checks, pasted URLs most of the failures. A hero box
   is claim-first by construction; URL autodetect (`triageUrl`) covers the rest.
3. **Single-claim text skips the selection pause** — so a box submission is
   the shortest path through the pipeline that exists.
4. **It is the shape strangers already know** for compute-on-demand research
   products. No category education needed for *how to start*; only for *what
   comes back* — and the sample record carries that.

**Risks — each has a mitigation, none is a reason not to do it**

| Risk | Why it is real here | Mitigation |
|---|---|---|
| **Verdict expectation** (invariant #7, D3 language lock) | A search box is the UI shape where "is this true?" is strongest. Users type a claim and expect yes/no. | Placeholder and the line beneath the box do the work: *"Paste a claim or a question — get the evidence for and against."* Never "check if this is true". Result page unchanged (it is already verdict-free). |
| **Latency expectation** | Boxes imply instant. Tru8 takes 60–180 s. | One honest line under the box (*"a record in about two minutes; you get a permanent link"*) and the existing progress stream. |
| **Cost exposure** (Phase 2 only) | 1.18p × abuse. 1,000 bot checks/day ≈ £12/day. | Turnstile (skill exists), per-IP allowance, a **global daily signed-out budget** with a graceful "sign in to run" fallback, and a **cross-user cache on public records** so a repeated claim costs nothing. |
| **Reopening settled decisions** | D-R4 no splash; single dev-led front door; human-first hero. | None reopened. A box in the existing hero is still one front door, no splash. Developer showcase stays where it is. |
| **Distracting from send week** | Sends start today. | Phase 1 is a hero + form change; it touches no pipeline code and no record. Ship it *because* recipients will click through this week. |

**What it does not change:** the record is the product; the box only commissions it.

---

## 4. Options

### A — The box is the entry, the account is still the gate  *(Phase 1)*
Hero input on `/`. Signed in → `POST` and go to the check. Signed out → auth
modal with the claim **preserved** (`redirect_url=/dashboard/new-check?text=…`;
add `?text=` beside the existing `?url=`). Keep "See a sample record". Same
box in the `/r/` page footer. Triage runs client-side before anything is spent.
- **Scope:** ~1 day. `stitch-hero.tsx`, `new-check/page.tsx` (`?text=`), `/r/`
  footer CTA, analytics events (`hero_submit`, prefilled auth completion).
- **Cost:** nil. **Reversible:** yes.
- **What it tests:** whether a stranger *starts* — box submits vs today's
  button clicks — and whether a claim-in-hand survives the auth modal.
- **What it does not test:** whether they would use it *without* giving an email.

### B — The box runs a real check signed-out  *(Phase 2, gated)*
An anonymous allowance (e.g. 1/day/IP, global cap), result at `/r/[id]`,
claim attaches to the account on sign-up. Cross-user claim-hash cache on
public records so a repeat is free and instant — the first thing that genuinely
*behaves* like a search engine.
- **Scope:** ~1 week. Anonymous check ownership + claim on sign-up, Turnstile,
  rate/budget gate, public-by-default for anonymous runs (state it plainly),
  cache that is not user-scoped, abuse logging.
- **Cost:** bounded by the daily cap you set.
  **Founder question 2026-09-02: "I can't charge for signed-out runs — I don't have the money to sponsor a large number of people's research."**
  Answer logged: correct, B cannot charge and is not meant to; it is a *capped subsidy*, and the cap is the whole mechanism.
  A global daily budget of runs plus a per-IP allowance; past either, the field reads "sign in to keep going". Exposure is a
  number the founder sets, not demand. At the measured ~1.2p real cost per check, 30 signed-out runs/day ≈ £11/month;
  a £10–15/month ceiling is the shape. Tru8 already subsidises research (three free checks per sign-up), so B moves part of
  that spend in front of the email gate rather than adding a new class of spend. The cross-user public-record cache only
  pays off at volume — nothing for the money in the first months. **Recommendation (2026-09-02): do not build until §5 #4's
  numbers show submits dying at the modal; if they do, build with a £10–15/month ceiling.** Founder: "ok" to measuring first.
- **What it tests:** the actual question — *does a stranger use it* — with no
  email in the way. This is the only variant that removes the gate.
- **Gate:** build it when Phase 1 shows people submitting and abandoning at the
  modal, **or** when the first strangers say the sign-in was the friction.

### C — Search existing records first, run a new check on miss  *(Phase 3, at volume)*
The true "engine": the box searches public `/r/` records (title/claim text),
shows hits instantly, offers a fresh run only on miss. Records go in the
sitemap; each is a landing page (the artefact loop from
`audit/2026-08-10_distribution_reality.md`).
- **Why not now:** ~130 checks exist, 104 the founder's. An empty shelf is
  worse than no shelf. Low volume only anyway (mass content penalised 50–90%).
- **When:** once public records are in the hundreds and strangers are making them.

---

## 5. Recommendation

1. **Ship A this week.** It is the cheapest true test of the founder's
   instinct and it fixes a copy/page contradiction on the page every outreach
   recipient will land on next. No pipeline code. No spend.
2. **Write B's gate now, decide later.** Trigger = Phase 1 data or first-stranger
   feedback. Set the daily cap when you build it, not before.
3. **Do not change the category word.** "Evidence research" stays in the
   eyebrow, title, JSON-LD. Internally, yes: treat retrieval as a search engine
   and build the cache F-02 already asked for — it is a margin item whatever
   the front door looks like.
4. **Measure, in this order:** hero submits / visitors → auth completions with
   a claim in hand → checks completed → `/r/` links shared. If the box does not
   move the first number against the button's `start_check_click`, the metaphor
   did not matter and B is not worth building.

---

## 6. What this review does NOT reopen
- D3 verify/verdict language lock — unchanged; the box copy must obey it.
- D-R4 no splash / single front door — a box in the hero is still one door.
- Pricing structure, Console cap, trial of 3 — untouched by A; B adds a
  signed-out allowance *outside* the trial, it does not change the trial.
- The outreach plan — A supports it (better click-through page); B is not a
  prerequisite for any send.

## 7. Founder decisions owed
1. **A: go / no-go this week** (recommended go, after the first sends are out
   the door if you want the current page as the baseline for a day).
2. **B: agree the gate in advance** — what Phase 1 number, or which stranger
   comment, triggers it — so it is a decision made once, not re-litigated.
   *2026-09-02: money question answered under §4B — capped subsidy, £10–15/month ceiling if ever built; gate unchanged.*
3. **Placeholder copy** — proposed: *"Paste a claim or a question"* (box) ·
   *"Get the evidence for and against — a signed record in about two minutes."*
   (beneath). Your call on the exact words; the constraint is no "true/false".

---
*Sources read for this review:* `web/components/marketing/stitch-hero.tsx`,
`web/app/page.tsx`, `web/middleware.ts`, `web/app/dashboard/new-check/page.tsx`,
`web/lib/input-triage.ts`, `web/app/robots.ts`, `web/app/sitemap.ts`,
`backend/app/pipeline/runner.py:743-760`, `backend/app/api/v1/agent.py`
(lookup/cache path), `backend/app/services/usage_ledger.py`,
`audit/2026-08-03_launch_readiness_audit.md` (F-01, F-02),
`audit/OUTREACH.md`, `audit/2026-06-17_repositioning_agreements.md` (via memory).
