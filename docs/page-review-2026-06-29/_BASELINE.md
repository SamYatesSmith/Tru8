# Code-derived baseline (design + positioning)
> Pre-launch page audit · researcher-buyer lens · 2026-06-29
> Ground truth = current code; every finding was adversarially verified against shipped source.
> This document supersedes nothing. It is the pre-launch review only.

> Extracted from current code only (`globals.css`, `tailwind.config.ts`, `layout.tsx`, `stitch-*` components). Use THIS, not `docs/DESIGN_SYSTEM.md` (stale).

## Design language (as shipped)

SHIPPED Stitch "document-grammar" system, confirmed in code (globals.css, tailwind.config.ts, stitch-* components):

THEME: Light only. Body is `bg-white text-zinc-900 antialiased font-sans` (layout.tsx:73). Zinc neutral scale throughout.

TOKENS (globals.css :root): --surface #FFFFFF / --surface-raised #F9FAFB; --border #E5E7EB / --border-strong #D1D5DB; --text-primary #111827, --text-secondary #6B7280, --text-muted #9CA3AF. ACCENT --accent #EA580C (orange-600) + --accent-muted rgba(234,88,12,0.12). Confirmed single orange. NOTE: layout.tsx viewport.themeColor is a DIFFERENT orange #f27907 (browser chrome only) — inconsistent with the #EA580C accent.

FONTS: Inter (var --font-inter) sans + JetBrains Mono (var --font-mono) mono, both via next/font/google (layout.tsx). Mono is load-bearing for eyebrows, refs, numbers, labels.

DOCUMENT GRAMMAR (verified): SheetHeader component = 1px border-top rule + rotated 2px orange registration glyph (`w-2 h-2 bg-accent rotate-45`) + mono two-digit sheet number + mono uppercase label (tracking-[0.3em]) + right-aligned mono datasheet ref. Sheets numbered 01 (Record), 02 (Process), etc. page.tsx adds a 2px orange top rule (`h-[2px] w-full bg-accent`), a fixed vertical mono left spine ("TRU8 · EVIDENCE RESEARCH INFRASTRUCTURE · REV 2026.06", text-zinc-300, xl+ only), and a continuous 1px inset document frame at max-w-7xl.

TYPOGRAPHY HIERARCHY: font-normal headings, SIZE is the lever (hero h1 up to lg:text-[84px] tracking-[-0.03em] leading-[0.95]; h2 text-3xl→5xl font-normal). Bold reserved: hero h1 emphasis word ("before it ships." font-bold) + preview/differentiator labels (font-bold mono in stitch-record). 1px borders everywhere (border-zinc-200/100), NO drop-shadows, NO gradients on marketing, square corners (no radius classes on marketing cards). Accent budget self-policed per-section (stitch-record comment: "eyebrow + 5 numbers + 1 seal only").

ACCENT USAGE: orange appears as small rotated-square glyphs/seals and as mono row-number text (`text-accent`) — i.e. as marks. NOTE vs rubric "stroke/mark NEVER a fill": the glyphs ARE small `bg-accent` fills (rotated squares), and the 2px top rules are accent fills — but all are hairline marks/rules, not panels or gradients, so in spirit on-system.

ELEMENT-STATE COLOURS (globals.css): saturated traffic-light values exist — --state-supported #22C55E (green), --state-disputed #F59E0B, --disposition-supports #10B981 emerald, --disposition-challenges #F59E0B amber. These are PRODUCT-UI tokens (claim-map/evidence-views), NOT used on the marketing homepage, where "supported" renders as a plain zinc token (stitch-hero RECORD_LINES, enforced by comment §2.2). They are not "muted" though — flag if any leak page-level.

OTHER: .bg-grid-dot radial-dot pattern (hero bg). Mobile-first base font 14px→15px(640)→16px(768). Skip-link present. focus-visible outline 2px #111827.

## Positioning (as shipped)

The shipped HOMEPAGE is verification/developer-LED, not researcher-led — confirmed by code comments ("verification/dev-led, Phase 2 art-direction") and the actual CTA.

EYEBROW (stitch-hero.tsx:35): "Evidence Research Infrastructure" (mono, uppercase, text-zinc-500). Same string is the global title category and the left-spine watermark.

HERO HEADLINE (stitch-hero.tsx:39-43): "The evidence behind every factual claim — before it ships." with "before it ships." in font-bold.

HERO SUB (stitch-hero.tsx:49-53): "Tru8 decomposes AI-generated content into checkable claims and returns a structured evidence record — what supports each, what challenges it, what's missing. You decide what to publish, escalate, re-check or block." Followed by tagline "We organize; you decide." (US spelling, line 55).

