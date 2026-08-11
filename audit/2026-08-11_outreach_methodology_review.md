# Outreach methodology — a critical review of our own plan

**Date:** 2026-08-11
**Status:** REVIEW for founder. Supersedes the channel-first framing in
`2026-08-11_distribution_next_steps.md` §3 for the 0→10 stage; that doc's
channel analysis becomes the 10→100 playbook.
**Sources of method:** Paul Graham "Do Things That Don't Scale"; Rob
Fitzpatrick *The Mom Test*; Gabriel Weinberg *Traction* (Bullseye); Amy Hoy
"Sales Safari"; the Stripe "Collison installation" pattern. Named so they can
be read first-hand rather than taken on my authority.

---

## 1. The critique of what we have written so far

Both distribution docs (10 Aug, 11 Aug this morning) share one framing error:

> **They treat "get the first ten strangers" as a channel-selection problem.
> It is not. 0→10 is a list problem. Channels are the 10→100 problem.**

A channel is a repeatable mechanism you test with volume and a kill condition.
Ten people is not volume — at n=10 every channel metric is noise, and a
"30-day, one-channel, kill condition" experiment on ten targets can kill a good
channel or bless a dead one on luck alone. The established answer for 0→10 is
older and more uncomfortable: **recruit the first users by hand, one at a
time, by name.** Airbnb went door to door. Stripe's founders installed the
product on people's laptops in person. Nobody at that stage had a channel;
they had a list.

Three further faults in our own docs, stated plainly:

1. **No named user.** Eighteen months of documents and not one names WHO the
   first user is. "People arguing about claims" is a behaviour, not a person
   you can put on a list. Segmentation has to come before any outreach.
2. **The kill conditions are calendar-shaped, not effort-shaped.** "N signups
   by [date]" fails if the founder does the work in a burst or not at all.
   At this scale the right ceiling is effort: *50 personalised contacts, then
   judge.*
3. **The agent channel is mislabelled as a first-users play.** An agent
   developer wiring us in validates *integration demand*. It tells us nothing
   about whether a human values the report — the deepest unknown. B stays (it
   is build-once and already paid for), but it cannot substitute for humans.

## 2. The asset we keep under-using

Tru8 has a property most products at this stage do not: **it can produce a
personalised, complete, public demonstration of itself, about the exact thing
a specific person is working on, in ~3 minutes for pennies.**

That makes the strongest known 0→10 motion available to us in an unusually
pure form — the Collison installation, inverted. Instead of "may I show you my
product?", the move is:

> Find a named person currently wrestling with a specific claim. Run the check
> yourself. Send them the `/r/` record with two sentences: *"Saw you were
> digging into X — I ran it through a tool I've built that organises the
> evidence either way. Here's what it found. Curious whether this is useful to
> how you work."*

No ask. No signup required to receive value. The record does the category
education by existing. The reply — or its absence — is the datum. This is the
10 Aug "artefact loop" sharpened from *posting into communities* (broadcast,
needs standing, reads as promotion) to *sending to individuals* (personal,
needs no standing, reads as a favour).

**The one email to the business-domain account is the prototype of this
entire motion.** It should be sent first and its shape reused.

## 3. Who — segment hypotheses, because outreach without a segment is spam

The job Tru8 does: *"I need to know what the evidence actually says about a
contested claim, organised, with receipts, faster than I could assemble it."*
People who have that job professionally, ranked by fit:

| # | Segment | Why they have the job | Reachable? | Pays? |
|---|---|---|---|---|
| 1 | **Freelance / local journalists** on deadline | Fact-gathering IS the job; no researcher support staff | Very — bylines are public, beats are legible, they read messages about their beat | Modest budgets, but £20/mo is a tool-stack price |
| 2 | **Newsletter writers / independent analysts** on contested beats (health, policy, climate, economics) | Credibility is their product; a sourced evidence base is their moat | Very — their work is public and signed | Yes — they already pay for tools |
| 3 | **Policy / think-tank researchers** | Literature-and-evidence sweeps constantly | Public reports, named authors | Employer pays |
| 4 | **OSINT / misinformation researchers** | Adjacent job; strong sharers if impressed | Very visible community | Mixed |
| 5 | **PR / comms rapid-rebuttal** | Need the evidence landscape on claims about their client | Harder to identify from outside | Yes, well |
| 6 | **Debate coaches / academic writing instructors** | Teaching exactly this skill | Seasonal, slower | Rarely |

**Recommendation: pick two — one you can build a list of 25 for from public
work (1 or 2), plus one wildcard (4, because they amplify).** Two segments,
not one, because if the first is wrong we learn it against a contrast rather
than against silence. Not more than two, because 50 personalised contacts is
the founder-hours ceiling.

A journalist or newsletter writer also collapses the "no category demand"
problem: they do not need to know the category exists, because the message
arrives holding a finished example about *their* topic.

## 4. The motion, operationally

