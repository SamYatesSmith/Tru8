# About  /about
> Pre-launch page audit · researcher-buyer lens · 2026-06-29
> Ground truth = current code; every finding was adversarially verified against shipped source.
> This document supersedes nothing. It is the pre-launch review only.

**Buyer fit:** 2/5 — currently speaks to **mixed**

It names the researcher once — "whether you're a professional analyst, a journalist, a researcher, or simply someone who reads the news and wants clarity" (line 63) — but the dominant register is consumer/wellness: "Most people don't have the time" (45), "No noise. / No pressure. / No agenda." (55-57), "calm, useful, and grounded" (106), "feel a little more confident" (106). None of the researcher's decision substance (for-and-against, receipts, the verification record, defensible sourcing) appears. It dilutes the fixed buyer into a general news reader.

**Verifier check:** CONFIRMED. The buyer_fit assessment is accurate and grounded. The page names the researcher exactly once at line 63 ("whether you're a professional analyst, a journalist, a researcher, or simply someone who reads the news and wants clarity"), but the dominant register is consumer/clarity-seeking: line 45 "Most people don't have the time — or the tools — to dig through dozens of sources", lines 55-58 "No noise. / No pressure. / No agenda. / Just clarity you can use.", line 67 "Make evidence accessible, calm, and clear", line 102 "they just want clarity", line 106 "calm, useful, and grounded" / "feel a little more confident". None of the show-your-working researcher's decision substance (for-and-against, receipts, the verification record, defensible sourcing, the six views) appears anywhere in the body. The audience line even demotes the researcher by trailing it with "or simply someone who reads the news" — the opposite of the fixed-buyer priority. Score 2 / "mixed" is fair. One correction: the metadata description (line 9) compounds this — "Built for anyone who wants clarity on what's being reported" hard-codes the general-consumer audience into the SEO surface too, which the reviewer did not flag (see missed_findings).

**Overall:** A warm, honest founder/mission page that is clean on the language lock but speaks to the wrong buyer: it repeatedly frames Tru8 for "someone who reads the news and wants clarity" rather than the show-your-working researcher who must defend their sourcing, and it carries none of that buyer's substance (for-and-against, receipts, the evidence record, the views). It also drifts off the shipped Stitch document-grammar system — no numbered SheetHeaders, no orange registration glyph/top-rule/left-spine, and font-bold on every heading where the system uses font-normal with size as the hierarchy lever — so it reads like a generic prose page rather than part of the same product.

## Verified findings

### MAJOR

**[positioning] Page is framed for a general news consumer, not the show-your-working researcher**  _( confirmed )_
- **Evidence:** Line 45 "Most people don't have the time — or the tools — to dig through dozens of sources"; lines 55-58 emphasis block "No noise.<br/>No pressure.<br/>No agenda.<br/><span text-accent>Just clarity you can use.</span>"; line 63 "...or simply someone who reads the news and wants clarity"; line 106 "feel a little more confident in the information they're faced with". All quotes verified verbatim in current source.
- **Why it matters (buyer):** The fixed buyer is a journalist/analyst/policy researcher who must SEE evidence for AND against and DEFEND their sourcing. Anxiety-reduction language ("calm", "No pressure", "confident") is the wrong promise for them and signals a mass-consumer product, undercutting credibility.
- **Fix:** Re-anchor on the researcher's job — seeing what supports and what challenges a claim, every exclusion carrying a receipt, the user forming a defensible view. Lead the audience line with the researcher and demote "anyone who reads the news" to a trailing clause. Keep the founder warmth.
- **Verifier:** Grounded and correct. This is the central defect of the page and the most important finding. Severity major is right — it is the dominant register across both sections, not an isolated line.

**[content] No researcher-relevant substance or proof — pure narrative + vibes**  _( confirmed )_
- **Evidence:** The only product description is line 49 "...searches across multiple source types, organises the evidence, and gives you a structured report you can explore." The body never mentions for-and-against, receipts/exclusions, the evidence record, the six views, the no-verdict edge, or the signed manifest. Verified by full read of lines 39-123.
- **Why it matters (buyer):** An About page is where a sceptical researcher decides whether to trust the tool's method. With zero concrete substance about HOW the record is built (and what it deliberately does not do — no verdict), the page gives them nothing to evaluate.
- **Fix:** Add one short on-system block stating the method in the buyer's terms: organizes evidence for and against each claim, shows what's missing, records why anything was excluded, never issues a verdict — "We organize; you decide." Adds substance and reinforces the no-verdict edge.
- **Verifier:** Confirmed. The page gives a sceptical researcher nothing concrete about HOW the record is built to evaluate trust. Recommendation stays inside the locks (no forbidden language, reinforces no-verdict).

