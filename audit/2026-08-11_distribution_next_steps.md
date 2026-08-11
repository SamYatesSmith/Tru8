# Distribution — the next genuine steps

**Date:** 2026-08-11
**Status:** REVIEW for founder decision. One question at the end decides the shape.
**Builds on:** `audit/2026-08-10_distribution_reality.md` (the numbers) — and
challenges one of its recommendations, deliberately.

---

## 1. Where we actually are

Twelve accounts in five months. Two are the founder, at least two are family, the
rest are friends. **One** account has ever belonged to a stranger. The product
works end to end — pipeline, payments, agent API, MCP on four registries — and
approximately nobody has used it.

That is not a failure of the product. It is that **the product has never been
put in front of anyone**, and everything we believe about pricing, positioning
and retention is therefore untested.

## 2. The constraint nobody has stated plainly

Tru8 deliberately does not issue verdicts. That is settled, correct, and the
whole differentiator. It also has a distribution consequence that has never been
faced head-on:

> **Nobody can search for what we do, because they do not know the category
> exists. The one adjacent category with real search volume — "is X true",
> fact-checking, verdicts — is precisely the positioning we reject.**

So any channel that depends on someone *naming the category* is dead on arrival.
That single test kills most of the obvious options:

| Channel | Requires the person to… | Verdict |
|---|---|---|
| SEO / content | search for the category by name | **Dead for now.** Backlog already exhausted; it harvests demand that does not exist. |
| Registries (Smithery, MCP, PyPI, Glama) | be shopping the category | **Weak but done.** Shelves, not demand. Keep, don't invest. |
| Communities where claims are argued | nothing — you appear *during* the job | **Live option A.** |
| Agent / MCP ecosystem | nothing — their job IS "ground my agent in evidence" | **Live option B.** |

Everything that works has the same shape: **appear while the person is already
doing the job, rather than wait to be searched for.**

## 3. The two live options, and why I am challenging the recorded plan

`2026-08-10_distribution_reality.md` recommends the human artefact loop and says
to **hold the agent channel** until a human channel produces something. The
reasoning — agents teach us nothing for months — is sound on its own terms. I
think it is wrong on one input, and the input is decisive.

**The binding constraint is not attention or money. It is founder-hours, and
their durability.**

| | A — Artefact loop (human) | B — Agent / MCP |
|---|---|---|
| What it costs | Sustained, authentic participation in communities, **forever**. 2–3 hand-picked records a week, every week. | One worked example, built once. Then it sits there. |
| What it needs from the founder | Credibility that already exists in a place where claims are argued | An afternoon, then nothing |
| Category education | None — a person arguing understands "here is what supports and challenges it" instantly | None — the developer already searches "MCP evidence / grounding / citations" |
| Distribution built? | No. Every post is manual. | **Yes, and paid for already** — hosted endpoint, four registries, per-call pricing |
| What it teaches | **Whether the output is worth returning to** — the deepest unknown we have | Whether developers will wire us in. Says nothing about quality. |
| Failure mode | Founder runs out of time or enthusiasm in week three; half-hearted posting reads as spam and gets penalised | Silence, and it is hard to tell silence from "nobody looked" |

**The honest read:** A is the higher-information channel and B is the more
durable one. A solo, time-poor founder who has spent five months building rather
than distributing is exactly the person for whom "post authentically every week
forever" fails on contact — not through lack of will, but because it is the first
thing to go when a build week appears.

**So I would run both, with different jobs, and measure only one:**

- **B is the distribution bet.** Build once, no ongoing performance required,
  already has its rails paid for. Measured, with a kill condition.
- **A is the learning bet.** Two or three records a fortnight, chosen by hand.
  Its output is **conversations, not signups** — someone telling you the report
  was useful, or telling you what was missing. Do not measure it in users; that
  is not what it is for at this n.

This is a genuine disagreement with the recorded plan, not a rewrite of it. The
founder should overrule it if the answer to §4 is "yes".

## 4. 🔑 The question that decides the shape

**Is there a community where you already participate credibly — where people
argue about claims, and where you posting a record would read as a contribution
rather than an advert?**

- **Yes, and you can name it** → run A as the measured channel. It is the
  higher-information path and the plan of 10 August stands as written.
