# Research front door  /research
> Pre-launch page audit · researcher-buyer lens · 2026-06-29
> Ground truth = current code; every finding was adversarially verified against shipped source.
> This document supersedes nothing. It is the pre-launch review only.

**Buyer fit:** 5/5 — currently speaks to **researcher**

Native copy names the buyer outright ('For researchers, journalists, and analysts who have to defend their sources'), frames no-verdict as the feature, leads with for/against/missing, demotes the API to a footnote, and points the CTA at the browser console (/dashboard) not an API key. This is the page that nails the fixed buyer. The imported carousel's 'Your Research Team' framing plus profession names dilute an otherwise-precise voice but do not change who the page is for.

**Verifier check:** Confirmed. The page speaks squarely to the show-your-working researcher and earns a high buyer-fit score. Verified in current source: hero h1 "See the evidence for and against. / Show your working." (page.tsx:105-107) over the sub "For researchers, journalists, and analysts who have to defend their sources" (109-110); the For/Against/Missing block with tier/type classification and an exclusion receipt "Your working, written down and defensible." (WORKING, lines 53-69); the honest LIMITS block "Not a verdict." / "Bounded by what's public." / "A snapshot in time." (71-88); CTA → /dashboard "Start in the browser" with the API demoted to a quiet zinc-50 footnote (193-210); ResearchStartCta fires research_start_click with a surface param (research-start-cta.tsx:21). The two genuine dilutions are both imported homepage components — StitchFeatures' "Your Research Team" + profession names, and StitchCompareTeaser's orphan "04" — neither changes who the page is for. Buyer = researcher; score ~5 is fair.

**Overall:** The page's own hand-authored copy is the strongest researcher-buyer pitch in the codebase: the hero ("See the evidence for and against. Show your working."), the For/Against/Missing block, and the honest Limitations section speak directly to the show-your-working researcher and respect the language locks. The damage comes from two borrowed homepage components: StitchFeatures exposes the forbidden profession names ("The Cartographer" etc.) on the front door, and StitchCompareTeaser drops an orphan numbered "04 / COMPARE" sheet header onto a page that otherwise abandons the document-grammar numbering — so the calibrated-document feel breaks exactly where the buyer should sense rigour.

## Verified findings

### MAJOR

**[copy] Six views shown by PROFESSION name on the researcher front door**  _( confirmed )_
- **Evidence:** stitch-features.tsx:13-56 hard-codes name: 'The Cartographer' / 'The Librarian' / 'The Correspondent' / 'The Projectionist' / 'The Chronologist' / 'The Seeker', rendered as <h4>{profession.name}</h4> (line 167) under eyebrow 'Your Research Team' (line 99), and again inside the dot aria-label `View ${professions[index].name}` (line 192). Imported and rendered on the page at research/page.tsx:155.
- **Why it matters (buyer):** The action-names lock exists because the researcher cares about the OUTPUT, not an internal persona cast. 'The Projectionist'/'The Seeker' read as product whimsy and obscure what each view actually returns, weakening the 'defend your sourcing' promise the rest of the page makes.
- **Fix:** Use a /research-specific variant that names the six views by ACTION (Map · Sources · Evidence · Video · Timeline · Gaps), with the profession allowed only as a muted subtitle, and fix the dot aria-labels to match. Re-eyebrow 'Your Research Team' → an output frame such as 'SIX WAYS TO READ THE RECORD' (the page comment at line 154 already calls it 'Six ways to read the same record'). Keep the carousel mechanics.
- **Verifier:** Confirmed verbatim in current source. Direct violation of the action-names lock on the buyer's front door. Severity major is correct — it is the single most prominent lock breach on the page; the dot aria-labels propagate it to assistive tech too (reviewer missed the aria-label instance; folded in here).

**[accessibility] Carousel cards are click-only divs; auto-advance pauses on hover but not focus, no reduced-motion**  _( confirmed )_
- **Evidence:** stitch-features.tsx card wrapper is <div … onClick={() => !isActive && goTo(index)}> (line 151) — no role/tabIndex/key handler. Auto-advance every AUTO_ADVANCE_MS=6000 (lines 59,76-80). Pause is wired to onMouseEnter/onMouseLeave only (lines 109-114); goTo merely pauses for 12s then resumes (88-90). No prefers-reduced-motion check anywhere; no persistent stop control.
- **Fix:** Make the cards non-interactive for navigation (the dot buttons at 184-194 are already real, accessible controls) or convert them to buttons; add a prefers-reduced-motion guard that disables auto-advance, and pause on focus-within as well as hover.
- **Verifier:** Confirmed against current source. Auto-starting motion lasting >5s with no persistent pause/stop mechanism and no reduced-motion respect is a genuine WCAG 2.2.2 / 2.3 issue; the 12s goTo pause is not a stop. Major stands. Note the component is shared with the homepage, so the fix benefits both surfaces.