**[aesthetic] Off the shipped document-grammar system (no SheetHeader, frame, spine, or glyph)**  _( confirmed )_
- **Evidence:** Eyebrows are hand-rolled "Module — Company Overview" (line 33) and "Module — Founder" (line 78), NOT the shared SheetHeader component. Confirmed SheetHeader exists at web/components/marketing/sheet-header.tsx and renders a two-digit number + "w-2 h-2 bg-accent rotate-45" registration glyph + uppercase mono label + datasheet ref. The about page does not import it. Layout is a plain centred container mx-auto ... max-w-4xl (line 20) vs the homepage's max-w-7xl document frame; no 2px orange top rule, no mono left spine.
- **Why it matters (buyer):** The document-grammar IS the brand's credibility signal (Stripe/Linear restraint). A generic prose page makes the About read as an afterthought disconnected from the product, weakening trust for a buyer who judges rigor by presentation.
- **Fix:** Replace the "Module —" eyebrows with the shared SheetHeader (e.g. 01 ORIGIN / 02 FOUNDER) and wrap content in the same top-rule/inset frame the homepage uses. Drop the bespoke "Module" vocabulary, which appears nowhere else in the codebase.
- **Verifier:** Confirmed against sheet-header.tsx and the about source. The "Module" vocabulary genuinely appears nowhere else. needs_human_eye flag is appropriate for the final composition. Real major.

### MINOR

**[aesthetic] font-bold on every heading violates the font-normal / size-is-the-lever rule**  _( adjusted )_
- **Evidence:** h1 line 35 "text-3xl sm:text-4xl md:text-5xl font-bold"; h2 line 80 "...font-bold"; h3 line 127 "text-2xl md:text-3xl font-bold". Homepage hero h1 (stitch-hero.tsx line 39) is font-normal with a single bold emphasis span ("before it ships."), and SheetHeader labels are mono/normal — confirming the system uses size, not weight, for heading hierarchy.
- **Why it matters (buyer):** Heavy bold headings clash visibly with every other page's restrained type, making the site feel inconsistent and less considered — a quiet credibility tax with a discerning buyer.
- **Fix:** Change the three headings to font-normal and let the size scale carry hierarchy. Keep bold only for a single intentional emphasis word if desired, matching the hero pattern.
- **Verifier:** Real and grounded, but downgrade major→minor. The reviewer's claim that bold is "reserved system-wide for the hero h1 emphasis word and preview labels only" is overstated — the hero CTAs (stitch-hero.tsx lines 62, 73) and the about CTA button (line 135) also use font-bold, which is consistent. The defect is weight-only on three headings; a clear consistency tax but not a structural break. Minor is the honest severity.

**[copy] UK spelling on a marketing page ("organises") breaks the US marketing locale**  _( confirmed )_
- **Evidence:** Line 49 "...searches across multiple source types, organises the evidence...". Homepage marketing copy uses US "We organize; you decide." (stitch-hero.tsx line 55). Lock: US on marketing/dev pages, UK on legal + product UI.
- **Why it matters (buyer):** Mixed spelling across marketing surfaces reads as inattentive; the lock is US on marketing/dev pages, UK only on product UI + legal.
- **Fix:** Change "organises" to "organizes" to match the US marketing locale.
- **Verifier:** Confirmed. About is a marketing page → US spelling. Verified the homepage uses "organize". Correct minor.

**[copy] Core positioning line "We organize; you decide." is absent**  _( confirmed )_
- **Evidence:** The mission is restated only as line 67 "Make evidence accessible, calm, and clear — in a world that often feels anything but." The canonical tagline "We organize; you decide." (present in stitch-hero.tsx line 55) does not appear anywhere in about/page.tsx.
- **Why it matters (buyer):** The About page is the natural home for the mission statement; omitting the signature line misses a chance to reinforce the no-verdict promise the researcher buys.
- **Fix:** Work "We organize; you decide." into the mission paragraph, ideally paired with the for-and-against substance from the content finding.
- **Verifier:** Confirmed. Line 67 substitutes a bespoke, consumer-toned mission for the canonical no-verdict tagline. Valid minor; reinforces the no-verdict promise the researcher buys.

**[accessibility] zinc-400 low-contrast text (eyebrows, back link, footer)**  _( adjusted )_
- **Evidence:** Eyebrows text-zinc-400 (lines 32, 77), back button text-zinc-400 (line 24), footer mono text-zinc-400 (line 143). Homepage hero eyebrow uses text-zinc-500 (stitch-hero.tsx line 34) and SheetHeader label tone is text-zinc-500 — so the document system itself uses zinc-500, not zinc-400, for these labels.
- **Why it matters (buyer):** Small low-contrast mono labels are the document-grammar's load-bearing wayfinding; if they fail contrast they are hard to read and flag the known zinc-400 trap.
- **Fix:** Bump the eyebrow/footer mono and the back-link rest state to text-zinc-500 (or zinc-600) to clear AA and match the homepage/SheetHeader convention.
- **Verifier:** Real and grounded; the off-system zinc-400 is verified at all four cited lines. Adjusted only to correct the reviewer's hex: zinc-400 is #a1a1aa (the reviewer cited #9CA3AF, which is gray-400). Conclusion unchanged — #a1a1aa on white is ~2.6:1, still below WCAG AA 4.5:1. Severity minor stands.

