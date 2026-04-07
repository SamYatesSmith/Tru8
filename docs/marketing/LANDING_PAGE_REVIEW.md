# Tru8 Landing Page — Review & Solutions

**Date:** 2026-04-08
**Scope:** Home page (`web/app/page.tsx` + the five Stitch marketing components) as of commit `bb8733c`.
**Method:** Synthetic persona objection mining, grounded in `docs/marketing/MARKETING_RESEARCH.md` and `docs/marketing/DEEP_RESEARCH_SYNTHESIS.md`. Every solution is sourced to existing code, verified services, or named real-world prior art.
**Related working files:** `docs/marketing/synthetic-research/2026-04-07_objection-mining_landing-page.md`, `docs/marketing/synthetic-research/2026-04-08_solutions_landing-page.md`.

---

## Executive summary

The landing page has real strengths — the "We organise; you decide" framing lands, the Seeker view is a genuine differentiator, and the six-profession metaphor does useful cognitive work. But three structural problems undermine it:

1. **The video placeholder is broken.** It's the most prominent visual on the page and it doesn't work. Every persona independently flagged it as a credibility hit that made them distrust the rest of the page.
2. **No worked example is visible without signing up.** Asking professional users to bet a credit on an unseen product inverts the normal order of operations.
3. **The Professional tier fights itself.** It's both the *highlighted* tier (the one you most want people to buy) and the *developer* tier (API/MCP access). Those are two different jobs. Journalists and researchers look at it and say "that's for someone else, I'll pick Starter"; developers look at it and say "200 checks/mo is too low for real API work". Nobody is the right buyer for the highlighted tier.

Fixing these three things is the single most impactful intervention possible on the current page. Everything else in this document is refinement.

**Hard requirement:** a working demo must exist on the landing page. This document proposes shipping that in three phases (static preview today → inline live mini-demo next week → video later), using existing infrastructure with no new backend work.

---

## 1. Method

This review is **synthetic persona research**, not real user research. Claude played three personas grounded in the audience segments from `MARKETING_RESEARCH.md` and reacted to the current landing page copy. The output is a backlog of objections, plus sourced solutions for each.

### What synthetic persona research can and cannot do

| Can do | Cannot do |
|---|---|
| Generate hypotheses worth testing on real people | Prove what real users think |
| Surface articulate objections that are easy to miss | Model silent bounces (users who leave without thinking it through in words) |
| Compare framings cheaply at scale | Tell you the conversion impact of any fix |
| Stress-test positioning before paid spend | Replace a 30-minute call with a real journalist / researcher / developer |

Every objection below should be treated as "something worth testing, or fixing if you already agree". None of it is evidence of what real users believe.

---

## 2. The personas

Drawn from the five audience segments in `MARKETING_RESEARCH.md`.

| Name | Segment | Tier fit | Key trait |
|---|---|---|---|
| **Maria** | Investigative journalist (freelance, BIJ-adjacent) | Starter / Professional | Burned once by an AI tool that hallucinated a quote into print. Cares about source provenance, archive longevity, defensibility in court. |
| **Priya** | Policy researcher, Westminster think tank | Professional / Enterprise | Cites Hansard, ONS, GOV.UK daily. Risk-averse — won't put anything in a briefing paper she can't audit. |
| **Dev** | OSINT analyst, Bellingcat-adjacent open collective | Professional (API access) | Power user, methodology over UI. Distrusts black boxes, respects open methodology above all. |

Three other personas (Tom — independent science YouTuber; Aanya — agent developer; Marcus — hostile reviewer) are available for follow-up experiments but were not used in this first round.

---

## 3. What works on the page today

Before the objections, the genuine strengths — these should be protected during any rework:

- **"We organise; you decide."** lands for all three personas. It is the only line on the page that tells skeptical professionals what kind of *partner* this product is. Keep it.
- **The Seeker view** — "every evidence gap, surfaced clearly" — is the most interesting single feature for all three personas. All three independently flagged it as the reason they'd try the product.
- **Auto-archive to Wayback** (currently invisible to the reader but confirmed in `backend/app/services/wayback_archive.py`) is a major selling point inherited from Track F.
- **The three-step process section** is honest about what happens. It doesn't claim "AI fact-check" magic. This honesty is the right philosophical fit for the target audience.
- **The six-profession metaphor** does real cognitive work — it converts "six views of the same data" (boring) into "six roles investigating the same story" (memorable).

