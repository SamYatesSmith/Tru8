# Blog: evidence-research-for-agents
> Pre-launch page audit · researcher-buyer lens · 2026-06-29
> Ground truth = current code; every finding was adversarially verified against shipped source.
> This document supersedes nothing. It is the pre-launch review only.

**Buyer fit:** 2/5 — currently speaks to **developer**

The page is explicitly built for API/MCP integrators: h1 'Evidence Research for AI Agents and Developer Tools', primary CTA 'Developer Portal' (x2), and a use-case list dominated by agent pipelines, content moderation, browser extensions. The researcher buyer ('show-your-working' journalist/analyst/policy researcher) appears only once, mid-list: 'Research tools — integrating structured evidence search into academic or journalistic workflows'. No mention of the human review console or /research, no for-and-against-as-defensible-sourcing angle. Per the review lens this developer-first framing is the defect to flag, not the buyer — but as a standalone blog post about the API it is at least on-topic, which is why it is a 2 not a 1.

**Verifier check:** Confirmed. The page is genuinely developer/agent-led and the researcher buyer is nearly absent. h1 (line 57-59) "Evidence Research for AI Agents and Developer Tools"; lead (line 68-70) addresses "developers, AI agents, and automated workflows"; the only researcher-facing line is one buried list item (line 185) "Research tools — integrating structured evidence search into academic or journalistic workflows"; the sole dashboard/console reference is a passing clause on line 112. Both outbound links go to /developers (inline line 197 + CTA button line 222) — no link to /research or the human console. As a standalone blog post about the API this is on-topic, so the reviewer's score of 2 (not 1) is fair; the developer-first framing is the defect to flag, not a reason to re-open the buyer.

**Overall:** This is a competently-written but entirely developer/agent-led blog post that drifts hard from the fixed researcher buyer — the title, primary CTA, and use-case framing all address API integrators, with the journalist/analyst getting a single buried line. Body copy is largely language-lock compliant ("This isn't a summary or a verdict. It's a structured dataset"; for-and-against framing intact), but it carries two real lock violations (a compliance/regulatory use-case and repeated "verify claims" framing) plus a "fact checking API" SEO keyword. Visually it ignores the shipped Stitch document-grammar system entirely — generic font-bold article template, no SheetHeader, no mono eyebrow/spine — so it reads off-brand against the homepage and /developers.

## Verified findings

### MAJOR

**[positioning] Page is agent/developer-led end to end; researcher buyer is nearly absent**  _( confirmed )_
- **Evidence:** h1 line 57-59 'Evidence Research for AI Agents and Developer Tools'; lead line 68-70 '...so developers, AI agents, and automated workflows can run structured, multi-source analysis programmatically'; inline link line 197 and CTA line 218-222 both point to /developers; the lone researcher line is list item line 185.
- **Why it matters (buyer):** The 'show-your-working' researcher who lands here from search finds nothing addressed to them — no human console, no 'defend your sourcing', no for/against-as-evidence-trail. They bounce, and the page reinforces the homepage's developer-first drift instead of widening the funnel toward the fixed buyer.
- **Fix:** Keep the post (the API/MCP is a legitimate dev topic) but add a short researcher-facing paragraph and a secondary link to /research — 'the same evidence record, in a console built for people who must defend their sourcing' — and lead the use-case list with the journalist/analyst case instead of burying it fourth.
- **Verifier:** All quotes and line numbers verified verbatim in current source. Fix stays inside the locks and targets the fixed buyer. Confirmed at major.

**[copy] Compliance/regulatory framing is a forbidden frame**  _( confirmed )_
- **Evidence:** Use-case list, page.tsx line 186: 'Compliance and risk — verifying claims in regulatory filings, reports, or public statements'.
- **Why it matters (buyer):** The positioning lock explicitly forbids compliance/regulatory framing (no compliance/regulatory positioning; no policy engine exists). Promising 'compliance and risk' verification overstates what the tool is and pulls away from the honest evidence-record story the researcher buyer trusts.
- **Fix:** Replace with an honest user action inside the locks, e.g. 'Editorial review — surfacing the supporting and challenging evidence behind claims in reports or public statements before they're published.' Drop 'compliance', 'regulatory', and 'risk'.
- **Verifier:** Verified verbatim at line 186. Directly violates the positioning lock (no compliance/regulatory framing; no policy engine). It compounds with the verify-claims violation on the same line. Confirmed at major.

