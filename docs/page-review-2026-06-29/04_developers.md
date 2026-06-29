# Developers  /developers
> Pre-launch page audit · researcher-buyer lens · 2026-06-29
> Ground truth = current code; every finding was adversarially verified against shipped source.
> This document supersedes nothing. It is the pre-launch review only.

**Buyer fit:** 4/5 — currently speaks to **developer**

This route is allowed to address developers, and it does so well while staying on-positioning: the no-verdict language survives ('It does not return a true/false verdict. We organise; you decide.', FAQ line 41), and it ladders back to the researcher value via 'Same claim, Tru8 vs four grounding APIs →' (line 121). It loses a point because it never links back to the human review console (/research) and frames everything as 'Your agent decides what matters.' (line 130) — a one-line ladder to the researcher app would keep it consistent with the rest of the funnel.

**Verifier check:** Confirmed and grounded. This route is permitted to address developers/agent builders, and it does so without breaking the positioning locks: the no-verdict line survives verbatim in the FAQ ("It does not return a true/false verdict. We organise; you decide.", page.tsx:41), the manifest is framed honestly as tamper-evident via GET /verify/{check_id} (lines 53, 942), and it ladders to the researcher proof through "Same claim, Tru8 vs four grounding APIs →" → /compare (lines 117-122). The one demerit the reviewer assigned (no in-content link to the human /research console; hero closes on "Your agent decides what matters.", line 130) is real and verified — the nav exposes "Research App"→/research (navigation.tsx:94-98) but the page body never does. Score 4 / speaks_to "developer" is accurate.

**Overall:** A genuinely substantial, honest developer/API reference that — correctly for this route — speaks to developers and agent builders while keeping the positioning locks intact ("It does not return a true/false verdict. We organise; you decide.") and laddering back to the researcher product via the /compare link. The main defects are consistency, not compliance: it does NOT use the shipped homepage document-grammar (numbered SheetHeaders, left spine, orange top rule) — it runs its own "Module —" eyebrow system with all-bold headings and orange-fill CTAs/badges — and it hard-codes GBP prices that are supposed to be founder-gated and conflict with the settled "$ currency" decision.

## Verified findings

### MAJOR

**[aesthetic] Page runs a different visual grammar from the shipped homepage document-datasheet system**  _( confirmed )_
- **Evidence:** Confirmed in source. Every section eyebrow is `<div className="font-mono text-[10px] tracking-[0.3em] uppercase text-zinc-400">Module — Developer API</div>` (lines 94-96, 163-165, repeated through 1000-1001). The shipped SheetHeader component (components/marketing/sheet-header.tsx) renders a 1px top rule + rotated orange registration glyph (`w-2 h-2 bg-accent rotate-45`) + two-digit sheet number + label + mono datasheet ref, and is the established homepage grammar. /developers imports it nowhere — it is a plain max-w-4xl column with "Module —" eyebrows and no sheet numbers, glyph, spine, or orange top rule.
- **Why it matters (buyer):** A researcher who arrives from the homepage or /compare experiences a visibly different product surface; the composed datasheet identity that signals 'rigorous, document-grade' is exactly the trust cue this buyer responds to, and it evaporates here.
- **Fix:** Replace the "Module —" eyebrows with the shipped SheetHeader (numbered sheets + rotated orange glyph + mono ref) so /developers reads as numbered sheets in the same datasheet, inside existing stitch-* tokens.
- **Verifier:** Grounded exactly as quoted; SheetHeader confirmed to exist and to be the homepage grammar. Major is defensible — it is a whole-page identity break across the funnel, though a consistency issue, not a lock violation.

**[positioning] Hard-coded GBP prices that are founder-gated, and a currency that conflicts with the settled '$ currency' decision**  _( confirmed )_
- **Evidence:** Confirmed. Pricing block hard-codes `£0.02` / `£0.03` / `£0.07` / `£0.15` (lines 393, 403, 413, 423) and metadata.description hard-codes 'From £0.02/query' (line 10). The positioning lock states price NUMBERS are gated and currency is OPEN; the settled repositioning note records '$ currency' and CLAUDE.md's agent_pricing lists the same figures in dollars ($0.02…$0.15), while the page's own JSON examples use `chargedPence` (GBP).
- **Fix:** Flag for the founder — do not invent or alter the numbers. Resolve the $/£ split deliberately and currency-consistently across the product before relaunch rather than per-page.
- **Verifier:** Prices and currency conflict verified in source and against CLAUDE.md. The fix correctly stays inside the lock (confirm-with-founder, do not invent). Major is appropriate for a shipped, indexed, gated-price surface.