---

## 4. Objection mining — the findings

### 4.1 Maria — investigative journalist

**Top objections:**

1. **"Tru8 isn't a fact checker" — okay, but then what is it?** The differentiation is *told*, never *shown*. I can't tell my editor in one sentence what I'd be using.
2. **The video is a placeholder.** I clicked "Platform Walkthrough" and nothing happened. Now I don't trust the rest of the page either.
3. **"Proximity and type" is jargon.** If I have to learn your vocabulary before I trust the output, I won't bother.
4. **"30+ sources" — which sources?** Editors will ask. Hiding the list is the opposite of "no hidden curation".
5. **The carousel auto-advances.** By the time I've read one card, you've moved to the next and I've lost my place.
6. **"The Cartographer" / "The Librarian"** — the whimsy reads as condescending to a 15-year journalist. Works for understanding, actively repels trust.
7. **No bylines, no team, no methodology paper.** Anonymous platform asking me to bet a career-relevant story on its output.
8. **No permanence story on the homepage.** What if my source link rots in 18 months? (Wayback is there in the codebase but invisible in the marketing.)
9. **Pricing per "check" is wrong-shape** for real investigations. 200 checks/mo burns out in two pieces of serious work.
10. **"All source types" appears in Free, Starter, AND Professional** — so what actually changes between tiers?
11. **"Form your view"** assumes I want to *form* a view. Investigative work is hypothesis-driven, not exploratory.
12. **"Start Analysing" — analysing what?** I haven't given it anything. The CTA presumes I'm already mid-task.

**What would have closed the sale:** A 60-second walkthrough showing one real headline → the actual evidence landscape → clicking through. Plus a public source list. Plus a worked example of a Chronologist output on a story she might have covered.

### 4.2 Priya — policy researcher

**Top objections:**

1. **"Government data" is too vague.** Which government? UK only? I work UK-centric but can't tell from the page whether this is for me.
2. **No methodological transparency for the classification itself.** Who decided what counts as "primary"? What's the appeals process if Tru8 misclassifies a primary source as commentary?
3. **No citation export information.** Can I get footnotes? Hansard-style citations? If I have to manually re-cite everything, the time saving evaporates.
4. **No GDPR / data residency information.** A think tank cannot put a research subject's name into a tool whose data location is unknown.
5. **No SOC 2 / ISO 27001 / any compliance signal.** Enterprise says "SLA guarantee" without specifying *what* the SLA is. I can't take this to procurement.
6. **No team / seat plan visible.** I work in a team of 12. Enterprise is "Contact Us" with no starting price — that black box is what stops me even starting the conversation.
7. **"Audit logs" / "version history" are absent from Pro.** Without these I can't show provenance to a client or under FOI.
8. **The Pro tier highlight ("Full API & MCP access") prices me out of my own use case.** Why is the £29 tier built for a developer, not for a researcher?
9. **No mention of versioning the underlying data.** If ONS revises a figure six months from now, does the analysis I cited still work? Does it warn me?

**What works:** The Seeker is the single most interesting feature on the page for her. "We organise; you decide" is *perfect* for a civil-service-adjacent audience — compatible with the impartiality requirement.

**What would have closed the sale:** A one-page methodology document linked from the homepage. A "Team — from £X/seat" tier. A clear sentence about UK hosting and GDPR. An example of a citation export.

### 4.3 Dev — OSINT analyst

**Top objections:**

1. **No GitHub link. No methodology paper. No open classification schema.** OSINT respects transparency above all.
2. **"30+ sources" — list them.** Hiding the list directly contradicts "we organise; you decide".
3. **The video placeholder is doubly damaging** — (a) I can't see the product, (b) the team ships incomplete things.
4. **No reproducibility statement.** If two analysts run the same claim at different times, do they get the same evidence set? Or does the model drift? OSINT requires reproducibility.
5. **No API rate limits or pricing.** The Pro tier says "Full API & MCP access" but doesn't say how much I can hit it.
6. **No webhook support, no batch operations, no "list of completed checks" endpoint visible.** OSINT workflows are programmatic.
7. **No "view a sample report" link.** I should not have to sign up to see what your output looks like.
8. **"Proximity and type"** — define both, on the homepage. Is "proximity" my term (source-to-event distance) or yours (geographic)?
9. **The Seeker is buried as the LAST card in the carousel.** It's the most interesting thing you have. Lead with it.
10. **"Echoing the same original"** — the strongest line on the entire page is hidden inside a Cartographer card description.
11. **£29 for 200 checks burns out fast.** A single OSINT investigation can need 30+ claim checks.
12. **No mention of Wayback / archive integration** even though the codebase has it.

