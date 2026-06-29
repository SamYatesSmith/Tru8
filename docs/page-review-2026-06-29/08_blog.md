# Blog index  /blog
> Pre-launch page audit · researcher-buyer lens · 2026-06-29
> Ground truth = current code; every finding was adversarially verified against shipped source.
> This document supersedes nothing. It is the pre-launch review only.

**Buyer fit:** 2/5 — currently speaks to **developer**

The page's actual substance is the subtitle and two post excerpts, and all three are developer/agent-framed: subtitle 'News, updates, and insights from Tru8 — platform, API, and agent integrations'; post 1 'available as an API and MCP server... for agents, developer tools, and automated workflows'; post 2 'dashboard, API, and MCP server for AI agents'. A journalist/analyst/policy researcher who must SEE evidence for-and-against and defend their sourcing finds nothing addressed to them — no post about the evidence record, receipts, no-verdict framing, or research workflow. The researcher path (/research) is not even surfaced from this content.

**Verifier check:** CONFIRMED — score 2, audience = developer/agent, is correct and well-grounded. Re-reading web/app/blog/page.tsx: the subtitle (line 56 "News, updates, and insights from Tru8 — platform, API, and agent integrations"), excerpt 1 (line 17 "...for agents, developer tools, and automated workflows") and excerpt 2 (line 24 "...dashboard, API, and MCP server for AI agents") are the page's entire substance and all three are developer/agent-framed. There is nothing for the show-your-working researcher — no mention of for-and-against, receipts, the evidence record, or no-verdict framing, and /research is not surfaced. Two corrections that make the verdict WORSE, not better: (1) the SEO meta description itself (line 9 "...including the API, MCP server, and agent integrations") is also developer-skewed, so even the SERP snippet a searching researcher sees steers away; (2) both linked post detail pages (e.g. evidence-research-for-agents/page.tsx) are wholly developer/agent-framed, so the drift is the whole blog section, not just the index.

**Overall:** A clean, restrained list page that is technically on-brand but does NOT use the shipped document-grammar system (no numbered SheetHeader, mono spine, or 2px orange top rule) the way the homepage and record sheets do, so it reads as a generic blog rather than a Tru8 datasheet. More importantly for the fixed buyer, every word here — the subtitle and both post excerpts — speaks to developers/agents (API, MCP server, agent integrations); there is nothing for the show-your-working researcher. As a low-traffic surface the defects are mostly minor, but the positioning drift and the document-grammar inconsistency are the two worth fixing.

## Verified findings

### MAJOR

**[positioning] All visible copy targets developers/agents, none speaks to the researcher buyer**  _( confirmed )_
- **Evidence:** Confirmed verbatim: subtitle (page.tsx:56), excerpt 1 (page.tsx:17 '...agents, developer tools, and automated workflows'), excerpt 2 (page.tsx:24 '...dashboard, API, and MCP server for AI agents'). These three strings are the page's whole substance.
- **Why it matters (buyer):** Per the fixed lens, drift to a developer/agent audience is a defect. A journalist/analyst landing here sees zero signal that Tru8's for-and-against evidence record and receipts are for them.
- **Fix:** Broaden the subtitle to buyer-inclusive, currency-neutral framing, e.g. 'How Tru8 organizes the evidence behind factual claims — for researchers, plus notes on the API and integrations.' Add at least one researcher-framed post (defending sourcing / the evidence record / no-verdict).
- **Verifier:** Strongest finding, correctly severity-rated and lock-clean (no forbidden terms in the suggested rewrite). Understated if anything — the meta description (line 9) and both linked detail pages share the same drift (see missed findings).

### MINOR

