# Tru8 Design System

> **Rewritten from code on 2026-06-29.** This supersedes the previous version, which
> described a dark "fact-checking" theme with green/red/amber **verdict colours** and
> confidence bars — none of which is shipped. That aesthetic was retired in the Track D
> light redesign and the no-verdict repositioning. **Ground truth is the code**
> (`web/app/globals.css`, `web/tailwind.config.ts`, `web/components/marketing/*`,
> `web/app/layout.tsx`); if this doc and the code ever disagree, the code wins.

The shipped system is the **Stitch "document-grammar"** language: a light, calibrated,
instrument-like surface that reads like the artifact it produces. Reference quality bar:
**Stripe · Linear · Vercel** — composed and width-using, restraint *with* direction.

---

## Theme

Light only. The body is `bg-white text-zinc-900 antialiased font-sans`
(`app/layout.tsx`). A zinc neutral scale carries the whole interface; there is no dark
mode on marketing (one dark *band* — the developer showcase — is an intentional inversion,
not a theme).

## Colour tokens (`globals.css :root`)

| Token | Value | Use |
|---|---|---|
| `--surface` | `#FFFFFF` | page background |
| `--surface-raised` | `#F9FAFB` | raised "rooms" / alternating sections |
| `--border` | `#E5E7EB` | 1px hairline borders |
| `--border-strong` | `#D1D5DB` | emphasised borders |
| `--text-primary` | `#111827` | headings, body |
| `--text-secondary` | `#6B7280` | secondary text |
| `--text-muted` | `#9CA3AF` | muted labels (⚠ see contrast note) |
| `--accent` | `#EA580C` (orange-600) | the single accent |
| `--accent-muted` | `rgba(234,88,12,0.12)` | rare accent wash |

**One accent, used as a mark — not a fill.** Orange appears only as small rotated-square
registration glyphs / seals (`w-2 h-2 bg-accent rotate-45`), as mono row numbers
(`text-accent`), and as the 2px document top-rule. No orange panels, no gradients, no fills.
Accent budget is self-policed per section (e.g. `stitch-record` ships with the comment
"eyebrow + 5 numbers + 1 seal only").

> **Known inconsistency to fix:** `layout.tsx` `viewport.themeColor` is a *different* orange
> (`#f27907`, browser chrome only) than the `#EA580C` accent. Align when convenient.

### Element-state colours are PRODUCT-UI tokens, not marketing colours
`globals.css` also defines saturated state values — `--state-supported #22C55E`,
`--state-disputed #F59E0B`, `--disposition-supports #10B981`, `--disposition-challenges
#F59E0B`. These belong **only inside Claim-Map / evidence-view element context**. They must
**never** appear on marketing pages, and never as a **page-level verdict** (e.g. a summary
panel must not headline green/amber counts). On the homepage, "supported" renders as a plain
zinc token by design.

## Typography

- **Inter** (`--font-inter`, sans) + **JetBrains Mono** (`--font-mono`, mono), both via
  `next/font/google`. Mono is **load-bearing**: eyebrows, refs, sheet numbers, labels.
- **Headings are `font-normal`. SIZE is the hierarchy lever, not weight.** Hero `h1` runs up
  to `lg:text-[84px] tracking-[-0.03em] leading-[0.95]`; section `h2` is `text-3xl→5xl
  font-normal`.
- **Bold is reserved**: the hero `h1` emphasis word and the preview/differentiator panel
  labels only. Do not reach for `font-bold` to make a section header louder — make it bigger.
- Base font scales mobile-first: 14px → 15px (≥640) → 16px (≥768).

## Document grammar

- **`SheetHeader`** (`components/marketing/sheet-header.tsx`): 1px top rule + rotated 2px
  orange registration glyph + mono two-digit **sheet number** + mono uppercase label
  (`tracking-[0.3em]`) + right-aligned mono datasheet ref. Sheets are numbered (`01` Record,
  `02` Process, …) — keep the series contiguous; a lone `04`/`05` reads as a leak.
- **Document frame:** a continuous 1px inset border at `max-w-7xl`, a single 2px orange top
  rule (`h-[2px] w-full bg-accent`), and a fixed vertical mono **left spine**
  (`TRU8 · EVIDENCE RESEARCH INFRASTRUCTURE · REV …`, `text-zinc-300`, `xl+` only).
- **Surfaces:** square / minimal radius, 1px borders, **no drop-shadows, no gradients** on
  marketing. Alternate white / `zinc-50` "rooms" rather than stacking undifferentiated whites.

## Spacing & layout

4pt grid; Tailwind spacing scale. Sections breathe asymmetrically (open → chapter → fast →
proof → close) rather than a flat `py-32` metronome. Content max-width `max-w-7xl` with the
inset frame; headers narrow, artifacts wide.

## Accessibility (standing requirements)

- **Contrast:** `--text-muted #9CA3AF` / `zinc-300`/`zinc-400` are **AA traps** for
  load-bearing text (eyebrows, refs, back links, table marks). Lift load-bearing text/marks
  to `zinc-500/600`. Reserve `zinc-300/400` for genuinely decorative strokes.
- Skip-link present; `focus-visible` outline `2px #111827`. Keep heading order sequential.

## Voice (cross-reference, not a design token)

UK English across the whole surface (marketing, product UI, and legal — D13, updated
2026-06-29). Language locks (no "verdict"/"confidence score"/"policy"; views named by
**action** — Evidence · Sources · Timeline · Gaps · Map · Video) live in
`audit/2026-06-17_repositioning_agreements.md` and the pre-launch review
`docs/page-review-2026-06-29/`.

---

## Hard rules

**MUST**
1. Light theme, zinc scale, one orange accent **as a mark** (glyph / rule / mono number).
2. `font-normal` headings; size is hierarchy; bold reserved (hero h1 + preview labels).
3. 1px borders; no shadows, no gradients on marketing.
4. Mono for eyebrows / refs / numbers; contiguous sheet numbering.
5. Load-bearing text meets AA (≥ `zinc-500`).

**NEVER**
- ❌ Verdict / traffic-light colours (green=supported, red=contradicted) anywhere on
  marketing, or at page-summary altitude in the product.
- ❌ Orange as a fill, gradient, or panel.
- ❌ `font-bold` section headers (use size).
- ❌ Drop-shadows or gradients on marketing surfaces.
- ❌ Confidence bars / credibility scores (the retired theme) — they contradict the product.