**What would have closed the sale:** A GitHub link with methodology doc + source list. A public sample report. A Pro tier with more headroom or a clear API-rate-limit story.

### 4.4 Cross-cutting findings

These came up for two or three personas independently and are the highest-confidence problems.

| # | Issue | Personas | Confidence |
|---|---|---|---|
| **C1** | The video placeholder damages credibility of the entire page | Maria, Priya, Dev | Very high |
| **C2** | No worked example / sample report visible without signup | Maria, Priya, Dev | Very high |
| **C3** | The 30+ sources are hidden — list never shown | Maria, Priya, Dev | Very high |
| **C4** | "Proximity and type" is undefined jargon | Maria, Priya, Dev | Very high |
| **C5** | No published methodology / `/methodology` page | Maria, Priya, Dev | Very high |
| **C6** | The Seeker is buried as the last carousel card | Maria, Priya, Dev | Very high |
| **C7** | Carousel auto-advances faster than people read carefully | Maria, Priya | High |
| **C8** | Pricing per check is wrong-shape for serious users | Maria, Dev | High |
| **C9** | "All source types" appears in every tier; Pro tier fights itself | Maria, Priya | High |
| **C10** | No team / seat plan, no Enterprise starting price | Priya | High |
| **C11** | No archive / permanence story on the homepage (despite Wayback existing) | Maria, Dev | High |
| **C12** | No GDPR / hosting / compliance signal | Priya | High |
| **C13** | "The Cartographer / The Librarian" — twee determiner | Maria, Dev | Medium |
| **C14** | "Echoing the same original" — strongest line on the page, hidden | Dev | Medium |
| **C15** | "Form your view" assumes exploratory intent; investigative work is hypothesis-driven | Maria | Medium |
| **C16** | CTA "Start Analysing" presumes the user has a target | Maria | Medium |
| **C17** | No reproducibility statement | Dev | Medium |
| **C18** | No GitHub link / public roadmap | Dev | Low |

---

## 5. THE DEMO — sourced, three-phase

The user requirement is unambiguous: **a demo on the landing page, showing how the product works**. This is the linchpin and directly addresses the two highest-confidence objections (C1 + C2).

### Phase 1 — Static evidence-landscape preview (ships today, 2-4 hours)

**What:** Replace the video placeholder with a screenshot of a real Cartographer view from a real check, plus a "See the full report →" link to that check's public URL. Caption below.

**How:**
1. Pick one production check with a visually rich Cartographer landscape. Capture desktop + mobile screenshots from `/dashboard/check/[id]`.
2. Save to `web/public/demo/cartographer-landscape-{wide,mobile}.png`.
3. Edit `web/components/marketing/stitch-video.tsx` (32 lines of dead placeholder) — replace the `aspect-video` block with a Next.js `<Image priority>` wrapped in `<Link href="/r/{check-id}">`.
4. Caption: `"Real evidence landscape from a real check. Click to explore the full report."`

**Sourced:**
- Public report route exists: `web/app/r/[id]/page.tsx`
- Public-check API exists: `backend/app/api/v1/checks.py:2404` — any completed check is publicly accessible by ID with no auth
- Pattern: Stripe does this on `stripe.com/payments`. Linear does it on `linear.app`. Both use a static product screenshot with a "Try the demo" link.

**Effort:** 2-4 hours (90% is picking the right check + capturing clean screenshots).
**Dependencies:** One completed production check appropriate to show publicly. If none exists, run one with a public news headline.

### Phase 2 — Inline live mini-demo (1-2 days)

**What:** A new landing-page section that fetches a curated public check at SSR time and renders a stripped-down Cartographer view inline on the home page. Click-through to the full `/r/[id]` for the rest of the experience.