**[aesthetic] Accent over-budget: 4px orange left border + orange tagline fill**  _( confirmed )_
- **Evidence:** Line 53 emphasis block "bg-zinc-50 border-l-4 border-accent"; line 58 "<span className=\"text-accent\">Just clarity you can use.</span>". The shipped system uses orange as hairline 1px/2px marks and one rotated-square glyph per section (sheet-header.tsx: single w-2 h-2 bg-accent rotate-45; lock: orange as stroke/mark, never a fill).
- **Why it matters (buyer):** A 4px orange rule plus an orange marketing phrase reads heavier/softer than the disciplined hairline accent elsewhere, diluting the one-accent restraint that signals rigor.
- **Fix:** Reduce the left rule to border-l-2 and drop text-accent on the tagline (use zinc-900), reserving orange for a single registration glyph/rule per section.
- **Verifier:** Confirmed at both lines. The text-accent on a marketing phrase is the clearer violation (orange as a text fill, not a mark). Stays inside the one-accent lock. needs_human_eye is reasonable. Valid minor.

**[ia] No AboutPage/Organization JSON-LD**  _( confirmed )_
- **Evidence:** about/page.tsx exports only metadata (title/description/canonical, lines 7-11) with no JSON-LD <script>. Verified the homepage ships structured data: app/page.tsx line 22 "const jsonLd = {" rendered via a type="application/ld+json" script at lines 74-75.
- **Why it matters (buyer):** An Organization/AboutPage schema (founder, sameAs, description) helps a new zero-authority domain earn entity recognition — relevant to the active visibility push.
- **Fix:** Add an AboutPage or Organization JSON-LD block (founder, sameAs, currency-neutral description) mirroring the homepage pattern, to help the zero-authority domain earn entity recognition during the active visibility push.
- **Verifier:** Confirmed both halves: about has no JSON-LD, homepage does. Relevant to the live visibility/SEO push. Correct minor, lighter-touch as the rubric directs.

## Additional issues caught in verification

**[MINOR · positioning] Metadata description hard-codes the general-consumer audience into the SEO surface**
- **Evidence:** Line 9 metadata description: "Tru8 researches the evidence behind news articles and claims so you can form your own view. Built for anyone who wants clarity on what's being reported." The "Built for anyone who wants clarity" clause is the same consumer drift as the body, but baked into the indexed <meta> description and title surface.
- **Fix:** Rewrite the description around the researcher's job and the no-verdict method, e.g. lead with seeing what supports and challenges each claim with receipts for every exclusion, so you can defend your sourcing. Keep it currency-neutral and inside the language lock. Pairs with the body re-anchor in finding 1.

**[MINOR · ia] About page has no funnel into the product or proof — both CTAs and the only links dump to the homepage**
- **Evidence:** The page's only internal links are the back-to-home link (line 22 href="/") and the CTA "Try Tru8 Today" (lines 133-138 href="/"). There is no link to a sample/verification record, /research (the research console), /developers, or /compare — the surfaces where a sceptical researcher would actually evaluate the method. The hero offers "See a Sample" and an "Open the Research App" path; the about page offers neither.
- **Fix:** Point the primary CTA at where the researcher starts (the research app or a sample record) rather than the homepage, and add at least one internal link to real proof (a sample verification record or the views). Improves the funnel and internal-link equity for the visibility push.

**[MINOR · copy] "clarity" is repeated as the core promise across the page, cementing the wrong value proposition**
- **Evidence:** "clarity" / "clear" appears at line 58 ("Just clarity you can use."), line 63 ("wants clarity"), line 67 ("accessible, calm, and clear"), line 102 ("they just want clarity"), plus the meta description line 9. The repeated promise is emotional clarity/reassurance, not defensible evidence — the researcher's actual need.
- **Fix:** Replace most instances of "clarity" with the researcher's terms (the evidence for and against, what's missing, a record you can defend). Keep the founder's voice but swap the value noun. This is the lexical mechanism behind the audience drift in findings 1 and 2.

## Strengths to keep
- Language-lock clean: no "verdict", "fact-check", confidence scores, or page-level Supported/Contradicted labels; the object stays the evidence ("what's well-supported and what isn't", "holds up").
- Aligned with the no-verdict positioning: "gives you a structured report you can explore" and "form your own view" echo "you decide" without overstating.
- Genuine, specific founder narrative (construction → retrained → built it himself) that builds human trust and differentiates from faceless competitors.
- Retains some document-grammar texture: mono uppercase tracking-[0.3em] eyebrows and the footer metadata stamp "TRU8 — ABOUT — V1.0" gesture at the system.
- Correct heading order (h1 → h2 → h3), sensible metadata with canonical, and a clean single-column reading layout.
