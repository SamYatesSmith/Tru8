# Tru8 Marketing — Deep Research Synthesis

> Compiled 2026-04-02 from 4 parallel research agents covering: open-source marketing platforms, developer marketing strategies, AI-powered marketing tools, and marketing-as-code GitHub repos. Cross-referenced against existing `MARKETING_RESEARCH.md`.

---

## Executive Summary

Your existing marketing research doc is **largely correct**. The phased approach, the tool choices (Postiz, n8n, Typefully, F5Bot), and the "never automate replies in researcher communities" principle are all validated by independent research. This synthesis adds **6 tools your doc missed**, **challenges 2 recommendations**, and **reorders your priorities** based on what actually drove growth for comparable products.

**The single most important finding:** For developer/researcher tools, documentation and a Show HN launch outperform any marketing automation tool. PostHog, Supabase, and Resend all grew from organic channels with near-zero ad spend. The tools matter less than the content strategy.

---

## Part 1: What Your Existing Doc Gets Right

| Recommendation | Verdict |
|---|---|
| Postiz for social scheduling | **Confirmed.** 27.8k stars, actively maintained, MCP-compatible agent CLI. Best open-source Buffer alternative. |
| n8n as automation glue | **Confirmed and underweighted.** 182k stars. Every research stream flagged this as the single most valuable tool. Elevate from "notable" to core infrastructure. |
| Typefully + Hypefury for scheduling | **Confirmed.** Typefully ($12.50/mo) for cross-posting, Hypefury ($6/mo) for X evergreen recycling. Best value combo. |
| F5Bot for conversation monitoring | **Confirmed.** Free, proven, right channel for your audience. |
| MCP registry submissions | **Confirmed.** Highest-leverage free action for the developer/agent audience. |
| "Never automate replies" in OSINT/journalism communities | **Strongly confirmed.** Research shows AI-generated content preference dropped from 60% to 26%. These audiences detect and distrust automation. |
| LangChain Social Media Agent for draft generation | **Confirmed.** Good human-in-the-loop approach via Slack. |
| Phase 1 free tools first, paid tools later | **Confirmed.** Every successful dev tool started with organic/free channels. |

---

## Part 2: What Your Doc Missed (6 Tools)

### 1. PostHog — Product Analytics (FREE cloud tier)
- **GitHub:** 32.3k stars, MIT licence
- **What:** Product analytics, session replay, feature flags, A/B testing, surveys, error tracking — all-in-one
- **Free tier:** 1M events/month, 5k session replays, 1M feature flag requests. No credit card.
- **Why it matters:** You cannot optimise marketing without knowing what users do after they arrive. Track signup → first check → return visit → upgrade funnel. PostHog replaces Mixpanel + Hotjar + LaunchDarkly.
- **Honest note:** Use the cloud tier, not self-hosted. PostHog themselves advise against self-hosting for small teams — the operational overhead isn't worth it.
- **Stack fit:** Python + TypeScript SDKs. Perfect for FastAPI + Next.js.

### 2. Listmonk — Email/Newsletter (FREE self-hosted)
- **GitHub:** 19.3k stars, Go binary, PostgreSQL backend
- **What:** High-performance newsletter and mailing list manager. Single binary. Handles millions of subscribers.
- **Why it matters:** Your doc has no email strategy. Email is the only channel you own — X, LinkedIn, HN can change algorithms overnight. Product updates, methodology articles, and changelog broadcasts should go to an email list.
- **Limitation:** No native drip campaigns. For onboarding sequences, pair with n8n or use Dittofeed/Plunk.
- **Stack fit:** Uses PostgreSQL (can share your existing instance). Docker deployment is one command.
- **Cost:** Free. Pair with AWS SES at $0.10/1,000 emails.

### 3. Umami — Website Analytics (FREE self-hosted)
- **GitHub:** 35.8k stars, MIT licence, Next.js + PostgreSQL
- **What:** Privacy-first web analytics. No cookies, GDPR-compliant. < 1KB tracking script.
- **Why it matters:** You need to know which marketing pages convert, which blog posts drive signups, and where traffic comes from. Umami is the simplest tool for this.
- **Stack fit:** Literally runs on Next.js + PostgreSQL — identical to your stack.
- **Honest note:** This is *website* analytics only. Use PostHog for *product* analytics. They complement, not compete.

