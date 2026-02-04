# Prompt: Single Claim Card

## Design Request

Design a social media Open Graph card for sharing a single verified claim with its evidence.

---

## Specifications

- **Dimensions:** 1200 x 630 px
- **Safe zone:** Keep text within 1100 x 580 px (50px margins)
- **Must be readable at 500px width** (mobile rendering)

---

## Brand

**Product:** Tru8 - Evidence verification platform (NOT a fact-checker - we aggregate what sources say)

**Aesthetic:** Professional, data-forward, authoritative. Think Bloomberg terminal meets scientific journal. Clean, modern, trustworthy.

**Typography:** Inter or similar clean sans-serif. Bold headings, clear hierarchy.

---

## Color Palette

```
Primary brand:     #f57a07 (orange)
Accent:            #22d3ee (cyan)
Dark background:   #0f1419
Card surface:      #1e293b
White:             #FFFFFF
Light gray:        #F3F4F6
Text dark:         #111827
Text muted:        #374151
```

**Verdict Colors:**
```
Supported:     #059669 (emerald green)
Contradicted:  #DC2626 (strong red)
Uncertain:     #D97706 (amber)
```

---

## Content Layout (Top to Bottom)

### 1. Header Bar
- Tru8 logo or wordmark (left)
- "EVIDENCE REPORT" label/badge (right or beside logo)

### 2. Claim Text
- The claim in quotation marks
- Bold, prominent, 2-3 lines maximum
- Example: **"The virus has a 40-75% mortality rate in humans"**

### 3. Verdict Badge (Visual Focal Point)
Large, prominent verdict indicator:
- Text: "SUPPORTED BY EVIDENCE" or "CONTRADICTED BY EVIDENCE" or "UNCERTAIN"
- Use semantic verdict color as background or accent
- Include source agreement: "8 sources agree" or "94% confidence"

This is the HERO element - should draw the eye immediately.

### 4. Source Evidence
Show 4 source badges/chips:
- **WHO** (with credibility indicator)
- **CDC** (with credibility indicator)
- **The Lancet** (with credibility indicator)
- **NHS** (with credibility indicator)
- **"+4 more"** text for additional sources

Credibility indicator could be dots (●●●●●) or small bar.

### 5. Footer CTA
- "See the full evidence →"
- tru8.app

---

## Example Data for Mockups

**Supported Claim:**
```
Claim: "The virus has a 40-75% mortality rate in humans"
Verdict: SUPPORTED BY EVIDENCE
Confidence: 94%
Source count: 8 sources agree
Top sources: WHO, CDC, The Lancet, NHS
Additional: +4 more
```

**Contradicted Claim:**
```
Claim: "The outbreak was caused by 5G towers"
Verdict: CONTRADICTED BY EVIDENCE
Confidence: 97%
Source count: 12 sources contradict
Top sources: WHO, Nature, BBC, Reuters
Additional: +8 more
```

**Uncertain Claim:**
```
Claim: "The virus originated from fruit bats in a specific cave"
Verdict: UNCERTAIN - INSUFFICIENT EVIDENCE
Confidence: 45%
Source count: 3 sources, mixed findings
Top sources: Nature, Science, WHO
Additional: +0 more
```

---

## Variations Needed

1. **Supported verdict** - Green (#059669) accent, positive visual treatment
2. **Contradicted verdict** - Red (#DC2626) accent, alert visual treatment
3. **Uncertain verdict** - Amber (#D97706) accent, cautious visual treatment

All three on dark theme (#0f1419 background).

---

## Visual Direction

**Do:**
- Make verdict badge the dominant visual element
- High contrast between verdict color and background
- Claim text should be clearly readable
- Source chips should look credible and authoritative
- Clear hierarchy: Claim → Verdict → Sources → CTA

**Don't:**
- Use "TRUE" or "FALSE" language - we say "Supported/Contradicted by evidence"
- Make it look judgmental - we're showing evidence, not ruling
- Crowd the claim text - it needs to breathe
- Use low-contrast verdict colors
- Make sources look like an afterthought

---

## Mood References

- Scientific paper abstract cards
- Medical journal findings summaries
- Legal ruling announcements
- Financial analyst ratings

---

## Success Criteria

- [ ] Verdict is instantly visible and clear
- [ ] Claim text is readable and prominent
- [ ] Source names add credibility at a glance
- [ ] Creates curiosity to see full evidence
- [ ] Each verdict variation is visually distinct
- [ ] Professional, not sensational
- [ ] Tru8 brand is clear but not overpowering
