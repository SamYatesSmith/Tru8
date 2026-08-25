# OUTREACH — the single source of truth

> **This is the only outreach plan. Its predecessors are in `audit/_archive/`
> and git history; do not resurrect them.** Edit this file first when anything
> here ships, changes, or dies — same protocol as `OPEN_WORK.md`.
> Written 2026-08-11. Methods behind it: *Do Things That Don't Scale* (Graham),
> *The Mom Test* (Fitzpatrick), Sales Safari (Hoy), the Collison installation.

---

## Why this plan is shaped the way it is — four facts

1. **Tru8 has never been used by a stranger — by literally zero.** 12 accounts
   in five months: two are the founder, the rest family and friends. The one
   "business domain" account previously read as the sole stranger signal is
   **the founder's sister** (corrected 2026-08-11 — her feedback has been
   flowing into the product for months). 104 of 129 checks are the founder's;
   the last non-founder check was 2026-07-23; last signup 20 July.
2. **Nobody can search for this category** — it has no name in buyers' heads,
   and the adjacent category with volume (verdicts/fact-checking) is the
   positioning we deliberately reject. Channels that require someone to *name
   the category* are dead on arrival: SEO harvests demand that does not exist,
   registries are shelves.
3. **0→10 users is a list problem, not a channel problem.** Channels need
   volume to test; ten people is noise. First users are recruited by hand, by
   name. Channels become relevant at 10→100, informed by what the first ten say.
4. **The product produces its own demonstration.** A check yields a permanent
   public record (`/r/[id]`) about any claim, in ~3 minutes, for pennies. So we
   never ask for attention — we arrive holding finished work about the
   recipient's own topic.

## The motion, in one paragraph

Find a named person currently working on a specific contested claim. Run the
check ourselves. Read the record. Send it with two sentences and no ask:
*"Saw you were digging into X — I ran it through a tool I've built that
organises the evidence either way. Here's what it found. Curious whether this
is useful to how you work."* Their reply — or silence — is the datum.

## Who — two segments, fifty names

**Primary: journalists and newsletter writers on contested beats** (health,
policy, climate, economics). Fact-gathering is their job, their work is public
and signed, and a finished record about their own beat needs zero category
education. **Wildcard: OSINT / misinformation researchers** — adjacent job,
loud amplifiers when impressed.

A list row is valid only if it names a **current** claim the person is working
on this week. "Covers health" is not a row. The list lives in the untracked
contact map (`audit/2026-06-18_outreach_contact_map.md` — PII, deliberately
never committed), extended with: name · current claim · reach route · tagged
link · sent/replied/useful/signed-up/self-ran.

---

## ⛔ PREREQUISITES — nothing sends until every box is ticked

**A. The founder is checkable.** The first thing a cold recipient does is look
up the sender. That path must be clean, not impressive:
- [ ] One public profile (X/Bluesky and/or LinkedIn) with a one-line bio that
      says what Tru8 is, linking to trueight.com. Real name, real face.
- [ ] Send from `sam@trueight.com` where the route is email — not gmail.
      Verify SPF/DKIM/DMARC pass before the first real send (send one to a
      mailbox you control and check headers).
- [ ] The site answers "who made this" somewhere findable.
- Do **not** manufacture authority — no bought followers, no burst of
  backdated posts. An honest thin profile beats a fake thick one.

**B0. The second touch survives. ✅ SHIPPED 2026-08-11.** The 23 external
checks showed three kill-points before any value was seen: half the news-URL
attempts died at an empty claim-selection gate, homepages/videos/papers ate a
check to learn they were unreadable, and bare topics failed. Fixed: top claim
pre-selected at the gate (one-click default), input triage refuses
never-works inputs at the paste box with recovery guidance (`lib/input-triage.ts`,
12 tests), copy leads claim-first on all surfaces, CLAIM tab is the default.

