# Track I: Implementation Advisory — I-05, I-06, I-12

**Written:** 2026-03-09
**Read alongside:** `audit/track-i/PROGRESS.md` (original task list, unchanged)
**Purpose:** Precise implementation spec for the three remaining code items, grounded in actual file contents.

---

## Why This Document Exists

PROGRESS.md lists tasks in checklist form. This advisory adds the implementation detail — exact line references, before/after code patterns, and architectural decisions — so each item can be executed accurately in one pass.

---

## I-05: Developer Page Polish

**File:** `web/app/developers/page.tsx` (416 lines)
**Goal:** Apply Stitch accent language. Currently zinc-only except one callout box.

### 5.1 Step Number Squares → Accent Orange

Three step number boxes (lines 71, 105, 124) all use `bg-zinc-900 text-white`:

```tsx
// BEFORE (lines 71, 105, 124):
<div className="flex-shrink-0 w-8 h-8 bg-zinc-900 text-white flex items-center justify-center font-mono text-sm font-bold">

// AFTER:
<div className="flex-shrink-0 w-8 h-8 bg-accent text-white flex items-center justify-center font-mono text-sm font-bold">
```

Three instances. `bg-accent` maps to `#f27907` via the Tailwind theme (already configured globally).

### 5.2 CTA Button → Accent Orange

Bottom CTA (line 398) uses `bg-zinc-900 hover:bg-zinc-800`:

```tsx
// BEFORE (line 398):
className="inline-flex items-center gap-2 px-8 py-4 bg-zinc-900 hover:bg-zinc-800 text-white text-xs font-bold uppercase tracking-[0.2em] transition-colors"

// AFTER:
className="inline-flex items-center gap-2 px-8 py-4 bg-accent hover:bg-accent/90 text-white text-xs font-bold uppercase tracking-[0.2em] transition-colors"
```

### 5.3 MCP Tool Icons → Differentiated

Lines 216–245: three MCP tools render identically with `<FileJson size={16} className="text-zinc-400" />`.

Replace with distinct icons per tool purpose:

| Tool | Current Icon | New Icon | Rationale |
|------|-------------|----------|-----------|
| `tru8_check` | `FileJson` | `Search` | Primary action — evidence research |
| `tru8_get_result` | `FileJson` | `BarChart3` | Computed analytics retrieval |
| `tru8_get_result_raw` | `FileJson` | `FileJson` | Keep — raw data fetch |

`Search` and `BarChart3` are already imported (line 4). Change the icon in each tool's map entry.

Additionally, accent the primary tool name:

```tsx
// For tru8_check only, add accent colour to the tool name:
<code className="text-sm font-mono font-semibold text-accent">{tool.name}</code>

// Other two tools keep text-zinc-900.
```

### 5.4 Tier Cards → Visual Differentiation

Lines 154–190: Lookup/Quick/Full cards are visually identical — same border, same icon (`Search`), same layout.

Differentiate by adding a left accent border to Full tier (the flagship product):

```tsx
// In the map function (line 174), conditionally add accent border:
<div key={t.tier} className={`flex items-start gap-4 border border-zinc-200 p-4 ${
  t.tier === 'Full' ? 'border-l-4 border-l-accent' : ''
}`}>
```

Add the Consensus tier (Track M addition, currently missing from the page):

```tsx
// Add to the tiers array (after Lookup, before Quick):
{
  tier: 'Consensus',
  desc: 'Cross-user aggregate evidence landscape — no individual evidence items. Available when k\u22653 independent checks exist.',
  price: '~$0.03',
  time: 'instant',
},
```

### 5.5 Response Shape Annotations

Lines 284–335: large JSON block with no guide. Add inline annotation callouts after the code block:

```tsx
<div className="mt-6 space-y-3">
  <div className="flex gap-3 bg-zinc-50 border border-zinc-200 p-4">
    <div className="flex-shrink-0 w-6 h-6 bg-accent/10 text-accent flex items-center justify-center font-mono text-xs font-bold">?</div>
    <div className="text-xs text-zinc-600">
      <p className="font-semibold text-zinc-900 mb-1">claims[].claimMap</p>
      <p>Each claim is decomposed into 1–5 elements. Evidence maps to elements with relationship types (supports/challenges/context) and reasoning.</p>
    </div>
  </div>
  <div className="flex gap-3 bg-zinc-50 border border-zinc-200 p-4">
    <div className="flex-shrink-0 w-6 h-6 bg-accent/10 text-accent flex items-center justify-center font-mono text-xs font-bold">?</div>
    <div className="text-xs text-zinc-600">
      <p className="font-semibold text-zinc-900 mb-1">_meta vs _computed</p>
      <p><code className="text-zinc-400">_meta</code> is always present — tier, cost, limitations. <code className="text-zinc-400">_computed</code> requires <code className="text-zinc-400">?computed=true</code> — adds analytics, corroboration, diagnostics.</p>
    </div>
  </div>
</div>
```

