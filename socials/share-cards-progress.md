# Share Cards - Progress & Decisions Log

## Overview

This document tracks design decisions and build requirements for Tru8 social share cards.

---

## Platform Compatibility

| Platform | OG Image Support | Dimensions | Status |
|----------|------------------|------------|--------|
| **X/Twitter** | Yes - `twitter:image` | 1200x630 (1.91:1) | Compatible |
| **LinkedIn** | Yes - `og:image` | 1200x627 (1.91:1) | Compatible |
| **WhatsApp** | Yes - `og:image` | 1200x630 | Compatible |
| **Instagram** | **NO** | N/A | **Not compatible** |

### Instagram Limitation

Instagram does **not** support OG link previews. When you share a link:
- **Feed posts**: Cannot include clickable links
- **Stories**: Link sticker, but NO preview card
- **DMs**: May show basic preview, inconsistent
- **Bio**: Just a link, no card

**Options for Instagram:**
1. Users screenshot the card and post as image (manual)
2. Generate a downloadable image they can post natively
3. Skip Instagram for link sharing (focus on X, LinkedIn, WhatsApp)

**Recommendation:** Add "Download as Image" option alongside share buttons. This serves Instagram users and anyone who wants to post the card as native content.

---

## Card Type 1: Single Claim Card

### Design Status: Draft Complete

**Screenshot:** `c:\Users\james\Pictures\Screenshots\Screenshot 2026-01-28 113143.png`

### Approved Elements

| Element | Decision |
|---------|----------|
| **Layout** | Dark theme, claim left, logo right |
| **Claim text** | Large, bold, white - add quotation marks |
| **Verdict badge** | Green "SUPPORTED" - prominent placement |
| **Confidence** | Show "94% confidence" (remove "verified" prefix) |
| **Source chips** | WHO, CDC, The Lancet, NHS, +4 more |
| **Logo placement** | Right side, Tru8 logo |
| **CTA** | Single CTA: "See what the sources say" (changed from "SEE THE REPORT") |

### Changes Required

| Change | Priority | Notes |
|--------|----------|-------|
| Add quotation marks to claim | Medium | Signals "this is being examined" |
| Remove "verified" word | High | Too certain, fact-checker framing |
| Remove duplicate CTA | High | Keep only main CTA top-right |
| Fix arrow icon rendering | Low | Replace text with actual icon |
| Change CTA text | Medium | "SEE THE REPORT" → "See what the sources say" |
| Add "EVIDENCE REPORT" label | Low | Can add during build |

### Verdict Variations Needed

| Variation | Color | Badge Text |
|-----------|-------|------------|
| Supported | #059669 (green) | "SUPPORTED" |
| Contradicted | #DC2626 (red) | "CONTRADICTED" |
| Uncertain | #D97706 (amber) | "UNCERTAIN" |

---

## Card Type 2: Full Report Card

### Design Status: Draft Complete

**Screenshot:** `c:\Users\james\Pictures\Screenshots\Screenshot 2026-01-28 125307.png`

### Current Design Elements

| Element | Current State | Assessment |
|---------|---------------|------------|
| **Dark theme** | Yes | Consistent with Single Claim Card |
| **Tru8 logo** | Top left | Correct placement |
| **"EVIDENCE REPORT" badge** | Top right, orange | Good - present and visible |
| **Title** | "Nipah Virus Outbreak in Kerala, India" | Large, bold, clear - works well |
| **Stats row** | 8 claims, 231 sources, 47 evidence | Prominent orange numbers, good impact |
| **Source quality breakdown** | Health Authorities 65% bar | Good concept, needs expansion |
| **Top sources list** | WHO, Ministry of Health India | Needs more sources |
| **CTA** | Missing | Must add |
| **URL** | Missing | Must add |

### What Works Well

1. **Stats row** - The three big orange numbers (8, 231, 47) are visually impactful and immediately communicate thoroughness
2. **Title prominence** - Clear hierarchy, readable
3. **"EVIDENCE REPORT" badge** - Good framing, present unlike Single Claim Card draft
4. **Source quality breakdown concept** - Differentiates Tru8 from simple fact-checkers
5. **Dark theme consistency** - Matches Single Claim Card aesthetic
6. **Layout flow** - Title → Stats → Quality → Sources reads naturally

### Changes Required

