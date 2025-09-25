# 04. Marketing Analytics Integration - MVP Conversion Tracking

## 🎯 Objective
Implement lean, MVP-focused analytics tracking to measure basic conversion performance and user behavior. Focus on essential metrics needed for launch optimization without over-engineering.

## 📊 Current State Analysis

### Existing Analytics Setup
```tsx
// From web/app/layout.tsx - basic Vercel analytics
import { Analytics } from '@vercel/analytics/react';

// From web/lib/performance.ts - gtag foundation ready
function sendToAnalytics(metric: any) {
  if (typeof window !== 'undefined' && (window as any).gtag) {
    (window as any).gtag('event', metric.name, { /* metric data */ });
  }
}
```

### MVP Analytics Needs (Keep It Simple)
- **4 core conversion events** (not 20+)
- **Single analytics platform** (not 3 platforms)
- **Basic cookie consent** (not complex GDPR framework)
- **Performance integration** (build on Phase 01 foundation)

## 🏗️ Implementation Strategy (MVP-Focused)

### 1. Single Analytics Platform (PostHog Recommended)

#### Why PostHog for MVP:
- **Free tier:** 1M events/month (generous for startup)
- **Session recordings:** See actual user behavior
- **Product analytics:** Better than GA4 for early-stage decisions
- **Privacy-friendly:** Can be configured without cookie banner
- **Simple setup:** One package, minimal configuration

#### Minimal Analytics Implementation
```tsx
// Create: web/lib/analytics.ts (MVP Version - 30 lines, not 200)
'use client';

import posthog from 'posthog-js';

class MVPAnalytics {
  private initialized = false;

  initialize() {
    if (typeof window === 'undefined' || this.initialized) return;

    posthog.init(process.env.NEXT_PUBLIC_POSTHOG_KEY!, {
      api_host: process.env.NEXT_PUBLIC_POSTHOG_HOST || 'https://us.i.posthog.com',
      person_profiles: 'identified_only', // Privacy-friendly
      capture_pageview: false, // We'll do manual pageviews
    });

    this.initialized = true;
  }

  // MVP: Only 4 essential events
  trackPageView(page: string) {
    if (!this.initialized) return;
    posthog.capture('page_viewed', {
      page,
      referrer: document.referrer,
      timestamp: Date.now()
    });
  }

  trackCTAClick(location: string, ctaType: 'primary' | 'secondary') {
    posthog.capture('cta_clicked', { location, ctaType });
  }

  trackSignupStart() {
    posthog.capture('signup_started', {
      source: 'marketing_page',
      timestamp: Date.now()
    });
  }

  trackSignupComplete() {
    posthog.capture('signup_completed', {
      source: 'marketing_page',
      timestamp: Date.now()
    });
  }

  // Integrate with existing Core Web Vitals (Phase 01)
  trackPerformance(metric: any) {
    posthog.capture('performance_metric', {
      name: metric.name,
      value: Math.round(metric.value),
      rating: metric.rating,
    });
  }
}

export const analytics = new MVPAnalytics();
```

### 2. Simple Tracking Hook (MVP Only)

#### Basic Tracking Hook
```tsx
// Create: web/hooks/useTracking.ts (Simple wrapper)
'use client';

import { useEffect } from 'react';
import { analytics } from '@/lib/analytics';

export function useTracking() {
  useEffect(() => {
    // Initialize analytics on page load
    analytics.initialize();
    analytics.trackPageView('marketing_home');
  }, []);

  return {
    trackCTA: analytics.trackCTAClick,
    trackSignupStart: analytics.trackSignupStart,
    trackSignupComplete: analytics.trackSignupComplete,
  };
}
```

### 3. Simple Component Integration

#### Add Tracking to Existing Components
```tsx
// Update existing homepage buttons (no new components needed)
import { useTracking } from '@/hooks/useTracking';

export default function HomePage() {
  const { trackCTA, trackSignupStart } = useTracking();

  return (
    <MainLayout>
      {/* Hero Section */}
      <section className="hero-section">
        <div className="container">
          <h1 className="hero-title">Instant Fact-Checking with Dated Evidence</h1>

          <SignedOut>
            <SignInButton mode="modal">
              <Button
                size="lg"
                className="btn-primary px-8 py-4 text-lg"
                onClick={() => {
                  trackCTA('hero', 'primary');
                  trackSignupStart();
                }}
              >
                Start Fact-Checking Now
              </Button>
            </SignInButton>
          </SignedOut>
        </div>
      </section>
    </MainLayout>
  );
}
```