### MINOR

**[aesthetic] All headings are font-bold, breaking the 'size is the hierarchy lever, not weight' rule**  _( confirmed )_
- **Evidence:** Confirmed. h1 `text-3xl sm:text-4xl md:text-5xl font-bold` (line 97); section h2 `text-2xl sm:text-3xl md:text-4xl font-bold` (line 166 and every section); CTA h3 `text-2xl md:text-3xl font-bold` (line 1025). The homepage uses font-normal headings with one reserved bold emphasis word: stitch-hero.tsx:39 h1 is `font-normal` with a single `<span className="font-bold">before it ships.</span>` (line 42), and stitch-record.tsx:84 h2 is `font-normal`.
- **Why it matters (buyer):** Uniform bold flattens the typographic restraint that gives the rest of the site its Stripe/Linear composure; it reads more like generic docs than the deliberate document grammar.
- **Fix:** Move section h2/h3 to font-normal and let size carry hierarchy, reserving at most one bold emphasis word as the homepage does.
- **Verifier:** Verified against both this page and the homepage components; the weight-vs-size contrast is real.

**[aesthetic] Orange used as solid fills on badges and the primary CTA, against accent discipline and the homepage's black CTA**  _( confirmed )_
- **Evidence:** Confirmed. Step badges `w-8 h-8 bg-accent text-white` (lines 173, 207, 226); final CTA `bg-accent hover:bg-accent/90 text-white` (line 1035); hero callout `border-l-4 border-accent` (line 125) and MCP primary tool `border-l-4 border-l-accent` (line 323) — 4px rules. The nav/home primary CTA is `bg-black text-white` (navigation.tsx:79 and :103), not orange.
- **Fix:** Make the primary CTA `bg-black` to match nav/home, render step numbers as mono `text-accent` marks rather than filled squares, and drop the 4px left rules to match the system's lighter accent budget.
- **Verifier:** All class references verified including the navigation bg-black CTA. Orange-as-fill vs black-CTA inconsistency is real.

**[copy] UK spelling on a marketing/dev page, including the tagline spelled differently from the homepage**  _( confirmed )_
- **Evidence:** Confirmed. /developers: 'organised by source tier' (line 103), 'Structured, not summarised.' (line 129), 'It does not return a true/false verdict. We organise; you decide.' (FAQ line 41 — also baked into the FAQPage JSON-LD). The homepage uses US spelling: stitch-hero.tsx:55 'We organize; you decide.' and stitch-faq.tsx:20/24 'organizes'/'organized'. Lock: US on marketing/dev pages.
- **Why it matters (buyer):** Seeing the same signature line spelled two ways across the funnel (organize vs organise) is a small but real credibility ding for a buyer whose whole job is consistency and sourcing discipline.
- **Fix:** Switch this page (visible copy and the FAQ array that feeds JSON-LD) to US spelling — organise→organize, summarised→summarized — keeping UK only on legal pages and product UI.
- **Verifier:** Both sides verified; the signature line literally ships two ways across the funnel, including in indexed structured data. Real.

**[content] Metadata promises 'three payment rails' the body never substantiates**  _( adjusted )_
- **Evidence:** Confirmed. metadata.description: 'Three tiers, three payment rails, MCP server…' (line 10), but the body only ever describes prepaid credits — 'deducted from your prepaid credit balance' (line 379), 'billed from prepaid credits' (FAQ line 49). x402/Skyfire appear nowhere on the page.
- **Why it matters (buyer):** A metadata claim with no on-page backing is a small honesty gap; for a developer evaluating integration it's a dead promise, and the researcher-adjacent trust bar is 'say only what you show'.
- **Fix:** Soften the description to 'prepaid credits' rather than adding an x402/Skyfire rails note — per internal state the alternative rails are disabled in production, so listing them would over-claim a capability that is off.
- **Verifier:** Adjusted: finding is real, but of the reviewer's two options, the 'add a rails note' option is unsafe — memory/release-readiness records Skyfire/x402 rails as False (mitigated, not live). The correct fix is the soften option only; adding the rails would create a worse honesty gap, not close one.

