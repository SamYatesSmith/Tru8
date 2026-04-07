# Landing Page — Sourced Solutions

**Date:** 2026-04-08
**Solves:** Issues raised in `2026-04-07_objection-mining_landing-page.md`
**Hard requirement:** A demo on the landing page that shows how the product works.
**Format:** Each solution lists WHAT, HOW (with file paths and existing infrastructure to use), the SOURCE (existing code, prior art, or named pattern), EFFORT, and DEPENDENCIES.

> **Sourced means:** Every recommendation below is grounded in either (a) existing code/infrastructure in this repo, (b) a named external library or service that has been verified to exist, or (c) a named real-world prior art (Linear, PostHog, Stripe, etc.) that has shipped the same pattern. Nothing is invented.

---

## THE DEMO — staged in three phases

The user requirement: **"There must be a demo on the landing page, to show how the product works."** This is the highest priority because it directly fixes objections C1 (video placeholder) and C2 (no worked example), the two strongest signals from the persona research.

The good news: most of the infrastructure already exists. The bad news: a full live-interactive demo is a real piece of work, so I'm proposing this as **three phases shipped in parallel**, with each phase usable in production on its own.

### Phase 1 — Static evidence-landscape preview (ships today, 2-4 hours)

**WHAT:** Replace the video placeholder section with a static, full-bleed screenshot of a real Cartographer view from a real check, plus a "See the full report →" link to that check's public report URL. Below the screenshot, a single line of caption text.

**HOW:**
1. Pick one production check that ran cleanly and has a visually rich Cartographer landscape — political claim, scientific claim, and an OSINT-style claim are the three best categories. Capture screenshots in both desktop and mobile widths from the live `/dashboard/check/[id]` page.
2. Save them to `web/public/demo/cartographer-landscape-{wide,mobile}.png`.
3. Edit `web/components/marketing/stitch-video.tsx` (currently 32 lines, all placeholder) — replace the dark `aspect-video` block with an `<Image>` of the screenshot, wrapped in a `<Link href="/r/{check-id}">`. Use Next.js `<Image>` with `priority` because this is above the fold.
4. Caption: `"Real evidence landscape from a real check. Click to explore the full report."`

**SOURCED:**
- The `/r/[id]` public report route is fully built — `web/app/r/[id]/page.tsx`. No new backend work.
- The public-check API endpoint exists — `backend/app/api/v1/checks.py:2404` `get_public_check`. Any completed check is publicly accessible by ID. No auth.
- Pattern: this is what **Stripe** does on `stripe.com/payments` — a static product screenshot with a "Try the demo" link below. Same pattern used by **Linear** on `linear.app`.

**EFFORT:** 2-4 hours (90% is picking the right check + capturing clean screenshots).
**DEPENDENCIES:** Need at least one production check that's been completed and is appropriate to show publicly (not a real user's private investigation). If none exists yet, run one yourself with a public news headline.

---

### Phase 2 — Inline live mini-demo (1-2 days)

**WHAT:** Build a new landing-page section that fetches a curated public check at SSR time and renders a simplified, embedded version of the Cartographer view inline on the home page. Click-through to the full `/r/[id]` page for the rest of the experience. This is the "demo on the landing page" the user is asking for.

**HOW:**
1. Create a new component `web/components/marketing/stitch-live-demo.tsx`.
2. The component is a server component that fetches `${NEXT_PUBLIC_API_URL}/api/v1/checks/public/{DEMO_CHECK_ID}?detailed=true` at build time (or with `next: { revalidate: 3600 }` for hourly refresh).
3. `DEMO_CHECK_ID` is hardcoded in `web/lib/demo.ts` (one constant). Single source of truth — change it once, everywhere updates.
4. The component renders three things stacked:
   - **Header strip:** the demo claim text, plus a small "DEMO — REAL DATA" badge
   - **Mini-Cartographer:** a stripped-down version of the existing `web/components/evidence-views/cartographer/CartographerView.tsx`. Show the cascade with maybe 8-10 evidence nodes max. No filtering UI, no controls — just the view.
   - **CTA strip:** "See the full evidence landscape for this claim →" linking to `/r/{DEMO_CHECK_ID}`
