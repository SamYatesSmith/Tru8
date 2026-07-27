# Landing Reframe — Scoping Doc

**Date:** 2026-05-11
**Status:** Scoping only. This doc does **not** prescribe positioning. It defines what must be researched/decided before reframing.
**Trigger:** User flagged 2026-05-11 that V1 Step 7's "marketing copy" is too narrow. The developer/agent surface is comprehensive (4-tier API, MCP server, x402+Skyfire+credits, manifest signing, /verify endpoint) but buried in the current consumer-led landing. Reframe could materially shift revenue mix.

---

## Why this is being scoped, not just done

Step 7 of the V1 Quality Plan was originally scoped as a copy update reflecting the "1-3 claim sweet spot". The 2026-05-11 user message reframes this as a positioning question. Direct quote:

> "Quality from news is heading in the direction of requiring aggregation, and comparison amongst numerous outlets, so the user is able to easily summarise the many, rather than the narrative driven few."

> "Then there's the question of whether agents ARE MORE LIKELY to use this sort of paid API, because they will be responsible to providing accurate news, and this provides them an easy way to dig deeper into factual, or accurate news sources, such as APIs."

This is a **revenue-shaping** decision. Choosing wrongly costs months of marketing momentum and conversion funnel investment. The user explicitly asked for research, not a hot take. This doc defines what the research should answer.

---

## Current state of the landing surface (verified 2026-05-11)

Reading `web/app/page.tsx` and the five `web/components/marketing/stitch-*.tsx` files:

| Section | Content | Audience implied |
|---|---|---|
| `<head>` title | "Tru8 — AI-Powered News Evidence Research" | Consumer / general |
| `<head>` description | "Paste a news article, headline, or claim. ... No verdicts — just structured evidence so you can form your own view." | Consumer |
| Hero | "Look behind the headlines. **Form your view.**" + "Tru8 isn't a fact checker. Headlines make claims every day..." + "We organise. You decide." | Consumer reading news |
| Process | 3 steps: Submit / Research / Explore — describes a single user paste-and-research flow | Consumer |
| Features | "Your Research Team" — Six Professions carousel (Cartographer, Librarian, Correspondent, Projectionist, Chronologist, Seeker), metaphor-driven | Consumer |
| Video | Stitch-styled placeholder (no video src) | Both |
| Pricing | 4 tiers (Free / Pro £7 / Developer £29 / Enterprise) — Developer highlighted but contextless on a consumer-framed page | Both, but unexplained for devs |

**Developer surface** lives at `/developers`. Verified by reading `web/app/developers/page.tsx`: headline "Evidence Research for AI Agents", "One API call. Multi-source evidence retrieval. Structured, not summarised. Your agent decides what matters." Curl quick-start, pipeline tier table, MCP, pricing per tier and payment rail, async, batch, webhooks, response shape. Reachable only via top-nav link from the homepage.

**Gap:** essentially 100% of landing real estate goes to the consumer pitch. ~0% signals that an agent-integration surface exists. The Developer pricing tier shows on the pricing card but has no narrative thread on the homepage.

---

## The two hypotheses (from user's 2026-05-11 message)

### Hypothesis A — News users need aggregation

**Operative claim:** users distrust narrative-driven outlets and want a tool that does the source-comparison work for them. Tru8's "we organise; you decide" + multi-source evidence landscape + receipts + tier/type classification directly addresses this.

The user's framing is stronger than this neutral restatement — that major media outlets perpetrate lies and fake news with agendas, that quality news now requires aggregation and comparison to escape narrative capture. The research questions below stay neutral on that thesis (the research is about market demand, not media diagnosis), but the scope doc records the framing so the build directive isn't lost.

**What needs to be true for this to drive revenue:**
- Sufficient consumer demand at £7/mo or above for this category of tool
- Demand not already saturated by adjacent tools (Ground News, AllSides, Memeorandum, Reuters/AP raw feeds)
- Conversion funnel from "I distrust news" → "I will pay" works at scale
- The Six Professions metaphor resonates with cold consumer audiences rather than confusing them

**Research questions:**
- What's the current size and growth of the "news distrust → tooling" market?
- Ground News: pricing, ARR estimates, traffic, positioning. Same for AllSides, Memeorandum.
- Why isn't a free Twitter/X thread or Reddit aggregator already sufficient for most consumers?
- Has the Six Professions metaphor been tested with anyone outside our heads? Does "Cartographer" mean anything to a non-technical reader cold?
- Customer acquisition cost in this category?
- Is the politics-of-misinformation positioning a strength (clarity) or risk (alienates segments)?

### Hypothesis B — AI agents need paid evidence APIs

**Operative claim:** AI agents producing user-visible news/analysis output are increasingly accountable for accuracy. Paid, structured, signed evidence retrieval is exactly the missing piece — better than web search hallucination, better than rolling your own retrieval pipeline.

