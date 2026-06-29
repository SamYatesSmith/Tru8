# Pricing  /pricing
> Pre-launch page audit · researcher-buyer lens · 2026-06-29
> Ground truth = current code; every finding was adversarially verified against shipped source.
> This document supersedes nothing. It is the pre-launch review only.

**Buyer fit:** 4/5 — currently speaks to **researcher**

Unlike the homepage (developer/API-led), /pricing is correctly researcher-led: the Console is the elevated hero artifact ('fair-use unlimited evidence research in the browser', 'Run as many checks as your research needs'), Teams speaks to 'newsrooms and research teams', and the API is demoted to a single quiet band for 'systems and agents'. The buyer sees their own workflow first. Only mild drift: 'Personal API allowance - Light scripting against your own account', which reads fine as a Console sub-feature, not re-targeting.

**Verifier check:** Confirmed. /pricing is genuinely researcher-led in current source: the Console is the elevated artifact panel (lg:col-span-7, border-t-2 border-t-accent, numbered feature ledger) carrying "Run as many checks as your research needs" (stitch-pricing.tsx:24) and "fair-use unlimited evidence research in the browser" (:78); Teams targets "newsrooms and research teams" (:149-151); the developer/agent API is correctly demoted to one quiet band "For systems and agents" (:170). The six views are named by action — "Evidence, Sources, Timeline, Gaps, Map and Video." (:29). Score 4 is fair. The only drift is the "Personal API allowance — Light scripting against your own account" feature row (:43-44), which reads as a Console sub-feature rather than re-targeting — minor, as the reviewer says.

**Overall:** For the "show-your-working" researcher this page is well-targeted and on-system: the Console is the hero, the API is a quiet band, the six views are named by action, and the language lock is clean (signed record framed honestly, "metered verification", "We organize; you decide."). The decisive problem is that it ships three hard-coded GBP prices (£20/mo, £200/yr, From £75/mo) plus a price in the meta description, directly against the active price-gate lock that says no display price until the founder sets one. Secondary defect: the page has no h1, hurting both accessibility heading order and SEO on the most commercially important page.

## Verified findings

### BLOCKER

**[content] Three hard-coded GBP prices ship against the active price-gate lock**  _( confirmed )_
- **Evidence:** stitch-pricing.tsx:74 `<span className="text-5xl font-light text-zinc-900">£20</span>`; :78 'or £200/yr · fair-use unlimited evidence research in the browser.'; :144-146 'From £75 <span...>/mo</span>'. page.tsx:11 meta description: '...evidence research in the browser for £20/month.' The component's own doc comment (:9-17) also hard-codes '£20/mo' and notes 'a real £20 Stripe checkout needs a new Stripe product + price-id env (deferred to P4/deploy)' — i.e. the price is displayed but not even wired to a checkout.
- **Why it matters (buyer):** The standing rule (project_pricing_not_set_2026_06_23 + the rubric price-gate) is that no display price may appear on any pricing/packaging surface until the founder sets one, and surfaces should read currency-neutral. A researcher anchors hard on these numbers; publishing them pre-decision risks committing the founder to figures that were not signed off, and the £ currency is also locked-open.
- **Fix:** Do not invent or alter the numbers. Confirm £20/£200/£75 and the £ currency with the founder before this page is indexable; the active lock (project_pricing_not_set_2026_06_23) says no display price on any pricing surface until the founder sets one, and currency is locked-open. Until confirmed, gate Console/Teams the way the API band already is (qualitative 'fair-use unlimited' / 'team plans' + CTA) and strip the price from the meta description.
- **Verifier:** Confirmed verbatim against current source on all four cited locations, including the meta description. Squarely violates the standing price-gate lock and currency-open rule. Blocker is correct: this is exactly the launch-gating, founder-sign-off issue the rubric tells reviewers to flag rather than invent. The recommendation stays inside the locks (does not propose numbers).

### MAJOR

**[accessibility] Pricing page has no h1 — heading order starts at h2**  _( confirmed )_
- **Evidence:** page.tsx renders only Navigation, MobileNav, main > StitchPricing, Footer — no h1. StitchPricing's first heading is h2 'Choose how you work.' (stitch-pricing.tsx:54-56). SheetHeader (sheet-header.tsx:35-59) emits only span/div, no heading element. Feature 'key' labels are h3 (:93). So the document has no h1 and a top-level h3 nested under the h2.
- **Fix:** Promote the section title to an h1 (or add a visually-styled h1 above it), keeping the font-normal/size-as-hierarchy treatment, e.g. h1 'Choose how you work.' or 'Pricing — Console & API'. Keep the feature labels one level below.
- **Verifier:** Confirmed: SheetHeader genuinely emits no heading, and StitchPricing is the only content in main, so /pricing has no h1. Real a11y heading-order break plus lost answer-first/SEO signal on the most commercial route. Major is appropriate.

### MINOR

**[positioning] Console and Teams expose numbers while the API is gated — inconsistent price discipline**  _( adjusted )_
- **Evidence:** API band stitch-pricing.tsx:169-172 is number-free ('metered verification, billed per call from a prepaid balance'), while Console (:74) and Teams (:144-146) carry explicit £ figures.
- **Fix:** Apply one consistent gate posture across all three products; given the lock, default Console/Teams to the same qualitative + CTA pattern the API band already uses, until prices are signed off.
- **Verifier:** Real and correctly grounded, but downgraded major→minor: it is a corollary of the blocker (the same displayed-price problem), not an independent major defect, and its fix is identical to the blocker's. Worth keeping as an internal-consistency observation, not double-counting as major.

