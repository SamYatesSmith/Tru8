# Distribution — what the database actually says (2026-08-10)

**Status: the single most important finding in this document is that Tru8 has
never been used by a stranger.** Not "retention is poor" — no market exposure
has ever happened. Everything about growth, pricing, SEO and registries is
downstream of that, and most of it is speculation about an untested market.

Queried live against production. No personal data is recorded here — the
account list is PII and stays in the database, consistent with the outreach
contact map being deliberately untracked.

---

## The numbers

| | |
|---|---|
| Accounts, all time | **12** |
| Most recent signup | **2026-07-20** (three weeks before this audit) |
| Checks, all time | **129** |
| Checks by the founder | **104** (two of the 12 accounts are the founder) |
| Accounts that ever ran a check | 11 |
| Accounts active on **more than one day** | **3 of 11** |
| Accounts that signed up and ran **zero** checks | 1 |

**Composition of the 12 accounts:** two are the founder, at least two are
family (surname match), the remainder are personal webmail addresses
consistent with friends. **Exactly one account is on a business domain.**

**External check outcomes** (everything except the founder): 25 checks —
19 completed, 3 failed, 3 abandoned at `waiting_for_selection`.

---

## What this does and does not tell us

**It does NOT tell us retention is bad.** Earlier in this session the
one-and-done pattern was read as a retention problem, and a recommendation was
built on it — ten user conversations. That was wrong and is withdrawn. Friends
and family have no need for an evidence-research tool, so their failure to form
a habit is not a signal about the product. A sample of people who signed up as
a favour cannot measure product-market fit in either direction.

**It DOES tell us the market has never been tested.** In roughly five months
live, with pricing set, payments working, six views built, an agent API, an MCP
server and four registry listings, the product has been put in front of
approximately **one** stranger.

**The one genuine signal in the whole database** is that single
business-domain account: it consumed the entire 3-check free trial in one
sitting and never returned. That is one data point, and it is the only one.
Worth one email. Nothing more can be concluded from n=1.

**Secondary observations, low confidence:**
- Nobody hit the paywall and declined. They stopped before or at the trial
  boundary, which is a different failure from "too expensive".
- 3 of 25 external checks failed and 3 more were abandoned at the
  claim-selection gate. The gate is a known interaction cost (article mode
  pauses and asks the user to choose claims). At this sample size it is a hint,
  not a defect — but it is the only friction the data actually shows.

---

## Why the existing visibility plan cannot carry this

`audit/2026-06-27_visibility_plan.md` is sound on its own terms and its on-site
half is essentially complete. But it treats the problem as **visibility**, and
visibility work harvests demand that already exists.

Tru8's category has none. Nobody searches for "evidence landscape" or
"no-verdict claim research". The adjacent queries with real volume are
fact-check queries, and the positioning is **deliberately orthogonal** to those
— we do not issue verdicts (invariant #7, and the repositioning is settled and
locked). That is the right product decision and it is also the reason search
cannot be the primary engine at this stage.

Keep the weekly `tru8-visibility-loop` routine: it is free, it compounds slowly,
and its backlog is already exhausted. **Do not mistake it for a growth plan.**

Registries are the same shape: Smithery, the official MCP registry, PyPI and
Glama are all shelves. A shelf does not generate demand.

---

## Methodology proposed

**The goal is not growth. It is the first ten strangers.** Until someone with
no relationship to the founder runs a check because they wanted the answer,
every other metric is untested.

**1. Attribution first — nothing else is measurable without it.**
With 12 accounts, any channel producing 10 signups is transformative, but only
if it can be identified. Today it cannot: `Check.client` records *how* a check
arrived (web/mcp), never *why the person came*. A signup-source tag surfaced
beside the existing client breakdown is small, and it is engineering work.

**2. One channel, thirty days, with a kill condition written in advance.**
Not five channels at 10% each. "N signups from outside my network by [date], or
this channel is dead." No channel has ever been killed on evidence because no
target was ever set.

**3. The channel to try first: the artefact loop.**
Tru8 has an asset most pre-launch products lack — every check produces a
permanent, public, substantive URL (`/r/[id]`). It is the atomic unit of
distribution and it needs no category education: a person arguing about a claim
immediately understands "here is what supports and challenges it, with
receipts". The method is to find a claim being actively argued in a community
the founder genuinely participates in, run it, and post **the record** into that
argument as a contribution.

Deliberately low volume — two or three a week, human-selected. The prior
research finding stands: mass or automated content is penalised 50–90%, and
manipulated AI-visibility is now classified as spam. Low volume is a
requirement, not a limitation.

**4. Hold the agent channel until a human channel produces something.**
For an agent there is no category to explain, which makes it the compounding
play long-term. But it compounds slowly and would teach us nothing for months.
One worked, copy-pasteable example solving a real agent problem end-to-end is
the right artefact when the time comes — not more documentation.

---

## Split of work

**Engineering (can be picked up by an agent):**
- Signup-source attribution + a report alongside `scripts/mcp_usage.py`.
- Look at the 3 failed external checks and the 3 abandoned at claim-selection;
  decide whether the gate needs work or whether n=6 is too small to act on.
- The agent worked-example, when step 4 is reached.

**Founder only — cannot be delegated, and faking it is what gets penalised:**
- Authentic participation in communities where claims are argued.
- The one email to the business-domain account.
- Choosing which claim to run and where the record belongs.

---

## Correction recorded

This session initially recommended interviewing the existing users, reasoning
from a retention signal. The founder pointed out the accounts were friends and
family; checking the list confirmed it. **The lesson is to establish who is in a
sample before drawing behaviour from it** — 11 rows looked like a cohort and
were not one.