**[accessibility] Low-contrast zinc-400 text traps on labels, the back link, and footnotes**  _( confirmed )_
- **Evidence:** Confirmed. Section eyebrows `text-zinc-400` on white (lines 94, 138, 163, 248, 286, 369, …); back link `text-zinc-400` (line 86); pipeline footnote `text-xs text-zinc-400` (line 276); 'No' table cells `text-zinc-300` (lines 267-272). zinc-400 (~#9CA3AF) on white is ~2.6:1, below the 4.5:1 AA threshold for these informational strings.
- **Why it matters (buyer):** Researchers often read on dim laptop screens and include low-vision users; sub-AA labels and footnotes are hard to read and weaken the 'rigorous documentation' impression.
- **Fix:** Lift small informational text to zinc-500/zinc-600 for AA; keep zinc-400 only for the genuinely decorative glyph. Replace the zinc-300 'No' cells with a dash at zinc-500.
- **Verifier:** All class references verified. Contrast math is sound; these are body/label text, not purely decorative.

### NIT

**[positioning] No path back to the human research console from the dev page**  _( confirmed )_
- **Evidence:** Confirmed. The body's only outward marketing link is /compare (line 118); other links go to /dashboard/settings and the external Swagger/ReDoc docs. /research never appears in the page body, though the nav exposes 'Research App'→/research (navigation.tsx:94-98).
- **Why it matters (buyer):** A researcher who lands here (e.g. from search on 'evidence API') has no in-content nudge toward the human console that actually serves them.
- **Fix:** Add one quiet line near the hero or CTA — 'Prefer a human review console? Open the Research App →' to /research — mirroring the funnel's reciprocal linking, inside the locks.
- **Verifier:** Verified: zero /research reference in page.tsx body. Nit severity is right.

## Additional issues caught in verification

**[MINOR · ia] Primary 'Documentation' links fall back to http://localhost:8000 when NEXT_PUBLIC_API_URL is unset**
- **Evidence:** Both documentation cards — the page's main outbound resources — use `href={`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/docs`}` (line 962) and `.../api/redoc` (line 978). If NEXT_PUBLIC_API_URL is not injected at build time, the Interactive API Docs and ReDoc Reference links resolve to localhost:8000 and are dead in production. The curl examples elsewhere hard-code `https://api.trueight.com` (lines 213, 232, 490, 539), so the base URL is also inconsistent across the page. Missed by the reviewer; this is the page's main outbound resource region and a real dead-link risk for the developer buyer it serves.
- **Fix:** Confirm NEXT_PUBLIC_API_URL is set in the production build, or fall back to the real public docs origin (e.g. https://api.trueight.com) rather than localhost, so the two primary resource links can never ship dead.

**[MINOR · accessibility] White-on-orange CTA and badge text fails WCAG AA contrast for small bold text**
- **Evidence:** The final CTA is `bg-accent … text-white text-xs font-bold uppercase tracking-[0.2em]` (line 1035) and the step number badges are `bg-accent text-white … text-sm font-bold` (lines 173, 207, 226). White (#FFF) on orange-600 (#EA580C) is ~3.8:1 — below the 4.5:1 AA threshold for 12px bold text (which does not qualify as WCAG 'large text'). Distinct accessibility lens the reviewer's zinc-400 finding did not cover; finding #3's bg-black fix happens to also resolve it, but the contrast failure is a separate real defect.
- **Fix:** Moving the CTA to `bg-black` (the nav/home pattern) resolves this; for any orange-background label, ensure text meets 4.5:1 or render the mark as text-accent on a light ground instead of white-on-orange.

## Strengths to keep
- No-verdict positioning is preserved even on the developer page: FAQ answer states 'It does not return a true/false verdict. We organise; you decide.' (line 41) and the response section frames the manifest honestly as 'verify the signed fields haven't changed since signing' via GET /verify/{check_id} (lines 53, 942) — not overstated as independently verifiable.
- Ladders back to the researcher proof: 'Grounding APIs return passages and a score. Tru8 returns structure' followed by 'Same claim, Tru8 vs four grounding APIs →' linking to /compare (lines 109-122) — the strongest differentiation argument, reused well.
- Genuine, non-placeholder substance: working curl Quick Start, pipeline-per-tier table, MCP config, async/batch/webhooks, rate limits, a full error-code table with agent actions, and a realistic response-shape JSON — this is real documentation, not a stub.
- Single FAQ source array drives both the visible <dl> and the FAQPage JSON-LD (lines 34-69, 1006-1017), so rendered answers always match the structured data — correct SEO hygiene.
- On-system surface details: JetBrains-mono refs/labels, 1px zinc borders, square corners, no drop-shadows or gradients, and element-state words like 'supported' appear only inside the claimMap JSON, never as a page-level colour-coded judgment.
