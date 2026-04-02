# Tru8 Marketing Research

> Research conducted 2026-03-26. Tools, pricing, and availability should be verified before purchase.

---

## Target Audience Segments

Five distinct audience segments identified from the codebase, pricing tiers, marketing copy, and the 635-role user list in `audit/POT_USERS.md`.

| Segment | Examples | Primary Channel | Pricing Tier Fit |
|---------|----------|-----------------|------------------|
| **Information professionals** | Journalists, OSINT analysts, policy researchers, academic researchers, legal researchers | LinkedIn, X, Reddit (r/OSINT, r/journalism) | Starter / Professional |
| **Content creators** | YouTubers, podcasters, newsletter writers, documentary researchers, science communicators | X, YouTube, Product Hunt | Free Trial / Starter |
| **Business analysts** | Market researchers, competitive intelligence, equity/VC analysts, strategy consultants | LinkedIn | Professional / Enterprise |
| **Government & policy** | Parliamentary researchers, civil service, policy advocates, think tank researchers | LinkedIn | Professional / Enterprise |
| **Developers & AI builders** | Agent developers, MCP integrators, tool-chain builders, browser extension devs | GitHub, MCP registries, HN | Professional (API access) / Agent API |

### Six "Profession" Views Map to Audience Needs

| View | Archetype | Question | Primary Audience |
|------|-----------|----------|-----------------|
| Cartographer | Map maker | Shape of the conversation? | Analysts, OSINT professionals |
| Librarian | Data curator | Full set, clearly labelled? | Academic researchers, journalists |
| Interpreter | Domain expert | Does this answer the question? | Specialists, policy analysts |
| Projectionist | Media researcher | What's on camera? | Content creators, media analysts |
| Chronologist | Historian | When did evidence appear? | Investigative journalists, historians |
| Seeker | Investigator | What don't we know? | OSINT professionals, researchers |

### Agent API Audience

Four tiers for programmatic evidence research:
- **Lookup** (GBP 0.02) -- instant cached results
- **Consensus** (GBP 0.03) -- cross-user aggregate landscape
- **Quick** (GBP 0.07, ~15s) -- fast analysis for real-time agents
- **Full** (GBP 0.15, 60-90s) -- complete pipeline, 30+ sources

Three payment rails: prepaid credits, x402 (USDC/SIWE), Skyfire (JWT).

---

## Recommended Tool Stack

### Phase 1 -- Immediate (Free, High-Leverage)

| Action | Tool | Cost | Notes |
|--------|------|------|-------|
| Publish MCP server | Official MCP Registry | Free | registry.modelcontextprotocol.io -- canonical discovery for Claude, Copilot, etc. |
| Publish MCP server | Smithery | Free | smithery.ai -- 4,000+ servers, largest community hub |
| Publish MCP server | Glama | Free | glama.ai/mcp/servers -- 17,200+ servers, quality scores |
| Publish MCP server | PulseMCP | Free | pulsemcp.com/servers -- 14,274+ servers |
| Publish MCP server | mcpservers.org | Free | Curated list, submit via website |
| List as AI tool | There's An AI For That | Free | theresanaiforthat.com -- 80M users, largest AI tool directory |
| List as AI tool | Futurepedia | Free | futurepedia.io/submit-tool -- 3,000+ tools indexed |
| List as AI tool | AI Agent Store | Free | aiagentstore.ai -- agent-specific directory |
| Permanent listing | Toolify.ai | GBP 39 one-time | toolify.ai/submit -- 230+ categories, permanent listing |
| Monitor conversations | F5Bot | Free | f5bot.com -- email alerts for keywords on Reddit, HN, Lobsters |
| GitHub visibility | awesome-ai-agents PR | Free | github.com/e2b-dev/awesome-ai-agents |

**Keywords to monitor via F5Bot:** "evidence research", "OSINT tool", "claim verification", "fact checking tool", "source analysis", "evidence platform", "MCP server", "AI agent API"

### Phase 2 -- Month 1: Content + Scheduling (~GBP 20/mo)

| Tool | What | Cost | URL |
|------|------|------|-----|
| **Typefully Creator** | Cross-post to X + LinkedIn, AI assist, thread writing, Bluesky/Mastodon support | $19/mo | typefully.com |
| **Hypefury** | X evergreen recycling -- top tweets auto-repost then auto-remove. Constant presence. | $6/mo | hypefury.com |

### Phase 3 -- Month 2: Audience Intelligence + LinkedIn Depth (~GBP 80-120/mo)