### MINOR

**[aesthetic] Document-grammar numbering is half-applied: orphan '04' sheet with no 01-03**  _( adjusted )_
- **Evidence:** research/page.tsx renders its own sections with bare mono eyebrows and no SheetHeader ('What the record shows' line 125, 'Limitations' line 160), then embeds StitchCompareTeaser (line 152) which renders <SheetHeader number="04" label="Compare" refText="THE RECORD LAYER" /> (stitch-compare-teaser.tsx:30). So the only numbered sheet on the page is '04', mid-scroll, with no 01/02/03.
- **Why it matters (buyer):** The numbered-sheet system is the visual proof of 'this is one calibrated specification document' — the exact composed-rigour signal that sells a sourcing tool. A lone '04' reads as a copy-paste leak and undercuts that credibility for a detail-oriented buyer.
- **Fix:** Either give /research its own coherent SheetHeader sequence (01…04) or drop the SheetHeader from the embedded teaser on this route so no lone '04' ships. The component is literally commented 'Homepage — Sheet 04' (line 8), so the number is a copy-paste leak.
- **Verifier:** Real and correctly grounded, but severity downgraded major→minor: it is a single mislabeled section header, not a layout/hierarchy break. Most users will not parse the absence of 01-03; the buyer who does will read it as a polish slip, not a credibility wound. Fix is sound and inside the locks.

**[accessibility] Heading order skips a level in the embedded carousel**  _( confirmed )_
- **Evidence:** stitch-features.tsx uses <h2> 'Six ways to explore' (line 101) then <h4> for each card title (line 166), skipping h3 — while the page's own card blocks correctly use h3 (research/page.tsx:141 and 169).
- **Why it matters (buyer):** Inconsistent heading nesting degrades screen-reader navigation of the views list, the part of the page that explains what the buyer actually gets.
- **Fix:** Change the carousel card titles from h4 to h3 so the tree stays h1 → h2 → h3.
- **Verifier:** Confirmed. Genuine heading-nesting skip in the views section; minor is correct.

**[aesthetic] Embedded carousel breaks the font hierarchy rule (font-light + italic)**  _( confirmed )_
- **Evidence:** stitch-features.tsx:101 heading is 'text-3xl md:text-4xl font-light tracking-tight'; card questions are 'text-sm text-zinc-500 italic' (line 169). The document-grammar lock is font-normal headings (size is the lever) and no italic appears elsewhere; /research's own h2s are font-normal (page.tsx:104,128,163,181).
- **Why it matters (buyer):** Mixed weights/italics make the views section look like a different product than the crisp sheets above it, chipping at the composed-document impression.
- **Fix:** Normalize to font-normal headings and drop the italic on the questions (or render them in mono like other labels) when this component is used on /research.
- **Verifier:** Confirmed verbatim. font-light and italic both diverge from the shipped Stitch tokens used by the rest of the page; minor is correct.

**[copy] Hero sub is one dense block; 'We organize; you decide.' repeated, 'you decide' echoes**  _( adjusted )_
- **Evidence:** research/page.tsx:109-116 is one ~60-word paragraph ending 'You read the record and decide. We organize; you decide.' The exact tagline recurs in the footer CTA copy (line 186). The variant 'you read the record and decide' also appears in LIMITS (line 74).
- **Fix:** Break the hero sub into two short sentences leading with the action ('Paste a headline, article, or claim…'), and drop the tagline from one of the two CTA blocks so 'We organize; you decide.' lands once in the hero and once at close.
- **Verifier:** Real, but the count is overstated: the exact tagline 'We organize; you decide.' appears twice (hero line 115, footer line 186), not three times — 'three' counts looser 'you decide' echoes. Corrected here; severity minor stands and the fix is sound.

**[ia] No researcher-specific OG image; reuses generic /api/og/default**  _( confirmed )_
- **Evidence:** research/page.tsx:26 and :32 set openGraph/twitter images to '/api/og/default', with the code comment at lines 20-22 acknowledging 'no researcher-specific /api/og route exists yet'. Title/description (lines 12-14) are correctly researcher-framed.
- **Why it matters (buyer):** When a journalist shares this page, the card shows the generic developer-leaning art, muting the 'show your working' hook at the exact moment of social distribution.
- **Fix:** Add a /research OG variant echoing 'See the evidence for and against. Show your working.' Non-blocking — the text metadata is already correct. Needs a visual pass on the rendered card.
- **Verifier:** Confirmed. Genuinely non-blocking; minor is right.