**Stage 0 — this week, before any outreach:**
- Ship signup-source attribution (already logged as a requirement). Every
  outreach link carries a tag; untagged = `unknown`, never `direct`.
- Send the business-domain email.
- Flip Smithery to listed (founder toggle — still the cheapest unforced fix).
- Decide the comp: outreach recipients who bite should not hit the 3-check
  wall mid-evaluation. A founder code for ~30 checks costs pence per user at
  API rates (~2–7p/check) and is standard do-things-that-don't-scale.
  **Founder call — it is money, so flagged, not assumed.**

**Stage 1 — Sales Safari (3–4 hours, once, before writing to anyone):**
Read 20–30 pieces of the target segments' public work and the places they
complain (journalism Slacks/Discords are closed, but their Twitter/Bluesky,
newsletters and "how I work" posts are not). Capture *their* words for the
job — the vocabulary for the outreach messages comes from here, not from our
positioning docs. We say "evidence landscape"; they say something else, and
what they say is what converts.

**Stage 2 — the list (2–3 hours):**
50 named people across the two segments. For each: name, what they are
working on RIGHT NOW (a live claim, this week), where to reach them, and the
tagged link they will get. A row is only valid if it names a *current* claim —
"covers health" is not a row.

**Stage 3 — the sends (steady state, ~1.5 h/week):**
- **5 per week, every week, for 10 weeks.** Each: find the claim (10 min),
  run the check (3 min, ~2–7p), write the two-sentence note (5 min).
- Every message bespoke. No template beyond the skeleton in §2. The moment it
  smells templated it becomes spam, and the 50–90% penalty finding from the
  visibility research applies to outreach exactly as it does to content.
- Track per row: sent → replied → said-useful → visited record → signed up →
  ran own check. **The metric that matters at this stage is replies and
  said-useful, not signups** — a reply of "interesting but I'd never use it
  because X" is worth more than a silent signup.

**Stage 4 — the conversations (the actual payload):**
Anyone who replies gets Mom-Test questions, not a pitch:
- "Last time you had to pull together evidence on a contested claim — what
  did you actually do?" (past behaviour, not hypotheticals)
- "What's missing from this record that you'd have needed?"
- Never "would you pay?" — watch whether they *come back* instead; the
  attribution + `Check.client` data answers it honestly.

**Effort ceiling and verdict — not a calendar kill condition:**
After **50 sends**: if fewer than ~10 replies and fewer than ~3 said-useful,
the segments are wrong or the record does not land cold — and the failure
tells us which (silence = wrong list; "nice but no" = product/record gap).
Both are worth more than ten lukewarm signups. If ≥3 people run their own
second check, THAT segment becomes the 10→100 channel test from this
morning's doc, now aimed at a proven audience.

## 5. What each existing workstream becomes under this frame

| Workstream | Role now |
|---|---|
| Agent/MCP channel (B) | Keep as passive infrastructure. One worked example when time allows. **Not the measured motion** — it cannot answer the quality question. |
| Community artefact posting (A as written on 10 Aug) | Only where the founder already has standing (the still-open question). Otherwise superseded by §4's direct sends — same artefact, precise audience, no standing required. |
| `/r/` record polish + OG cards | **Rises in priority.** In the direct motion the record IS the first touch for every single contact. I-06 stops being cosmetic. |
| Claim-selection gate friction | Matters more: outreach recipients who convert will hit it on their first self-run check. |
| SEO / registries | Unchanged: maintain free routine, invest nothing. |
| Weekly review | One look, Mondays: rows sent, replies, said-useful, self-run checks. Four numbers, no dashboard needed. |

## 6. Honest risks

- **This does not scale, by design.** That is the point — it buys the
  information that decides what to scale. Refusing the unscalable stage is how
  the last five months happened.
- **Founder discomfort is the real kill risk.** Cold-messaging named people is
  harder than building features. The effort ceiling (50 sends) exists so the
  judgement is made on completed work, not on week-two discomfort.
- **A journalist may write about the tool rather than use it.** Acceptable
  failure — arguably a channel discovering itself.
- **Choosing claims for named people brushes against neutrality.** The record
  itself stays mechanically honest (invariant #7 protects us); but pick claims
  where we are confident the pipeline performs, without cherry-picking topics
  to flatter the recipient's priors. Send the record whatever it shows —
  sending only agreeable landscapes would be the sycophancy invariant breached
  at the distribution layer instead of the mapping layer.
- **n stays tiny.** Nothing from 50 sends is statistically sound; it is
  qualitative evidence gathered systematically. The 10 Aug lesson holds:
  establish who is in the sample before reading behaviour from it.

## 7. Decisions owed by the founder — nothing here starts without them

1. **Pick the two segments** (§3 — recommendation: journalists + newsletter
   writers, wildcard OSINT).
2. **The standing-community question from this morning** — still open, still
   decides whether community posting supplements the direct motion.
3. **The comp code** (~30 checks for outreach recipients — pence, but money).
4. Send the business-domain email (unchanged, still first).
