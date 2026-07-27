# Tru8 Visibility Plan — 2026-06-27

**Trigger:** Zero Google impressions. **Root cause:** *not* technical SEO (already strong — server-side Metadata API, JSON-LD, SSR, llms.txt, OG images all present and correct). The real gap is a brand-new, zero-authority domain with **no off-site footprint**. Basis: a deep-research run (15 verified / 10 refuted claims, 28 sources) + a full on-site SEO audit. Both agree: the on-site work is mostly done; visibility now comes from off-site authority and AI-citability.

---

## SHIPPED this session (on-site, code)

| Commit | Change |
|--------|--------|
| `ee31d87` | Apex `trueight.com` → `www` **308 redirect** — canonical-host consolidation. **Verified live.** |
| `38b4a39` | "verification" → "research" positioning copy (hero, spine, metadata, JSON-LD, footer, OG); sitemap +3 missing routes; canonicals on 4 legal pages. |
| `362cc5b` | Homepage **FAQ section + FAQPage JSON-LD** (answer-first, server-rendered); explicit **AI-crawler allow rules** in robots.txt (GPTBot/ClaudeBot/PerplexityBot/Google-Extended etc.). |

---

## OFF-SITE — FOUNDER ACTIONS (the dominant lever — only you can do these)

> Research finding (high confidence, Ahrefs 75k brands): **brand web mentions correlate 0.664 with AI visibility vs 0.218 for backlinks.** For a zero-authority site, getting *named across the open web* matters more than links. Correlational, not causal — but the direction is strong and consistent.

Ranked by impact:

1. **Google Search Console hygiene** — remove the errored `robots.txt` row from the Sitemaps tool (keep only `sitemap.xml`). Use URL Inspection → Request Indexing for `/`, `/research`, `/compare`, `/developers`, `/pricing`. Watch the Coverage/Pages report over the next 1–2 weeks.
2. **Bing Webmaster Tools** — add + verify the site, submit the sitemap. Bing's index feeds ChatGPT search, so this is AEO infrastructure, not just "Bing traffic".
3. **Seed brand mentions where LLMs actually cite** (authentic participation, *never* spam — Google now classifies manipulated AI-visibility as spam):
   - **Reddit** — Perplexity cites Reddit heavily. Genuinely help in communities like r/journalism, r/OSINT, r/datajournalism, r/AcademicPsychology, r/AskHistorians-adjacent research subs. Mention Tru8 only where it actually answers the question.
   - **Hacker News** — a "Show HN" post (demo check `TRU-8723-1E97`), and be present in the comments. Dev-tool framing fits HN.
   - **IndieHackers / relevant Slack/Discord communities** for researchers + AI builders.
4. **SaaS / AI directories** — durable backlinks + discovery surface. (Specific high-value list not yet verified — flagged as an open research item below.)
5. **Wikipedia** — ChatGPT draws ~48% of citations from Wikipedia. Where Tru8 is a *legitimately relevant* external resource on an existing article, add it following Wikipedia norms. Do **not** self-promote or create a thin page.
6. **Published transcripts** — podcasts / video appearances *with transcripts on your own pages* correlate with AI Overview visibility. Repurpose any talk/demo as a transcript page.

---

## ON-SITE BACKLOG (the continuous loop works these, one vetted item per cycle)

- **A5 — `/r/[id]` public report pages**: confirm they emit clean SSR HTML, are indexable, and are well-structured. These are your *unique-data citable surface* — the one legitimate form of programmatic SEO that still ranks in 2026.
- **Direct-answer opening lines** (first ~100 words) on `/research`, `/compare`, `/developers` — the answer-first structure AI engines quote.
- **FAQ + FAQPage schema** on `/developers` and `/pricing` (homepage done).
- **Internal linking** between marketing pages and the two blog posts.
- **Core Web Vitals** — reduce client JS on marketing pages where feasible (several Stitch components are `'use client'`).

---

## DO NOT DO (refuted in research / penalised in 2026)

- ❌ **Mass / automated content generation** — "scaled content abuse"; 50–90% traffic drops under Google's 2026 spam/core updates. *This is why the continuous loop does NOT pump out blog posts.*
- ❌ Bare programmatic/template pages without unique per-page data.
- ❌ Chasing specific GEO "uplift %" tactics (the +41% statistics / +115% external-sources claims were **refuted** in verification).
- ❌ Treating schema as a magic rich-result unlock or an AI-citation prerequisite (**refuted** — schema is a minor signal; structure/clarity matter more).
- ❌ Manipulating AI Overviews / biased listicles — Google classifies this as spam (May 2026).

---

## Open research questions (unresolved — revisit)

- Does `llms.txt` actually influence LLM retrieval/citation in 2026? No surviving evidence either way. We keep ours (harmless); don't over-invest.
- Which specific directories/communities yield fastest week-one credibility for a research/dev tool? No concrete list survived verification.

---

## Continuous-loop remit

Each cycle: (1) confirm shipped items still healthy (redirect / sitemap / robots / build green); (2) implement **one** vetted on-site backlog item — build, verify in rendered HTML, commit; (3) surface the next off-site action for the founder. **No content spam, ever.**
