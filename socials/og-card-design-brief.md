# Tru8 Social Share Card - Design Brief

## Overview

Design two OG (Open Graph) image templates for social media sharing. These cards appear when Tru8 links are shared on X/Twitter, LinkedIn, Facebook, WhatsApp, Slack, and Discord. They are the **primary marketing asset** driving traffic to Tru8.

**Goal:** Stop the scroll, create curiosity, drive clicks to the public report page.

---

## Technical Specifications

| Property | Value |
|----------|-------|
| Dimensions | 1200 x 630 px (1.91:1 ratio) |
| Format | PNG |
| Safe zone | Keep critical content within 1100 x 580 px (50px margin) |
| Mobile rendering | Cards display ~500px wide on mobile - text must be readable |
| File size | Under 300KB for fast loading |

---

## Brand Identity

### Brand Essence
- **Tru8** = Verification platform (NOT a fact-checker)
- **Positioning:** "See what credible sources say" - neutral, evidence-based
- **Emotion:** Trust, Authority, Modern Confidence
- **Aesthetic:** Pop sophistication - vibrant but authoritative

### Logo
- Tru8 wordmark or logomark should appear
- Position: Top left or integrated into header
- Not dominant - the content is the hero

### Color Palette

**Primary:**
```
Tru8 Orange: #f57a07 (main brand color)
Tru8 Cyan: #22d3ee (accent, highlights)
Dark BG: #0f1419
Card BG: #1e293b
```

**Verdict Colors:**
```
Supported: #059669 (Emerald Green)
Contradicted: #DC2626 (Strong Red)
Uncertain: #D97706 (Warning Amber)
```

**Neutrals:**
```
White: #FFFFFF
Gray 100: #F3F4F6
Gray 300: #D1D5DB
Gray 700: #374151
Gray 900: #111827
```

**Gradients:**
```
Primary gradient: linear-gradient(135deg, #f57a07 0%, #fb923c 100%)
Card gradient: linear-gradient(145deg, #1e293b 0%, #0f1419 100%)
```

### Typography
- **Font:** Inter (or similar clean sans-serif)
- **Headings:** Bold (700) or Black (900)
- **Body:** Regular (400) or Medium (500)
- **Numbers/Stats:** Bold, slightly larger for impact

---

## Card Type 1: Full Report Card

**Purpose:** Share an entire verification report (multiple claims)

### Content Elements (Priority Order)

1. **Header Bar**
   - Tru8 logo/wordmark
   - "EVIDENCE REPORT" label

2. **Title Zone**
   - Article/content title (2 lines max)
   - Truncate with "..." if needed
   - Example: "Nipah Virus Outbreak in Kerala, India"

3. **Stats Row** (The Hook)
   - Claims examined: "8 claims"
   - Sources searched: "231 sources"
   - Evidence cited: "47 evidence pieces"
   - Use icons or visual indicators

4. **Source Quality Visual**
   - Show breakdown of source types
   - Options: Horizontal bars, pie segment, tier badges
   - Categories: Health Authorities, Scientific Journals, Tier 1 News, Government, Other
   - This demonstrates BREADTH and QUALITY

5. **Source Names** (Social Proof)
   - List 4-6 top source names
   - Example: "WHO • CDC • The Lancet • BBC • Reuters"
   - Shows credibility at a glance

6. **CTA Footer**
   - "See what the sources say →"
   - tru8.app URL
   - Subtle but clear

### Example Data for Mockup
```
Title: "Nipah Virus Outbreak in Kerala, India"
Claims: 8
Sources searched: 231
Evidence pieces: 47
Source breakdown:
  - Health Authorities: 12
  - Scientific Journals: 8
  - Tier 1 News: 15
  - Government: 5
  - Other Credible: 7
Top sources: WHO, CDC, The Lancet, BBC, Reuters, Nature
```

---

## Card Type 2: Single Claim Card

**Purpose:** Share one specific claim with its evidence

### Content Elements (Priority Order)

1. **Header Bar**
   - Tru8 logo/wordmark
   - "EVIDENCE REPORT" label

2. **Claim Text**
   - The actual claim in quotes
   - 2-3 lines max, truncate if needed
   - Example: "The virus has a 40-75% mortality rate in humans"