### 4. Dub — Link Attribution + Referral Programs (open-source core)
- **GitHub:** 23.3k stars, YC-backed
- **What:** Short links, real-time analytics, conversion tracking, embedded referral/affiliate programs. Used by Twilio, Buffer, Perplexity.
- **Why it matters:** When you share links on social, you need to know which posts drove signups. Built-in referral program means early users can bring others.
- **Stack fit:** TypeScript, API-first. Self-hostable or use cloud tier.

### 5. Formbricks — In-App Surveys (FREE self-hosted)
- **GitHub:** 12k stars, Next.js + Tailwind + Prisma
- **What:** In-app surveys, NPS, feature requests. Trigger surveys based on user behaviour.
- **Why it matters:** Once users arrive, you need to learn what's working and what isn't. Trigger a survey after first analysis completes.
- **Stack fit:** Same stack (Next.js, Tailwind, Prisma). Near-zero integration effort.

### 6. SerpBear — Keyword Rank Tracking (FREE self-hosted)
- **GitHub:** 1.9k stars, Next.js + SQLite
- **What:** Track Google keyword rankings. Notifications when rankings change. Google Search Console integration.
- **Why it matters:** Track your target terms ("evidence research tool", "OSINT platform", "MCP evidence server") over time.
- **Stack fit:** Next.js, runs on free tiers of Fly.io.

---

## Part 3: What Your Doc Gets Wrong (2 Challenges)

### Challenge 1: Lately and Byword.ai Are Probably Not Worth It

Your doc recommends Lately ($49-199/mo) for content repurposing and Byword.ai ($99/mo) for programmatic SEO in Phase 4.

**Research finding:** At $150-300/mo combined, these are expensive for what they do. The repurposing workflow (one blog post → 15-20 social variants) can be achieved with the LangChain Social Media Agent (free) + n8n (free) + Claude API (~$5/mo at your volume). For programmatic SEO pages, a simple Next.js dynamic route with structured data generates the same "evidence research for [profession]" pages at zero marginal cost.

**Recommendation:** Skip both. Reinvest that budget into ConvoHunter ($50-99/mo) earlier — conversation discovery has a more direct path to users than automated content generation.

### Challenge 2: Taplio at $55/mo Is Too Early

Your doc includes Taplio in Phase 3 for LinkedIn. At $55/mo, this only makes sense if LinkedIn is already driving measurable signups. Start with Typefully's LinkedIn cross-posting (included in the $12.50/mo plan) and only add Taplio when you have data showing LinkedIn converts.

---

## Part 4: The Developer Marketing Strategy (What the Winners Did)

This is the most important section. **Tools don't matter if the strategy is wrong.**

### What PostHog, Supabase, and Vercel Actually Did

All three grew with near-zero ad spend. The pattern:

1. **Free tier is mandatory.** You already have this (3 free checks).
2. **Documentation is your best marketing asset.** Interactive API playground, copy-paste code samples, real worked examples. This matters more than any blog post or social media tool.
3. **Show HN is the highest-leverage single launch action** for a technical product. Audience overlap with Tru8 is near-perfect: technically sophisticated, interested in evidence/verification, building with AI agents.
4. **Defensive SEO pages** — "best evidence research tools", "evidence research API comparison", "Tru8 vs [competitor]". High-intent, doubles as sales collateral. PostHog calls this their most effective content type.
5. **One substantive content piece per week** beats 20 shallow social posts. Technical depth signals credibility to this audience.
6. **Build a channel you own (email).** X/LinkedIn algorithms are fickle. An email list is the only channel that can't be taken from you.

### The Show HN Playbook

Research identified this as your single highest-leverage launch action.

**What works:**
- Crystal clear title: "Show HN: Tru8 — an API that searches 30+ evidence sources in 90 seconds"
- Specifics and numbers, not superlatives
- Link to working product or live demo
- Modest language — no "fastest", "biggest", "first", "best"
- 8-10 genuine upvotes + 2-3 thoughtful comments in first 30 minutes (from people with established HN accounts)
- Post demo/repo link as top-level comment once at 20+ points

**What kills an HN post:**
- Public Twitter/LinkedIn requests for upvotes (shadow-banned)
- Requiring signup before seeing value
- Marketing language of any kind
- Clickbait

**Preparation:** Write a technical blog post about evidence research methodology *first* — this becomes the HN link target. The product should be reachable from the post but the post itself should provide genuine value.

