# Stitch Prompt Contract — Tru8 Track C

**Purpose:** Rules, structure, and template for every Stitch page/screen prompt in this pack.
Paste `STITCH_STYLE_GUIDE.md` into Stitch first (once), then paste individual page prompts one at a time.

---

## 1. Prompt Structure (mandatory sections)

Every page prompt follows this exact order. Sections marked (skip) may be omitted when genuinely empty.

```
A) PAGE IDENTITY
B) NAV + SHELL
C) LAYOUT (section-by-section, top-to-bottom)
D) DATA + UI
E) CLAIM MAP RENDERING            ← skip if page has no claim data
F) STATES (loading / empty / error / gating / offline)
G) COPY TONE
H) DO NOTS
```

### A — PAGE IDENTITY
- Page name, route (web) or screen name (mobile)
- Platform: `web` or `mobile (iOS + Android)`
- Primary user goal in one sentence

### B — NAV + SHELL
- Which persistent chrome wraps this page (SignedInNav, tab bar, footer, etc.)
- Breadcrumb / back-button pattern if applicable
- Whether BetaBanner or UpgradeBanner appears

### C — LAYOUT
- Ordered list of visual sections from top to bottom
- Each section: component name, 1-line intent, approximate height/width hints where useful
- Use consistent component names from the inventory (e.g., `PageHeader`, `CheckCard`, `ClaimMapView`)

### D — DATA + UI
- Fields displayed per section (use exact field names from shared types)
- Grouping, sorting, filtering, tabs, accordions
- Pagination / infinite scroll / load-more patterns

### E — CLAIM MAP RENDERING
- Where `ClaimMapView`, `ElementList`, `OrientationLine`, `ElementStateBadge`, `ClaimTypeBadge` appear
- Evidence refs grouped by element with relationship chips (supports / challenges / context)
- Uncertainty notes inline under elements
- Orientation line as final mechanical sentence, never styled as a verdict

### F — STATES
- Loading skeleton shape
- Empty state (icon + copy + CTA)
- Error state (icon + copy + retry)
- Pro gating / upgrade modal trigger
- Mobile: offline banner, queue indicator

### G — COPY TONE
- Neutral, evidence-first language
- Active voice, concise, factual
- Never judgmental, never conclusory

### H — DO NOTS
- Always include the full forbidden list (see Section 4 below)

---

## 2. Dos

| Rule | Rationale |
|------|-----------|
| One page per prompt | Stitch performs best with focused, single-screen prompts |
| Paste style guide first | Global tokens load before any page prompt |
| Use exact component names | Consistency across 31 prompts lets Stitch reuse patterns |
| Specify section order | Stitch renders top-to-bottom; order = information hierarchy |
| Describe states explicitly | Stitch omits states unless told |
| Keep prompts under 3,000 chars | Long prompts cause Stitch to drop components |
| Use UI/UX keywords | "card layout", "tab bar", "accordion", "skeleton loader" — Stitch parses these |
| Reference elements specifically | "the primary CTA button in the hero section", not "the button" |

---

## 3. Don'ts

| Anti-pattern | Why |
|--------------|-----|
| Combining layout + feature changes | Causes Stitch to reconstruct the entire layout |
| Mixing web and mobile in one prompt | Different shells, different constraints |
| Requesting animations or transitions | Keep static; animation is implementation detail |
| Writing React/JSX code | Stitch generates its own; code confuses it |
| Using verdict-era language | "Verdict", "Confidence Score", "Supported/Contradicted" — forbidden everywhere |
| Referencing colors by hex | Use semantic names from the style guide |
| Prompt over 5,000 characters | Stitch consistently omits components in long prompts |
| Multiple major changes per prompt | "One major change at a time" per Stitch docs |

---

## 4. Forbidden Terms (include in every prompt Section H)

These terms must NEVER appear in any UI text, label, badge, heading, tooltip, or alt text:

```
- "Verdict" / "verdict"
- "Supported" / "Contradicted" / "Uncertain" (as verdict labels)
- "Confidence score" / "Confidence %" / "Confidence bar"
- "Generating Verdict"
- "Judge" / "Judgment" (as pipeline stage)
- "Decision Trail"
- "Credibility Score" / "credibilityScore"
- "Misinformation rate"
- "VerdictPill" / "ConfidenceBar" / "ConfidenceBreakdown"
- "How was this determined?"
- "Was this verdict helpful?"
- Any three-way supported/contradicted/uncertain breakdown
```

---

## 5. Platform Notes