**B. The record survives a cold viewer.** The `/r/` link is the entire first
impression, opened inside a DM with no context:
- [x] I-06 OG cards reviewed — the link *preview* is the advert. **Verified
      LIVE 2026-08-12, no rebuild needed** (built `0d595b9` 2026-07-02): the
      sample record's card renders in <1s (58KB PNG, claim + neutral stance
      bar + tier mix + sources), and the served page carries correct
      `og:title/description/image` + `twitter:summary_large_image` with
      absolute URLs. Card has no logo, so the 2026-08-10 brand change left
      nothing stale. ⚠️ Remaining is the founder eyeball only: paste one `/r/`
      link into WhatsApp/X/LinkedIn/Slack and check the crop — key content is
      left-anchored, so a square small-preview crop is the thing to look at.
- [x] One cold-viewer pass of a real record: does a stranger grasp in ~10
      seconds what they are looking at and why it beats 30 seconds of
      googling? Fix what fails; ship nothing speculative.
      **RUN 2026-08-12 on the live sample record. Comprehension PASSES** —
      the first screen carries claim, EMPIRICAL badge, the one-line reading
      ("Of 3 elements examined, 2 predominantly supported; 1 with conflicting
      evidence"), element badges and the stance bar; a stranger knows what
      they are looking at without scrolling. **Two defects found, one
      serious:**
      1. ✅ **Renderer freezes: NOT user-facing — CLOSED 2026-08-12.**
         Founder hand-scrolled the sample record on a normal browser: no
         freezes. The 30s stalls were an artefact of the automated CDP
         session (screenshot capture pressure on the compositor), which also
         fits the evidence — JS stayed healthy and example.com captured
         instantly in the same tab. Does not block sends.
      2. ✅ **MAP icon clump — FIXED AND LIVE-VERIFIED 2026-08-12
         (`0758154`).** The layout was never wrong: the DOM had every icon
         correctly placed (verified via getBoundingClientRect) while the
         PIXELS showed one clump — Chrome's compositor left the
         CSS-transitioned SVG `<g>` transforms painted at a stale frame,
         minutes after the transition ended. Nodes now use the SVG
         `transform` attribute (always paints) with an opacity-only
         entrance. Same commit clamps `columnWidth` at zero, killing the
         recorded prod `<rect> negative width` console error (the component
         mounts display:none on mobile where the container measures 0).
         Post-deploy check: icons distributed across all columns and tiers.
      Minor (not send-blocking): evidence titles truncate mid-word with no
      ellipsis ("…: a Burden of"); "SOURCES REVIEWED 14" vs "SOURCES
      ORGANISED 17" is unexplained on the page.
- [x] Cold load speed acceptable on mobile. **Founder-confirmed on a real
      phone 2026-08-12** (page TTFB ~0.4s measured earlier).
- [x] Card crop eyeball: **founder pasted the record into
      WhatsApp/X/LinkedIn/Slack 2026-08-12 — all previews fine.**
      Prerequisite B is CLOSED in full.

**C. Measurement exists. ✅ SHIPPED 2026-08-11.**
- [x] Signup-source attribution: outreach links carry `?src=<tag>`
      (`utm_source` honoured). First-touch capture in localStorage on any
      page (`lib/attribution.ts`), flushed once post-auth to
      `User.signup_source` — write-once, 72h window so an old account cannot
      be re-attributed. Report: `python -m scripts.signup_sources` (mirrors
      `mcp_usage.py`; NULL prints `(unknown)`, never `direct`). 31 tests.
      ✅ Verified in prod 2026-08-12: `alembic_version` = `signup_source`
      AND the `user.signup_source` column exists (checked directly, not
      inferred — note the table is `user`, singular). Verified via
      `railway ssh "<command>"` — command mode works non-interactively, no
      founder-in-the-loop needed for container checks.

**D. Founder decisions. ✅ CLOSED 2026-08-12.**
- [x] Two segments confirmed by founder (journalists/newsletter writers +
      OSINT wildcard).
- [x] Comp approved and BUILT (`9346e71`): when a recipient bites, run
      `railway ssh "python -m scripts.grant_checks --email <them> --checks 10"`.
      **Founder sized it at 10 (2026-08-12, revised down from ~30)** — if
      someone exhausts 10, that is a strong engagement signal and a top-up
      is one command at exactly the right moment.
      Mechanically a bump to `User.credits` (the trial gate reads
      `max(3, credits + total_credits_used)`); refuses subscribers, where a
      grant would be silently inert. Three tests pin the mechanism.
- [x] Smithery listing was already public (resolved 2026-08-11).

**E. Calibration.** 
- [x] ~~Send the business-domain email first.~~ **DISSOLVED 2026-08-11: the
      account is the founder's sister.** There is no stranger to learn from —
      the first cold send in Stage 3 becomes the prototype of the motion.
- [ ] Sales Safari, 3–4 hours, once: read 20–30 pieces of the targets' public
      work and their complaints. Outreach uses **their** words for the job —
      we say "evidence landscape"; they don't. What they say is what converts.
- [ ] The list: 50 valid rows.

## STATE OF PLAY (2026-08-13, end of day — SENDS START TOMORROW MORNING)

**Founder decision: starting in the morning.** Sequence + the definitive send
set live in `OPEN_WORK.md` 📍 HANDOFF. In one line: founder closes prereq A
(Zoho mailbox confirm + DKIM TXT — the only DNS gap; MX/SPF/DMARC already
verified live — + one public profile) and says "approved"; agent runs +
grades the McSweeney check, drafts five bespoke notes with tagged links,
delivers a send sheet; founder sends by hand. Send the ORIGINAL records
(`11f54993`, `7a6a4b91`, `d18d1b02`) — the 2026-08-13 re-runs (two rounds,
under the new mapping gates + recital rule) confirmed the originals are the
right artefacts and that the remaining weaknesses are echo (NHS class) and
rebuttal-retrieval (Scotland/dairy class), both recorded as pipeline work,
both deliberately parked until strangers exist.

## THIRD RE-GRADE 2026-08-21 (post quality package A/B/C — echo gate, support floor, strict ties, claimant arming)
| Record | Re-run check | Grade | Movement |
|---|---|---|---|
| Wildfire | `fa08cff7-ed8c-470e-9767-8ea0d51e4579` | **A−** | Holds disputed 2/2; Ridley tweet correctly `context` as claim-recital. Russia/GWIS crux no longer named in uncertainty — the ORIGINAL `d18d1b02` names it, so send the original. |
| NHS 29% | `cad4c621-3ca8-46f4-ae73-c403bfce1a9a` | **B+** | Echo gate fired on all 3 elements: 4 press derivatives of NHS England's release scoped to context, supports 7→1, `sole_domain: england.nhs.uk` receipted. The echo problem is now STATE-BEARING and fixed. Run-variance dropped TTE from the pool, so no provenance note — original `11f54993` (A−) remains the send. |
| Scotland 48p | `5d69fc71-d52c-450a-8625-a5498460a03a` | **B− (up from C+)** | Recital gate armed (subjects: scottish government); Macfarlane's 587 post scoped supports→context on all 3 elements. Modelled-estimate caveat on every element. Still zero challenges, 589 still unretrieved. **SWAP the Tapper send to this record.** |
| Dairy | `48e8c12d-8d4e-4f6a-9a5f-91a599fcc3aa` | **C+ (up from C−), HOLD** | Echo gate scoped 5 derivatives of the trial. New named limit: the same trial surfaces as ~4 distinct primary records (PubMed/OpenAlex/journal) that derivation chains cannot link, so weighted support stays high. Teardown still absent. Not sendable to Gid M-K. |

**Second NHS attempt 2026-08-21 (`7ed3e0ad-b08e-4f50-9197-0cb964c6c17f`, 15p): TTE still
not retrieved — run-variance did not recover the provenance note (and a Reddit comment
counted as support this time). Echo gate fired with receipts again. Verdict: stop
chasing; the ORIGINAL `11f54993` is the send. Question settled, no further re-runs.**

**McSweeney check RUN 2026-08-21 (`6fe1a7e8-c3c8-4a20-a263-fb77080bf6ed`, 15p, grade B):**
the claim splits into two elements that behave differently — aerosol-contribution
`supported` with a conflicting-evidence note, "not climate change" `disputed` on
all challenges (WWA-led) — the exact structure of his factcheck. Known seam,
disclosed in the note: his factcheck entered the pool via a Reddit mirror, not
carbonbrief.org. **ALL FIVE NOTES DRAFTED — send sheet complete at
`audit/2026-08-21_send_sheet.md` (untracked, privacy rule). Prereq A CLOSED
2026-08-21: DKIM/SPF/DMARC pass proven on a live send, LinkedIn headline now
names Founder, Tru8 (trueight.com) — verified in browser. Nothing gates the
sends but the founder's hand.**

**Send set after this round: wildfire ORIGINAL `d18d1b02` · NHS ORIGINAL `11f54993` ·
Scotland NEW `5d69fc71-d52c-450a-8625-a5498460a03a` (re-tag Tapper's link) · dairy HOLD.**
Nothing reads `supported` off echoes any more; every scoping carries a receipt.

## STATE OF PLAY (2026-08-12, end of day)

**The list exists: 42 verified rows** (untracked contact map, August section —
4 parallel research agents, every row's piece fetched and byline/date/claim
confirmed; 4 rows independently re-verified). Three dispute clusters where one
record serves several sends. Tags minted per person (`o-<name>`, attribution
charset).

**Four checks run** (~4.8p measured; 60p internal agent-balance transfer),
graded as artefacts for their recipients:
| Claim | Check | Grade | Note |
|---|---|---|---|
| "2026 quietest wildfire year" | `d18d1b02` | **A** | Both elements disputed; Russia-dataset crux named; serves Viglione + Seymour (+ Ridley later) |
| NHS App "29% queue reduction" | `11f54993` | **A−** | Echo detector: 6 of 7 supports derive from 1 original; unpublished-evaluation provenance named. For Heneghan/Jefferson |
| Scotland 48p "lost £22m" | `7a6a4b91` | **C+** | Zero challenges — Macfarlane's published rebuttal missing from pool; fine for Tapper only |
| Full-fat dairy "no weight gain" | `c2bfbb8c` | **C−** | One trial + its echo, uniformly supported; Gid M-K's teardown absent. Do not send as-is |

**RE-GRADED 2026-08-13 after the assertion-evidence gates shipped** (fresh
full-tier re-runs, 45p; design `audit/2026-08-13_assertion_evidence_design.md`
§9b passed on the Trump fixture first). The gates did NOT lift these three,
each for a structural reason now on the register:
| Record | Re-run | Grade | Why unchanged |
|---|---|---|---|
| NHS 29% | `ae8c2e27` | **A− → send the ORIGINAL `11f54993`, not the re-run (re-run grades C+)** | Gates never armed: the claimant (NHS England) is not in the claim's key_entities ("NHS App" is PRODUCT), so recital anchoring has no subject. Run-variance also LOST the A−'s virtues: TTE's own critique flipped context→supports and the unpublished-evaluation uncertainty note vanished. |
| Scotland 48p | `12cc567a` | **C+ (unchanged), Tapper only** | Not a recital claim (the claim is Neidle's, not the Scottish Government's). Macfarlane's actual rebuttal (post 589) STILL absent from the pool; his post 587's distill now carries the critique lines but is mapped `supports`. Zero challenges. |
| Dairy | `c2bfbb8c` re-run `5a32dd70` | **C− (unchanged), HOLD** | `subjects: []` — no PERSON/ORG entity, gates structurally unarmed. One trial + 9 echoes uniformly `supports`; Gid M-K's teardown still not retrieved. |

**SECOND RE-GRADE 2026-08-13 late (post Phase 2 recital prompt rule, 45p):**
| Record | Check | Grade | Movement |
|---|---|---|---|
| NHS 29% | `a8a1e127` | **B−** | Up from the C+ midday run: TTE's critique correctly `context` on all elements, its e3 reasoning names the internal-evaluation provenance. Still below the ORIGINAL `11f54993` (A−): no uncertainty note, and the six press echoes of NHS England's stat still read `supports` — press asserts the number in its own voice, so it is an ECHO problem (originals: 1 / derivatives: 6, annotated but not state-bearing), not a recital one. |
| Scotland 48p | `d1833200` | **C+** | Unchanged. e1 uncertainty now cites its evidence ("modelled assumptions, not official outturn, as noted in ev-49e2…") — marginally better transparency; still zero challenges, Macfarlane's rebuttal still unretrieved. |
| Dairy | `d8547278` | **C−** | Unchanged, structurally out of the gates'/rule's reach: `subjects: []`, and sources report a *finding*, not a claim-being-made — correctly not recital. One trial + echoes; teardown still unretrieved. |

**Conclusion, three-layer:** Trump-class (named claimant + own organ + recitals)
is FIXED. NHS-class needs the ECHO structure to become state-bearing — the
mechanism already measures it (`support_structure.derivation`), it just doesn't
count. Scotland/dairy-class needs RETRIEVAL to fetch the named rebuttal.
Recorded in OPEN_WORK; both remain deliberately unactioned pipeline work.

**⏳ OPEN DECISION (founder):** approve the swap — first five = Heneghan/
Jefferson (send the ORIGINAL `11f54993`), Viglione, Seymour, Tapper (keep
original `7a6a4b91` — today's equal-grade rerun buys nothing worth re-tagging),
McSweeney (one more ~1.5p check needed); Macfarlane + Gid M-K to round two once
their records can carry the rebuttals.

**⚠️ Learned, recorded in OPEN_WORK, not actioned:** Substack/small-site
rebuttals of mainstream claims don't reach the evidence pool — the exact
failure both weak records share. Never send a record to a disputant whose own
rebuttal it missed.

## ADVERSARIAL VERIFICATION ROUND (2026-08-24) — the TTE note was wrong four ways before it was right

Founder-ordered pressure test: three parallel agents verified every claim in
the first send against the recipients' own pages and the LIVE `/r/11f54993`
record. **Four drafter faults fixed in the send sheet:** Jefferson is **Dr,
not Professor**; "OSR referral" escalated their own words ("shared our
concerns with") — now quotes their framing; "maps *every* source" literally
false (filter cascade + caps); the central paragraph described the record's
DATA, not its RENDERED page — the e3 provenance note (unpublished NHS England
evaluation + OSR) renders nowhere on the web page, only in the PDF + JSON, and
per-source derivation tracing does not exist on the page (aggregate flag
only). Rewritten to what a reader sees, plus an honest-seam paragraph (their
piece maps `context`; elements read `supported`; Gaps lens says "WELL
COVERED"). **Rule for every future note: draft from the rendered `/r/` page,
never from the data or grading notes — and verify titles.** Same pass owed on
the other four notes before their send days (all carry a milder "each
source... each part" overstatement).

**Send schedule (founder, 2026-08-24): Day 1 Tue 25 Aug — TTE, Viglione,
Seymour · Day 2 Wed 26 Aug — Tapper, McSweeney.** Reply guard: the 29% is
phone-queuing reduction, never "missed appointments". Product gaps found by
the pass are on the OPEN_WORK register (uncertainty rendering = approved
frontend fix; derivation persistence + gaps-vs-caveats = parked pipeline work).

## ADVERSARIAL VERIFICATION ROUND 2 (2026-08-25) — Viglione + Seymour, both wrong before sending

Same method as the TTE pass. Both notes had send-blocking errors. Both rewritten
in the send sheet (untracked — recipient data). Reasoning kept here.

**Error 1, in both notes: they said the record shows the GWIS/Russia dataset
problem. It does not appear on the page.** That reasoning is held in element
`uncertainty`, which has no frontend surface (the gap found 2026-08-24; the fix
is approved and unbuilt). This is the TTE failure one note later — drafted from
the data, not the rendered page. Worst possible version of it here, because
Viglione co-wrote that dataset analysis and would look for it.

**Error 2, Viglione only: the note said Ridley's tweet was marked as a recital
rather than evidence. The linked record showed the opposite** — `Matt Ridley
(@mattwridley) on X · 01 · challenges`. The tweet making the claim was mapped as
challenging it. The recital behaviour belongs to the re-run, not the original;
the note was written from one record and linked to another.

**Record swapped, reversing the 2026-08-21 decision.** That decision kept the
ORIGINAL `d18d1b02` because it "names the Russia/GWIS crux". It names it only in
`uncertainty`, which does not render — so the original's sole advantage was
invisible to every reader, while the re-run's advantage (Ridley correctly scoped
to context) is visible. Both notes now use the re-run `fa08cff7`.

Trade-off accepted and recorded: the re-run is thinner — 5 of 13 sources bear
directly vs 10 of 14, and it loses the World Weather Attribution study and the
JRC data. For a factchecker, thin is better than visibly wrong.

**Error 3, Seymour: "useful ammunition for your writing" removed.** He is an
avowedly Marxist writer and the claim circulates on the right. Offering
ammunition frames Tru8 as a partisan weapon, which contradicts invariant #7 and
the "organises, doesn't decide" line the Viglione note closes on.

**Also corrected:** "each source's relationship" softened (17 reviewed, 13
organised); the "EFFIS" label removed (the page never carried it); Robert
McSweeney credited as co-author of the factcheck — he is a separate recipient
with a different record, and the two notes must not read as templated.

**Recipient facts verified:** Giuliana Viglione is Associate editor at Carbon
Brief (since Jan 2026, PhD Caltech); Robert McSweeney is Senior science editor;
Seymour's "Welcome to the Pyrocene" (5 Aug, New Statesman) confirmed live.

**Standing rule, now twice-proven: draft from the rendered page, and check the
note is describing the record it actually links to.**

## The cadence

- **5 sends/week for 10 weeks. Every message bespoke.** Each ≈ 20 min: find
  the live claim (10), run + read the check (5; **measured median 1.18p/check,
  full tier ~1.3p** — prod telemetry via `scripts/cost_report.py` 2026-08-12;
  the old ~2–7p estimate was 2–5x high), write the note (5).
- **Never send an unread record**, and send it whatever it shows — choosing
  only agreeable landscapes would breach invariant #7 at the distribution
  layer.
- Replies get Mom-Test questions, not a pitch: "last time you had to pull
  evidence together on a contested claim, what did you actually do?" · "what's
  missing from this that you'd have needed?" Never "would you pay?" — watch
  whether they come back instead.
- **Weekly review, Mondays, four numbers:** sent · replied · said-useful ·
  ran-their-own-check. No dashboard.

## The verdict — effort ceiling, not a calendar

Judge at **50 sends**, not at a date:

| Outcome | Reading | Next |
|---|---|---|
| ≥3 people run their own second check | A segment works | That segment becomes the 10→100 channel test: one channel, 30 days, kill condition written in advance |
| Replies but "nice, wouldn't use it" | List right, record doesn't land | Fix the record from their words; re-run 25 sends |
| Silence (<10 replies) | Wrong list or wrong segment | Re-segment; the Safari notes say where |

Every outcome is worth more than ten lukewarm signups.

## What this plan deliberately does NOT do

- **No community broadcast** unless the founder already has standing somewhere
  claims are argued (open question — answering it changes nothing above, it
  only adds a supplementary lane).
- **No automation, no templates, no volume.** Mass/automated content is
  penalised 50–90% and manipulated AI-visibility is classified as spam. Low
  volume is a requirement of the method, not a limitation.
- **The agent/MCP channel stays passive.** It is built, listed and paid for;
  one worked example when time allows. It validates integration demand, not
  whether a human values the report — which is the question this plan exists
  to answer.
- **No SEO investment.** The weekly `tru8-visibility-loop` keeps running
  (free); it is not a growth plan.
- **No pipeline-quality work until strangers exist.** The instinct to improve
  the machine is the most expensive habit on the list.
