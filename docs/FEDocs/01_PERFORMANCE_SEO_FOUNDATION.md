# 01. Performance & SEO Foundation - Marketing Optimization

## 🎯 Objective
Establish performance monitoring, Core Web Vitals optimization, and SEO preservation strategy to ensure the redesigned marketing page maintains fast loading times and search visibility while supporting conversion goals.

## 🔀 **Dual-Track Impact**
- **Track A (Marketing)**: Primary focus - optimize marketing page performance for conversions
- **Track B (App)**: Secondary benefit - performance monitoring helps all pages including dashboard

## 📊 Current State Analysis

### Existing Performance (web/app/page.tsx)
```tsx
// Current homepage is lightweight:
- 174 lines of React code
- Basic CSS styling
- No heavy animations or effects
- Fast initial load
```

### Current SEO Structure
```tsx
// From web/app/layout.tsx (lines 12-16)
export const metadata: Metadata = {
  title: "Tru8 - Instant Fact Checking",
  description: "Get instant, explainable fact checks with sources and dates",
  keywords: ["fact check", "verification", "truth", "misinformation"],
};
```

## 🏗️ Implementation Strategy

### Performance Budget Framework
**Establish hard limits for marketing page performance:**

1. **Core Web Vitals Targets**
   - LCP (Largest Contentful Paint): < 2.5s
   - FID (First Input Delay): < 100ms
   - CLS (Cumulative Layout Shift): < 0.1

2. **Bundle Size Limits**
   - Initial JS bundle: < 150KB gzipped
   - CSS bundle: < 50KB gzipped
   - Images: WebP/AVIF with fallbacks

3. **Loading Performance**
   - Time to Interactive: < 3s
   - Critical rendering path optimization
   - Above-fold content priority

## 🛠️ Technical Implementation

### 1. Performance Monitoring Setup

#### Real User Monitoring (RUM)
```tsx
// Add to web/app/layout.tsx after line 16
import { Analytics } from '@vercel/analytics/react';
import { SpeedInsights } from '@vercel/speed-insights/next';

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <ClerkProvider>
      <html lang="en" suppressHydrationWarning>
        <body className={inter.className}>
          <ThemeProvider>
            <QueryProvider>
              <SessionProvider>
                {children}
                <Toaster />
                <Analytics />
                <SpeedInsights />
              </SessionProvider>
            </QueryProvider>
          </ThemeProvider>
        </body>
      </html>
    </ClerkProvider>
  );
}
```

#### Core Web Vitals Tracking
```tsx
// Create: web/lib/performance.ts
'use client';

import { getCLS, getFID, getFCP, getLCP, getTTFB } from 'web-vitals';

function sendToAnalytics(metric: any) {
  // Send to your analytics provider
  if (typeof window !== 'undefined' && (window as any).gtag) {
    (window as any).gtag('event', metric.name, {
      custom_parameter_1: metric.value,
      custom_parameter_2: metric.id,
      custom_parameter_3: metric.name,
    });
  }
}

export function initPerformanceMonitoring() {
  getCLS(sendToAnalytics);
  getFID(sendToAnalytics);
  getFCP(sendToAnalytics);
  getLCP(sendToAnalytics);
  getTTFB(sendToAnalytics);
}
```

### 2. Enhanced SEO Structure

#### Comprehensive Meta Tags
```tsx
// Update web/app/page.tsx metadata
export const metadata: Metadata = {
  title: "Tru8 - Instant Fact-Checking with Dated Evidence | Professional Verification",
  description: "Get explainable fact-check verdicts in under 10 seconds. Process URLs, images, videos, and text with transparent sourcing. Professional-grade verification for journalists and researchers.",
  keywords: [
    "fact checking", "fact checker", "verification", "misinformation",
    "disinformation", "truth", "evidence", "sources", "journalism tools",
    "research verification", "claim verification", "AI fact checking"
  ],
  authors: [{ name: "Tru8" }],
  creator: "Tru8",
  publisher: "Tru8",

  // Open Graph
  openGraph: {
    type: "website",
    locale: "en_US",
    url: "https://tru8.ai",
    title: "Tru8 - Professional Fact-Checking Platform",
    description: "Instant fact-checking with transparent sources and dated evidence. Built for journalists, researchers, and truth-seekers.",
    siteName: "Tru8",
    images: [
      {
        url: "/og-marketing-hero.jpg",
        width: 1200,
        height: 630,
        alt: "Tru8 Fact-Checking Platform",
      }
    ],
  },

  // Twitter
  twitter: {
    card: "summary_large_image",
    site: "@tru8platform",
    creator: "@tru8platform",
    title: "Tru8 - Instant Fact-Checking",
    description: "Professional-grade verification in seconds with transparent sourcing",
    images: ["/og-marketing-hero.jpg"],
  },

  // Additional SEO
  robots: "index, follow",
  canonical: "https://tru8.ai",
  alternates: {
    canonical: "https://tru8.ai",
  },
};
```