| Tool | What | Cost | URL |
|------|------|------|-----|
| **ConvoHunter** | AI finds relevant conversations across Reddit, X, LinkedIn, HN | ~$50-99/mo | convohunter.com |
| **Taplio Standard** | LinkedIn AI content generation, scheduling, 3M contact database | $55/mo | taplio.com |

### Phase 4 -- Month 3: Repurposing + SEO (~GBP 120-200/mo)

| Tool | What | Cost | URL |
|------|------|------|-----|
| **Lately** | Feed one blog post, get 15-20 social variants automatically | ~$49-199/mo | lately.ai |
| **Byword.ai** | Programmatic SEO pages: "evidence research for [profession]" | ~$99/mo | byword.ai |

### Steady-State Monthly Budget

| Phase | Tools | Approx. Monthly |
|-------|-------|----------------|
| Directories + monitoring | Free tools | GBP 0 |
| Content + scheduling | Typefully + Hypefury | GBP 20 |
| Intelligence + LinkedIn | ConvoHunter + Taplio | GBP 80-120 |
| Repurposing + SEO | Lately + Byword | GBP 120-200 |
| **Total steady-state** | | **GBP 180-340/mo** |

---

## Open-Source / Self-Hosted Options

For maximum autonomy without recurring SaaS costs.

### LangChain Social Media Agent

- **URL:** github.com/langchain-ai/social-media-agent
- **Stars:** 2.4k
- **What:** AI agent that takes URLs as input, generates platform-specific posts for X and LinkedIn with human-in-the-loop review. Slack integration for curation, scheduled posting via cron.
- **Tech:** LangGraph (TypeScript), Claude, Supabase, Arcade (social auth), FireCrawl.
- **Tru8 fit:** Feed it blog posts or evidence research results, generates LinkedIn + X posts. Human approves via Slack. Could be adapted to use Tru8's own API for content ideas.

### Postiz + Postiz Agent CLI

- **URL:** github.com/gitroomhq/postiz-app (27.6k stars)
- **Agent CLI:** github.com/gitroomhq/postiz-agent (MCP-compatible)
- **What:** Self-hosted Buffer alternative. 28+ platforms including LinkedIn and X. The Agent CLI is an MCP server that allows AI agents to schedule posts programmatically.
- **Tech:** NextJS + NestJS + Prisma/PostgreSQL. AGPL-3.0.
- **Tru8 fit:** Self-host for zero recurring cost. The MCP-compatible agent CLI means an AI pipeline can schedule posts without manual intervention.

### Potential Autonomous Pipeline

```
Tru8 blog post / release notes / evidence methodology article
        |
        v
LangChain Social Media Agent (generates drafts)
        |
        v
Human review via Slack (approve/edit/reject)
        |
        v
Postiz Agent CLI (schedules to LinkedIn + X)
        |
        v
Hypefury (recycles top-performing X posts as evergreen)
```

All self-hosted except Hypefury ($6/mo). Full pipeline runs with minimal daily input.

### Other Notable Open-Source Tools

| Tool | Stars | What | URL |
|------|-------|------|-----|
| **CrewAI** | 47.3k | Multi-agent orchestration -- build a marketing "crew" with research, writing, scheduling agents | github.com/crewAIInc/crewAI |
| **n8n** | 181k | Visual workflow automation with AI. 510 social media workflow templates. Self-hostable. | github.com/n8n-io/n8n |
| **Mixpost** | 3.1k | Self-hosted social media management. Laravel + Vue.js. | github.com/inovector/mixpost |
| **ALwrity** | 965 | AI digital marketing: blog writer, LinkedIn writer with citations, content calendar | github.com/AJaySi/ALwrity |
| **Tweepy** | 11.1k | Standard Python library for X API. Free tier: 1,500 tweets/mo write-only. | github.com/tweepy/tweepy |
| **LinkedIn Official Python Client** | 240 | Official thin client for LinkedIn REST APIs. Requires Partner Program approval. | github.com/linkedin-developers/linkedin-api-python-client |

---

## MCP & Agent Discovery (Highest Leverage)

Tru8 already has an MCP server and Agent Commerce Gateway. The MCP ecosystem is expanding rapidly -- registries are the "app stores" for AI agents.

### MCP Registries to Publish To

| Registry | Size | How to Submit | Priority |
|----------|------|---------------|----------|
| **Official MCP Registry** | Canonical | `mcp-publisher` CLI, GitHub OAuth | Critical |
| **Smithery** | 4,000+ servers | `smithery mcp publish` CLI | Critical |
| **Glama** | 17,200+ servers | Web submission | High |
| **PulseMCP** | 14,274+ servers | Web submission | High |
| **GitHub MCP Registry** | Curated | Self-publish when available | High |
| **mcpservers.org** | Curated | Web submission | Medium |
| **MCP Market** | Growing | Web submission | Medium |
| **MCP.so** | Growing | GitHub issue | Medium |