**How:**
1. Create `web/components/marketing/stitch-live-demo.tsx` as a server component.
2. Fetch `${NEXT_PUBLIC_API_URL}/api/v1/checks/public/{DEMO_CHECK_ID}?detailed=true` at build time with `next: { revalidate: 3600 }`.
3. `DEMO_CHECK_ID` is a single constant in `web/lib/demo.ts`. Change once, everywhere updates.
4. Component renders three elements stacked:
   - **Header strip:** the demo claim text + a "DEMO — REAL DATA" badge
   - **Mini-Cartographer:** embedded `web/components/evidence-views/cartographer/CartographerView.tsx` with a stripped-down dataset (~8-10 evidence nodes). No filters, no controls.
   - **CTA strip:** "See the full evidence landscape for this claim →" linking to `/r/{DEMO_CHECK_ID}`, plus "Try Tru8 with your own claim" opening the auth modal.
5. Insert into `web/app/page.tsx` between `<StitchHero />` and `<StitchProcess />` — second thing on the page, not below the fold.
6. Fall back to Phase 1's static image if the SSR fetch fails.

**Sourced:**
- Cartographer component already exists: `web/components/evidence-views/cartographer/CartographerView.tsx`. We embed the existing view, we don't build a new one.
- SSR fetch pattern already proven: `web/app/r/[id]/page.tsx:24-42` (`getPublicCheck`). Copy directly.
- Pattern: PostHog embeds a live analytics chart on `posthog.com/product-analytics`. Linear embeds a real interactive board on `linear.app`. Cal.com embeds a working booking form on `cal.com`. All three use their own real product as the landing-page demo.
- **Anti-pattern to avoid:** do NOT iframe `/r/[id]`. Iframes break SSR, SEO, mobile, and serve duplicate Navigation/Footer chrome.

**Effort:** 1-2 days. Most of the work is deciding what to show vs. hide vs. lock behind the click-through.
**Dependencies:** One curated demo check; Phase 1 shipped first as the fallback.

### Phase 3 — Real video walkthrough (deferred)

Track I-15. Not urgent once Phases 1+2 ship because there's a real demo without it. Come back to this when you have product footage worth narrating.

---

## 6. Solutions to the cross-cutting findings, sourced

Each row lists the fix, the concrete files to touch, the source/pattern for the recommendation, and rough effort.

### Tier 1 — Highest-confidence, fix first

| # | Fix | File(s) to touch | Source / pattern | Effort |
|---|---|---|---|---|
| **C1** | Kill video placeholder | `web/components/marketing/stitch-video.tsx` | Folded into demo Phase 1 | 30 min |
| **C2** | Surface a worked example | `web/components/marketing/stitch-hero.tsx:27-29` (add link) | `/r/[id]` route already exists | 5 min |
| **C3** | Public sources page | New `web/app/sources/page.tsx`; data from `backend/app/services/api_adapters/__init__.py:46-83` (27 named adapters) + Serper/Brave/SerpAPI/Fact-Check/YouTube for 30+ | Pattern: OpenAlex publishes its source list publicly | 4-6 hrs |
| **C4** | Define "tier and type" inline (marketing copy uses "proximity" but the codebase uses "tier" per CLAUDE.md:6 — the marketing page is wrong) | `stitch-hero.tsx:27-29`, `stitch-process.tsx:19-24` | Schema: `backend/app/models/check.py`; existing visual: `web/components/evidence-views/librarian/EvidenceHeatmap.tsx` | 1 hr |
| **C5** | `/methodology` page | New `web/app/methodology/page.tsx`; content drawn from `CLAUDE.md` pipeline architecture block + `audit/pipeline-issues/fireside_discussion.md` (locked philosophy doc) | Pattern: PostHog publishes full data model at `posthog.com/docs/product-analytics`. DuckDB publishes query engine internals. | 1 day |
| **C6** | Promote Seeker out of carousel | New `web/components/marketing/stitch-seeker-spotlight.tsx`; insert into `web/app/page.tsx` after `<StitchFeatures />` | Seeker component exists at `web/components/evidence-views/seeker/`; shipped in Track G (commit `a758856`) | 4-6 hrs |

### Tier 2 — Strong signal