**[copy] Repeated 'verify claims' framing puts the verdict object on the claim, not the evidence**  _( confirmed )_
- **Evidence:** Line 144 'Verify claims before presenting them to users'; line 183 '...so claims are checked before being surfaced to users'; metadata keyword line 17 'claim verification API'.
- **Why it matters (buyer):** The lock requires the object of verification to always be the EVIDENCE / the RECORD, never 'the claim is true/false'. 'Verify claims before presenting' reads as a true/false gate — exactly the verdict implication the no-verdict researcher buyer is told this product avoids. It quietly contradicts the page's own line 'This isn't a summary or a verdict.'
- **Fix:** Reframe onto the evidence/record: 'Surface the evidence behind a claim before presenting it' / 'attach a structured evidence record to claims before they reach users'. Change the keyword to 'evidence verification API' or 'claim evidence API'.
- **Verifier:** All three instances verified. The lock requires the object of verification to be the evidence/record, never the claim's truth; 'verify claims before presenting' reads as a true/false gate and contradicts the page's own line 171 'This isn't a summary or a verdict.' Confirmed at major.

**[aesthetic] Page ignores the shipped Stitch document-grammar system**  _( confirmed )_
- **Evidence:** Grep of web/app/blog for SheetHeader|StitchSheet|bg-accent returns no matches; the page is a generic centered article (max-w-3xl, plain header with a zinc-400 mono date eyebrow). The document-grammar components exist and are used elsewhere (components/marketing/sheet-header.tsx + 7 stitch-* components).
- **Why it matters (buyer):** Against the homepage and /developers (Stripe/Linear/Vercel bar), this reads as a different, less considered product. A researcher evaluating credibility notices the inconsistency. The blog is a primary SEO landing surface in the current visibility push, so off-system first impressions cost trust.
- **Fix:** Bring the blog template onto document grammar: reuse the SheetHeader component (mono eyebrow + sheet number), the 2px orange top rule / rotated registration glyph, and JetBrains Mono for the date/byline, matching the homepage and /developers.
- **Verifier:** Confirmed the grep is empty and that SheetHeader/stitch-* are the shipped marketing system. needs_human_eye is appropriate for final pixel judgment. Confirmed at major.

### MINOR

**[aesthetic] font-bold headings throughout violate the 'size is the hierarchy lever, not weight' rule**  _( adjusted )_
- **Evidence:** h1 'font-bold' line 57; every h2 'font-bold' lines 76,92,124,154,174,191; every h3 'font-bold' lines 100,105,110,115; CTA h3 'font-bold' line 212.
- **Why it matters (buyer):** Blanket bold flattens the document-grammar hierarchy the rest of the site uses size and mono labels to create. It looks like a default blog theme, not the composed Tru8 system, undercutting the 'serious evidence infrastructure' impression the researcher is buying.
- **Fix:** Switch section headings to font-normal and let size + the mono eyebrow carry hierarchy, reserving bold for at most one hero emphasis word, per the document-grammar spec.
- **Verifier:** All classes verified. Real deviation, but it substantially overlaps finding 4 (same 'off-system' first impression) and is a weight-only issue rather than a structural one; rating it a second major double-counts the same defect. Adjusted to minor — it should be fixed as part of the same template pass.

**[copy] 'fact checking API' SEO keyword leans on a forbidden frame**  _( confirmed )_
- **Evidence:** metadata.keywords, page.tsx line 13: 'fact checking API'.
- **Why it matters (buyer):** Tru8's terminology lock is 'evidence research' not 'fact-checking'; the researcher buyer was chosen partly because 'no verdict' is a feature. Even in non-visible metadata, indexing on 'fact checking' attracts the wrong intent and contradicts the brand line.
- **Fix:** Replace with on-lock keywords already present in spirit: 'evidence research API', 'claim evidence API', 'source classification API'. Drop 'fact checking API'.
- **Verifier:** Verified at line 13. Terminology lock is 'evidence research' not 'fact-checking'; even in non-visible metadata it attracts the wrong search intent. Confirmed at minor.

**[ia] No Article/BlogPosting JSON-LD and no canonical on the post**  _( confirmed )_
- **Evidence:** page.tsx metadata (lines 7-30) has openGraph article fields but no JSON-LD script and no alternates.canonical; the blog index sets one (blog/page.tsx line 10 'alternates: { canonical: "/blog" }'), this post does not.
- **Why it matters (buyer):** During an active zero-impressions visibility push, a long-form post is the ideal candidate for BlogPosting structured data and a self-canonical. Missing both forfeits rich-result eligibility and clean indexing for a page meant to pull researchers/developers from search.
- **Fix:** Add BlogPosting JSON-LD (headline, datePublished 2026-03-25, author Sam Yates-Smith per line 62, publisher Tru8) and alternates: { canonical: '/blog/evidence-research-for-agents' }, mirroring the FAQPage pattern on /developers and /compare.
- **Verifier:** Verified the post lacks both and that the index has a canonical. Author/date in the recommendation match lines 62 and 52. Confirmed at minor.