**What needs to be true for this to drive revenue:**
- Sufficient agent-builder demand at the £29/mo Developer tier or per-call API pricing
- Agents not already solved by free / cheap tools (Brave Search API, Tavily, Perplexity Sonar API, Bing Search, Exa)
- The Tru8 differentiators (manifest signing, tier classification, element decomposition, "we organise" framing) are enough additional value over "web search wrapped in JSON" to justify premium pricing
- MCP distribution channel produces actual installs and recurring queries

**Research questions:**
- What are agent-builders currently using for evidence retrieval? Tavily, Brave Search API, Perplexity Sonar, Exa, Serper? Pricing and capability comparison?
- How big is the "agent builds news/analysis content" market currently? Growth rate?
- Are there published incidents of agents being held accountable for accuracy (lawsuits, regulatory action, brand damage) that would push demand?
- What's the MCP ecosystem's installed base? How many MCP servers cross meaningful install thresholds (1k, 10k)?
- Would a free Lookup tier (~£0.02 → free for first 1k/mo) drive Developer-tier conversions?
- What does Anthropic's tool-use / Computer Use ecosystem look like as a distribution channel?

### Hypothesis C — implicit: parallel tracks

Tru8 already has both surfaces built. The current landing chooses to surface only one. A third option: homepage shows both audiences side-by-side with parallel CTAs. Risk: dual-audience landings are notoriously poor converters (split attention, weakened message).

**Research questions:**
- Are there comparable B2C-and-API products that successfully run dual-audience landing pages? (Stripe is a near-analogue but B2B-only.)
- Could the landing be sequenced — primary message for one audience, secondary entry point for the other?

---

## Three positioning options under consideration

### Option 1 — Consumer-lead (current, with copy refinements)

- Keep hero + process + features consumer-positioned
- Add an "API for AI Agents" callout band between Features and Video sections
- Link to `/developers` for the full developer pitch
- Step 7 copy refinements happen within this frame
- **Revenue thesis:** £7 Pro subscriptions drive volume; £29 Developer tier captures the agent-builders who self-select via direct discovery (MCP registry, dev listings)

**Pros:**
- Lowest disruption to existing funnel
- Aligns with "We organise; you decide" mission
- Doesn't bet the company on one untested audience

**Cons:**
- Continues to under-leverage the comprehensive developer surface
- Agent-builders won't discover Tru8 unless they hit it via direct channels (MCP registry, dev-tool listicles)
- £7 consumer ARPU is small; revenue ceiling lower

### Option 2 — Developer/agent-lead (full reframe)

- Hero: "Evidence research API for AI agents" — lift framing from `/developers`
- Process: replace consumer flow with developer quick-start (curl + JSON response snippet)
- Features: tier table, MCP install, manifest signing — concrete differentiation from web search
- Consumer dashboard moved to secondary nav, kept but de-emphasised
- **Revenue thesis:** £29/mo Developer + per-call API + Enterprise contracts; consumer is incidental

**Pros:**
- Leans into the comprehensive developer build (Agent Commerce Gateway, MCP, x402/Skyfire/credits, manifest signing)
- Higher ARPU per customer
- API-first positioning is easier to differentiate (no major MCP-listed competitor doing structured-evidence-with-receipts)

**Cons:**
- Abandons consumer market that Tru8's frontend was built for (Track D was a full redesign across 17 pages and 10 PRs)
- The Stitch design system and Six Professions metaphor become orphaned
- Risk of becoming "just another search API" in a crowded developer-tools space

### Option 3 — Two-surface parallel

- Landing has a primary frame (consumer OR agent) and a strong secondary entry
- Strong navigation differentiation: clear consumer path AND clear developer path on the homepage
- Both pricing models surfaced
- **Revenue thesis:** capture both audiences in their native context

**Pros:**
- Leverages both builds
- Doesn't require betting on one hypothesis ahead of data
- Easy to A/B test which entry converts at what rate

**Cons:**
- Highest UX complexity — dual landings rarely outperform single-audience ones
- Pricing page already has 4 tiers + agent-commerce; parallel-audience messaging risks more confusion, not less
- Splits brand voice between "We organise; you decide" (consumer) and "Evidence Research for AI Agents" (developer)

---

## What objective signals would shift the answer

Not "what does the team think" — what data would tip toward each option:

| Signal | If observed → tips toward |
|---|---|
| MCP server publication produces >5,000 installs in 60 days | Option 2 |
| Developer-tier signups outpace Pro-tier 2:1 unprompted in first 30 days | Option 2 |
| Six Professions metaphor tests poorly with cold consumer audience | Option 2 or 3 (drop the metaphor in either) |
| Existing consumer competitors (Ground News, AllSides) reach >$10M ARR with similar positioning | Option 1 |
| Per-call API usage from existing devs hits >£500/customer/month | Option 2 |
| Public-report views via `/r/[id]` grow >10k/day organically | Option 1 |
| 1-3 agent-builder interviews show willingness to pay £100+/month per agent | Option 2 |
| No major agent-builder uptake in 90 days post-MCP launch | Option 1 or 3 |
| Consumer Pro conversion rate from free-tier sign-ups exceeds industry average | Option 1 |