| Change | Priority | Notes |
|--------|----------|-------|
| **"CLAIMS VERIFIED" → "CLAIMS EXAMINED"** | High | "Verified" implies truth judgment |
| **Add CTA** | High | Missing entirely - need "See what the sources say" |
| **Add tru8.app URL** | High | No URL visible, users need destination |
| **"TOP TRUSTED SOURCES" → "TOP SOURCES"** | Medium | "Trusted" implies Tru8 judgment |
| **Show more sources** | Medium | Only 2 shown, need 4-5 for social proof |
| **Remove green checkmarks** | Medium | ✓ implies "verified/approved" - use neutral bullets |
| **Show multiple source tiers** | Medium | Only Health Authorities shown, show 2-3 tiers |
| **Clarify 65% meaning** | Low | What does percentage represent? Add context or reconsider |
| **Consider verdict summary** | Low | "6 supported • 1 contradicted • 1 uncertain" creates hook |

### Language Issues (Same as Single Claim Card)

| Current | Problem | Change To |
|---------|---------|-----------|
| "CLAIMS VERIFIED" | Implies truth judgment | "CLAIMS EXAMINED" |
| "TOP TRUSTED SOURCES" | Implies Tru8 decides trust | "TOP SOURCES" |
| Green checkmarks ✓ | Implies verification/approval | Neutral bullets or none |

### Source Quality Breakdown

**Current:** Only shows one tier (Health Authorities at 65%)

**Recommended:** Show 2-3 tiers to demonstrate source diversity:
```
Health Authorities    ████████████░░░░  65%
Scientific Journals   ██████░░░░░░░░░░  25%
Tier 1 News          ████░░░░░░░░░░░░  10%
```

**Question:** What does the percentage represent?
- % of total evidence from this tier?
- Average credibility of sources in tier?

Needs clarification for viewer comprehension.

### Top Sources Section

**Current:**
- ✓ World Health Organization
- ✓ Ministry of Health, India

**Recommended:** Show 4-5 sources inline for better social proof:
> WHO • Ministry of Health India • The Lancet • BBC • Reuters • +8 more

### Missing Elements

| Element | Recommendation |
|---------|----------------|
| **CTA button** | Add top-right: "See what the sources say" |
| **URL** | Add bottom-right: tru8.app |
| **Verdict summary** | Optional hook: "6 supported • 1 contradicted • 1 uncertain" |

### Verdict Summary (Optional Enhancement)

Adding a verdict breakdown creates curiosity:
> "Wait, one claim was contradicted? Which one?"

Could appear below stats row:
```
✓ 6 supported  ✗ 1 contradicted  ? 1 uncertain
```

This transforms the card from "we did research" to "here's what we found" - stronger hook.

### Design Prompt Reference

See: `socials/prompt-full-report-card.md`

---

## Logo Placement Requirements

### Tru8 Logo Must Appear On All Cards

| Card Type | Primary Logo Position | Notes |
|-----------|----------------------|-------|
| **Single Claim Card** | Top left (wordmark) | Current design has logo right side - consider consistency |
| **Full Report Card** | Top left (wordmark) | Current design correct |

### Logo Specifications

- **Format:** Tru8 logo with orange triangle icon + "TRU8" wordmark
- **Position:** Top left corner, consistent across both card types
- **Size:** Proportional to card, readable at 500px width (mobile)
- **Clearance:** Adequate padding from edges and other elements

### Consistency Note

Single Claim Card currently shows logo placeholder on **right side**. Full Report Card has logo **top left**.

**Decision needed:** Should both cards have logo in same position for brand consistency?

**Recommendation:** Top left for both cards - this is conventional placement and matches Full Report Card.

---

## Key Brand/Language Decisions

### Positioning
- Tru8 is an **evidence aggregator**, NOT a fact-checker
- We show "what sources say" - user decides
- Neutral, not judgmental

### Language Rules

| Avoid | Use Instead |
|-------|-------------|
| "TRUE" / "FALSE" | "Supported" / "Contradicted" |
| "We verified" | "Sources indicate" |
| "Fact check" | "Evidence report" |
| "Debunked" | "Contradicted by evidence" |
| "Confirmed" | "Supported by X sources" |

### Legal Consideration
Emotional/viral positioning = legal liability. Neutral evidence aggregation = defensible. Design should be professional and rational, not sensational.

---

## Technical Build Requirements

### Public Routes Needed
```
/r/[checkId]              → Public report page (full check)
/r/[checkId]?claim=[n]    → Public report, scrolled to specific claim
```

### API Endpoints Needed
```
GET /api/v1/public/checks/[id]           → Public check data (limited)
GET /api/v1/public/checks/[id]/claims/[n] → Single claim data
```

### OG Image Generation Endpoints
```
/api/og/check/[id]        → Full report card image
/api/og/claim/[checkId]/[claimIndex]  → Single claim card image
```

### Data Required for Cards

**Single Claim Card:**
```typescript
interface SingleClaimCardData {
  claimText: string;
  verdict: 'supported' | 'contradicted' | 'uncertain';
  confidence: number;
  sourceCount: number;
  topSources: string[];  // ["WHO", "CDC", "The Lancet", "NHS"]
  additionalSourceCount: number;  // For "+4 more"
}
```