3. **Verdict Badge** (Visual Focal Point)
   - Large, prominent verdict indicator
   - "SUPPORTED BY EVIDENCE" / "CONTRADICTED" / "UNCERTAIN"
   - Use semantic colors (green/red/amber)
   - Include confidence or source count: "8 sources agree"

4. **Source Evidence**
   - Show 4 source badges/chips with names
   - Example: WHO, CDC, The Lancet, NHS
   - "+4 more" indicator if additional sources
   - Optional: Small credibility dots (●●●●●)

5. **CTA Footer**
   - "See the full evidence →"
   - tru8.app URL

### Example Data for Mockup
```
Claim: "The virus has a 40-75% mortality rate in humans"
Verdict: SUPPORTED
Confidence: 94%
Source count: 8
Top sources: WHO, CDC, The Lancet, NHS
Additional sources: 4 more
```

---

## Visual Direction

### Do's
- **Bold contrast** - Must pop in a busy feed
- **Clear hierarchy** - Eye flows: Title → Stats/Verdict → Sources → CTA
- **Whitespace** - Don't crowd; let elements breathe
- **Professional** - Authoritative, trustworthy, not gimmicky
- **Readable at small size** - Test at 500px width

### Don'ts
- ❌ Too much text - this isn't a report, it's a hook
- ❌ Cluttered/busy - every element must earn its place
- ❌ Generic stock imagery - data IS the visual
- ❌ Low contrast text - must pass accessibility
- ❌ Overly playful - we're serious about truth
- ❌ "TRUE" / "FALSE" language - we say "Supported/Contradicted by evidence"

### Mood References
- Bloomberg terminal aesthetics (data-forward)
- Financial report summaries (authoritative)
- Scientific journal infographics (credible)
- Modern SaaS product cards (clean, professional)

---

## Variations to Design

### Full Report Card
1. **Light theme** - White/light gray background
2. **Dark theme** - Dark background (#0f1419 / #1e293b)

### Single Claim Card
1. **Supported verdict** - Green accent
2. **Contradicted verdict** - Red accent
3. **Uncertain verdict** - Amber accent

*(6 total variations)*

---

## Deliverables

1. **Full Report Card** - Light theme
2. **Full Report Card** - Dark theme
3. **Single Claim Card** - Supported (green)
4. **Single Claim Card** - Contradicted (red)
5. **Single Claim Card** - Uncertain (amber)
6. **Component library** - Reusable elements (logo placement, stat blocks, source chips, verdict badges)

---

## Success Criteria

The card succeeds if:
- [ ] Readable when rendered at 500px width (mobile)
- [ ] Brand is recognizable (Tru8 identity clear)
- [ ] Value proposition is instant (what did they verify? how thoroughly?)
- [ ] Creates curiosity (I want to see the full report)
- [ ] Looks professional (I trust this source)
- [ ] Differentiates from fact-checkers (evidence-based, not judgmental)

---

## AI Design Prompt

Use this prompt for AI design tools:

```
Design a social media OG card (1200x630px) for Tru8, a fact verification platform.

Style: Modern, professional, data-forward design. Bloomberg meets scientific journal. Clean sans-serif typography (Inter). High contrast for social feed visibility.

Colors:
- Brand orange #f57a07
- Dark background #0f1419 or white #FFFFFF
- Verdict green #059669, red #DC2626, amber #D97706
- Accent cyan #22d3ee

Layout for Full Report Card:
- Top: Tru8 logo + "EVIDENCE REPORT" badge
- Center: Article title in bold
- Stats row: "8 claims | 231 sources | 47 evidence pieces" with icons
- Source tier breakdown as horizontal progress bars
- Bottom: Source names (WHO, CDC, BBC, Reuters) + CTA "See what the sources say →"

Layout for Single Claim Card:
- Top: Tru8 logo + "EVIDENCE REPORT" badge
- Center: Claim text in quotes, large verdict badge "SUPPORTED BY EVIDENCE"
- Source chips showing WHO, CDC, The Lancet, NHS + "+4 more"
- Bottom: CTA "See the full evidence →"

Mood: Authoritative, trustworthy, modern. NOT a fact-checker - an evidence aggregator. The card should make viewers curious to click and see the full verification.
```