**[aesthetic] Page ignores the shipped document-grammar system used by the homepage**  _( adjusted )_
- **Evidence:** Confirmed in source: header is ad-hoc — eyebrow `<div className="font-mono text-[10px] tracking-[0.3em] uppercase text-zinc-400 mb-4">Publication Archive</div>` + `<h1 className="...font-bold">Blog</h1>` (page.tsx:49-58). The shipped SheetHeader device exists (components/marketing/sheet-header.tsx: border-t rule + `w-2 h-2 bg-accent rotate-45` glyph + two-digit number + uppercase label + mono ref) and is NOT used here.
- **Why it matters (buyer):** The researcher judges credibility partly by visual coherence; a blog that looks like a different, plainer product than the homepage undercuts the 'evidence infrastructure' positioning and the Stripe/Linear/Vercel restraint bar.
- **Fix:** Use SheetHeader for the page header (e.g. number "" + label "PUBLICATION ARCHIVE") to inherit the rotated bg-accent glyph and 1px top rule, matching the homepage. Hairline-only, no new panels.
- **Verifier:** Real and correctly grounded — SheetHeader is the genuine signature device. Downgraded major→minor: /blog is low-traffic (reviewer's own overall note says defects are 'mostly minor'), the page is otherwise fully on-token, and the blog sub-surface is internally consistent (both /blog/[slug] detail pages use the same ad-hoc header), so it reads as a deliberate sub-system rather than a one-off break.

**[aesthetic] font-bold headings break the size-is-hierarchy rule**  _( confirmed )_
- **Evidence:** Confirmed: `<h1 className="text-3xl sm:text-4xl md:text-5xl font-bold text-zinc-900 mb-4">Blog</h1>` (page.tsx:52) and `<h2 className="text-xl md:text-2xl font-bold ...">` (page.tsx:74). Verified the lock against shipped code: stitch-hero.tsx:39 uses `font-normal` on the h1 with a single bold word (`<span className="font-bold">before it ships.</span>` line 42).
- **Why it matters (buyer):** The baseline locks headings to font-normal with SIZE as the hierarchy lever and bold reserved for the hero h1 emphasis word + preview labels. Bold headings here read heavier and off-system versus the rest of the marketing surface.
- **Fix:** Set the h1 and post h2s to `font-normal` and let the size scale carry hierarchy, matching stitch-hero/stitch-record.
- **Verifier:** Grounded against actual shipped homepage code, not just the rubric — the hero genuinely is font-normal + one bold word. Fix stays inside the locks.

**[accessibility] zinc-400 low-contrast text on eyebrow, back link, and post meta**  _( confirmed )_
- **Evidence:** Confirmed: eyebrow `text-zinc-400` (page.tsx:49), Back-to-Home `text-zinc-400` (page.tsx:41), post date/readtime row `text-zinc-400` (page.tsx:68). zinc-400 (#9CA3AF) on white ≈2.5:1, below WCAG AA 4.5:1.
- **Why it matters (buyer):** Below WCAG AA 4.5:1 for the small mono meta text the researcher scans to date/triage posts; the baseline explicitly warns about zinc-400 low-contrast traps.
- **Fix:** Use `text-zinc-500` (≈4.6:1) for the eyebrow and the date/read-time meta; keep hover affordances. The 10px mono size makes legibility more important.
- **Verifier:** Grounded; the same zinc-400 meta pattern recurs on the detail pages, so a single token swap is worth doing across the blog section.

**[aesthetic] Whole post title flips to orange on hover — heavier than the mark/stroke accent discipline**  _( confirmed )_
- **Evidence:** Confirmed: `<h2 className="... group-hover:text-accent transition-colors">` (page.tsx:74) recolours the entire title to #EA580C on hover. Card already has `hover:border-black` (line 66) and a Read-more arrow gap-shift (line 82).
- **Why it matters (buyer):** The system budgets orange as hairline marks/seals/row-numbers, not large filled type; a full orange heading on hover is a bigger accent surface than the document grammar elsewhere allows, weakening the restraint cue researchers read as quality.
- **Fix:** Drop `group-hover:text-accent`; rely on the existing border-darken + arrow gap-shift, or limit accent to the arrow, keeping the title text-zinc-900.
- **Verifier:** Real and consistent with the 'orange = hairline mark/stroke, never large fill' lock. Minor is the right severity — hover-only, low-traffic.

**[ia] No Blog/ItemList JSON-LD on a page that exists for SEO**  _( confirmed )_
- **Evidence:** Confirmed: metadata exports only title/description/canonical (page.tsx:7-11), no structured data. Verified the comparison claim against code — app/compare/page.tsx, app/developers/page.tsx, app/page.tsx and app/r/[id]/page.tsx all contain ld+json; /blog does not.
- **Why it matters (buyer):** Blog/ItemList + BlogPosting schema improves how these posts surface in search, the dominant lever for a zero-authority domain trying to reach researchers.
- **Fix:** Add a Blog/ItemList JSON-LD listing both posts (headline/url/datePublished), consistent with /compare and /developers.
- **Verifier:** Grounded and verified the cited precedent exists in shipped code. Sound for the visibility/SEO push on a zero-authority domain.

### NIT

**[copy] UK-style date format on a US-spelling marketing surface**  _( confirmed )_
- **Evidence:** Confirmed: `date: '25 March 2026'` (page.tsx:18) and `'6 January 2026'` (page.tsx:25). Same UK format on detail headers (e.g. evidence-research-for-agents/page.tsx:52).
- **Why it matters (buyer):** Minor consistency: US readers expect 'March 25, 2026'. Low stakes but the locale lock is explicit for marketing.
- **Fix:** Render 'March 25, 2026' / 'January 6, 2026' on this marketing surface; keep UK formats on product UI/legal.
- **Verifier:** Correctly grounded; nit is right. Note the same fix applies to the detail pages for consistency.

**[ia] Redundant 'Back to Home' link above a full nav**  _( confirmed )_
- **Evidence:** Confirmed: `<Link href="/" ...><ArrowLeft/> Back to Home</Link>` (page.tsx:39-45) sits under the fixed <Navigation/> (line 33) whose logo already links home.
- **Why it matters (buyer):** Harmless but adds a second, lower-contrast home affordance that the document-grammar surfaces generally omit; tightening reinforces the composed look.
- **Fix:** Optional — drop it or restyle as a mono breadcrumb to fit the system.
- **Verifier:** Accurate, low stakes. Genuinely optional.

## Additional issues caught in verification

**[MAJOR · positioning] Compliance/regulatory framing in a linked blog post — lock violation**
- **Evidence:** On the post linked from this index (app/blog/evidence-research-for-agents/page.tsx:186): 'Compliance and risk — verifying claims in regulatory filings, reports, or public statements'. The positioning lock explicitly forbids compliance/regulatory framing (no compliance demand; never claim it). Same page line 184 'verifying claims in regulatory filings' compounds it.
- **Fix:** Remove the compliance/risk use-case (or recast as a concrete user action — publish/re-check/escalate — with no regulatory claim). Scope note: this is on /blog/[slug], not the /blog index, but it is part of the blog surface directly reachable from this route.

**[MINOR · ia] SEO meta description is developer/agent-skewed — the SERP snippet steers researchers away**
- **Evidence:** page.tsx:9 description = 'News, updates, and insights on AI-powered evidence research from Tru8 — including the API, MCP server, and agent integrations.' This is the snippet a searching researcher sees in Google before they ever click. The reviewer's positioning finding only addresses the on-page subtitle/excerpts, not this meta string.
- **Fix:** Rewrite the description to lead with the researcher value (organizing the evidence behind a claim, for-and-against, sourcing you can defend) and mention API/integrations second; stays currency-neutral and lock-clean.

**[NIT · ia] Thin <title>Blog</title> and no OpenGraph on a page built for discovery**
- **Evidence:** page.tsx:8 title is just 'Blog' and metadata has no openGraph block (only title/description/canonical, lines 7-11), whereas the detail page carries a descriptive title + openGraph (evidence-research-for-agents/page.tsx:8,23-29). For the active visibility push a bare 'Blog' title and missing OG card under-serve both search and social shares.
- **Fix:** Give a descriptive title (e.g. 'Tru8 Blog — Notes on Evidence Research') and add a minimal openGraph block, consistent with the detail page. Defer the OG image to the open I-06 visual review.

## Strengths to keep
- Stays inside the core Stitch tokens: 1px borders (border-zinc-200, hover:border-black), no drop-shadows, no gradients, square corners, single orange accent — on-system in spirit.
- Mono eyebrow and mono uppercase meta row (font-mono text-[10px] tracking-[0.3em]/widest) correctly use the load-bearing JetBrains Mono for labels/dates.
- Language-lock clean: no verdict/confidence/credibility language anywhere in the visible copy; framing stays on evidence research and the record.
- Clear, restrained card pattern with a tidy hover affordance (border darken + Read-more arrow gap-shift) and correct heading order (single h1, h2 per post).
- Live rendered page exactly matches source — no drift between code and what ships, and canonical metadata is set.
