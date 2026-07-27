# Tru8 — Global Style Guide for Stitch

> Paste this entire document into Stitch ONCE before generating any page.
> It defines the visual system for every page and screen in the app.

---

## IDENTITY

Tru8 is an AI-powered evidence research platform. It collects, organises, and presents evidence — it does not render judgments. The visual language should feel like an **architectural specification sheet**: precise, authoritative, trustworthy, and calm.

**Keywords:** technical, clinical, institutional, spec-sheet, blueprint, calibrated.

---

## PALETTE

### Neutral (primary surface)
| Token | Hex | Usage |
|-------|-----|-------|
| `surface` | `#FFFFFF` | Page background, card background |
| `surface-raised` | `#F9FAFB` | Slightly elevated cards, table headers |
| `border` | `#E5E7EB` | Thin dividers, card borders (1px) |
| `border-strong` | `#D1D5DB` | Active borders, focused inputs |
| `text-primary` | `#111827` | Headlines, body text |
| `text-secondary` | `#6B7280` | Micro-labels, metadata, timestamps |
| `text-muted` | `#9CA3AF` | Placeholders, disabled text |

### Accent (used sparingly)
| Token | Hex | Usage |
|-------|-----|-------|
| `accent` | `#EA580C` | Single vivid orange. Active tab underline, tiny indicator squares, progress markers. NEVER as background fill. |
| `accent-muted` | `#EA580C` at 12% opacity | Hover state on accent elements only |

### Semantic (element states — used ONLY in Claim Map context)
| Token | Hex | Usage |
|-------|-----|-------|
| `state-supported` | `#22C55E` | ElementStateBadge: supported |
| `state-supported-bg` | `#F0FDF4` | Badge background |
| `state-disputed` | `#F59E0B` | ElementStateBadge: disputed |
| `state-disputed-bg` | `#FFFBEB` | Badge background |
| `state-unresolved` | `#94A3B8` | ElementStateBadge: unresolved |
| `state-unresolved-bg` | `#F8FAFC` | Badge background |

### System feedback
| Token | Hex | Usage |
|-------|-----|-------|
| `success` | `#059669` | Completed status, online indicator, checkmarks |
| `danger` | `#DC2626` | Error state, failed status, destructive actions |
| `warning` | `#D97706` | Warnings, offline indicator, connection issues |
| `info` | `#1E40AF` | Primary brand, links, information callouts |

---

## TYPOGRAPHY

### Hierarchy
| Level | Weight | Size | Transform | Tracking | Usage |
|-------|--------|------|-----------|----------|-------|
| `display` | 800 | 40px / 2.5rem | none | -0.02em | Landing hero only |
| `h1` | 700 | 28px / 1.75rem | none | -0.01em | Page titles (PageHeader) |
| `h2` | 600 | 20px / 1.25rem | none | normal | Section headings |
| `h3` | 600 | 16px / 1rem | none | normal | Card titles, claim text |
| `body` | 400 | 14px / 0.875rem | none | normal | Body text, descriptions |
| `small` | 400 | 12px / 0.75rem | none | normal | Timestamps, footnotes |
| `micro-label` | 600 | 10px / 0.625rem | uppercase | 0.08em | Section labels, metadata keys |
| `mono` | 400 | 12px / 0.75rem | none | 0.02em | Metadata values, IDs, hashes, build lines |

### Font stack
- **Primary:** Inter, system-ui, sans-serif
- **Mono:** JetBrains Mono, ui-monospace, monospace (metadata rows, IDs, system labels)

### Rules
- Micro-labels are ALWAYS uppercase with wide letter-spacing
- Metadata rows use monospace: `REF: TRU8-2026-001 / SYS: CALIBRATED / BUILD: d40668b`
- Never use italic for emphasis — use weight or micro-label style instead

---

## LAYOUT GRAMMAR

### Grid
- Web: 12-column grid, 1280px max-width, 24px gutters, 32px page padding
- Mobile: Single column, 16px horizontal padding, 12px gaps between cards

### Spacing scale
| Token | Value | Usage |
|-------|-------|-------|
| `space-xs` | 4px | Inline gaps, icon-to-text |
| `space-sm` | 8px | Badge padding, compact gaps |
| `space-md` | 16px | Card padding, section gaps |
| `space-lg` | 24px | Between major sections |
| `space-xl` | 40px | Page-level vertical breathing room |
| `space-2xl` | 64px | Hero sections, major breaks |

### Dividers
- Thin horizontal rules: 1px solid `border` token
- Used BETWEEN sections, never inside cards
- Generous whitespace above and below (space-lg minimum)

### Cards
- Background: `surface` (white)
- Border: 1px solid `border`
- Border radius: 8px (web), 12px (mobile)
- Padding: space-md (16px) on all sides
- Shadow: none (flat design — depth comes from border only)
- No background fills, no gradients

---

## COMPONENT CONVENTIONS

### Micro-labels
- Small uppercase text (`micro-label` style) above data values
- Examples: `CLAIM TYPE`, `ELEMENT STATE`, `SOURCE COUNT`, `PROCESSING TIME`
- Color: `text-secondary`
- Always paired with a value below in `body` or `mono` style