### 5.6 Response Shape — Verify JSON Accuracy

The example JSON (lines 284–335) should be verified against the actual API response shape. Current fields to check:

| Field in Example | Actual API | Status |
|-----------------|-----------|--------|
| `"orientation"` | `claims[].claimMap.orientation` | Correct (fixed in I-08) |
| `"_meta.cached"` | `_meta.cached` | Exists in agent responses |
| `"_meta.limitations"` | `_meta.limitations` | Exists — array of strings |
| `"_computed.diagnosticValues"` | `_computed.diagnosticValues` | Exists when `?computed=true` |
| `"_meta.landscape"` | `_meta.landscape` | **Missing from example** — should be added |
| `"_manifest"` | `_manifest` | **Missing from example** — Track M addition, should be added |

Add `landscape` and `_manifest` blocks to the example JSON:

```json
"_meta": {
  "executedTier": "quick",
  "chargedCents": 7,
  "limitations": ["heuristic_classification", "no_coverage_recovery"],
  "cached": false,
  "landscape": {
    "sourceDiversity": { "uniqueDomains": 5, "typeCoverage": 3 },
    "freshness": { "freshestDaysAgo": 2, "undatedCount": 1 },
    "gaps": [],
    "providerStatus": null
  }
},
"_manifest": {
  "checkId": "check-uuid",
  "landscapeHash": "a1b2c3d4...",
  "signedAt": "2026-03-09T12:00:00Z",
  "signature": "hmac-sha256-...",
  "kid": "tru8-2026-03",
  "verifyUrl": "/verify/check-uuid"
}
```

### 5.7 MCP Tool Description Update

Line 219: `tru8_check` description says "lookup → quick → full". Should now read "lookup → consensus → quick → full" to reflect Track M's consensus tier insertion.

### I-05 Summary

| Change | Lines | Type |
|--------|-------|------|
| Step squares → accent | 71, 105, 124 | Class swap |
| CTA → accent | 398 | Class swap |
| MCP icons differentiated | 216–245 | Icon + class swap |
| Full tier accent border | 174 | Conditional class |
| Add Consensus tier card | 154–190 | Array entry |
| Response shape annotations | after 335 | New JSX block |
| Add landscape + manifest to example | 284–335 | JSON text |
| MCP fallback chain text | 219 | Text update |

---

## I-06: Social / OG Card Alignment

**Goal:** Complete the metadata infrastructure. OG image generation already works.

### 6.1 Current State

**Working:**
- Dynamic OG images: `/api/og/check/[id]` (Full Report Card) and `/api/og/social/[id]` (Social Share Card)
- Components in `web/app/api/og/_components/`: `FullReportCard`, `SocialShareCard`, `Logo`, `StatsBlock`, `SourceList`, `SourceChip`, `SourceTierBar`
- Uses `@vercel/og` with edge runtime, 1-hour caching
- Public report page (`web/app/r/[id]/page.tsx`) has `generateMetadata()` with OpenGraph + Twitter card metadata
- Currently uses the Social card (`/api/og/social/[id]`) for OG images — correct choice (snappier on mobile)

**Missing:**
- JSON-LD structured data
- `theme-color` in root layout
- `apple-touch-icon` in root layout
- Cross-platform rendering verification

### 6.2 Root Layout Metadata

**File:** `web/app/layout.tsx`

Add to the existing `metadata` export:

```tsx
export const metadata: Metadata = {
  title: 'Tru8 — AI-Powered Evidence Research',
  description: 'Professional evidence research platform...',
  // ADD:
  themeColor: '#f27907',
  icons: {
    icon: '/favicon.proper.png',
    apple: '/apple-touch-icon.png',
  },
  metadataBase: new URL('https://tru8.app'),
};
```

**Asset required:** Create `web/public/apple-touch-icon.png` (180×180px, orange background with white Tru8 logo). This can be generated from the existing `logo.proper.png`.

### 6.3 JSON-LD Structured Data

**File:** `web/app/r/[id]/page.tsx`

Add a `<script type="application/ld+json">` block in the page component's return. Use `WebPage` + `ClaimReview` schema (Schema.org has a specific `ClaimReview` type for evidence/fact-checking contexts):