### 4. Cookie Consent (Simple)

#### Install Cookie Consent Package
```bash
npm install react-cookie-consent
```

#### Basic Cookie Banner
```tsx
// Add to web/app/layout.tsx
import CookieConsent from 'react-cookie-consent';

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html>
      <body>
        {children}

        <CookieConsent
          location="bottom"
          buttonText="Accept"
          declineButtonText="Decline"
          enableDeclineButton
          cookieName="tru8-analytics-consent"
          style={{ background: "#2B373B" }}
          buttonStyle={{ color: "#4e503b", fontSize: "13px" }}
          onAccept={() => {
            // Initialize analytics only after consent
            import('@/lib/analytics').then(({ analytics }) => {
              analytics.initialize();
            });
          }}
        >
          We use cookies to improve your experience and analyze site usage.{" "}
          <Link href="/privacy" style={{ fontSize: "10px" }}>Privacy Policy</Link>
        </CookieConsent>
      </body>
    </html>
  );
}
```

### 5. Performance Analytics Integration

#### Core Web Vitals Tracking
```tsx
// Enhanced performance tracking
export function initializePerformanceTracking() {
  // Web Vitals tracking (from Phase 10)
  import('web-vitals').then(({ getCLS, getFID, getFCP, getLCP, getTTFB }) => {
    const sendToAnalytics = (metric: any) => {
      analytics.track({
        event: 'core_web_vital',
        category: 'marketing',
        action: 'performance_metric',
        label: metric.name,
        value: Math.round(metric.value),
        properties: {
          metricId: metric.id,
          metricName: metric.name,
          metricValue: metric.value,
          metricRating: metric.rating,
        },
      });
    };

    getCLS(sendToAnalytics);
    getFID(sendToAnalytics);
    getFCP(sendToAnalytics);
    getLCP(sendToAnalytics);
    getTTFB(sendToAnalytics);
  });
}
```

### 6. Custom Analytics Dashboard API

#### Analytics API Endpoint
```tsx
// Create: web/app/api/analytics/track/route.ts
import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  try {
    const data = await request.json();

    // Store in database for custom dashboard
    // This would integrate with your backend analytics storage

    return NextResponse.json({ success: true });
  } catch (error) {
    return NextResponse.json({ error: 'Failed to track event' }, { status: 500 });
  }
}
```

## ✅ Testing Checklist

### Analytics Implementation
- [ ] Google Analytics 4 tracking active
- [ ] PostHog event capture working
- [ ] Microsoft Clarity heat mapping active
- [ ] Custom analytics API functional

### Event Tracking Validation
- [ ] CTA clicks tracked correctly
- [ ] Section scroll tracking working
- [ ] Form interaction events captured
- [ ] Conversion funnel complete

### A/B Testing Validation
- [ ] Variant assignment consistent
- [ ] Traffic split accurate
- [ ] Test assignment tracking working
- [ ] Conversion tracking per variant

### Performance Monitoring
- [ ] Core Web Vitals captured
- [ ] Performance budget alerts active
- [ ] Real User Monitoring data flowing
- [ ] Error tracking functional

## 📈 Success Metrics

### Conversion Tracking
- **Signup Conversion Rate:** Track A vs B variants
- **CTA Performance:** Compare primary vs secondary CTAs
- **Funnel Analysis:** Identify drop-off points
- **Attribution:** Track conversion sources

### Engagement Analytics
- **Section Engagement:** Time spent per section
- **Scroll Depth:** How far users scroll
- **Feature Ralewayest:** Most clicked features
- **Navigation Patterns:** User journey through page

### Performance Impact
- **Core Web Vitals:** Maintain >90 scores
- **Conversion Correlation:** Performance vs conversion rates
- **User Experience:** Bounce rate, time on page
- **Technical Performance:** Error rates, load times

## 🚀 Implementation Priority
**Phase**: Marketing Analytics Foundation
**Priority**: HIGH (Essential for optimization)
**Estimated Effort**: 3-4 days
**Dependencies**: Must be implemented with marketing page launch
**Impact**: HIGH - Enables data-driven optimization

---

**This comprehensive analytics strategy provides the data foundation needed to continuously optimize the marketing experience and maximize conversion rates.**