### AI Tool Directories

| Directory | Audience | Cost | URL |
|-----------|----------|------|-----|
| **There's An AI For That** | 80M users | Free | theresanaiforthat.com |
| **Futurepedia** | 3,000+ tools | Free | futurepedia.io/submit-tool |
| **AI Agent Store** | Agent-specific | Free | aiagentstore.ai |
| **Toolify.ai** | 230+ categories | $49 one-time | toolify.ai/submit |
| **awesome-ai-agents** | Developer audience | Free (PR) | github.com/e2b-dev/awesome-ai-agents |

---

## Communities to Engage

### Where the Audience Lives

| Community | Platform | Relevance | Approach |
|-----------|----------|-----------|----------|
| r/OSINT | Reddit | Core audience | Monitor via F5Bot, respond authentically |
| r/journalism | Reddit | Core audience | Share methodology, not product pitches |
| r/datascience | Reddit | Secondary | Evidence classification methodology |
| r/SaaS, r/SideProject | Reddit | Launch community | Show HN-style launch posts |
| OSINT Twitter/X | X | Core audience | Thought leadership, tool demonstrations |
| Bellingcat Discord | Discord | Core OSINT | Engage as a community member |
| News Nerdery | Slack | Journalism | Share evidence research methodology |
| Hacker News | HN | Developer + researcher | Show HN launch, comment on verification threads |

### Engagement Principles

1. **Never automate replies** in journalist, OSINT, or researcher communities -- they will detect and distrust it
2. Use F5Bot/ConvoHunter to *find* conversations, respond *manually* and *authentically*
3. Lead with methodology, not product. "Here's how we think about evidence classification" not "Try our tool"
4. The product philosophy ("We organise; you decide") is the marketing message -- it differentiates from verdict-based competitors

---

## Content Strategy

### Content Pillars

1. **Evidence methodology** -- how claims are decomposed, how sources are classified, why tier/type matters
2. **OSINT and research techniques** -- appeal to the investigator audience
3. **AI agent integration** -- tutorials, use cases, MCP setup guides for the developer audience
4. **Case studies** -- real evidence landscapes (anonymised) showing the product in action
5. **Industry commentary** -- thoughtful takes on misinformation, verification, media literacy (never preachy)

### Repurposing Workflow

Write one substantive piece per week (blog post, methodology deep-dive, case study), then:
1. **Lately** or LangChain agent generates 15-20 social variants
2. **Typefully** schedules across X + LinkedIn
3. **Hypefury** recycles top-performing X posts as evergreen
4. **Byword.ai** generates long-tail SEO pages from the same themes

---

## What Not to Do

| Tool/Approach | Why Not |
|---------------|---------|
| LinkedIn scraper tools (Expandi, Dripify, OpenOutreach) | Account ban risk. Journalists and researchers distrust automated outreach. |
| Fully autonomous Reddit reply bots (ReplyAgent, Scaloom) | Target audiences are sophisticated, will call out astroturfing. Damages credibility. |
| Jasper | Overkill for niche B2B. Platform-specific tools (Taplio, TweetHunter) understand social algorithms better. |
| Generic influencer marketing | The audience is too niche. Micro-communities and thought leadership work better. |
| Verdict/fact-checker positioning | Contradicts core philosophy. Marketing must reinforce "we organise; you decide." |

---

## Answer Engine Optimisation (AEO)

Emerging channel: ensuring Tru8 appears in AI search responses (ChatGPT, Perplexity, Gemini). The target audience is likely to use AI search. Key actions:

1. Structured content with clear definitions ("evidence research platform", "evidence landscape")
2. Schema markup on product pages
3. Presence in MCP registries and AI directories (feeds AI training data)
4. Blog content answering questions like "what tools exist for evidence research?"

---

## API Access Notes

**X/Twitter API (2026):**
- Free tier: 1,500 tweets/month write-only (no reads). Sufficient for a posting bot.
- Basic: $200/month, 15k reads + 50k writes.
- Pay-per-use: ~$0.01/tweet (launched Feb 2026).

**LinkedIn API:**
- Requires LinkedIn Partner Program approval.
- All applications start at Development tier with restrictions.
- Must upgrade to Standard within 12 months.
- Legitimate posting requires Community Management API with Partner approval.
- Unofficial Selenium-based tools violate TOS and risk account bans.