```tsx
// In the page component, add before the main content:
const jsonLd = {
  '@context': 'https://schema.org',
  '@type': 'WebPage',
  name: checkData.title || 'Evidence Research Report',
  description: checkData.description || 'Structured evidence analysis',
  url: `https://tru8.app/r/${id}`,
  datePublished: checkData.created_at,
  dateModified: checkData.completed_at || checkData.created_at,
  publisher: {
    '@type': 'Organization',
    name: 'Tru8',
    url: 'https://tru8.app',
    logo: {
      '@type': 'ImageObject',
      url: 'https://tru8.app/logo.proper.png',
    },
  },
  mainEntity: {
    '@type': 'Dataset',
    name: 'Evidence Landscape',
    description: `${claimCount} claims examined across ${sourceCount} sources`,
  },
};

// In JSX:
<script
  type="application/ld+json"
  dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
/>
```

**Design decision:** Use `WebPage` + `Dataset`, not `ClaimReview`. `ClaimReview` implies a verdict (`reviewRating`), which contradicts Tru8's "we organise; you decide" philosophy. `Dataset` accurately describes what Tru8 produces — a structured evidence collection.

### 6.4 Canonical URLs

Add to `generateMetadata()` in `web/app/r/[id]/page.tsx`:

```tsx
alternates: {
  canonical: `https://tru8.app/r/${id}`,
},
```

### 6.5 OG Card Decision

Keep the Social Share Card (`/api/og/social/[id]`) as the default OG image. It renders better on mobile platforms (X, WhatsApp, LinkedIn) where space is limited. The Full Report Card is available at `/api/og/check/[id]` for explicit embedding but is too dense for small OG previews.

No code change needed — current wiring is correct.

### 6.6 Cross-Platform Testing

Manual testing checklist (not code):

- [ ] X (Twitter): Paste `https://tru8.app/r/{id}` in composer, verify card renders
- [ ] LinkedIn: Share URL, verify title + image + description
- [ ] WhatsApp: Send link in chat, verify preview
- [ ] Slack: Paste URL, verify unfurl
- [ ] Facebook/Meta: Use [Sharing Debugger](https://developers.facebook.com/tools/debug/) to verify
- [ ] Google: Check structured data with [Rich Results Test](https://search.google.com/test/rich-results)

### I-06 Summary

| Change | File | Type |
|--------|------|------|
| theme-color + apple-touch-icon | `layout.tsx` | Metadata update |
| Create apple-touch-icon.png | `public/` | Asset creation |
| JSON-LD structured data | `r/[id]/page.tsx` | New script block |
| Canonical URL | `r/[id]/page.tsx` | Metadata addition |
| Cross-platform testing | Manual | Verification |

---

## I-12: API Terms in Terms of Service

**File:** `web/app/terms-of-service/page.tsx` (227 lines)
**Goal:** Add API-specific terms section for developer usage.

### 12.1 Current State

The Terms of Service covers:
- Sections 1–13: Agreement, service description, accounts, subscriptions, acceptable use, limitations, IP, liability, indemnification, termination, disputes, changes, contact
- Section 4 covers subscription plans (Free + Professional) — already outdated (doesn't mention Developer or Enterprise tiers)
- Section 5.2 mentions "Automated abuse or scraping" as prohibited — but doesn't distinguish legitimate API usage
- No mention of API keys, rate limits, data retention, or agent usage

### 12.2 Section 4 Update — Add Missing Tiers

Section 4 currently lists only Free and Professional. Add Developer and Enterprise:

```tsx
<h3>4.3 Developer Plan (£29/month)</h3>
<ul>
  <li>200 analyses per month</li>
  <li>All Professional features</li>
  <li>API access with dedicated API key</li>
  <li>MCP server integration</li>
  <li>Agent Commerce Gateway access (lookup, consensus, quick, full tiers)</li>
</ul>

<h3>4.4 Enterprise Plan (Custom)</h3>
<ul>
  <li>Custom analysis volume</li>
  <li>Dedicated support</li>
  <li>Custom integrations</li>
  <li>Volume pricing</li>
</ul>
```

Renumber existing "4.3 Billing" to "4.5 Billing".

### 12.3 New Section — API & Agent Usage

Insert as **Section 5A** (after Acceptable Use, before Service Limitations), or as a new **Section 13** before Contact. Inserting after Section 5 is more logical since it extends the usage terms.

**Recommended: Add as Section 6, renumber existing 6–13 to 7–14.**

```tsx
<h2>6. API & Developer Usage</h2>

<h3>6.1 API Access</h3>
<ul>
  <li>API access requires a Developer or Enterprise subscription plan</li>
  <li>Each API key is tied to a single account and carries your identity and usage quota</li>
  <li>You are responsible for all activity performed using your API key</li>
  <li>API keys must be stored securely — never in client-side code, version control, or logs</li>
  <li>Compromised keys must be revoked immediately via dashboard settings</li>
</ul>

<h3>6.2 Rate Limits & Fair Use</h3>
<ul>
  <li>API requests are subject to rate limits based on your subscription tier</li>
  <li>Concurrent request limits apply per API key (currently 3 simultaneous requests)</li>
  <li>Requests exceeding rate limits will receive HTTP 429 responses</li>
  <li>Sustained high-volume usage beyond plan limits may require an Enterprise agreement</li>
</ul>

<h3>6.3 Agent & Automated Usage</h3>
<ul>
  <li>AI agents and automated systems may use the API under the same terms as human users</li>
  <li>Agent usage via MCP (Model Context Protocol) or direct API calls is permitted within plan limits</li>
  <li>The Agent Commerce Gateway (x402, Skyfire, prepaid credits) provides pay-per-use access for agents without a subscription</li>
  <li>Agent operators are responsible for their agents&apos; compliance with these terms</li>
</ul>

<h3>6.4 Data Retention & Privacy</h3>
<ul>
  <li>Analysis results are retained for the duration of your subscription</li>
  <li>API responses may be cached server-side to improve performance and reduce costs</li>
  <li>Cached results may be served to subsequent requests for the same claim (lookup tier)</li>
  <li>You may request deletion of your data in accordance with our Privacy Policy</li>
  <li>Evidence snippets displayed are extracted from publicly available sources and attributed with URLs</li>
</ul>

<h3>6.5 Redistribution</h3>
<ul>
  <li>You may incorporate Tru8 results into your own applications and services</li>
  <li>Attribution to Tru8 is required when displaying results to end users</li>
  <li>You may not resell raw API access or create a competing evidence research service using Tru8 data</li>
  <li>Signed manifests and verification URLs may be shared publicly to demonstrate evidence provenance</li>
</ul>
```

### 12.4 Section 2 Update — Service Description

The current service description (Section 2) doesn't mention the API or agent access. Add a bullet:

```tsx
// Add to the existing <ul> in Section 2:
<li>Provides a developer API and MCP server for programmatic and AI agent access</li>
```

### 12.5 Last Updated Date

Update the `lastUpdated` prop from `"6 January 2026"` to the current date when changes are applied.

### I-12 Summary

| Change | Location | Type |
|--------|----------|------|
| Add Developer + Enterprise plan descriptions | Section 4 | New subsections |
| Add API & Developer Usage section | New Section 6 | New section (5 subsections) |
| Add API mention to service description | Section 2 | Bullet point |
| Update lastUpdated date | Component prop | Text update |
| Renumber sections 6–13 → 7–14 | Throughout | Numbering |

---

## Implementation Sequence

```
Phase 1 — I-05 (Developer Page Polish):
  Single file change: web/app/developers/page.tsx
  No dependencies. Pure visual. Can verify immediately in dev server.

Phase 2 — I-12 (API Terms):
  Single file change: web/app/terms-of-service/page.tsx
  No dependencies. Pure content. Can verify immediately.

Phase 3 — I-06 (OG / Metadata):
  Files: web/app/layout.tsx, web/app/r/[id]/page.tsx
  Asset: web/public/apple-touch-icon.png
  Requires: Deployed URL for cross-platform testing (or Vercel preview)
  Do last — JSON-LD and metadata testing benefits from I-05 being live.
```

All three items are independent and could be parallelised, but the sequence above minimises risk (I-05 is safest, I-06 needs manual verification).

---

## Scope Boundaries

**In scope:** Visual polish, metadata, legal content updates.

**Not in scope:**
- ~~Stripe product creation (I-03)~~ — DONE long ago in production (stale-doc fix 2026-05-01)
- ~~Feature flag flip (I-04)~~ — DONE long ago, `SUBSCRIPTIONS_ENABLED=True` deployed (user confirmed 2026-05-01)
- MCP publication (I-07) — ops/process task
- Blog post (I-09) — content task
- Demo video (I-15) — deferred
- Pricing restructure — noted for future, not part of Track I

---

*This advisory does not modify PROGRESS.md. Read both together. Where this document adds implementation detail beyond the checklist, follow this advisory for accuracy.*