---

## Decision gates

This scope does NOT decide. Decision should be made after **all four** of:

1. **I-07 MCP publication** ships and 30+ days of usage data accumulates (free directional signal on agent demand)
2. **Consumer competitor analysis** — pricing, traffic estimates, publicly disclosed ARR for Ground News / AllSides / Memeorandum
3. **3-5 agent-builder conversations** — what they currently use (Tavily / Brave / Perplexity / Exa / Serper), what they'd pay, what would make them switch
4. **First 30 days of post-V1 production usage** — does the existing consumer funnel convert at meaningful rates?

After those four, the data narrows the option set.

**Earliest reasonable decision date:** 30 days post-V1 ship AND post-MCP launch, whichever is later.

**Hard constraint:** do NOT reframe the landing before V1 ship. V1 ships under current consumer-led positioning. Reframe is a separate post-launch workstream.

---

## 2026-05-12 — constraint revised (Option 1+ proceeding pre-V1)

User overrode the "do not reframe before V1 ship" constraint, narrowly. The full reframe (Option 2) stays gated on data; what's landing now is **Option 1+** — between the scope doc's Option 1 (callout band only) and Option 2 (full reframe).

**Changes shipping now (homepage only, no nav/sitemap change, no pricing change):**

| Surface | Change | Rationale |
|---|---|---|
| Hero sub | Add one sentence: agent-builders can wire the same evidence via the API | Plants the dual-audience signal at first-glance without losing the consumer hero |
| Process step 3 | Append "in the browser or as JSON via the API" | One-word change linking the consumer flow to the dev surface |
| Features → Pricing gap | New section: "API for AI Agents" band (single row, mono micro-label, headline, link to `/developers`) | The callout the scope doc's Option 1 specifies |
| Video section | Removed entirely. Replaced with split layout: product screenshot (Librarian view) on the left, real `/agent/quick` JSON snippet on the right | Concrete proof for both audiences, replacing a placeholder that was never going to ship a video |

**Out of scope (still deferred to post-V1 decision):**
- Hero h1 copy (still consumer-led)
- Six Professions metaphor (untouched)
- Pricing card order / Developer-tier promotion
- Nav structure (`/developers` stays a single nav link, not promoted)

**Decision-gate signals (from the table above) remain unchanged.** This 2026-05-12 change is *additive surfacing of the developer surface*, not a positioning bet. If post-V1 data tips toward Option 1, the band stays and the screenshot section keeps its consumer-side image primary. If data tips toward Option 2, this change is a stepping stone, not a u-turn.

**Implementation:** new `stitch-api-band.tsx` and `stitch-product-preview.tsx`; `stitch-video.tsx` deleted. `web/app/page.tsx` reordered to Hero → Process → Features → ApiBand → ProductPreview → Pricing.

---

## Out of scope for this doc

- **Site architecture changes** (nav, sitemap, routing). Reframe might require these; not scoped here.
- **Pricing changes.** 4-tier structure stays for V1. Reframe might reshape pricing; that's a separate question.
- **Brand identity changes.** Stitch design system is locked. Reframe is copy + section order + emphasis, not visual redesign.
- **`/r/[id]` public report.** Independent surface, unaffected by landing positioning.
- **The misinformation/media-quality thesis itself.** The user has a strong view; the research questions in this doc stay neutral on that view because what matters for revenue is *market demand for the solution*, not *agreement on the diagnosis*. If the market validates Hypothesis A, the thesis is reinforced. If it doesn't, the thesis still might be correct but unmarketable at £7/mo.

---

## Immediate next steps if user wants to advance this

1. **Don't block.** Add MCP publish (I-07) as a research-feeding action — let it ship; data starts accumulating
2. **Commission a 1-pager** on Ground News + AllSides + Memeorandum positioning, traffic estimates, publicly disclosed pricing/ARR (web research task — could be a sub-agent run)
3. **Identify 3-5 agent builders** for 30-minute conversations (current tools, willingness-to-pay, accuracy responsibility framing)
4. **Set a decision date on the calendar** — 30 days post V1 ship + MCP publish, whichever is later
5. **Capture daily usage signals** — consumer sign-ups, Dev-tier sign-ups, MCP installs, per-call API volume, `/r/[id]` traffic. Already feasible via existing Sentry/analytics + Stripe + Railway logs

---

## Cross-links

- `audit/2026-05-11_consolidation.md` — Tier 1.5 references this scope
- `audit/track-i/PROGRESS.md#I-07` — MCP publication, the directional signal generator
- `web/app/page.tsx` — current landing assembler
- `web/components/marketing/` — current consumer-positioned section components
- `web/app/developers/page.tsx` — current buried developer surface
- `~/.claude/projects/C--Users-projects-Tru8/memory/feedback_trust_user_on_production_state.md` — lesson on not letting docs drift from production reality (applies here: don't reframe based on assumed audience demand before data confirms it)

---

*This doc is a scope, not a plan. When the decision is made, a separate implementation doc takes over.*