#### Structured Data Implementation
```tsx
// Add to marketing homepage component
function MarketingStructuredData() {
  const structuredData = {
    "@context": "https://schema.org",
    "@type": "SoftwareApplication",
    "name": "Tru8",
    "applicationCategory": "BusinessApplication",
    "description": "Professional fact-checking platform with instant verification and transparent sourcing",
    "url": "https://tru8.ai",
    "author": {
      "@type": "Organization",
      "name": "Tru8"
    },
    "offers": {
      "@type": "Offer",
      "price": "0",
      "priceCurrency": "USD",
      "priceValidUntil": "2025-12-31"
    },
    "featureList": [
      "Lightning-fast verification in under 10 seconds",
      "Multi-format support (URLs, images, videos, text)",
      "Transparent sourcing with publication dates",
      "AI-powered verdict generation",
      "Real-time progress tracking",
      "Global news source coverage"
    ],
    "screenshot": "https://tru8.ai/app-screenshot.jpg",
    "softwareVersion": "1.0",
    "operatingSystem": "Web Browser"
  };

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(structuredData) }}
    />
  );
}
```

### 3. Image Optimization Strategy

#### Next.js Image Implementation
```tsx
// Update feature icons and hero images
import Image from 'next/image';

// Replace icon divs with optimized images
<div className="feature-icon-container">
  <Image
    src="/icons/lightning-fast.svg"
    alt="Lightning Fast Verification"
    width={28}
    height={28}
    priority={false}
    className="feature-icon"
  />
</div>
```

#### Image Asset Requirements
```
public/
├── icons/
│   ├── lightning-fast.svg (optimized)
│   ├── transparent-sources.svg
│   ├── multi-format.svg
│   └── real-time.svg
├── og-marketing-hero.jpg (1200x630, optimized)
├── app-screenshot.jpg (marketing demo)
└── hero-background.webp (with .jpg fallback)
```

### 4. Loading Performance Optimization

#### Critical CSS Inlining
```css
/* Extract critical above-fold CSS */
.hero-section,
.hero-title,
.hero-subtitle,
.btn-primary {
  /* Inline critical styles */
}
```

#### Progressive Loading Strategy
```tsx
// Implement progressive enhancement for glass effects
'use client';

import { useState, useEffect } from 'react';

export function ProgressiveGlassCard({ children, className }: { children: React.ReactNode, className?: string }) {
  const [supportsBackdrop, setSupportsBackdrop] = useState(false);

  useEffect(() => {
    // Feature detection for backdrop-filter
    setSupportsBackdrop(CSS.supports('backdrop-filter', 'blur(10px)'));
  }, []);

  return (
    <div className={cn(
      'card',
      supportsBackdrop ? 'glass-card' : 'solid-card',
      className
    )}>
      {children}
    </div>
  );
}
```

## ✅ Testing Checklist

### Performance Testing
- [ ] Core Web Vitals meet targets in production
- [ ] Page Speed Insights score > 90
- [ ] Mobile performance acceptable (3G simulation)
- [ ] Bundle size within limits
- [ ] Images properly optimized

### SEO Testing
- [ ] Google Search Console validation
- [ ] Structured data validates (schema.org validator)
- [ ] Meta tags display correctly in search results
- [ ] Open Graph preview works on social platforms
- [ ] Canonical URLs properly set

### Monitoring Setup
- [ ] RUM data collecting properly
- [ ] Performance budgets configured
- [ ] Alerts set for Core Web Vitals degradation
- [ ] SEO monitoring dashboard active

## 📈 Success Metrics

### Performance KPIs
- **Core Web Vitals:** All green (LCP <2.5s, FID <100ms, CLS <0.1)
- **Page Speed Score:** >90 mobile, >95 desktop
- **Bounce Rate:** Maintain or improve current rates
- **Time to Interactive:** <3 seconds

### SEO KPIs
- **Search Rankings:** Maintain current positions for target keywords
- **Organic Traffic:** No decline from redesign
- **Click-Through Rate:** Monitor SERP performance
- **Core Web Vitals as Ranking Factor:** Pass Google requirements

## 🚀 Implementation Priority
**Phase**: Foundation (Must complete before visual enhancements)
**Priority**: CRITICAL
**Estimated Effort**: 2-3 days
**Dependencies**: Must be implemented alongside any performance-impacting changes
**Impact**: HIGH - Protects conversion and search visibility

---

**This foundation ensures the marketing redesign enhances rather than harms business performance.**