### Supabase's "Launch Week" Format

Ship one feature announcement per day for a week. Immediate growth spike. Supabase has done 15 of these.

**Tru8 applicability:** You have 14 completed tracks of features that have never been marketed. A "Launch Week" bundling the most impressive capabilities (Cartographer, Seeker, Agent API, MCP server, Chronologist) could be high-impact. Each day = one blog post + social push.

---

## Part 5: Recommended Tool Stack (Prioritised)

### Tier 0: Free, This Week

| # | Action | Tool | Effort |
|---|--------|------|--------|
| 1 | Product analytics | **PostHog Cloud** (free tier) | 1 hour |
| 2 | Website analytics | **Umami** (self-hosted) | 30 min |
| 3 | Keyword monitoring | **F5Bot** (free) | 15 min |
| 4 | MCP registry listings | Official + Smithery + Glama + PulseMCP | 2 hours |
| 5 | AI directory listings | There's An AI For That + Futurepedia + awesome-ai-agents PR | 1 hour |
| 6 | Keyword rank tracking | **SerpBear** (self-hosted) | 30 min |

### Tier 1: ~£20/mo, Month 1

| # | Action | Tool | Cost |
|---|--------|------|------|
| 7 | Social scheduling | **Typefully** | £10/mo |
| 8 | X evergreen recycling | **Hypefury** | £5/mo |
| 9 | Show HN launch | Manual (prepare blog post + demo) | Free |
| 10 | Submit to launch directories | DevHunt, BetaList, SaaSHub, Product Hunt | Free |

### Tier 2: Self-Hosted, Month 1-2

| # | Action | Tool | Cost |
|---|--------|------|------|
| 11 | Email newsletter | **Listmonk** + AWS SES | ~£1/mo |
| 12 | Workflow automation | **n8n** (self-hosted) | Free |
| 13 | Social media scheduling | **Postiz** (self-hosted) | Free |
| 14 | Content draft pipeline | **LangChain Social Media Agent** → Slack → Postiz | Free |

### Tier 3: When You Have Users, Month 2-3

| # | Action | Tool | Cost |
|---|--------|------|------|
| 15 | In-app surveys | **Formbricks** (self-hosted) | Free |
| 16 | Conversation discovery | **ConvoHunter** | ~£50-80/mo |
| 17 | Link tracking + referrals | **Dub** | Free tier or self-hosted |
| 18 | A/B testing (if needed) | PostHog built-in or **GrowthBook** | Free |

### Tier 4: When You Have Revenue

| # | Action | Tool | Cost |
|---|--------|------|------|
| 19 | Newsletter sponsorships | Python Bytes, TLDR (when budget allows) | £2-5k/placement |
| 20 | Demo booking | **Cal.com** (when enterprise sales start) | Free self-hosted |
| 21 | Live chat | **Chatwoot** (when traffic justifies it) | Free self-hosted |

### Total Costs

| Phase | Monthly Cost |
|-------|-------------|
| Tier 0 | £0 |
| Tier 1 | ~£15/mo |
| Tier 2 | ~£1/mo (SES) + a small VPS (~£15-20/mo for all self-hosted tools) |
| Tier 3 | Add ~£50-80/mo |
| **Realistic Month 1-2** | **£35-40/mo** |
| **Realistic Month 3+** | **£85-120/mo** |

---

## Part 6: The Autonomous Pipeline (Realistic)

**Honest ceiling:** "Autonomous draft generation with human approval, ~5-10 min/day."

True fully-autonomous marketing does not exist. The best achievable pipeline:

```
Blog post / release notes / methodology article
    │
    ▼
n8n webhook (triggers on new blog post or GitHub release)
    │
    ▼
Claude API (generates: tweet thread, LinkedIn post, newsletter blurb)
    │
    ▼
Slack notification (human approves/edits in <2 min)
    │
    ▼
Postiz API (posts to X + LinkedIn + Bluesky)
    │
    ▼
Hypefury (auto-recycles top X posts as evergreen)
    │
    ▼
Listmonk API (queues newsletter with same content)
```

**Self-hosted cost:** £0/mo recurring (everything runs on one VPS).
**Daily time commitment:** 5-10 minutes reviewing and approving drafts.
**What you still do manually:** Write the original blog post, engage in communities, respond to HN/Reddit threads.