### Web (Next.js)
- Desktop-first, responsive down to 768px
- Persistent shell: `SignedInNav` (top), `Footer` (bottom) inside `/dashboard/*`
- Public pages: `Navigation` (top), `MobileBottomNav` (mobile viewport), `Footer` (bottom)
- Legal pages: `LegalPageLayout` wrapper (centered prose, constrained width)
- Page transitions: none (server components, instant navigation)
- PageHeader pattern: oversized title + subtitle + optional decorative graphic

### Mobile (Expo / React Native)
- Bottom tab bar: 3 visible tabs (Home, History, Account)
- Hidden stack routes: check/[id], progress/[id], subscription, settings
- Header bar pattern: back arrow (left) + title (center) + optional action (right)
- Pull-to-refresh on list screens
- Offline-aware: queue indicator, connection-lost banner
- Safe area insets: respect top notch and bottom home indicator

---

## 6. Reusable Prompt Template

```markdown
# [PAGE_ID] — [Page Name]

> Paste STITCH_STYLE_GUIDE.md into Stitch before this prompt.

## A) PAGE IDENTITY
- **Name:** [Page Name]
- **Route:** [/route or screen name]
- **Platform:** [web | mobile (iOS + Android)]
- **User goal:** [One sentence]

## B) NAV + SHELL
- [Shell description]

## C) LAYOUT
1. **[SectionName]** — [intent]
2. **[SectionName]** — [intent]
...

## D) DATA + UI
- [Field list, grouping, filters, tabs]

## E) CLAIM MAP RENDERING
- [Where ClaimMapView / ElementList / OrientationLine appear, or "N/A"]

## F) STATES
- **Loading:** [skeleton description]
- **Empty:** [icon + copy + CTA]
- **Error:** [icon + copy + retry]
- **Gating:** [Pro feature modal, if applicable]

## G) COPY TONE
Neutral evidence language. Active voice. Never judgmental, never conclusory.
Refer to "evidence research" not "fact-checking". Refer to "analysis" not "verification".

## H) DO NOTS
Do not use: verdict, confidence score, confidence bar, supported/contradicted/uncertain
verdict labels, "Generating Verdict", judge, decision trail, credibility score,
misinformation rate, VerdictPill, ConfidenceBreakdown, or any three-way verdict breakdown.
```

---

## 7. Component Name Registry

Use these exact names in all prompts for cross-page consistency.

### Shared (web + mobile)
| Component | Purpose |
|-----------|---------|
| `ClaimMapView` | Full claim map: normalised claim, type badge, elements, evidence, orientation |
| `ElementList` | 1-5 elements with state badges, evidence refs, uncertainty notes |
| `ElementStateBadge` | Pill: supported (green) / disputed (amber) / unresolved (slate) |
| `ClaimTypeBadge` | Pill: empirical / definitional / causal-interpretive / predictive / normative-flagged |
| `OrientationLine` | Single mechanical sentence derived from element states |
| `EvidenceRefChip` | Small chip: source name + relationship (supports / challenges / context) |

### Web only
| Component | Purpose |
|-----------|---------|
| `PageHeader` | Oversized title + subtitle + optional decorative graphic |
| `CheckCard` | History/dashboard card: input preview, date, element state summary |
| `CheckTabs` | Tab toggle: EVIDENCE MAP / SOURCES |
| `CheckMetadataCard` | Input type, timestamp, processing time, source count |
| `ShareSection` | Copy link, social share buttons |
| `ProgressSection` | Pipeline stage stepper (select → decompose → analyze) |
| `UserInsightsCard` | Element state breakdown across all checks |
| `SourceAnalytics` | Source type distribution, domain breakdown |

### Mobile only
| Component | Purpose |
|-----------|---------|
| `ClaimCard` | Single claim: ClaimMapView wrapper with evidence drawer trigger |
| `EvidenceDrawer` | Full-screen modal: evidence list grouped by element |
| `ProgressStepper` | Vertical stage list with completion indicators |
| `RelevanceBar` | Horizontal bar showing evidence relevance score (0-1) |
| `CreateCheckForm` | URL/text input with offline queue awareness |

---

## 8. File Naming Convention

```
audit/track-c/stitch/pages/
  W-01__landing.md
  W-02__root_layout.md
  ...
  W-19__privacy_policy.md
  M-01__root_layout.md
  ...
  M-12__subscription.md
```

Pattern: `{PLATFORM_PREFIX}-{NUMBER}__{snake_case_name}.md`
