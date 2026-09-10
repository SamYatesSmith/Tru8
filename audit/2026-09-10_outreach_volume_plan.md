# Outreach at volume — hundreds of sends, and the marketing kit behind them

**Status:** DRAFT for the founder, 2026-09-10 (written the hour the line was drawn on pipeline work). Nothing here has been sent or built. Decisions marked ▶ are the founder's.
**Sits beside, not instead of:** `audit/OUTREACH.md` (the 50-name bespoke plan — still the highest-signal motion, and its five notes are still the first sends). This document is the second motion: volume, templated, segment-led.
**Founder's words:** *"I need, literally hundreds of people to send emails out to, and associated marketing information. The outreach push is here!!"*

---

## 0. What is already true (verified, not assumed)

| Prerequisite | State | Where proven |
|---|---|---|
| Sending domain `sam@trueight.com`, SPF / DKIM / DMARC pass | ✅ proven on a live send 2026-08-21 | `OUTREACH.md` prereq A |
| Public profile names Founder, Tru8 (trueight.com) | ✅ | same |
| Public record `/r/{id}` + OG card survive a cold viewer, phone-verified | ✅ | prereq B, closed 2026-08-12 |
| Signup attribution `?src=<tag>` → `User.signup_source`, 72 h window | ✅ live | prereq C |
| Comp mechanism (10 free checks on a bite) | ✅ built | prereq D |
| Roster | 126 rows in the untracked contact map; 42 fetch-verified; **none carries a published email** for the five bespoke targets | `audit/2026-06-18_outreach_contact_map.md` |
| Product state at the line | structure 8/10; blind label rate 89.4% (three-run), ≈94–95% adjudicated | `audit/2026-09-10_finding_not_topic_direction.md` §8 |
| Lifecycle emails (welcome, trial-exhausted) | ✅ live | `audit/2026-08-04_funnel_lifecycle_emails_design.md` |

