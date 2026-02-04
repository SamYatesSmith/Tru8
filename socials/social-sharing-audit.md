# Social Sharing Audit

## A) Summary

- **Share UI exists** on web with Twitter, LinkedIn, Facebook buttons + Copy Link + PDF download
- **Mobile share** uses native OS share sheet via Expo Sharing API
- **CRITICAL GAP**: All check URLs are auth-protected - shared links require login to view
- **No OG/Twitter card metadata** for dynamic check pages - previews will show generic site info
- **No WhatsApp button** in web share UI (mobile uses native share which includes WhatsApp)

---

## B) Current Capabilities

| Feature | Status | Where | Notes |
|---------|--------|-------|-------|
| X/Twitter share button | **Partial** | `web/app/dashboard/check/[id]/components/share-section.tsx:39` | Button works but shared URL requires auth |
| LinkedIn share button | **Partial** | `web/app/dashboard/check/[id]/components/share-section.tsx:40` | Same auth issue |
| Facebook share button | **Partial** | `web/app/dashboard/check/[id]/components/share-section.tsx:38` | Same auth issue |
| WhatsApp share button | **None** | - | Not implemented on web |
| Copy link | **Partial** | `web/app/dashboard/check/[id]/components/share-section.tsx:48-56` | Link copies but requires auth to view |
| PDF export | **Done** | `web/app/dashboard/check/[id]/components/share-section.tsx:58-88` | Works, downloads PDF |
| OG tags (static) | **Partial** | `web/app/layout.tsx:7-13` | Basic title/description only |
| OG tags (dynamic per-check) | **None** | - | No `generateMetadata` for check pages |
| Twitter cards | **None** | - | No `twitter:card`, `twitter:image` etc. |
| Public check view route | **None** | - | No `/r/[id]` or `/check/[id]` public route |
| Slack/Discord unfurl | **None** | - | Requires OG tags + public URL |
| Mobile share | **Done** | `mobile/app/(tabs)/check/[id].tsx:114-175` | Native share sheet works |
| Social API keys | **None** | No `.env` entries | Correct - no auto-post capability |

---

## C) Inventory

### API Endpoints
| Path | Handler | Purpose |
|------|---------|---------|
| `GET /api/v1/checks/{id}/export/pdf` | `backend/app/api/v1/checks.py` | PDF generation (auth required) |
| No public check endpoint | - | **GAP**: Need `GET /api/v1/public/checks/{id}` |

### Frontend Routes
| Route | File | Auth | Notes |
|-------|------|------|-------|
| `/dashboard/check/[id]` | `web/app/dashboard/check/[id]/page.tsx` | **Required** | Current check detail page |
| `/r/[id]` or `/check/[id]` | - | - | **GAP**: Public view needed |

### Share Components
| Component | File | Platform |
|-----------|------|----------|
| ShareSection | `web/app/dashboard/check/[id]/components/share-section.tsx` | Web |
| handleShare | `mobile/app/(tabs)/check/[id].tsx:114-175` | Mobile |

### Metadata/SEO
| File | Type | Content |
|------|------|---------|
| `web/app/layout.tsx` | Static | `title`, `description`, `favicon` only |
| Check detail page | - | **GAP**: No `generateMetadata` export |

---

## D) Evidence

### Share Section (Web)
```typescript
// web/app/dashboard/check/[id]/components/share-section.tsx:36-41
const shareUrls: Record<string, string> = {
  facebook: `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(shareUrl)}`,
  twitter: `https://twitter.com/intent/tweet?url=${encodeURIComponent(shareUrl)}&text=${encodeURIComponent(shareText)}`,
  linkedin: `https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(shareUrl)}`,
};
```

### Mobile Share
```typescript
// mobile/app/(tabs)/check/[id].tsx:149-161
await FileSystem.writeAsStringAsync(fileUri, shareText, {
  encoding: FileSystem.EncodingType.UTF8,
});
await Sharing.shareAsync(fileUri, {
  mimeType: 'text/plain',
  dialogTitle: 'Share Fact-Check Results',
});
```

### Auth Protection (Middleware)
```typescript
// web/middleware.ts:16-18
const isProtectedRoute = createRouteMatcher([
  '/dashboard(.*)',  // ALL dashboard routes require auth
]);
```

### Static Metadata Only
```typescript
// web/app/layout.tsx:7-13
export const metadata: Metadata = {
  title: 'Tru8 - AI-Powered Fact Verification',
  description: 'Professional claim verification platform...',
  icons: { icon: '/favicon.proper.png' },
}
// NO openGraph, NO twitter fields
```

---

## E) Gaps & TODOs (Priority Order)

### Critical (Blocks all sharing)
- [ ] **Create public check route** `web/app/r/[id]/page.tsx` or `web/app/check/[id]/page.tsx`
  - No auth required
  - Read-only view of completed checks
  - Different layout (no dashboard nav)
- [ ] **Create public API endpoint** `GET /api/v1/public/checks/{id}`
  - Returns limited check data (no user info)
  - Only for completed checks
  - Consider rate limiting

### High (Required for good previews)
- [ ] **Add dynamic OG metadata** to public check page:
  ```typescript
  export async function generateMetadata({ params }): Promise<Metadata> {
    const check = await fetchPublicCheck(params.id);
    return {
      title: `Fact Check: ${check.title || 'Verification Result'}`,
      description: `${check.claims?.length} claims analyzed...`,
      openGraph: {
        title: '...',
        description: '...',
        images: ['/api/og/check/' + params.id], // Dynamic OG image
        type: 'article',
      },
      twitter: {
        card: 'summary_large_image',
        title: '...',
        description: '...',
        images: ['/api/og/check/' + params.id],
      },
    };
  }
  ```
- [ ] **Create OG image endpoint** `web/app/api/og/check/[id]/route.tsx`
  - Generate dynamic preview image with verdict summary
  - Use `@vercel/og` or `satori`

### Medium (Better UX)
- [ ] **Add WhatsApp button** to web share section:
  ```typescript
  whatsapp: `https://wa.me/?text=${encodeURIComponent(shareText + ' ' + shareUrl)}`
  ```
- [ ] **Update share URL** to use public route instead of dashboard route
- [ ] **Add share tracking** analytics for conversion measurement

### Low (Nice to have)
- [ ] Add "Share" button to claim cards (share specific claim)
- [ ] Add short URL service for cleaner share links
- [ ] Consider X/Twitter API for "Share to X" with pre-filled content

---

## F) Definition of Done (V1 Sharing)

### Minimum Viable
1. Public check view page exists at `/r/[id]`
2. Unauthenticated users can view completed checks
3. OG tags render server-side with check-specific content
4. Slack/Discord link preview shows check summary
5. X/Twitter card preview shows check summary

### Full V1
All above plus:
6. WhatsApp share button on web
7. Dynamic OG image with verdict visualization
8. Share URLs point to public route (not dashboard)
9. Mobile share includes public URL (not just text)

### Verification Tests
- [ ] Curl public check URL, verify OG meta tags in HTML
- [ ] Paste link in Slack, verify preview card appears
- [ ] Share to X, verify card preview in tweet composer
- [ ] Share via WhatsApp, verify link unfurls

---

## Quick Verification Commands

```bash
# Check if OG tags exist (run against deployed site)
curl -s https://tru8.app/r/TEST_CHECK_ID | grep -E "og:|twitter:"

# Test with social media debuggers:
# - X/Twitter: https://cards-dev.twitter.com/validator
# - Facebook: https://developers.facebook.com/tools/debug/
# - LinkedIn: https://www.linkedin.com/post-inspector/
```