### NIT

**[positioning] Carousel eyebrow 'Your Research Team' is an off-buyer note**  _( confirmed )_
- **Evidence:** stitch-features.tsx:99 'Your Research Team' — homepage-era framing reused verbatim where the rest of /research keeps the object as the record.
- **Fix:** Replace with an output frame ('WAYS TO READ THE RECORD') as part of the profession-name fix above.
- **Verifier:** Confirmed; nit. Should be fixed together with the major profession-name finding, not as a separate change.

**[aesthetic] Card sub-heads use font-bold against the 'size is the hierarchy lever' rule**  _( confirmed )_
- **Evidence:** research/page.tsx:141 (For/Against/Missing heads 'text-base md:text-lg font-bold') and :169 (limitation heads 'text-sm font-bold'). The lock reserves bold for the single hero emphasis word and preview panels.
- **Why it matters (buyer):** Low-stakes, but spreading bold to every card label dilutes the deliberate bold-word emphasis used in the hero ('Show your working.').
- **Fix:** Consider font-medium/font-normal for these labels and let size + mono carry hierarchy; reserve bold for the emphasis word. Borderline — confirm visually.
- **Verifier:** Confirmed in source; nit. Note the page also uses intentional bold-word emphasis inside its h2s (lines 130,164,182), so the system is not purely size-driven; this is a defensible polish call rather than a clear breach.

## Additional issues caught in verification

**[MINOR · accessibility] zinc-400 low-contrast text on labels and the API footnote**
- **Evidence:** Mono eyebrows are 'text-[10px] … text-zinc-400' on white/zinc-50 (research/page.tsx:101,125,160) and the API footnote is 'font-mono text-[11px] … text-zinc-400' on bg-zinc-50 (line 196); the borrowed teaser also renders its lead heading in text-zinc-400 at text-3xl/5xl (stitch-compare-teaser.tsx:34). zinc-400 (#a1a1aa) on white is ~2.4:1, below WCAG AA (4.5:1 small text, 3:1 large). The rubric explicitly flags zinc-400 traps and the reviewer flagged no contrast issue.
- **Fix:** Darken load-bearing label/footnote text to zinc-500 (≈4.9:1, already used for body copy on this page) so the document-grammar eyebrows and the API footnote pass AA; keep zinc-400 only for genuinely decorative marks. Confirm the muted compare-teaser heading visually.

**[NIT · content] Carousel description of 'The Correspondent' may misdescribe what the view returns**
- **Evidence:** stitch-features.tsx:31-33 frames 'The Correspondent' as 'Who's in the room? See which domains contributed evidence, how concentrated or diverse they are…' — a source/domain-diversity framing, whereas the Correspondent view is the per-sub-question disposition panel ('Answer this sub-question?'). On the researcher front door this risks promising a view that returns something different from the card. Low confidence: project docs are noted as stale and I did not open the live view component.
- **Fix:** When building the /research-specific views section (per the major profession-name finding), describe each card by the OUTPUT the buyer actually gets, and reconcile the Correspondent copy against the shipped view before rewording — verify, do not assert.

## Strengths to keep
- Hero nails the fixed buyer: 'See the evidence for and against. Show your working.' over 'For researchers, journalists, and analysts who have to defend their sources' — exact audience, no-verdict reframed as the feature.
- For/Against/Missing block (research/page.tsx:53-69) is concrete and researcher-grade: tier/type classification, support surfaced beside challenge, named gaps PLUS an exclusion receipt for every set-aside source ('Your working, written down and defensible.').
- Limitations section (lines 71-88) is a genuine trust asset — 'Not a verdict', 'Bounded by what's public', 'A snapshot in time' — the honest edges a defensible-sourcing buyer wants, and rarely shown by rivals.
- Language lock fully respected: object is always the evidence/record, US spelling ('organize'), no verdict/confidence/credibility/policy language, no price shown (price gate honoured), CTA → /dashboard with the API as a quiet footnote (lines 193-210).
- Accent discipline in the page's own sections is on-system: the single rotated 2px orange registration glyph reused on the For/Against/Missing cards (line 136), 1px zinc borders, no gradients or shadows.
- Funnel is properly instrumented: ResearchStartCta fires research_start_click with hero/footer surface (research-start-cta.tsx:21), pairing with the nav's research_app_click for a measurable arrival→start conversion before any flip of '/'.