- **No, or you would have to start from scratch** → run B as the measured
  channel and treat A as opportunistic. Building a reputation in a new community
  is a 3–6 month project *before* it can carry any distribution, and that is not
  a 30-day experiment.

Nothing below depends on this answer except which channel gets the kill
condition.

## 5. Free, undone, and unforced — this week

These cost nothing and are all founder-only:

1. **The Smithery listing is still UNLISTED.** We scored 100/100 and are
   invisible in their search. We are on a shelf with the lights off. One toggle,
   and it is worth more than any score point we chased.
2. **Email the business-domain account.** It burned the entire 3-check trial in
   one sitting on 20 July and never came back. It is the only genuine signal in
   the whole database. One email, asking what they were trying to do — not a
   sales email.
3. **Re-check mcp.so and PulseMCP** (~17 Aug). Both index FROM the official
   registry, which changed on 10 August. Submit manually if still absent.
4. **`tru8-mcp` 1.0.4 to PyPI** — carries the security floor and the hosted route
   to stdio users. Glama grades us **D for maintenance** on release cadence alone.

## 6. Engineering, ordered by leverage

**1. Signup-source attribution.** Logged as a requirement today. Nothing below is
measurable without it, and step §7 is unfalsifiable without it. Small.

**2. The `/r/` public record is the front door, and it should be treated as the
most important surface in the company.** In both channels, the link is what a
stranger meets *first* — before signup, before any explanation, with zero
category understanding. It already requires no authentication, which is right.
What it must do is answer, in about ten seconds and cold: *what am I looking at,
why is it better than the thirty seconds I would have spent on Google, and why
should I believe it?* Concretely: finish I-06 (OG cards — the link preview IS the
advert), cold load speed, and a first-screen that shows the organised landscape
rather than asking the reader to learn a vocabulary. **This is the one piece of
engineering that pays off identically whichever channel wins.**

**3. The claim-selection gate on first run.** Of 25 external checks, 3 failed and
3 were abandoned at `waiting_for_selection` — **24% never reached a result**. For
a cold stranger the gate arrives *before* any value has been shown, and asks them
to make a choice in a vocabulary they have not learned yet. Cheapest honest fix:
pre-select the top-ranked claim so the default path is one click, keeping the
adjust affordance and the receipt. It removes an interaction cost without
removing user control. n=6 is small — but it is the only friction the data shows,
and it sits exactly at the first-impression moment.

**4. One worked agent example** (only if B is the measured channel). A
copy-pasteable, end-to-end solution to a real agent problem — not more
documentation. The docs are already good; what is missing is a reason to reach
for us.

## 7. Measurement — the thing that has never existed

Define the target precisely, because "users" is too vague to falsify:

> **A stranger is an account with no prior relationship to the founder, arriving
> from a tagged source, that runs at least one check.**

- **Target: 10 strangers in 30 days**, from ONE channel.
- **Write the kill condition before starting**, e.g. *"fewer than 3 strangers by
  10 September → this channel is dead and we do not return to it this quarter."*
- **Review one number weekly.** Strangers. Not traffic, not impressions, not
  signups. No channel has ever been killed on evidence here because no target was
  ever set.

## 8. What to stop doing

- **SEO and on-site content.** The backlog is exhausted and the mechanism does
  not fit the category. Keep the free weekly routine; do not mistake it for a plan.
- **More registries.** Four is enough. They are shelves.
- **Pipeline quality work, until someone is actually using it.** This is the
  hardest one to hold to — today, 65p and most of a morning went on a benchmark
  corpus that turned out never to have measured output quality at all, while the
  product still had zero strangers. The instinct to improve the machine is the
  single most expensive habit on the list.

## 9. Honest caveats

- **Ten strangers may say the product is not compelling.** That is the point of
  running it. It is a cheaper answer than another quarter of building.
- **Three free checks then £20/month is a steep ask** for someone with no
  category understanding. Worth considering whether the public record should do
  the selling *before* signup — it can, and that is an argument for §6.2 over
  any pricing change.
- **Do not automate the artefact loop.** Mass or automated content is penalised
  50–90% and manipulated AI-visibility is now classified as spam. Low volume is a
  requirement, not a limitation.
- **n=1 is not a cohort.** The lesson from 10 August stands: establish who is in
  a sample before drawing behaviour from it.