### Badges / Pills
- Border radius: 9999px (full round)
- Padding: 4px 10px
- Font: `small` weight 500
- Border: 1px solid (matching token)
- Background: muted version of semantic color
- Text: strong version of semantic color
- **ElementStateBadge:** supported (green), disputed (amber), unresolved (slate)
- **ClaimTypeBadge:** always `text-secondary` text on `surface-raised` background with `border` outline — neutral, never colored

### Buttons
- **Primary CTA:** Black background (`text-primary`), white text, wide letter-spacing (0.08em), uppercase, 48px height, full-width on mobile. Optional: tiny `accent` square (6x6px) at right edge as a subtle indicator.
- **Secondary:** White background, 1px `border` outline, `text-primary` text, same letter-spacing
- **Ghost:** No background, no border, `text-secondary` text, underline on hover
- **Destructive:** White background, 1px `danger` border, `danger` text

### Icons
- Size: 16px (inline), 20px (buttons), 48px (empty/error states)
- Stroke width: 1.5px
- Color: inherits from text context
- Library: Lucide (web), Lucide React Native (mobile)

### Metadata rows (spec-sheet style)
- Monospace font, `text-secondary` color
- Slash-separated on one line: `REF: abc-123 / SOURCES: 14 / PROCESSED: 2.3s`
- Or key-value pairs stacked vertically with micro-label + mono value

---

## CLAIM MAP VISUAL SPEC

This is the core UI component replacing the old verdict system. Use this exact structure.

### ClaimMapView (one per claim)
```
┌─────────────────────────────────────────────────────┐
│ CLAIM TYPE                                          │
│ ┌──────────────────┐                                │
│ │ ClaimTypeBadge    │                               │
│ └──────────────────┘                                │
│                                                     │
│ "Normalised claim text displayed in h3 style."      │
│                                                     │
│ ─────────────────── (thin divider) ──────────────── │
│                                                     │
│  ELEMENTS                                           │
│  ┌─ ElementList ──────────────────────────────────┐ │
│  │                                                │ │
│  │  1. Element description text                   │ │
│  │     [ElementStateBadge: supported]             │ │
│  │     Evidence: [EvidenceRefChip] [EvidenceRef…] │ │
│  │                                                │ │
│  │  2. Element description text                   │ │
│  │     [ElementStateBadge: disputed]              │ │
│  │     Evidence: [EvidenceRefChip] [EvidenceRef…] │ │
│  │     ⚠ Uncertainty: "Note about gap..."        │ │
│  │                                                │ │
│  │  3. Element description text                   │ │
│  │     [ElementStateBadge: unresolved]            │ │
│  │     Evidence: (none found)                     │ │
│  │     ⚠ Uncertainty: "Insufficient data..."     │ │
│  │                                                │ │
│  └────────────────────────────────────────────────┘ │
│                                                     │
│ ─────────────────── (thin divider) ──────────────── │
│                                                     │
│  ORIENTATION                                        │
│  "Mechanical summary sentence derived from element  │
│   states. Factual, never conclusory."               │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### ElementStateBadge
- **Supported:** green background (`state-supported-bg`), green text (`state-supported`), CheckCircle icon
- **Disputed:** amber background (`state-disputed-bg`), amber text (`state-disputed`), AlertTriangle icon
- **Unresolved:** slate background (`state-unresolved-bg`), slate text (`state-unresolved`), HelpCircle icon

### EvidenceRefChip
- Small pill: source name (truncated to ~20 chars) + relationship label
- Relationship label: `supports` (green text), `challenges` (amber text), `context` (slate text)
- On click/tap: navigates to evidence detail or expands inline

### OrientationLine
- Displayed as a single paragraph in `body` style, slightly larger weight (500)
- Preceded by `ORIENTATION` micro-label
- Never styled differently from body text — it must not look like a verdict
- No color coding, no icons, no badge

---

## ANIMATION

- None. Static layouts only.
- Loading states use skeleton placeholders (pulsing grey rectangles), not spinners.
- Exception: mobile pull-to-refresh uses native platform animation.

---

## DARK MODE

- Not in scope. Design for light mode only.

---

## MOBILE-SPECIFIC OVERRIDES

- Card border-radius: 12px (vs 8px web)
- Button height: 52px (vs 48px web)
- Typography scale: same ratios but `display` drops to 32px
- Bottom safe area: 34px padding for home indicator
- Tab bar: 3 tabs, icon + label, 49px height, `border` top edge
- Header bar: 44px height, centered title, back arrow left, action button right

---

## VOICE + TONE (for all UI copy)

- Present evidence, never conclusions
- "Analysis" not "verification" — "evidence report" not "fact-check result"
- "This claim has 3 elements: 2 supported, 1 disputed" — factual
- Never: "This claim is supported" / "This claim is false"
- Active voice, concise, lowercase where possible (except micro-labels)
- When uncertain: "Insufficient evidence was found for this element" — never "We couldn't verify this"