**[accessibility] Low-contrast zinc-400 used for default link state and small mono eyebrows**  _( confirmed )_
- **Evidence:** Back links 'text-zinc-400' lines 43 and 230; date/byline mono eyebrows 'text-zinc-400' at text-[10px] lines 51 and 61; CTA subtext 'text-zinc-500' line 215.
- **Why it matters (buyer):** zinc-400 at 10px fails WCAG AA for body/UI text; the date, byline and back-navigation are the orientation cues a careful reader uses. This is the documented 'zinc-400 low-contrast trap'.
- **Fix:** Use zinc-500/600 for default link and eyebrow text (keep zinc-900 hover) and avoid 10px for load-bearing text; bump mono eyebrows to 11-12px per the document-grammar spec.
- **Verifier:** All classes verified. zinc-400 on white is ~2.6:1 and fails WCAG AA (the reviewer's hex #9CA3AF is actually Tailwind gray-400; zinc-400 is #a1a1aa, but the contrast conclusion is unchanged). Confirmed at minor.

### NIT

**[copy] Title-tag and h1 diverge; UK date format on a US-spelling marketing surface**  _( confirmed )_
- **Evidence:** title line 8 'Evidence Research for AI Agents, Developers, and MCP — Tru8 API' vs h1 line 58 'Evidence Research for AI Agents and Developer Tools'; date rendered '25 March 2026' line 52.
- **Why it matters (buyer):** Minor polish: a title/h1 mismatch is a small SEO/consistency smell, and date-format locale should match the marketing US convention used elsewhere.
- **Fix:** Align h1 and title around the core phrase, and standardize the date format to the US convention used on other marketing pages.
- **Verifier:** Both strings and the date verified verbatim. Genuinely a nit. Confirmed.

## Additional issues caught in verification

**[MINOR · ia] Page redefines openGraph without images, dropping the inherited default OG card**
- **Evidence:** page.tsx lines 23-29 set a page-level openGraph block (type, publishedTime, title, description) with NO images/siteName/locale. The root layout (layout.tsx lines 37-50) provides the default og:image '/api/og/default' plus siteName 'Tru8' and locale 'en_US'. Next.js merges metadata shallowly per top-level field, so a page-level openGraph object overrides the parent's — this post's social/search card loses its image, siteName, and locale.
- **Fix:** Add images (the default /api/og/default or a post-specific 1200x630 card), siteName 'Tru8', and locale 'en_US' to the page's openGraph block. During the active zero-impressions visibility push, an image-less card on a primary SEO landing page is a needless loss; verify the rendered <meta property="og:image"> after the change.

**[MINOR · ia] Thin internal-link graph — post links only to /developers**
- **Evidence:** The only outbound links in the article body are the inline 'developer portal' link (line 197) and the CTA 'Developer Portal' button (line 218-222), both to /developers. No contextual links to the homepage, /compare, /research, or the dashboard.
- **Fix:** Add 1-2 contextual internal links (e.g. to /research for the human console and to /compare) so the post passes link equity into other key surfaces and offers the researcher a route off the dev page. This also supports the visibility push's on-site linking.

**[NIT · content] Unverified latency claim '~15 seconds' on a public page**
- **Evidence:** page.tsx line 107: Quick Analysis 'completes in roughly 15 seconds.'
- **Fix:** Confirm the 15-second figure still matches current quick-mode behaviour before relying on it publicly; concrete performance numbers drift and an out-of-date latency claim dents credibility with the careful researcher. If unstable, soften to 'in seconds' rather than pinning a number.

## Strengths to keep
- Strong language-lock compliance in body copy: 'This isn't a summary or a verdict. It's a structured dataset that your application or agent can interpret, filter, and present however it needs to.' (page.tsx:171).
- Honest for-and-against framing intact: 'what supports each, what challenges it, what's missing' (line 69) and 'the relationship (supports, challenges, or provides context)' (line 165) — no verdict, no traffic-light colours.
- Receipts/no-hidden-curation invariant surfaced plainly: 'Nothing is hidden; exclusions are logged with reasons' (line 85) and 'receipts for every exclusion' (line 167).
- Tier/Type vocabulary used correctly (primary/reporting/commentary; data/official/news/analysis/opinion/academic) without sneaking in credibility scores.
- No invented prices — tiers (Lookup/Quick/Full/Smart) are described currency-neutral, respecting the price gate.
- Views are not named by profession anywhere; accent discipline is otherwise clean (single text-accent link on /developers, line 197).
