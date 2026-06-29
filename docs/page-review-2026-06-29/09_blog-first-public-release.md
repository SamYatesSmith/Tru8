# Blog: first-public-release
> Pre-launch page audit · researcher-buyer lens · 2026-06-29
> Ground truth = current code; every finding was adversarially verified against shipped source.
> This document supersedes nothing. It is the pre-launch review only.

**Buyer fit:** 3/5 — currently speaks to **mixed**

The 'How Tru8 Might Be Useful' section addresses Journalists and Editors, Students and Academics, Content Creators and YouTubers, Professionals and Analysts AND 'Everyday Use' ('Settle disagreements with evidence rather than opinion'), then closes with a full 'For Developers and AI Agents' section. The researcher buyer is genuinely served ('Quickly cross-reference claims before publication', 'Identify where sources agree and where they diverge', 'Export sources and citations for bibliographies') but is one audience of five, so the page reads everyman rather than focused. The defining researcher value props — no verdict, evidence for-and-against, receipts/excluded-with-reasons you can DEFEND — appear only weakly ('where they agree, and where they don't', line 86; provenance only in the dev section).

**Verifier check:** Confirmed: score 3 / "mixed" is correct and grounded. The "How Tru8 Might Be Useful" section runs five human audience blocks — Journalists and Editors (line 95), Students and Academics (102), Content Creators and YouTubers (110), Professionals and Analysts (118), Everyday Use (125) — then a full "For Developers and AI Agents" section (line 156). The researcher buyer is genuinely served ("Quickly cross-reference claims before publication" L97; "Identify where sources agree and where they diverge" L99; "Export sources and citations for bibliographies" L107) but is one of five voices, so the page reads everyman. The defining researcher hooks — no verdict, evidence for-and-against, every exclusion with a reason you can DEFEND — are stated only weakly for humans ("where they agree, and where they don't" L86) and the explicit provenance/receipts language ("what was excluded (with reasons)" L171) is parked in the developer section. So the page is on-topic but not researcher-focused; 3/mixed stands.

**Overall:** A readable, honest launch post that is on-palette (zinc scale, white, single orange accent, 1px borders, no gradients/shadows) and largely language-lock compliant, but it abandons the shipped Stitch document-grammar entirely and reads as a generic prose blog template. For the show-your-working researcher it is only partially on-target: the researcher use-cases are present but buried in a broad journalists-to-everyday-users-to-developers sweep, and the page's strongest researcher hooks (no verdict, for-and-against, defend your sourcing) are never stated plainly. Substance is fine; consistency and audience focus are the weak points.

## Verified findings

### MAJOR

**[aesthetic] Page abandons the Stitch document-grammar system — generic blog template**  _( confirmed )_
- **Evidence:** page.tsx has no SheetHeader, no mono eyebrow tag, no 2px orange top rule, no rotated registration glyph, no mono left spine, no 1px document frame. Layout is a plain `container mx-auto px-4 md:px-6 max-w-3xl` (line 20) wrapping undifferentiated prose; the only system nod is the two mono date/author eyebrows (lines 32, 42).
- **Why it matters (buyer):** The homepage and marketing pages present a composed, distinctive 'document grammar' that signals rigour — exactly the credibility cue a researcher weighs before trusting a sourcing tool. A launch blog that looks like a default Tailwind article breaks that signal at a high-traffic SEO entry point.
- **Fix:** Wrap the article in the marketing shell: 2px orange top rule + a numbered mono SheetHeader-style post header, and the mono left spine on xl+, while keeping the narrow prose column — so the post reads as part of Tru8's document grammar, not a default CMS template.
- **Verifier:** Grounded exactly: line 20 and the absence of every Stitch construct confirmed against current source. Highest-leverage finding for a high-traffic SEO entry point where a researcher first weighs credibility. Confirmed at major.

**[aesthetic] All headings are font-bold — violates 'size is the hierarchy lever, not weight'**  _( confirmed )_
- **Evidence:** h1 `font-bold` (line 38); every h2 `text-2xl md:text-3xl font-bold` (lines 57, 75, 89, 137, 156, 179, 197); every h3 `text-lg md:text-xl font-bold` (lines 95, 102, 110, 118, 125); CTA h3 `font-bold` (line 210); lead `font-medium` (line 49).
- **Why it matters (buyer):** The shipped system reserves bold for the hero h1 emphasis word and preview labels only; size carries hierarchy. Blanket bold makes the page louder and less considered than the rest of the site, undercutting the restrained, Stripe/Linear-grade tone that reassures a discerning researcher.
- **Fix:** Switch headings to font-normal and let the existing size steps (text-5xl h1 → 3xl h2 → xl h3) carry hierarchy; reserve bold for at most the single lead line, matching the locked document-grammar rule.
- **Verifier:** All cited line numbers and classes verified. Overlaps thematically with finding 1 but is a distinct, explicit lock violation ('font-normal headings — SIZE is the hierarchy lever') applied page-wide, so it earns its own entry. Confirmed at major.

**[positioning] Everyman breadth dilutes the show-your-working researcher focus; no-verdict hook absent for humans**  _( adjusted )_
- **Evidence:** Five human audience blocks including 'Everyday Use' (lines 125-131: 'Check headlines that feel exaggerated', 'Settle disagreements with evidence rather than opinion') plus a full developer section (156). The for-and-against / receipts / no-verdict framing appears only weakly for humans ('where they agree, and where they don't', line 86); 'what was excluded (with reasons)' is confined to the dev section (line 171).
- **Fix:** Open the human section with the researcher value stated plainly — evidence for and against each claim, every source shown, every exclusion with a reason, no verdict imposed, so you can defend your sourcing — then subordinate the other audiences.
- **Verifier:** Evidence verified. Upgraded minor → major: the buyer is the FIXED lens of this review and this is the page's central defect (it sells general convenience to everyone rather than defensibility to the one buyer it must convert). Severity raised to match its weight.

### MINOR

**[accessibility] zinc-400 low-contrast text on white (the documented trap)**  _( adjusted )_
- **Evidence:** Date/read-time eyebrow `text-zinc-400` (line 32); author `text-zinc-400` (line 42); both 'Back to Blog' links `text-zinc-400` (lines 24, 228).
- **Why it matters (buyer):** zinc-400 (#9CA3AF) on white is ~2.5:1 — below WCAG AA 4.5:1 for the small mono metadata. Researchers often work in bright/print contexts and on older displays; failing metadata contrast looks careless on a tool whose whole pitch is legibility of evidence.
- **Fix:** Use text-zinc-500 for the back links and text-zinc-500/600 for the date and author eyebrows to clear WCAG AA while staying muted.
- **Verifier:** All four occurrences confirmed; the rubric explicitly warns of this trap so the finding is real. Adjusted only to correct the reviewer's hex: zinc-400 is #A1A1AA (≈2.6:1 on white), not #9CA3AF (that is gray-400). The sub-AA contrast point stands; severity minor is right.

**[copy] 'Verify claims' frames the claim as the object of verification**  _( confirmed )_
- **Evidence:** Line 112: 'Verify claims before including them in videos or podcasts'. Contrast the on-side line 97 'Quickly cross-reference claims before publication'.
- **Why it matters (buyer):** The language lock requires the object of verification to be the EVIDENCE / the RECORD, never the claim's truth ('verify the evidence' is permitted; verifying a claim implies a true/false verdict). For the researcher, 'no verdict' is the feature — this line quietly contradicts it.
- **Fix:** Reword so evidence is the object, e.g. 'Check the evidence behind a claim before including it in videos or podcasts.'
- **Verifier:** Quote verified verbatim at line 112. 'Verify claims' implies adjudicating truth, which softly contradicts the no-verdict lock that is the researcher's core feature. Confirmed at minor.

**[copy] 'evidence report' is off the locked term (evidence record / verification record)**  _( confirmed )_
- **Evidence:** Line 148: 'Does the evidence report help you understand the claim?' The locked nouns are 'evidence record' / 'verification record'.
- **Why it matters (buyer):** Consistent naming of the core artefact is what lets a researcher cite and reference it confidently; 'report' subtly implies an editorialised conclusion, which the product deliberately does not produce.
- **Fix:** Use 'evidence record' (or 'structured evidence record') to match the locked artefact name.
- **Verifier:** Verified verbatim at line 148. 'Report' implies an editorialised conclusion the product deliberately avoids; consistent artefact naming matters for a researcher who must cite it. Confirmed at minor.

**[copy] Primary CTA routes to the dev-first homepage; free-offer wording weakly flagged**  _( adjusted )_
- **Evidence:** CTA h3 'Ready to try Tru8?' (line 210), body 'Try Tru8. Your first checks are free.' (line 214), button links `href="/"` (lines 216-221). Verified: the homepage hero's primary CTA is 'Get API Key' → /developers (components/marketing/stitch-hero.tsx lines 59-64), with /research as a secondary link; /research exists (app/research/).
- **Fix:** Point the primary CTA at /research (the researcher-led app) rather than '/'. Leave the free-trial wording as is unless the founder wants it changed — it is currency-neutral.
- **Verifier:** Adjusted. The CTA-routing half is fully grounded and the fix is sound (verified /research exists and '/' lands on a 'Get API Key' dev hero). The free-wording half is weak and I reject it: a Free Trial tier exists in the product, 'free' contains no price NUMBER, so it does not breach the currency-gating lock and need not be 'confirmed with the founder'. Kept minor, recommendation narrowed to the routing fix.

**[ia] No Article/BlogPosting JSON-LD for a blog post**  _( confirmed )_
- **Evidence:** metadata (lines 7-11) sets title, description and `openGraph.publishedTime` only; no <script type=application/ld+json> Article schema anywhere in the file, unlike the FAQPage schema shipped on /, /compare, /developers.
- **Why it matters (buyer):** A new zero-authority domain needs every indexability lever; Article schema (author, datePublished, headline) helps this post surface for researchers searching for the tool. It is a cheap, on-system addition.
- **Fix:** Add a BlogPosting JSON-LD block (headline, author 'Sam Yates-Smith', datePublished 2026-01-06, publisher Tru8) following the existing on-site schema pattern.
- **Verifier:** Confirmed: no JSON-LD present in source; cheap indexability lever for a zero-authority domain. Minor is correct.

### NIT

**[accessibility] CTA heading is an h3 sitting outside the article heading flow**  _( adjusted )_
- **Evidence:** The standalone CTA box uses <h3> 'Ready to try Tru8?' (line 210) directly after the last article <h2> 'A Final Note' (line 197).
- **Fix:** Promote the CTA heading to h2 (or wrap it in its own section) so it reads as a top-level section rather than a sub-heading of 'A Final Note'.
- **Verifier:** Adjusted: the reviewer's stated rationale ('level jump'/'skip in the outline') is inaccurate — h2 (line 197) → h3 (line 210) is a valid one-level descent, not a skip. The real, lesser issue is semantic: an orphaned h3 reads as a child of the final article section. Kept at nit with corrected reasoning.

## Additional issues caught in verification

**[MINOR · ia] Meta description leads with the dev/agent pitch in search results**
- **Evidence:** metadata.description (line 9): 'The first public release of Tru8 — an evidence research platform with a dashboard, API, and MCP server for AI agents.' This is the snippet a researcher sees in search results, and it foregrounds API + MCP server for AI agents, not the researcher value (every source shown, evidence for and against, no verdict). Mirrors the body's dev drift on the SEO surface itself, working against the researcher buyer at the search-result entry point on a zero-authority domain.
- **Fix:** Rewrite the description researcher-first, e.g. lead with 'See the evidence for and against any claim — every source shown, every exclusion explained, no verdict imposed' and keep the API/MCP mention as a trailing clause.

**[MINOR · content] Over-precise '~15 seconds' latency claim in evergreen copy**
- **Evidence:** Line 166: 'Quick — a faster analysis (~15 seconds) with core evidence retrieval'. A specific performance number baked into permanent launch copy; the honest-framing lock discourages precise performance/benchmark claims the page cannot stand behind, and a researcher trusts a sourcing tool partly on its restraint.
- **Fix:** Hedge to a qualitative claim ('a faster analysis covering core evidence') or confirm the figure is reliable before keeping a hard number.

**[NIT · positioning] The page's single orange accent is spent on the developer-portal link**
- **Evidence:** The only `text-accent` (orange) usage on the entire page is the 'developer portal' link inside the dev section (line 176); every other interactive element (back links, CTA button) is zinc. The one brand-colour cue on a researcher-toned post visually points to the developer audience, reinforcing the same drift the copy shows.
- **Fix:** If the accent is used at all, spend it on a researcher-facing moment (the primary CTA or a key researcher value line) rather than solely on the developer link.

## Strengths to keep
- Colour and material discipline is intact: zinc neutral scale, white surface, a single orange accent used only as the 'developer portal' link (`text-accent`, line 176), 1px borders (CTA box line 209, divider line 225), no gradients, no drop-shadows, square corners — fully on-token.
- Language-lock compliance is strong for the human-facing copy: 'decide for themselves' (line 72), 'showing what sources say, where they agree, and where they don't' (line 86), 'what was excluded (with reasons)' = receipts (line 171), and full provenance described — no verdict labels, no traffic-light colours, no 'is this true?' framing.
- Honest, humble launch voice that fits the brand: 'There's no big announcement behind it', and 'Knowing where Tru8 doesn't help is just as important as knowing where it does' (line 153) — credibility-building for a sceptical researcher.
- Receipts/provenance and tier+type classification are surfaced accurately ('which sources were found, how they were classified, and what was excluded', '30+ sources', 'tier and type classification') — consistent with the product and the locks.
- The mono date/author eyebrows (`font-mono text-[10px] tracking-widest uppercase`, lines 32, 42) are the one genuine nod to the document grammar and are the right instinct to extend.
- US marketing spelling is consistent (analysing/analysis rendered as US 'analyzing'-style; no UK spellings leak into this marketing page).