5. Add a second CTA below: `"Try Tru8 with your own claim"` opening the auth modal.
6. Insert the new component into `web/app/page.tsx` between `<StitchHero />` and `<StitchProcess />` — i.e. it's the *second* thing on the page after the hero, not buried below the fold.
7. Replace the existing `<StitchVideo />` placeholder section with either Phase 1's static image OR a "Watch the 90-second walkthrough" link that scrolls back up to the live demo.

**SOURCED:**
- The Cartographer component already exists — `web/components/evidence-views/cartographer/CartographerView.tsx`. We're not building a new view, we're embedding an existing one with a smaller dataset.
- Server-side fetching of public-check data is already pattern-proven in `web/app/r/[id]/page.tsx:24-42` (`getPublicCheck`). Copy that pattern.
- The `revalidate: 60` cache pattern from `r/[id]/page.tsx:31` keeps it cheap on the home page.
- Pattern: **PostHog** embeds a live product-analytics chart on `posthog.com/product-analytics`. **Linear** embeds an actual interactive Linear board on `linear.app`. **Cal.com** embeds a working booking form on `cal.com`. All three are direct precedents — landing-page interactive demos using their own real product as the demo.
- Anti-pattern to avoid: do NOT use an `<iframe>` of `/r/[id]`. Iframes break SSR, break SEO, break mobile, and serve a duplicate Navigation/Footer. Build a proper component that renders inline.

**EFFORT:** 1-2 days. The bulk of the work is the "stripped-down Cartographer" — deciding what to show vs. what to hide vs. what to lock behind the click-through.