What does **not** exist: a bulk-sending route (Zoho mailbox is a person's mailbox, not a campaign tool), a list of hundreds of addresses, any segment landing page, any one-pager, any email sequence.

## 1. The shape of a volume motion that fits this product

The bespoke plan's core insight survives at volume: **the product produces its own demonstration.** A cold email that *describes* Tru8 competes with every SaaS pitch in the inbox; a cold email that *contains a finished record about a claim the recipient's field is arguing about this month* does not. So volume here does not mean one generic template ×300. It means **one record per segment-topic, sent to everyone in that segment for whom that topic is live** — 10–20 records carrying 300 sends, not 300 bespoke records.

Unit of the motion: **segment × current contested claim → one `/r/` record → one template → N recipients.**

## 2. Segments — ▶ founder picks two to start

Ranked by the 2026-09-07 commercial assessment's buyer research (budget × urgency × public work):

| # | Segment | Why they might reply | The topic hook | Where a list comes from (legitimately) | Est. reachable names |
|---|---|---|---|---|---|
| 1 | **UK small-firm litigators / barristers' clerks** — the assessment's top rank (hallucinated-citation sanctions ~8/day; Clearbrief at $300/user/mo) | Evidence provenance and receipts are their daily problem; a signed record is a work product they can file | A record on a claim from a live judgment or a Law Society / Bar Council guidance row | Law Society "Find a Solicitor", Bar Standards Board register, chambers websites — **firm addresses are corporate subscribers under PECR** (cold B2B email lawful with opt-out and identification) | 300–1,000 |
| 2 | **Journalists and newsletter writers on contested beats** (health, climate, economics, policy) — the bespoke plan's primary | Fact-gathering is the job; a record about their beat needs no category education | The week's contested claim on their beat | Bylines (public), Substack "about" pages, Muck Rack / Roxhill (paid media databases — ▶ founder budget), press-office listings | 200–500 UK; more with US |
| 3 | **Comms / public-affairs teams and think-tank researchers** | They are asked "is this true?" daily and must show their working | A record on a claim in the current news cycle in their sector | Organisation websites (staff pages), LinkedIn Sales Navigator (▶ budget), PRCA / CIPR member lists | 300+ |
| 4 | **OSINT / misinformation researchers** (the wildcard) | Loud amplifiers when impressed; adjacent job | A record on a viral claim they have already debunked, showing the landscape | Public: Bellingcat contributors, university misinformation labs, EU DisinfoLab | 50–100 |
| 5 | **Developers / agent builders** (the MCP, API and Smithery surface already exists) | Different message entirely: "an evidence tool your agent can call, 2p–15p a call, signed output" | Not a record — a working MCP demo | Product Hunt, Hacker News, MCP directories, Discord communities — this is a **launch**, not an email list | n/a |

**Recommendation:** start with **1 and 2**. Segment 1 because it is where the assessment found budget and urgency; segment 2 because the roster, the five notes and the Sales Safari already point there. Segment 5 is a separate launch motion (a post, not emails) and can run in parallel at near-zero cost.

## 3. The list — where hundreds of addresses come from, and the rules

**Rules (unchanged from the bespoke plan, and they bind at volume):**
- **No fabricated or guessed addresses.** An address is used only if it is published by the person or their organisation, or supplied by a licensed data provider. `firstname.lastname@` guessing is out.
- **UK PECR:** unsolicited marketing email to **corporate subscribers** (a firm's or organisation's address, including named individuals at a company address) is lawful with (a) clear sender identity, (b) a valid postal/contact address, (c) an easy opt-out honoured promptly. **Individual subscribers** (personal Gmail/Substack-forwarded addresses) need consent — so segment 2's Substack writers are reached via their *published* professional address or platform DM, not a scraped personal one.
- **GDPR:** legitimate-interests basis for B2B prospecting; keep a suppression list; delete on request; no sensitive data in the roster.
- **The record rule stays:** *never send a record to a disputant whose rebuttal it missed.* At volume this is why the records are about **segment topics**, not about the recipient's own work — the recipient is an *audience* for the topic, not the subject of the record.

**Sources by cost:**
| route | cost | yield | notes |
|---|---|---|---|
| Public registers + organisation sites, hand-built | founder/agent time only | slow, high quality, ~30–50 rows/hour with fetch verification | the roster method, scaled; the agent can build and fetch-verify rows but **cannot publish a personal address it has not seen on a public page** |
| Media database (Muck Rack, Roxhill, Cision) | £££/month | fast for segment 2 | ▶ founder decision; a one-month subscription covers the push |
| Apollo / Hunter / Lusha | £50–£150/month | fast for segments 1 and 3, corporate addresses, verified | ▶ founder decision; the most common route for exactly this motion |
| LinkedIn Sales Navigator | ~£80/month | names + roles, no emails (message via InMail) | pairs with Apollo |

**Target for the first push:** **300 sends** = ~150 segment 1 + ~150 segment 2, across ~12 topic records (6 per segment, 25 recipients each). That is the smallest volume that gives a readable reply rate.

## 4. Sending infrastructure — do not send 300 from a Zoho inbox

- **A separate sending subdomain** (`mail.trueight.com` or `hello@`), its own SPF/DKIM/DMARC, warmed for 2–3 weeks before volume — protects the root domain's reputation and the transactional lifecycle emails.
- **A sequencing tool** (Instantly, Lemlist, Smartlead, Apollo's sequencer, or Mailchimp for the simplest version): per-recipient merge fields (name, segment topic, record link with `?src=<segment>-<topic>`), automatic opt-out footer, bounce handling, reply detection, throttling (≤50/day/mailbox to start).
- **Suppression + consent log:** one sheet, appended on every opt-out and bounce; checked before every batch.
- **Reply routing:** replies land in `sam@trueight.com`; the founder answers within the day (the bespoke plan's datum is the reply, and that does not change).

▶ Founder decisions: tool (my recommendation: Apollo for list + sequencer in one, ~£100/month for the push), subdomain name, daily throttle.

## 5. The marketing kit — what "associated marketing information" is, concretely

Everything below is drafted by the agent from **verified product facts only** (speed 30–60 s measured; pricing Free 3 / Console £20 / API 2p–15p; signed records with a public verify endpoint; six lenses; PDF/CSV/JSON export; MCP on PyPI + Smithery + remote endpoint). No invented statistics, no "trusted by", no logos we do not have.

| # | Asset | Purpose | Form | Owner |
|---|---|---|---|---|
| K1 | **Segment landing pages** — `/for/legal`, `/for/journalists` | Where every email link lands; says the job in their words, shows one record from their field, one CTA (run a check, 3 free) | Next.js page reusing the marketing components (`stitch-hero`, `stitch-record`, `stitch-closing-cta`) | agent builds, founder approves copy |
| K2 | **One-pager PDF per segment** | Attach or link; the thing a recipient forwards to a colleague | 1 page: the problem in their words · what a record contains (annotated screenshot) · what it costs · who made it · how to verify a record | agent drafts from the live `/r/` screenshots |
| K3 | **Email templates** — per segment, 3-touch sequence (day 0 record · day 4 one-line nudge · day 10 different record) | The sends | ≤120 words each, plain text, one link, opt-out line, sender's real name | agent drafts, founder edits voice |
| K4 | **Topic records** — 6 per segment, each on a live contested claim in that field | The demonstration inside every email | run on the deployed build; each pressure-passed (rendered page, every lens, PDF) before it is linked | agent runs + grades (~5p each), founder eyeballs |
| K5 | **Proof page** — `/verify` already exists; add a short "how to check this record is unaltered" section on the record page footer | Answers the litigator's first question | small web change | agent |
| K6 | **Founder profile pack** — LinkedIn headline ✅, a 3-line bio, one headshot, one 60-second explanation video (optional) | The recipient looks the sender up | founder | founder |
| K7 | **Developer launch post** (segment 5) | Hacker News / Product Hunt / MCP directories | one post + the MCP README | agent drafts |
| K8 | **Reply playbook** | What the founder sends back to each of the five reply shapes (curious / sceptical / "how much" / "does it do X" / "not for me") | one page | agent drafts |

## 6. Measurement — what we read, and when we call it

- Sends, deliveries, bounces, opt-outs (tool); **record opens** (PostHog on `/r/`, cookie-consented only); **signups by `src` tag** (`scripts.signup_sources`); **checks run by those users** (`scripts.recent_activity`); replies (inbox).
- Read at **100 sends** (is the route working: bounce < 5 %, no spam-folder signal), and judge at **300 sends** per segment: **reply rate ≥ 3 % or signups ≥ 2 %** keeps the segment; below that, the segment or the message is wrong and we change one variable.
- The bespoke plan's verdict point (50 hand sends) stands separately.

## 7. Sequence, with time and cost

| step | what | time | spend |
|---|---|---|---|
| 0 | Finish the engineering tail (corpus record, push, verify) — running | today | £1.20 (running) |
| 1 | ▶ Founder picks two segments, the list route, the sending tool | 10 min | — |
| 2 | Subdomain + sending tool set up; warm-up starts (runs in the background for 2–3 weeks; the bespoke five go from the warm root domain meanwhile) | 1 h founder + agent | ~£100/month tool |
| 3 | Sales Safari per segment (read 20–30 pieces of their public work; capture their words) | 3–4 h | — |
| 4 | K1 landing pages + K2 one-pagers + K3 templates drafted | 1 day agent | — |
| 5 | K4 topic records: 12 runs, pressure-passed | ½ day | ~60p |
| 6 | List built to 300 rows, fetch/verify, PECR check, suppression sheet | 2–3 days (hand) or 1 day (Apollo) | tool |
| 7 | First 100 sends, read deliverability | day 1 of sending | — |
| 8 | Remaining 200; read at 300 | week 1–2 | — |

**Earliest first volume send: the day the warm-up clears, ~2–3 weeks from setup.** The five bespoke notes do not wait for that.

## 8. What the agent will not do
- Publish, guess or scrape a personal email address; every row cites where the address was seen.
- Put a number on the collateral that is not measured (no "95 % accurate", no "trusted by").
- Send anything. The founder sends, or the tool sends on his account with his approval of each batch.

## 9. ▶ Decisions needed to start
1. Segments (recommend 1 + 2).
2. List route (recommend Apollo for 1 and 3; media database or hand-built for 2).
3. Sending tool + subdomain name.
4. Whether segment 5 (developer launch) runs in parallel.
5. Budget ceiling for the push (tools ~£100–£250/month for one to two months).