| # | Fix | File(s) to touch | Source / pattern | Effort |
|---|---|---|---|---|
| **C7** | Carousel → grid | `stitch-features.tsx` — strip state machine lines 60-91 + absolute positioning 116-178, replace with `grid-cols-1 md:grid-cols-2 lg:grid-cols-3`. Card content 153-176 stays. | Pattern: Vercel, Resend both use static grids on their feature pages | 2-3 hrs |
| **C8** | Add a "Researcher" tier (~£69-99/mo, 1000 checks) | `web/lib/tiers.ts`; backend pattern from Track I-02 commit `d103ce3` | PostHog (5 tiers), Linear (4), Cal.com (5) — dev-tools pricing routinely uses >4 tiers | 1 day |
| **C9** | Split Pro into Researcher + Developer (highlight both) | `web/lib/tiers.ts:15-63`, render 5 cards in `stitch-pricing.tsx`. Pro is currently both "the highlighted tier" AND "the developer tier" — those are two jobs. | Pattern: Stripe highlights two tiers on `stripe.com/pricing` (Startups vs Enterprise); Vercel highlights Pro + Enterprise | 2-3 hrs frontend + Stripe setup |
| **C10** | Show Enterprise starting price (30 min fix) OR add full Team tier (days) | `web/lib/tiers.ts:51-62` — change `price: null` to `price: "from 199"` | Pattern: Notion, Slack, Linear all show "from £X/seat" instead of "Contact Us" | 30 min (quick) or several days (full) |
| **C11** | Wayback line in hero + fourth process step | `stitch-hero.tsx:27-29` append line; `stitch-process.tsx:10-32` add step 04 | Service exists: `backend/app/services/wayback_archive.py` (Track F) | 30 min — 2 hrs |
| **C12** | `/security` page | New `web/app/security/page.tsx`; existing privacy policy at `web/app/privacy-policy/page.tsx` to link from | Pattern: `resend.com/legal/security` is the cleanest minimum-viable example | 2-4 hrs |

### Tier 3 — Lower priority, quick wins

| # | Fix | File(s) to touch | Source / pattern | Effort |
|---|---|---|---|---|
| **C13** | Drop "The" from profession names | `stitch-features.tsx:13-56` — six small edits | CLAUDE.md "Six Profession Views" table already uses bare names | 15 min |
| **C14** | Promote "echoing the same original" to hero subhead | `stitch-hero.tsx:23-26` | Currently buried at `stitch-features.tsx:18-19` | 15 min |
| **C15** | A/B test H1 "Form your view" vs "Test the claim" — defer | `stitch-hero.tsx:23-26` + PostHog feature flags | PostHog already on Tier 0 list per `DEEP_RESEARCH_SYNTHESIS.md:135-145` | 1-2 hrs setup, 2 weeks runtime |
| **C16** | CTA copy | `stitch-hero.tsx:35` — "Start Analysing" → "Try a headline" | Pattern: Linear "Start building", Vercel "Start Deploying" | 5 min |
| **C17** | Reproducibility statement | Methodology page; first verify `temperature=0` in `backend/app/pipeline/relevance_scorer.py` and `backend/app/pipeline/claim_map_analyzer.py` | CLAUDE.md "Critical Invariants" #3 already implies this | 2 hrs |
| **C18** | GitHub link in footer (waits for Track I-07) | `web/components/layout/footer.tsx` | Pattern: Linear's `linear.app/changelog`, Vercel/PostHog use GitHub | 1 hr |

---

## 7. Recommended ship order

A sequence that minimises risk and maximises early signal. Each block can ship independently.

### This week (~half a day total, highest leverage)

1. **Phase 1 of THE DEMO (C1 + C2)** — 2-4 hrs
2. **C13** drop "The" — 15 min
3. **C14** promote "echoing the same original" — 15 min
4. **C16** CTA copy — 5 min
5. **C4** jargon fix — 1 hr
6. **C11** Wayback line — 30 min
7. **C10** quick version (Enterprise starting price) — 30 min

After this block: the page no longer has a broken element, shows a real worked example, fixes the jargon, surfaces the archive story, and unblocks Priya's procurement conversation. Biggest leverage per hour you can ship this project.

### Next week (~1-2 days)

8. **C3** sources page — half a day
9. **C5** methodology page — 1 day (mostly writing; content exists)
10. **C7** carousel → grid — 2-3 hrs
11. **C6** Seeker spotlight section — half a day