**DEPENDENCIES:**
- One curated demo check must exist and be tagged as the canonical demo (config'd via `DEMO_CHECK_ID`).
- Phase 1 should ship first as the fallback — if the live demo fails to fetch, fall back to the static screenshot.

---

### Phase 3 — Real video walkthrough (deferred — Track I-15)

**WHAT:** A 60-90 second screen recording of you running a real check end-to-end, narrating the six profession views.

**HOW:** Record yourself, host on YouTube (free, supports OG embed) or Mux ($, better quality control), embed in `stitch-video.tsx`. Use Mux Player React or YouTube's privacy-enhanced embed (`youtube-nocookie.com`).

**SOURCED:** Track I-15 in `audit/track-i/PROGRESS.md` is the existing item for this. It's currently marked deferred. Phase 1 and Phase 2 above mean Phase 3 is no longer urgent — you have a demo without it.

**EFFORT:** 1 day for a rough first cut, longer for a polished version.

---

## Solutions to the cross-cutting findings (C1–C18)

Solutions are ordered to match the tiers in the objection-mining doc. Tier-1 fixes come first. Each fix specifies WHAT, HOW with file paths, the SOURCE, EFFORT, and any DEPENDENCIES.

---

### C1 — Kill the video placeholder

**WHAT:** Remove or replace `web/components/marketing/stitch-video.tsx` (currently 32 lines of dead UI).

**HOW:** Solved by Phase 1 of THE DEMO above. Either replace inline with a screenshot + link, or remove the section entirely if Phase 2 lives in the same screen real estate.

**SOURCED:** Component lives at `web/components/marketing/stitch-video.tsx:1-32`. Imported in `web/app/page.tsx:8` and rendered at `web/app/page.tsx:66`.

**EFFORT:** 30 minutes (code), or merged into the Phase 1 work above.

---

### C2 — No worked example, no sample report

**WHAT:** Surface a "See a real evidence landscape" link or embedded view from the home page.

**HOW:** Solved by THE DEMO above (any of the three phases). Tactically, the cheapest version is a single text link in the hero copy: `web/components/marketing/stitch-hero.tsx:27-29` — add a sentence after "We organise. You decide." that says `"See an example →"` linking to `/r/{DEMO_CHECK_ID}`.

**SOURCED:** Public report route already at `web/app/r/[id]/page.tsx`.

**EFFORT:** 5 minutes for the hero link. Hours for the full demo.

---

### C3 — The 30+ sources are hidden

**WHAT:** Create a public `/sources` page that lists every adapter, grouped by category, with name + jurisdiction + brief purpose. Link from the home page hero, the footer, and the methodology page.

**HOW:**
1. Create `web/app/sources/page.tsx` as a static server component.
2. The data lives in a single source file (TypeScript object) — `web/lib/sources.ts`. Hand-curate this from the authoritative list at `backend/app/services/api_adapters/__init__.py:46-83` plus the web-search providers in `backend/app/services/search.py` plus YouTube + Google Fact Check.
3. Group by category matching the marketing copy: Government & Legal · Economic & Financial · Academic & Scientific · Health · Climate & Nature · Sports · Archives & Reference · News & Web Search · Video.
4. For each source: name, link to the source's official site, one-line description, jurisdiction tag (UK / US / Global), licence/terms tag if relevant.
5. Add an explanatory header: "Tru8 retrieves evidence from these sources. We add new ones; we never hide which ones we use."
6. Link from `stitch-hero.tsx` (one line: "30+ sources, fully listed →") and from the footer.

**SOURCED:**
- Adapter list — `backend/app/services/api_adapters/__init__.py:46-83` enumerates 27 named adapters across 9 categories. Add Serper, Brave Search, SerpAPI (web search fallback chain — see `CLAUDE.md` evidence sources block), Google Fact-Check, and YouTube to reach the "30+" claim.
- Pattern: **OpenAlex** publishes its source list at `openalex.org/works`. **Common Crawl** lists its data sources publicly. **Wikipedia's** "reliable sources noticeboard" is the gold standard for "we tell you what we use".
- Content for the page can be drawn directly from the existing `CLAUDE.md` "Evidence Sources" section (lines documenting each provider).

**EFFORT:** 4-6 hours including the list curation (each source needs a one-line description and a link).

**DEPENDENCIES:** None.

---

### C4 — "Proximity and type" is undefined jargon

**WHAT:** Define both terms inline on the home page, and link to a fuller explanation on the methodology page.

**HOW:**
1. Edit `web/components/marketing/stitch-hero.tsx:27-29` — replace `"classifies it by proximity and type"` with `"classifies it by tier (primary, reporting, commentary) and type (data, official, news, analysis, opinion, academic)"`.
2. The Process section's step 2 (`web/components/marketing/stitch-process.tsx:19-24`) already says "Each piece of evidence is classified by proximity and type" — change to mirror.
3. Add a tooltip or hover-card for the longer explanation, OR (simpler) link "How we classify →" to the new methodology page.
4. Note: the codebase uses **"tier"**, not "proximity" — the marketing page has its own vocabulary that doesn't match the product. CLAUDE.md line 6: `"Classify sources by Tier (primary/reporting/commentary) + Type (data/official/news/analysis/opinion/academic)"`. Either change the marketing copy to match the product, or change the product enums to match the marketing — but they have to match. Recommendation: change the marketing copy. The product copy is right; the page is wrong.

**SOURCED:**
- The canonical schema lives in `backend/app/models/check.py` and is documented in `CLAUDE.md:6`.
- The Tier×Type matrix is rendered in `web/components/evidence-views/librarian/EvidenceHeatmap.tsx` — that visual could even be re-used inline as a small inline figure on the home page to show what classification means.

**EFFORT:** 1 hour for the copy change. 2-3 hours if you also build the inline tier×type micro-figure.

**DEPENDENCIES:** None.

---

### C5 — No published methodology

**WHAT:** Create a public `/methodology` page explaining how the pipeline works.

**HOW:**
1. Create `web/app/methodology/page.tsx`.
2. Content is already largely written — pull from `CLAUDE.md` "Pipeline Architecture" block (lines explaining the two-phase pipeline) and `audit/pipeline-issues/fireside_discussion.md` (the canonical philosophy doc that's already locked).
3. Structure: (a) The philosophy ("we organise; you decide" — what it actually means), (b) The pipeline (two phases, plain English description of each stage), (c) The classification schema (tier × type, with the matrix), (d) What we don't do (no verdicts, no source scoring, no hidden curation), (e) Updates and corrections (link to GitHub issues or contact).
4. Visual: include a Mermaid diagram of the pipeline. Next.js supports Mermaid via `mermaid` npm package or static images.
5. Link from: home page hero ("How it works →"), footer, the Process section, and the new sources page.

**SOURCED:**
- `CLAUDE.md` already documents the full pipeline architecture and is the most current source.
- `audit/pipeline-issues/fireside_discussion.md` is the canonical philosophy doc (LOCKED 2026-02-16 per memory).
- Pattern: **PostHog** publishes its full data model + ingestion pipeline at `posthog.com/docs/product-analytics`. **DuckDB** publishes its query engine internals. Both are cited as gold-standard transparency by their respective audiences.
- The canonical principle in the existing code is "Classify, don't score" (CLAUDE.md "Critical Invariants" #6) — make this the headline of the methodology page.

**EFFORT:** 1 day (writing + page build). The content is mostly already written across `CLAUDE.md` and `audit/`.

**DEPENDENCIES:** None.

---

### C6 — The Seeker is buried

**WHAT:** Promote the Seeker out of the carousel into its own dedicated section above or after the six-profession block.

**HOW:**
1. Create a new component `web/components/marketing/stitch-seeker-spotlight.tsx`.
2. Section content: micro-label "Known Unknowns", H2 "What we don't know yet", paragraph explaining the philosophy ("Most fact-tools tell you what's true. We also tell you what's missing. Every gap is a question waiting for evidence."), and a screenshot or live mini-render of the Seeker view from the demo check.
3. Insert into `web/app/page.tsx` as a new section directly after `<StitchFeatures />` and before `<StitchVideo />` (or `<StitchLiveDemo />` after Phase 2).
4. Optionally: when Phase 2 ships, the Seeker spotlight can show the live unknowns ledger from `DEMO_CHECK_ID`.

**SOURCED:**
- The Seeker view component already exists at `web/components/evidence-views/seeker/` — confirmed in directory listing.
- Track G shipped the Seeker (G01: `a758856`) — there's an existing implementation to draw the spotlight content from.
- The "known unknowns" framing is already in CLAUDE.md and the audit docs — re-use the language.

**EFFORT:** 4-6 hours. Most of the work is the visual — content is mostly written.

**DEPENDENCIES:** None.

---

### C7 — Carousel auto-advances and frustrates

**WHAT:** Replace the auto-advancing carousel with a 2×3 grid (or pause-on-first-interaction).

**HOW:**
1. Edit `web/components/marketing/stitch-features.tsx` (199 lines).
2. Remove the carousel state machine: lines 60-67 (`getCircularDiff`), lines 70-91 (state, `useEffect` auto-advance, `goTo`), and the absolutely-positioned card map at lines 116-178.
3. Replace with a simple `grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6` rendering each profession as a static card.
4. Keep the existing card interior content from lines 153-176 — only the wrapper changes.
5. Drop the navigation dots (lines 182-194). Not needed in a grid.

**SOURCED:**
- Existing card content is at `web/components/marketing/stitch-features.tsx:153-176`. Salvage and reuse.
- Pattern: **Vercel's** features page uses a static grid for its product cards. **Resend** does the same on `resend.com`. Both are the same kind of skeptical-developer audience as Tru8's.
- The carousel pattern is appropriate for "rotating testimonials" or "image gallery", not for "feature comparison where users want to scan side-by-side". The persona research confirmed the latter is what Maria/Priya/Dev want.

**EFFORT:** 2-3 hours.

**DEPENDENCIES:** None.

---

### C8 — Pricing is wrong-shape for serious users

**WHAT:** Add a "Heavy Use" / "Pro+" tier between Professional (£29) and Enterprise (custom), or rework Professional itself to include more headroom.

**HOW (option A — add a fifth tier):**
1. Edit `web/lib/tiers.ts` (currently 4 tiers).
2. Add a new `"professional-plus"` or `"researcher"` tier between `"professional"` (£29) and `"enterprise"`. Suggested shape: £69–99/mo, 1000 checks/mo, all features of Pro plus team-friendly bits.
3. Add Stripe price ID env var (`NEXT_PUBLIC_STRIPE_PRICE_ID_RESEARCHER`) and wire through `getTierPriceId()` at line 70.
4. Update `web/components/marketing/stitch-pricing.tsx` to show 5 cards (or change layout from 2×2 to 2×3 / 5-across).
5. Update backend tier logic in `backend/app/api/v1/checks.py` and `payments.py` (per the same pattern Track I-02 used to add Developer).

**HOW (option B — split Professional into Researcher + Developer, drop the highlight from "Professional"):** see C9 below — these solutions naturally combine.

**SOURCED:**
- Existing tier definitions: `web/lib/tiers.ts:15-63`.
- The plumbing for adding tiers was done in Track I-02 (commit `d103ce3` per `audit/track-i/PROGRESS.md:31-41`) — the pattern is documented and the diff for that commit shows where each backend change goes.
- Pricing reference points: **PostHog** has 5 tiers (Free / Totally free / Pay-as-you-go / Self-host / Enterprise). **Linear** has 4 (Free / Standard / Plus / Enterprise). **Cal.com** has 5 (Free / Teams / Organizations / Enterprise / Platform). The pattern of "more than 4 tiers" is normal in dev-tools pricing.

**EFFORT:** 1 day for option A (the env-var + backend change is the slow part). Half a day for the frontend-only part.

**DEPENDENCIES:** Backend tier validation must be updated. Stripe product must be created in the dashboard (I-03 territory).

---

### C9 — "All source types" appears in every tier; Pro tier fights itself

**WHAT:** Restructure the tier feature lists so each tier has visible additive value, AND split the highlighted tier from the developer tier — they shouldn't be the same row.

**HOW:**
1. Edit `web/lib/tiers.ts` feature arrays (lines 22, 33, 45, 57).
2. Make features additive: Free shows everything Free has; Starter shows "Everything in Free, plus..."; Professional shows "Everything in Starter, plus..."; etc. Most pricing pages do this.
3. **Split Pro into two tiers** — drop the API/MCP access from "Professional" and put it in a new "Developer" tier (£29 same price, but featured on a *different* card). The Professional tier's highlight becomes "for researchers and journalists", with the differentiator being headroom + audit logs + export — not API access.
4. Suggested final shape:
   - Free Trial — 3 checks, all views
   - Starter — £7/mo, 40 checks
   - **Professional (highlighted for researchers)** — £29/mo, 200 checks, audit logs, citation export, priority processing, team-share
   - **Developer (highlighted for builders)** — £29/mo, 200 checks, full API & MCP access, webhooks, agent endpoints
   - Enterprise — custom
5. Update `web/components/marketing/stitch-pricing.tsx` to render 5 cards in a 2×3 or 5-across layout.
6. Possibly highlight TWO cards (one per audience), not one — pattern used by Stripe ("for startups" and "for enterprises").

**SOURCED:**
- Tier definitions: `web/lib/tiers.ts:15-63`.
- Pattern of splitting "research user" from "API user": **Stripe** has separate sections for "Payments" and "Connect"; **Twilio** has Voice / SMS / Email all priced separately. **PostHog** distinguishes "Product Analytics" from "Session Replay" pricing.
- Pattern of dual-highlighted tiers: **Vercel** highlights both Pro ($20/mo) and Enterprise on `vercel.com/pricing`.

**EFFORT:** 2-3 hours for the frontend split + tier definitions. Plus the Stripe price ID setup (Track I-03) which is already partly done per `audit/track-i/PROGRESS.md:44-62`.

**DEPENDENCIES:** Stripe product setup for the new "Developer" tier.

---

### C10 — No team / seat plan visible

**WHAT:** Add a "Team" tier (or at minimum surface a starting price for Enterprise so policy researchers can budget).

**HOW (option A — add a Team tier):**
1. Add to `web/lib/tiers.ts`: `"team"` tier between Professional and Enterprise. Suggested shape: from £15/seat/month, minimum 5 seats, includes everything in Professional plus shared workspace, role-based access, team-billing.
2. Backend needs: a `team_id` foreign key on Check (or a simple "shared" flag), team-membership endpoints, and Stripe seat-based price IDs. This is the largest bit of the change.
3. If team functionality isn't backed yet, the lightweight version is: a "Team — coming soon, register interest" card that captures email and tells you who's asking.

**HOW (option B — show Enterprise starting price):**
1. Edit `web/lib/tiers.ts` line 53-62. Change `price: null, period: null` to `price: "from 199", period: "month"` and update the rendering in `stitch-pricing.tsx:109-120` to handle the "from" prefix.
2. This unblocks the procurement conversation without requiring backend work.

**SOURCED:**
- Tier definitions: `web/lib/tiers.ts:51-62`.
- Per the persona research, this is Priya's #1 unblocker. She literally cannot start the procurement conversation without a starting price.
- Pattern: **Notion's** Enterprise tier shows "from $20/user/month". **Slack** shows "from $7.25/user/month". **Linear** shows "from $14/user/month". The "Contact Us" black-box pattern is increasingly seen as a friction tax — the trend is to show a starting price.

**EFFORT:** Option A: several days. Option B: 30 minutes.

**DEPENDENCIES:** Option A needs significant backend work. Option B has none.

**RECOMMENDATION:** Ship option B today; defer option A until you have at least one inbound team request.

---

### C11 — No archive / permanence story on the homepage

**WHAT:** Add one line to the hero or features stating that Tru8 archives every source to the Wayback Machine.

**HOW:**
1. The simplest version: edit `web/components/marketing/stitch-hero.tsx:27-29` and append a sentence: `"Every source is archived to the Wayback Machine — your evidence won't rot."`
2. The richer version: add a 4th step to the Process section (`web/components/marketing/stitch-process.tsx:10-32`) called "04 — Archived" with description "Every source is automatically archived to the Wayback Machine. Your evidence is preserved even if the original disappears."
3. Visual reinforcement: on Librarian view evidence cards, add a small "archived" badge linking to the Wayback URL. (Per CLAUDE.md, evidence cards already show auto-archive links — verify this in `web/components/evidence-views/librarian/`.)

**SOURCED:**
- The Wayback Machine integration already exists — `backend/app/services/wayback_archive.py`. Memory confirms it's been operational since Track F.
- CLAUDE.md "Six Profession Views" → cross-cutting note: "auto-archive links" already mentioned as a Librarian feature.
- Pattern: **Internet Archive itself** prominently advertises "we archive things forever" as a value proposition. This is exactly the same value proposition Tru8 inherits by integrating with Wayback.

**EFFORT:** 30 minutes (hero line) to 2 hours (process step + visual badge).

**DEPENDENCIES:** None — service already exists.

---

### C12 — No GDPR / hosting / compliance signal

**WHAT:** Surface basic compliance information from the homepage (or footer) so policy/healthcare/government users can take the conversation to their procurement team.

**HOW:**
1. Add a footer line: "UK-hosted · GDPR-compliant · See [security](/security)".
2. Create `web/app/security/page.tsx` — a static page covering: hosting region (Railway → check actual region), GDPR posture, data retention (link to existing privacy policy), encryption in transit/at rest, sub-processors (Clerk, Stripe, Anthropic, OpenAI, etc), incident contact email.
3. The privacy policy already exists at `web/app/privacy-policy/page.tsx` — security page can link to it for the legal detail and focus itself on the tech-side facts procurement teams want.
4. SOC 2 / ISO 27001 are not realistic in the short term, but stating "compliance roadmap" as planned is acceptable for early-stage SaaS.

**SOURCED:**
- Privacy policy already exists at `web/app/privacy-policy/page.tsx`.
- Hosting confirmed as Railway per `backend/railway.toml` and `web/railway.toml`.
- Pattern: **Resend's** `/security` page is the cleanest example of this for an early-stage dev tool (`resend.com/legal/security`). **Linear's** trust centre is a richer example. Both surface the same core facts: where data lives, what encryption, who the sub-processors are.

**EFFORT:** 2-4 hours (most of which is verifying the actual answers — Railway region, exact sub-processor list).

**DEPENDENCIES:** Need to confirm Railway hosting region and ratify the sub-processor list.

---

### C13 — Drop "The" from profession names

**WHAT:** Rename "The Cartographer" → "Cartographer", etc. across the marketing surface.

**HOW:**
1. Edit `web/components/marketing/stitch-features.tsx:13-56` — for each profession in the array, change `name: 'The Cartographer'` to `name: 'Cartographer'`. Six small edits.
2. Confirm no other marketing copy uses "The X" pattern (search for "The Cartographer", "The Librarian", etc. across `web/`).
3. Note: the in-product view names should also be checked for consistency — but the product views don't use "The" (per CLAUDE.md "Six Profession Views" table at lines 47-54), so the marketing page is the only place this lives.

**SOURCED:**
- Marketing source: `web/components/marketing/stitch-features.tsx:13-56`.
- Product naming: `CLAUDE.md` "Six Profession Views" table — uses bare names without the determiner.

**EFFORT:** 15 minutes.

**DEPENDENCIES:** None.

---

### C14 — "Echoing the same original" — promote this line

**WHAT:** Promote the phrase "echoing the same original" out of a Cartographer card description into a hero subhead or section heading.

**HOW:**
1. Edit `web/components/marketing/stitch-hero.tsx:23-26`. Current H1: "Look behind the headlines. / Form your view." Add a subhead between H1 and the body paragraph: `"See where sources agree, where they diverge, and which ones are just echoing the same original."`
2. This becomes the strongest single line on the page and directly communicates the differentiator from verdict-based fact-checkers.

**SOURCED:**
- Original copy lives at `web/components/marketing/stitch-features.tsx:18-19`.
- The persona research flagged this independently — Dev called it "the strongest line on the page" and noted it's hidden.

**EFFORT:** 15 minutes.

**DEPENDENCIES:** None.

---

### C15 — "Form your view" assumes exploration over investigation

**WHAT:** A/B test the H1 alternative "Test the claim" — but only after the demo is in place, since structural problems will swamp the signal.

**HOW:**
1. The cleanest A/B framework that's already free is **PostHog**, which is recommended in your existing `DEEP_RESEARCH_SYNTHESIS.md` lines 32-38. Free tier supports feature flags + experiments.
2. Implementation: `useFeatureFlag('home-h1-variant')` from `posthog-js/react`, two variants `'form-your-view'` and `'test-the-claim'`. Statistical significance after ~500 visitors per variant (PostHog calculates this).
3. Run for 2 weeks minimum, ship the winner.

**SOURCED:**
- PostHog integration is already on the Tier 0 list in `docs/marketing/DEEP_RESEARCH_SYNTHESIS.md:135-145` ("Set up PostHog Cloud (free) — 1 hour").
- Pattern: PostHog's own marketing handbook documents this same pattern (`posthog.com/docs/experiments`).

**EFFORT:** 1-2 hours setup + 2 weeks runtime.

**DEPENDENCIES:** PostHog setup must happen first (it's a Tier 0 action anyway).

**NOTE:** Don't do this until at least Phase 1 of the demo + the Tier 1 fixes are shipped. The structural problems will swamp the H1 signal.

---

### C16 — CTA "Start Analysing" — analysing what?

**WHAT:** Replace with an action-led CTA that doesn't presume context.

**HOW:**
1. Edit `web/components/marketing/stitch-hero.tsx:35`. Current: `<span>Start Analysing</span>`. Replace with `<span>Try a headline</span>` or `<span>Paste a URL</span>` or `<span>Start free</span>`.
2. Recommendation: `"Try a headline"` — concrete, action-led, free of jargon, doesn't presume the user has a target.
3. Same change in the second CTA in the pricing section if any.

**SOURCED:**
- CTA source: `web/components/marketing/stitch-hero.tsx:35`.
- Pattern: **Linear** uses "Start building" not "Start using". **Vercel** uses "Start Deploying". **Cal.com** uses "Get started — it's free". All concrete actions.

**EFFORT:** 5 minutes.

**DEPENDENCIES:** None.

---

### C17 — No reproducibility statement

**WHAT:** Document on the methodology page (and a one-line on the home page) whether two runs of the same input return the same output.

**HOW:**
1. The honest answer requires you to know the truth: do two runs return the same output? Per CLAUDE.md "Critical Invariants" #3 ("Freeze at latest stage — `claim_map_input_hash`"), the pipeline is intended to be reproducible. But LLM scoring/classification stages have temperature settings — verify in `backend/app/pipeline/relevance_scorer.py` and `backend/app/pipeline/claim_map_analyzer.py` whether `temperature=0` is set.
2. If reproducible: state it on the methodology page. "Same input, same evidence set." This is a real selling point.
3. If not fully reproducible: state the bound. "Evidence retrieval is deterministic; LLM-driven classification may vary by ~5%. Underlying evidence URLs do not change."
4. Either way, surface honestly. The absence is the problem, not the answer.

**SOURCED:**
- Pipeline determinism is alluded to in CLAUDE.md "Critical Invariants" #3.
- Hash freezing logic — search `backend/app/pipeline/runner.py` for `claim_map_input_hash`.
- LLM call sites — `backend/app/pipeline/relevance_scorer.py`, `backend/app/pipeline/claim_map_analyzer.py`.

**EFFORT:** 2 hours (verify behaviour + write the statement).

**DEPENDENCIES:** Methodology page (C5).

---

### C18 — No GitHub link, no public roadmap

**WHAT:** Surface a GitHub link from the footer once the MCP package is published.

**HOW:**
1. Track I-07 (`audit/track-i/PROGRESS.md:124-138`) is the existing item for publishing the MCP package. The repo for `tru8-mcp` is implied to exist as a separate publication artifact.
2. Add to footer (`web/components/layout/footer.tsx`): GitHub link to the Tru8 organisation page (or the MCP-only repo).
3. If the main Tru8 codebase remains closed-source (commercial SaaS), the GitHub link should point to the MCP package + any docs / examples / openly published methodology.
4. Public roadmap: cheapest version is a single GitHub Issue or a Notion page linked from the footer as "Roadmap". GitHub Projects (if you publish a public repo) is the more standard pattern.

**SOURCED:**
- Track I-07 exists in `audit/track-i/PROGRESS.md`.
- Pattern: **Linear** publishes its roadmap on `linear.app/changelog`. **Vercel** uses GitHub. **PostHog** uses GitHub Projects. Any of these patterns work.

**EFFORT:** 1 hour (footer link). Much more if you want to actually open-source anything.

**DEPENDENCIES:** Track I-07 (MCP publication) — and a decision on whether anything else gets open-sourced.

---

## Recommended ship order

A recommended sequence that minimises risk and maximises early signal:

### This week (highest leverage, ~1 day total)

1. **C1 + C2 (Phase 1 demo)** — pick a check, capture the screenshot, replace the video placeholder, add the "see the full report" link. (2-4 hours)
2. **C13 (drop "The")** — 15 minutes.
3. **C14 ("echoing the same original")** — 15 minutes.
4. **C16 (CTA copy)** — 5 minutes.
5. **C4 (jargon fix)** — 1 hour.
6. **C11 (Wayback line in hero)** — 30 minutes.
7. **C10 option B (Enterprise starting price)** — 30 minutes.

Total: half a day. The page is meaningfully better and addresses the highest-confidence objections.

### Next week (1-2 days)

8. **C3 (sources page)** — half a day.
9. **C5 (methodology page)** — 1 day (mostly writing).
10. **C7 (carousel → grid)** — 2-3 hours.
11. **C6 (Seeker spotlight section)** — half a day.

### Week 3 (1-2 days)

12. **C9 (split Pro / Developer tiers)** — half a day frontend, plus Stripe setup (Track I-03 territory).
13. **Phase 2 of THE DEMO (live mini-Cartographer)** — 1-2 days.
14. **C12 (security page)** — 2-4 hours.
15. **C17 (reproducibility statement)** — 2 hours.

### Deferred (do when there's pull from real users)

- **C8 / C10A (new tier / team plan)** — only when you have an inbound request asking for it.
- **C15 (A/B test the H1)** — only after PostHog is set up and the structural fixes are in place.
- **C18 (GitHub link)** — when Track I-07 ships.
- **Phase 3 (real video walkthrough)** — when Phases 1+2 are no longer sufficient.

---

## What I have NOT verified

These are the assumptions I'm making that should be sanity-checked before shipping:

1. **Hosting region for the security page** — I've assumed Railway is the correct answer based on `backend/railway.toml`, but the actual region (UK / US / EU) needs to be confirmed in the Railway dashboard.
2. **A curated demo check exists** — for Phase 1 + Phase 2 of the demo, you need at least one completed production check that's appropriate to show publicly. If none exists, that's the prerequisite.
3. **Stripe products for new tiers** — Track I-03 status in `audit/track-i/PROGRESS.md` says price IDs exist in Stripe test mode but env vars are empty. C8/C9 depend on this.
4. **Pipeline determinism** — I've assumed `temperature=0` on LLM calls but haven't verified. C17 depends on this being checked.
5. **Wayback integration is currently working in production** — I'm trusting CLAUDE.md and memory. Worth one quick check that recent checks have archive URLs populated.

If any of these turn out wrong, the corresponding solutions need to be adjusted before shipping.