**Full Report Card:**
```typescript
interface FullReportCardData {
  title: string;
  claimCount: number;
  sourcesSearched: number;
  evidenceCount: number;
  sourceTiers: {
    healthAuthorities: number;
    scientific: number;
    tier1News: number;
    government: number;
    other: number;
  };
  topSources: string[];
  verdictSummary: {
    supported: number;
    contradicted: number;
    uncertain: number;
  };
}
```

### Image Generation Tech
- Use `@vercel/og` (Satori) for server-side image generation
- React components render to PNG
- Cache generated images (same check = same image)

---

## Share Button Locations

| Location | What's Shared | Card Type |
|----------|---------------|-----------|
| Report header | Full report | Full Report Card |
| Claim card (expanded) | That claim | Single Claim Card |
| History list (collapsed) | Full report | Full Report Card |
| History list (expanded claim) | That claim | Single Claim Card |

---

## Outstanding Questions

1. **Instagram strategy** - Download button? Skip platform? Manual screenshot guidance?
2. **Short URLs** - Do we want `tru8.app/r/abc123` or shorter like `tr8.co/abc123`?
3. **Analytics** - Track shares per platform? UTM parameters?
4. **Rate limiting** - OG image generation could be abused, need caching/limits

---

## Design Review Summary

### Single Claim Card

| Aspect | Status |
|--------|--------|
| Layout | Approved with changes |
| Verdict badge | Good |
| Source chips | Good |
| Language | Needs fixes ("verified") |
| CTA | Needs consolidation |
| Logo | Needs consistency decision |

### Full Report Card

| Aspect | Status |
|--------|--------|
| Layout | Approved with changes |
| Stats row | Strong - good visual impact |
| Source breakdown | Good concept, needs expansion |
| Source list | Needs more entries |
| Language | Needs fixes ("verified", "trusted") |
| CTA | Missing - must add |
| URL | Missing - must add |
| Logo | Correct position (top left) |

### Cross-Card Consistency Checklist

| Element | Single Claim | Full Report | Consistent? |
|---------|--------------|-------------|-------------|
| Dark theme | Yes | Yes | ✓ |
| Logo position | Right side | Top left | ✗ Needs alignment |
| "EVIDENCE REPORT" badge | Missing | Present | ✗ Add to Single |
| CTA style | Present | Missing | ✗ Add to Full |
| URL | Missing | Missing | ✗ Add to both |
| Font/typography | Matches | Matches | ✓ |
| Orange accent color | Yes | Yes | ✓ |

---

## Next Steps

1. [x] ~~Get Single Claim Card design from AI design tool~~
2. [x] ~~Review Single Claim Card~~
3. [x] ~~Get Full Report Card design from AI design tool~~
4. [x] ~~Review Full Report Card~~
5. [x] Apply design revisions:
   - [x] Fix language issues on Single Claim Card (removed "verified" prefix)
   - [x] Consolidate CTA on Single Claim Card ("See what the sources say →")
   - [x] Add "EVIDENCE REPORT" badge to Single Claim Card
   - [x] Add tru8.app URL footer to Single Claim Card
   - [x] Add quotation marks to claim text
   - [x] Change "TOP VERIFIED SOURCES" → "TOP SOURCES"
   - [ ] Fix language issues on Full Report Card
   - [ ] Add CTA + URL to Full Report Card
   - [ ] Expand source tier breakdown on Full Report Card
6. [x] Single Claim Card implementation complete:
   - [x] Public API endpoint (`/api/v1/public/checks/{id}`)
   - [x] OG image generation (`@vercel/og`)
   - [x] Shared components (Logo, VerdictBadge, SourceChip, MoreChip)
   - [x] API route (`/api/og/claim/[checkId]/[claimIndex]`)
7. [ ] Remaining work:
   - [ ] Public routes (`/r/[checkId]`)
   - [ ] Full Report Card implementation
   - [ ] Share button components
   - [ ] "Download as Image" feature (for Instagram)
8. [ ] Build and test across X, LinkedIn, WhatsApp

---

## Files Reference

| File | Purpose |
|------|---------|
| `socials/share-cards-progress.md` | This document - decisions log |
| `socials/og-card-design-brief.md` | Combined design brief |
| `socials/prompt-full-report-card.md` | AI prompt for Full Report Card |
| `socials/prompt-single-claim-card.md` | AI prompt for Single Claim Card |
| `socials/social_research.md` | Original research document |
| `docs/social-sharing-audit.md` | Technical audit of current sharing |

---

*Last updated: 2026-01-28*