PRIMARY CTA (stitch-hero.tsx:59-70): "Get API Key" (black button, links to /developers, fires `get_api_key_click`). Secondary CTA "See a Sample" (→ #preview). The researcher/human path is demoted to a quiet text link below: "Need the human review console? Open the Research App" (→ /research).

WHO IT TARGETS (as shipped): primarily DEVELOPERS / agent builders — primary CTA is "Get API Key", JSON-LD types the product as `SoftwareApplication` / `DeveloperApplication`, the homepage section order leads Record→Process→DeveloperShowcase, and OG/twitter copy is "Research the evidence behind factual AI output before it ships." This is a POSITIONING DRIFT away from the fixed researcher buyer ("show-your-working" journalists/analysts/policy researchers). The /research page exists and IS researcher-led (head "Not a verdict.", "show your working"), but it is a secondary destination, not the homepage. Per the review lens, the homepage's developer-first CTA + framing is the defect to flag, not the buyer.

LANGUAGE LOCK COMPLIANCE: strong. "We organize; you decide." everywhere; object is always the evidence/record; "Not a verdict. A structured evidence record." (stitch-record.tsx:85); manifest described as "Signed record", HMAC self-signed, NOT overstated as tamper-evident/independently verifiable (comments explicitly avoid it); user actions are concrete (publish/escalate/re-check/block) not "policy". US spelling on marketing (organize), UK on product/legal + the developers FAQ ("organise").

## Forbidden-word scan

True lock violations are flagged; legitimate uses (rival-category contrast, legal nouns, third-party product names) are listed as non-violations.

| Term | Where | Phrase | Violation? |
|---|---|---|---|
| evidence research | layout.tsx:28/31, page.tsx:17/32/52/88, stitch-hero.tsx:35, sitewide eyebrow + JSON-LD + spine | 'Tru8 — Evidence Research Infrastructure' / 'Evidence research infrastructure for factual AI content' | no |
| verdict | stitch-record.tsx:85 | 'Not a verdict. A structured evidence record.' | no |
| verdict | stitch-compare-teaser.tsx:20 | { who: 'Fact-checkers', they: 'a verdict' } — describing rival category, the contrast Tru8 defines itself against | no |
| verdict | stitch-faq.tsx:20/36 | 'Tru8 does not issue a verdict. We organize; you decide.' / 'never issues a verdict' | no |
| verdict | developers/page.tsx:41 | 'It does not return a true/false verdict. We organise; you decide.' | no |
| verdict | research/page.tsx:73 + comments | head: 'Not a verdict.' | no |
| verdict | blog/evidence-research-for-agents/page.tsx:171 | 'This isn't a summary or a verdict. It's a structured dataset...' | no |
| fact checking | blog/evidence-research-for-agents/page.tsx:13 | keywords array: 'fact checking API' — SEO keyword metadata (not visible body copy), but it leans on the forbidden frame | **YES** |
| fact-check | stitch-faq.tsx:23 | 'How is Tru8 different from a fact-checker?' — positioning-by-contrast Q&A, then differentiates | no |
| fact-check | developers/page.tsx:268 | 'Google Fact-Check API' — real third-party product name in a comparison table | no |
| confidence | compare/demo-data.ts:72,833 | 'queryConfidence': null and 'confidence': 'medium' inside the abridged raw-API demo JSON shown on /compare | **YES** |
| credibility | blog/first-public-release/page.tsx:114 | 'Build credibility with audiences by showing your claims are well-sourced' — reputation, not a credibility score | no |
| credibility | stitch-faq.tsx:36 | 'It never scores credibility and never issues a verdict.' — explicit negation, reinforces the lock | no |
| policy | privacy-policy / cookie-policy / refund-policy / terms-of-service / 'Acceptable Use Policy' | legal page titles + 'Acceptable Use Policy' — required legal nouns, not a product 'policy engine' | no |
| policy | stitch-compare-teaser.tsx:15, stitch-hero.tsx:16, research/page.tsx:39 comments | code comments ('never your policy', 'No policy (D15)', 'policy researchers' = audience) — not user-facing | no |
| tamper-evident | stitch-record.tsx:13-16 (comments only) | comments instruct NOT to claim tamper-evident; no user-facing use | no |

## Doc-vs-code conflicts found
- RUBRIC says 'evidence research' is a FORBIDDEN word to flag, but the ACTUAL shipped category/positioning is literally 'Evidence Research Infrastructure' — it is the global title (layout.tsx:28), the hero eyebrow (stitch-hero.tsx:35), the left-spine watermark (page.tsx:88), and recurs in OG copy and JSON-LD. Code is reality: this is the deliberate shipped category line, not a violation. The rubric's forbidden-list entry is stale on this term.
- RUBRIC/buyer lens fixes the audience as the 'show-your-working' researcher and says developer/agent drift is a defect. The shipped HOMEPAGE is explicitly developer-led: stitch-hero.tsx comment 'verification/dev-led', primary CTA is 'Get API Key' → /developers, JSON-LD types the app as DeveloperApplication/SoftwareApplication, and the researcher path is demoted to a quiet 'Open the Research App' text link. The researcher-led surface lives at /research, not /. This is a real positioning conflict to flag (homepage speaks developer-first), not a doc error.
- RUBRIC design lock: 'ONE orange accent used as a stroke/mark, NEVER a fill or gradient.' Code uses orange as tiny `bg-accent` FILLS — the rotated-square registration glyphs/seals (SheetHeader, stitch-hero CTA diamond, stitch-record _manifest seal) and the 2px top rules. They are hairline marks/rules (in spirit on-system) but technically fills, so the 'never a fill' wording is stricter than shipped reality.
- RUBRIC: 'NO traffic-light verdict colours' and 'muted element-state colours only inside Claim-Map'. globals.css ships SATURATED, non-muted traffic-light values: --state-supported #22C55E (green), --disposition-supports #10B981 emerald, --disposition-challenges/--state-disputed #F59E0B amber, --danger #DC2626. They are scoped to product-UI/claim-map tokens and are NOT used on the marketing homepage (hero renders 'supported' as a plain zinc token per its §2.2 comment), but they are not 'muted' as the rubric claims — worth verifying no page-level leak in the product views.
- themeColor inconsistency: layout.tsx viewport.themeColor = '#f27907' (a brighter orange) while the design accent is #EA580C. Minor, browser-chrome only, but two different oranges ship.
- CLAUDE.md / MEMORY docs still describe profession-named views and call the product 'evidence research' / 'fact-checking' in places; the shipped marketing correctly uses action-named framing and avoids fact-check language in body copy. Treat shipped components as truth (consistent with the stale-docs warning).