---

## Part 7: Tools to Skip

| Tool | Why Not |
|---|---|
| **Jasper** ($59/mo) | A Claude system prompt does the same thing at your scale |
| **Copy.ai** ($29/mo useful, $249/mo for agents) | Team-oriented, the useful tier is 8x the price |
| **Lately** ($49-199/mo) | n8n + Claude API achieves the same repurposing for ~£5/mo |
| **Byword.ai** ($99/mo) | Next.js dynamic routes + structured data = free programmatic SEO |
| **Taplio** ($55/mo) | Too early. Typefully covers LinkedIn cross-posting. Add Taplio only if LinkedIn proves to convert. |
| **Clay** ($185+/mo) | Designed for GTM teams. Credit system punishes learning. |
| **Mautic** | Powerful but massive PHP application. Operational overhead disproportionate for a solo developer. |
| **erxes** | Tries to be everything (CRM + marketing + helpdesk). Too complex to bolt on. |
| **Cold email tools** (Instantly, Apollo paid) | Wrong channel for journalists, researchers, OSINT analysts. |
| **OpenOutreach** (LinkedIn automation) | Account ban risk. Your audience will detect and distrust it. |
| **Any tool claiming "fully autonomous"** | None of them are. Best case: autonomous drafting with human approval. |

---

## Part 8: Ordered Action Plan

### Week 1: Foundation (£0)
1. Set up PostHog Cloud (free) — add tracking to web app
2. Deploy Umami — add to marketing pages
3. Register F5Bot with 8 keywords
4. Submit MCP server to Official Registry + Smithery + Glama + PulseMCP
5. Submit to There's An AI For That + Futurepedia
6. PR to awesome-ai-agents
7. Write 3 defensive SEO blog posts: "best evidence research tools", "evidence research API comparison", "MCP servers for research"

### Week 2: Content + Launch Prep (~£15/mo)
8. Set up Typefully ($12.50/mo) + Hypefury ($6/mo)
9. Write the Show HN blog post (technical, methodology-focused)
10. Submit to DevHunt, BetaList, SaaSHub
11. Deploy SerpBear, start tracking target keywords
12. Enable GitHub Discussions on the repo

### Week 3: Launch
13. **Show HN** (primary launch moment)
14. Product Hunt submission (secondary)
15. Share on r/OSINT, r/SaaS, X, LinkedIn
16. Cross-post to Dev.to + Hashnode
17. Respond to every comment everywhere

### Week 4: Infrastructure
18. Deploy Listmonk + set up email capture
19. Deploy n8n + build the content→social pipeline
20. Deploy Postiz (self-hosted)
21. Connect: n8n → Claude API → Slack → Postiz → Listmonk

### Month 2+: Iterate
22. Publish one substantive piece per week
23. Pipeline handles social distribution semi-autonomously
24. Add ConvoHunter when budget allows
25. Add Formbricks for in-app feedback when users arrive
26. Consider "Launch Week" format when you have enough features to showcase

---

## Part 9: Honest Assessment

**What will actually move the needle for Tru8:**

1. **Show HN launch** — single highest-leverage moment. Worth significant preparation.
2. **MCP registry presence** — agents discovering Tru8 programmatically is a growth channel that doesn't exist for most SaaS products. Unique advantage.
3. **Documentation quality** — interactive API playground, real examples, copy-paste code. This is marketing for developers.
4. **One good blog post per week** — methodology articles, case studies, technical deep-dives. Quality over quantity.
5. **Email list** — the only channel you fully own.

**What won't move the needle:**
- Posting 20 times/day on social (noise)
- AI-generated content without editing (credibility risk)
- Paid ads before organic traction (wasted spend)
- Any tool costing >£50/mo before you have paying users

**The uncomfortable truth:** Marketing tools are 10% of the work. The other 90% is writing, engaging, and showing up consistently. No tool automates taste, authenticity, or domain expertise — which are exactly what your target audience values.

---

## Sources

Research conducted across 150+ web sources, 40+ GitHub repositories, and cross-referenced against growth case studies from PostHog, Supabase, Vercel, Resend, and Stripe. Key sources include PostHog's public marketing handbook, Supabase's launch week retrospectives, developer marketing guides from daily.dev and Strategic Nerds, and direct GitHub repository analysis for all recommended tools.
