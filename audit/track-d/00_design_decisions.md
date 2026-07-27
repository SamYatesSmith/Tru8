# Track D — Design Decisions (LOCKED)

**Date:** 2026-02-15
**Authority:** Product owner directive

---

## Decision 1: Full Light Theme

**Status:** LOCKED

The entire web frontend adopts the Stitch light theme. No page retains the old dark (`#0f1419`) aesthetic. This includes:
- All marketing/public pages (landing, about, blog, contact)
- All dashboard pages (dashboard, check detail, history, settings, new-check, sources)
- All legal pages (privacy, terms, cookie, refund)
- Public report page
- Root layout, dashboard layout
- Navigation, footer, all shared components

**Rationale:** The old dark theme was the pre-pivot "fact-checker" identity. The new Stitch design language (light, architectural, spec-sheet) reflects the evidence research platform positioning.

**Dark mode:** May be added later as a toggle. Track D designs for light only.

---

## Decision 2: Stitch Style Guide is Canonical

**Status:** LOCKED

The design system defined in `audit/track-c/stitch/STITCH_STYLE_GUIDE.md` is the canonical reference for all visual decisions. Key tokens:

### Palette
| Token | Value | Current (old) |
|-------|-------|---------------|
| `surface` | `#FFFFFF` | `#0f1419` |
| `surface-raised` | `#F9FAFB` | `#1a1f2e` |
| `border` | `#E5E7EB` | `slate-700` |
| `border-strong` | `#D1D5DB` | `slate-600` |
| `text-primary` | `#111827` | `white` |
| `text-secondary` | `#6B7280` | `slate-400` |
| `text-muted` | `#9CA3AF` | `slate-500` |
| `accent` | `#EA580C` | `#f57a07` |

### Typography
| Level | Font | Weight | Size |
|-------|------|--------|------|
| Primary | Inter | — | — |
| Mono | JetBrains Mono | — | — |
| display | Inter | 800 | 40px |
| h1 | Inter | 700 | 28px |
| micro-label | Inter | 600 | 10px, uppercase, 0.08em tracking |
| mono | JetBrains Mono | 400 | 12px |

### Components
- **Cards:** White bg, 1px `border`, 8px radius, no shadow, no gradients
- **Buttons (primary):** Black bg, white text, uppercase, wide letter-spacing, 48px height, optional orange square accent
- **Buttons (secondary):** White bg, 1px border, black text
- **Badges:** Full-round (9999px), 1px border, muted background
- **Dividers:** 1px solid `border`, generous whitespace
- **Grid background:** `radial-gradient(#e5e7eb 1px, transparent 1px)` at 40px — used on landing hero and some headers

### Animation
- None. Static layouts only.
- Loading states: skeleton placeholders (pulsing grey), not spinners.

---

## Decision 3: Copy Language Standard

**Status:** LOCKED

All UI copy follows the Stitch voice & tone guidelines:

| Old Term | New Term |
|----------|----------|
| Verification / verify | Analysis / analyse |
| Fact-checking / fact check | Evidence research |
| Verdict | *(deleted — never used)* |
| Confidence score | *(deleted — never used)* |
| Misinformation | Uncertain information |
| Start Verifying | Start Researching / Start Analysis |
| Claim verification | Evidence research |
| Professional claim verification | Professional evidence research platform |
| Get Results | Review Evidence |
| How Tru8 Works (steps) | Submit / Research / Review |

**Rule:** Present evidence, never conclusions. "Analysis" not "verification". "Evidence report" not "fact-check result".

---

## Decision 4: Stitch Designs Are the Mirror — Faithful Reproduction

**Status:** LOCKED

The Stitch HTML outputs are the definitive target. Implementation reproduces them faithfully. No elements are omitted, no assumptions are made about what is or isn't important.

**The spec-sheet aesthetic IS the design.** The technical-drawing elements — monospace micro-labels, system identifiers, module references, metadata rows, status indicators — are core to the architectural specification sheet identity. These are not filler or placeholder content. They are the design language.

Implementation will:
- Reproduce the Stitch output for each page as closely as possible
- Preserve ALL visual elements including micro-labels, system IDs, metadata rows, module references, status lines, and technical nomenclature
- Populate technical-drawing elements with real data where available (actual build hashes, actual system status, actual timestamps) and retain the Stitch format/structure where real data is not yet available
- Use Tailwind CSS classes mapped to the Stitch token system
- Replace Material Symbols icons with the closest Lucide equivalent (Lucide is already used across the codebase — the only permitted adaptation)
- Convert Stitch HTML structure to React/Next.js component patterns

**Rule:** If the Stitch design shows it, it ships. If something needs changing, that happens in a separate implementation after Track D. No pre-emptive edits, no omissions, no assumptions about intent.

---

## Decision 5: Scope Includes ALL Web Pages

**Status:** LOCKED

Track D converts every web page. No page is out of scope. Full list:

### Phase 1 — Foundation (tokens + shared components)
- Root layout (`app/layout.tsx`)
- CSS tokens (globals.css)
- Tailwind config
- Navigation component
- MobileBottomNav component
- Footer component
- LegalPageLayout component

### Phase 2 — Marketing pages
- Landing page (`/`)
- About (`/about`)
- Blog index (`/blog`)
- Blog post (`/blog/[slug]`)
- Contact (`/contact`)

### Phase 3 — Dashboard pages
- Dashboard layout (`app/dashboard/layout.tsx`)
- Dashboard home (`/dashboard`)
- New check (`/dashboard/new-check`)
- Check detail (`/dashboard/check/[id]`)
- Sources (`/dashboard/check/[id]/sources`)
- History (`/dashboard/history`)
- Settings (`/dashboard/settings`)

### Phase 4 — Legal + public pages
- Privacy policy (`/privacy-policy`)
- Terms of service (`/terms-of-service`)
- Cookie policy (`/cookie-policy`)
- Refund policy (`/refund-policy`)
- Public report (`/r/[id]`)

### Phase 5 — Cleanup
- Delete old marketing components (animated-background, old hero, etc.)
- Final copy sweep
- Grep gate for old tokens

---

## Decision 6: Track C Claim Map Components Are Retained

**Status:** LOCKED

The ClaimMapView, ElementList, ElementStateBadge, ClaimTypeBadge, OrientationLine, and EvidenceRefChip components built in Track C are structurally correct. They need only token/color updates to match the light theme (e.g., badge backgrounds shift from dark variants to `bg-emerald-50`, `bg-amber-50`, `bg-slate-50`).

These are NOT rebuilt from scratch — they are re-themed.