### Week 3 (~1-2 days)

12. **C9** split Pro / Developer tiers — 2-3 hrs frontend + Stripe setup
13. **Phase 2 of THE DEMO** (live mini-Cartographer) — 1-2 days
14. **C12** security page — 2-4 hrs
15. **C17** reproducibility statement — 2 hrs

### Deferred until pull from real users

- **C8** new Researcher tier — only when an inbound request asks for it
- **C10 option A** full Team plan — only with a specific team request
- **C15** H1 A/B test — needs PostHog set up AND structural fixes shipped first, or it'll measure noise
- **C18** GitHub link — when Track I-07 (MCP publication) ships
- **Phase 3** real video walkthrough — when Phases 1+2 are no longer sufficient

---

## 8. Assumptions to sanity-check before shipping

These are the things the solutions depend on that I have not personally verified in the codebase or production. Worth one quick check each before committing.

1. **A curated demo check exists in production.** If no completed check is appropriate to show publicly, that's the prerequisite for Phases 1+2 of THE DEMO. Cheapest fix: run one yourself with a public news headline.
2. **Railway hosting region.** Assumed based on `backend/railway.toml` and `web/railway.toml` but the actual region (UK / US / EU) needs Railway dashboard confirmation before the security page can state it accurately.
3. **Stripe products for new tiers.** Track I-03 status in `audit/track-i/PROGRESS.md` says price IDs exist in Stripe test mode but env vars are empty at runtime. C8/C9 depend on this being sorted.
4. **Pipeline determinism.** Solution C17 (reproducibility statement) assumes `temperature=0` on LLM calls. This should be verified in `backend/app/pipeline/relevance_scorer.py` and `backend/app/pipeline/claim_map_analyzer.py` before writing the claim.
5. **Wayback integration is populating archive URLs in production.** Trusting `CLAUDE.md` and memory; worth one quick check on a recent completed check that `archived_url` is populated on Evidence rows.

---

## 9. What this review does not cover

Things that were out of scope here and would need their own pass:

- **Mobile-specific UX.** All personas were imagined on desktop. Mobile has its own set of objections (e.g. the carousel is even worse on mobile, the pricing cards stack badly below 640px). Worth a separate mobile-focused pass.
- **The dashboard / check detail page** (`/dashboard/check/[id]`) — the *product* itself. This review only covers the marketing surface.
- **The developer portal** (`web/app/developers/`) — a different audience with different objections. Worth its own run of objection mining.
- **The Agent Commerce Gateway pitch** — Aanya persona was not used in this round. Would be the right next experiment given how little direct user data exists for that segment.
- **Conversion analytics.** None of this tells you which fix actually moves the needle. Set up PostHog (it's on the Tier 0 list in `DEEP_RESEARCH_SYNTHESIS.md:135-145`) so you can measure.

---

## 10. Honest caveats

- **The personas are stereotypes with your marketing docs grafted on.** They're useful as a backlog generator. They are not evidence.
- **Every objection above is a hypothesis worth testing on real people.** A 30-minute call with one real journalist, one real policy researcher, and one real OSINT analyst would convert about 60% of these hypotheses into knowns at near-zero cost.
- **Don't do the H1 A/B test (C15) yet.** The structural problems (demo, pricing, sources, methodology) will swamp any tagline-level signal. Ship the structural fixes first, then measure.
- **Don't rewrite the hero copy.** "We organise; you decide" worked for all three personas. The problem isn't the slogan; it's everything around the slogan that fails to back it up.
- **Don't change the six-profession metaphor.** The metaphor itself is fine. Only the "The" determiner and the carousel presentation need fixing.

---

## Appendix A — Related working files

- `docs/marketing/MARKETING_RESEARCH.md` — the original audience segmentation + tool stack research
- `docs/marketing/DEEP_RESEARCH_SYNTHESIS.md` — the validated tool stack recommendations and developer-marketing playbook
- `docs/marketing/synthetic-research/2026-04-07_objection-mining_landing-page.md` — the full original objection-mining transcript (longer, more verbatim persona reactions)
- `docs/marketing/synthetic-research/2026-04-08_solutions_landing-page.md` — the full original solutions doc (longer, more implementation detail)

This document consolidates the two synthetic-research files into a single report. Read it alongside the marketing research and deep research docs for the full picture.