**[ia] Orphaned sheet number '05' with no preceding sheets on a standalone page**  _( confirmed )_
- **Evidence:** stitch-pricing.tsx:52 `<SheetHeader number="05" label="Pricing" refText="CONSOLE · TEAMS · API" />`. Homepage sheets run 00→05 (stitch-problem 00, stitch-record 01, stitch-process 02, stitch-developer-showcase 03, stitch-compare-teaser 04, stitch-product-preview 05). A visitor landing cold on /pricing sees only sheet 05.
- **Why it matters (buyer):** The document-grammar conceit ('one calibrated specification document') reads as a non-sequitur when a researcher lands cold on /pricing and sees sheet 05 with no 01-04. It is a small but real consistency seam.
- **Fix:** Use a page-appropriate number (e.g. '00') or drop the numeric prefix on standalone routes while keeping the glyph + label, so the document-grammar conceit doesn't imply missing sheets 00-04.
- **Verifier:** Confirmed against source. Note the homepage already reuses '05' for both stitch-product-preview and (on its own page) pricing — so the number is not even unique across the system, reinforcing that '05' here is a copy-paste seam. Minor is correct.

**[accessibility] zinc-400 low-contrast text on secondary price/label elements**  _( confirmed )_
- **Evidence:** stitch-pricing.tsx:66-68 mono ref 'claimMap · export · signed' is text-zinc-400; :75 '/mo' is text-zinc-400 text-lg; :146 Teams '/mo' is text-zinc-400 text-lg.
- **Why it matters (buyer):** The rubric flags zinc-400 traps specifically. '/mo' is part of the price meaning and the mono ref is part of the artifact signal; both fall below WCAG AA for a researcher on a bright screen.
- **Fix:** Move the load-bearing '/mo' suffix to text-zinc-500 (already AA on white and used for body copy at :77/:97). Decorative mono refs can remain zinc-400 if treated as decorative. Confirm against rendered pixels.
- **Verifier:** Confirmed at all three locations. The rubric explicitly calls out zinc-400 traps, and '/mo' is semantically load-bearing (part of the price), so AA matters. needs-human-eye on exact pixels is fair. Minor is right.

### NIT

**[aesthetic] Price figures use font-light, off the 'size is the hierarchy lever, weight reserved' rule**  _( confirmed )_
- **Evidence:** stitch-pricing.tsx:74 'text-5xl font-light' (£20), :126 'text-3xl font-light' (Free), :144 'text-3xl font-light' (From £75). The system otherwise uses font-normal headings (:54) with font-bold reserved for emphasis (:55, :93).
- **Fix:** Either standardise price figures to font-normal at the same size (let size carry emphasis) or document font-light as the sanctioned price-display weight.
- **Verifier:** Confirmed: font-light appears as a third weight on three price figures. Defensible price-display convention but a genuine token-discipline drift. Nit is the right severity.

## Additional issues caught in verification

**[MINOR · ia] Console (£20) and Free CTAs point to the identical destination — no actual path to choose/pay for Console**
- **Evidence:** Console primary CTA 'Start in the browser →' → href="/dashboard" (stitch-pricing.tsx:110-116); Free taster CTA 'Start free →' → href="/dashboard" (:131-137). Both land on the same /dashboard route. The component comment (:14-17) confirms the £20 Stripe checkout is deferred, so the priced Console tier has no distinct sign-up/upgrade path — it is indistinguishable in action from the free tier. Missed by the reviewer; grounded in current source.
- **Fix:** Until checkout exists, either route the Console CTA to a waitlist/contact step distinct from the free entry, or make the copy honest that both currently start the same free flow. At minimum differentiate the two CTAs so a researcher can tell what selecting the £20 plan actually does. This also reinforces the blocker: showing a £20 price with no way to pay it is a half-finished pricing story.

## Strengths to keep
- Six views named correctly by ACTION, not profession: 'Evidence, Sources, Timeline, Gaps, Map and Video.' (stitch-pricing.tsx:29)
- Language lock fully respected: 'A signed evidence record, with a receipt for every exclusion.' framed honestly (no 'tamper-evident'/'independently verifiable' overstatement); 'metered verification'; 'We organize; you decide.' in meta. Object is always the evidence/record, no verdict language, no traffic-light colours.
- Researcher-first information architecture: Console is the elevated hero artifact, Free taster and Teams sit as an un-elevated supporting rail, and the developer/agent API is correctly demoted to a single quiet band - the opposite (correct) emphasis to the homepage.
- Strong document-grammar discipline and accent budget: border-t-2 border-t-accent on the Console panel, text-accent only on the 5 ledger numbers, one bg-accent rotate-45 seal in the 'signed record' footer - matches the self-policed 'eyebrow + 5 numbers + 1 seal' rule, with 1px zinc borders, no shadows, no gradients.
- Free taster copy gives the researcher the proof path they want: '3 checks · all features · all six views. See exactly what a record looks like.' (stitch-pricing.tsx:127-130)
- API kept number-free and qualitative ('billed per call from a prepaid balance') - the correct gated posture that the priced tiers should match.
