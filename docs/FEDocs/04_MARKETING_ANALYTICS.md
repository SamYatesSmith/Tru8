# 04. Marketing Analytics Integration - Conversion Tracking & Optimization

## 🎯 Objective
Implement comprehensive analytics tracking for the redesigned marketing page to measure conversion performance, user engagement, and design effectiveness. Enable data-driven optimization of the marketing experience through proper event tracking and A/B testing capabilities.

## 📊 Current State Analysis

### Existing Analytics Setup
```tsx
// From web/app/layout.tsx - minimal analytics
import { Analytics } from '@vercel/analytics/react';

// Current implementation:
<Analytics />
```

### Missing Marketing Analytics
- Conversion funnel tracking
- User engagement measurement
- A/B testing infrastructure
- Heat mapping capabilities
- Form abandonment tracking
- Section-specific analytics

## 🏗️ Implementation Strategy

### 1. Comprehensive Event Tracking System

#### Marketing Events Framework
```tsx
// Create: web/lib/analytics.ts
'use client';

interface MarketingEvent {
  event: string;
  category: 'marketing' | 'conversion' | 'engagement' | 'navigation';
  action: string;
  label?: string;
  value?: number;
  userId?: string;
  properties?: Record<string, any>;
}

class MarketingAnalytics {
  private isInitialized = false;

  initialize() {
    if (typeof window === 'undefined' || this.isInitialized) return;

    // Google Analytics 4
    this.initializeGA4();

    // PostHog for event tracking
    this.initializePostHog();

    // Microsoft Clarity for heat mapping
    this.initializeClarity();

    this.isInitialized = true;
  }

  private initializeGA4() {
    // GA4 setup with enhanced e-commerce tracking
    if (typeof window !== 'undefined' && (window as any).gtag) {
      (window as any).gtag('config', process.env.NEXT_PUBLIC_GA4_ID, {
        page_title: 'Tru8 Marketing',
        page_location: window.location.href,
        custom_map: {
          custom_parameter_1: 'user_type',
          custom_parameter_2: 'page_section',
        }
      });
    }
  }

  private initializePostHog() {
    if (typeof window !== 'undefined') {
      // PostHog initialization for detailed event tracking
      const posthog = (window as any).posthog;
      if (posthog) {
        posthog.init(process.env.NEXT_PUBLIC_POSTHOG_KEY, {
          api_host: 'https://app.posthog.com',
          autocapture: false, // We'll do manual tracking for precision
          capture_pageview: false, // Custom pageview tracking
        });
      }
    }
  }

  private initializeClarity() {
    // Microsoft Clarity for heat mapping and session recordings
    if (typeof window !== 'undefined') {
      (function(c: any, l: any, a: any, r: any, i: any, t: any, y: any){
        c[a] = c[a] || function () { (c[a].q = c[a].q || []).push(arguments) };
        t = l.createElement(r); t.async = 1; t.src = "https://www.clarity.ms/tag/" + i;
        y = l.getElementsByTagName(r)[0]; y.parentNode.insertBefore(t, y);
      })(window, document, "clarity", "script", process.env.NEXT_PUBLIC_CLARITY_ID);
    }
  }

  // Core tracking methods
  track(event: MarketingEvent) {
    if (!this.isInitialized) return;

    // Google Analytics 4
    this.trackGA4(event);

    // PostHog
    this.trackPostHog(event);

    // Custom events
    this.trackCustom(event);
  }

  private trackGA4(event: MarketingEvent) {
    if (typeof window !== 'undefined' && (window as any).gtag) {
      (window as any).gtag('event', event.action, {
        event_category: event.category,
        event_label: event.label,
        value: event.value,
        custom_parameter_1: event.properties?.userType || 'anonymous',
        custom_parameter_2: event.properties?.section || 'unknown',
        ...event.properties,
      });
    }
  }

  private trackPostHog(event: MarketingEvent) {
    if (typeof window !== 'undefined') {
      const posthog = (window as any).posthog;
      if (posthog) {
        posthog.capture(event.event, {
          category: event.category,
          action: event.action,
          label: event.label,
          value: event.value,
          ...event.properties,
        });
      }
    }
  }

  private trackCustom(event: MarketingEvent) {
    // Custom analytics for internal dashboard
    fetch('/api/analytics/track', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        event: event.event,
        timestamp: Date.now(),
        url: window.location.href,
        referrer: document.referrer,
        ...event,
      }),
    }).catch(console.error);
  }

  // Conversion tracking
  trackConversion(type: 'signup_started' | 'signup_completed' | 'demo_requested', value?: number) {
    this.track({
      event: `conversion_${type}`,
      category: 'conversion',
      action: type,
      value,
      properties: {
        timestamp: Date.now(),
        userAgent: navigator.userAgent,
        viewport: `${window.innerWidth}x${window.innerHeight}`,
      },
    });
  }

  // Engagement tracking
  trackEngagement(section: string, action: string, duration?: number) {
    this.track({
      event: 'engagement',
      category: 'engagement',
      action: action,
      label: section,
      value: duration,
      properties: {
        section,
        timestamp: Date.now(),
      },
    });
  }

  // Navigation tracking
  trackNavigation(from: string, to: string, method: 'click' | 'scroll' | 'keyboard') {
    this.track({
      event: 'navigation',
      category: 'navigation',
      action: method,
      label: `${from}_to_${to}`,
      properties: {
        from,
        to,
        method,
      },
    });
  }
}

export const analytics = new MarketingAnalytics();
```

### 2. Section-Specific Tracking Hooks

#### Scroll Tracking Hook
```tsx
// Create: web/hooks/useScrollTracking.ts
'use client';

import { useEffect, useRef } from 'react';
import { analytics } from '@/lib/analytics';

interface ScrollTrackingOptions {
  sectionId: string;
  threshold?: number;
  trackTime?: boolean;
}

export function useScrollTracking({ sectionId, threshold = 0.5, trackTime = true }: ScrollTrackingOptions) {
  const ref = useRef<HTMLElement>(null);
  const startTime = useRef<number>(0);
  const hasTrackedView = useRef(false);

  useEffect(() => {
    const element = ref.current;
    if (!element) return;

    const observer = new RalewaysectionObserver(
      ([entry]) => {
        if (entry.isRalewaysecting && !hasTrackedView.current) {
          // Track section view
          analytics.trackEngagement(sectionId, 'section_viewed');
          hasTrackedView.current = true;

          if (trackTime) {
            startTime.current = Date.now();
          }
        } else if (!entry.isRalewaysecting && startTime.current > 0 && trackTime) {
          // Track time spent in section
          const timeSpent = Date.now() - startTime.current;
          if (timeSpent > 1000) { // Only track if viewed for more than 1 second
            analytics.trackEngagement(sectionId, 'time_spent', timeSpent);
          }
          startTime.current = 0;
        }
      },
      { threshold }
    );

    observer.observe(element);

    return () => {
      if (startTime.current > 0 && trackTime) {
        const timeSpent = Date.now() - startTime.current;
        if (timeSpent > 1000) {
          analytics.trackEngagement(sectionId, 'time_spent', timeSpent);
        }
      }
      observer.disconnect();
    };
  }, [sectionId, threshold, trackTime]);

  return ref;
}
```

#### Conversion Tracking Hook
```tsx
// Create: web/hooks/useConversionTracking.ts
'use client';

import { useEffect } from 'react';
import { analytics } from '@/lib/analytics';

export function useConversionTracking() {
  useEffect(() => {
    // Track page load as marketing impression
    analytics.track({
      event: 'marketing_page_loaded',
      category: 'marketing',
      action: 'page_load',
      properties: {
        userAgent: navigator.userAgent,
        viewport: `${window.innerWidth}x${window.innerHeight}`,
        referrer: document.referrer,
        timestamp: Date.now(),
      },
    });
  }, []);

  const trackCTAClick = (ctaType: 'primary' | 'secondary', location: string) => {
    analytics.track({
      event: 'cta_clicked',
      category: 'conversion',
      action: `${ctaType}_cta_click`,
      label: location,
      properties: {
        ctaType,
        location,
        timestamp: Date.now(),
      },
    });
  };

  const trackFormStart = (formType: 'signup' | 'demo') => {
    analytics.trackConversion('signup_started');
    analytics.track({
      event: 'form_started',
      category: 'conversion',
      action: 'form_interaction',
      label: formType,
      properties: {
        formType,
        timestamp: Date.now(),
      },
    });
  };

  const trackFormComplete = (formType: 'signup' | 'demo') => {
    analytics.trackConversion('signup_completed', 1);
    analytics.track({
      event: 'form_completed',
      category: 'conversion',
      action: 'conversion_complete',
      label: formType,
      value: 1,
      properties: {
        formType,
        timestamp: Date.now(),
      },
    });
  };

  return {
    trackCTAClick,
    trackFormStart,
    trackFormComplete,
  };
}
```

### 3. Enhanced Marketing Components with Tracking

#### Tracked CTA Buttons
```tsx
// Enhanced CTA buttons with conversion tracking
export function TrackedCTAButton({
  children,
  href,
  ctaType = 'primary',
  location,
  ...props
}: {
  children: React.ReactNode;
  href: string;
  ctaType?: 'primary' | 'secondary';
  location: string;
} & React.ComponentProps<typeof Button>) {
  const { trackCTAClick } = useConversionTracking();

  const handleClick = () => {
    trackCTAClick(ctaType, location);
  };

  return (
    <Button
      {...props}
      asChild
      onClick={handleClick}
      data-analytics-cta={ctaType}
      data-analytics-location={location}
    >
      <Link href={href}>
        {children}
      </Link>
    </Button>
  );
}
```

#### Tracked Feature Section
```tsx
// Feature section with engagement tracking
export function TrackedFeatureSection({ features }: { features: Feature[] }) {
  const sectionRef = useScrollTracking({
    sectionId: 'features',
    threshold: 0.3,
    trackTime: true
  });

  const handleFeatureClick = (featureId: string) => {
    analytics.trackEngagement('features', 'feature_clicked', featureId);
  };

  return (
    <section ref={sectionRef} id="features" className="features-section">
      <div className="container">
        <h2 className="heading-section gradient-text-primary">
          Professional Fact-Checking, Simplified
        </h2>

        <div className="feature-grid">
          {features.map((feature) => (
            <div
              key={feature.id}
              className="feature-card"
              onClick={() => handleFeatureClick(feature.id)}
              data-analytics-feature={feature.id}
            >
              <h3 className="feature-title">{feature.title}</h3>
              <p className="feature-description">{feature.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
```

### 4. A/B Testing Framework

#### A/B Testing Hook
```tsx
// Create: web/hooks/useABTest.ts
'use client';

import { useState, useEffect } from 'react';
import { analytics } from '@/lib/analytics';

interface ABTestConfig {
  testName: string;
  variants: Record<string, any>;
  defaultVariant: string;
  trafficSplit?: Record<string, number>; // e.g., { A: 50, B: 50 }
}

export function useABTest<T = any>(config: ABTestConfig): { variant: string; data: T } {
  const [assignment, setAssignment] = useState<{ variant: string; data: T }>({
    variant: config.defaultVariant,
    data: config.variants[config.defaultVariant],
  });

  useEffect(() => {
    // Get or create user ID for consistent assignment
    let userId = localStorage.getItem('ab_user_id');
    if (!userId) {
      userId = `user_${Math.random().toString(36).substr(2, 9)}`;
      localStorage.setItem('ab_user_id', userId);
    }

    // Check for existing assignment
    const existingAssignment = localStorage.getItem(`ab_${config.testName}`);
    if (existingAssignment) {
      const variant = existingAssignment;
      setAssignment({
        variant,
        data: config.variants[variant],
      });
      return;
    }

    // Assign variant based on traffic split
    const variants = Object.keys(config.trafficSplit || { A: 50, B: 50 });
    const weights = Object.values(config.trafficSplit || { A: 50, B: 50 });

    const random = Math.random() * 100;
    let cumulative = 0;
    let selectedVariant = config.defaultVariant;

    for (let i = 0; i < variants.length; i++) {
      cumulative += weights[i];
      if (random <= cumulative) {
        selectedVariant = variants[i];
        break;
      }
    }

    // Store assignment
    localStorage.setItem(`ab_${config.testName}`, selectedVariant);

    setAssignment({
      variant: selectedVariant,
      data: config.variants[selectedVariant],
    });

    // Track assignment
    analytics.track({
      event: 'ab_test_assigned',
      category: 'marketing',
      action: 'test_assignment',
      label: `${config.testName}_${selectedVariant}`,
      properties: {
        testName: config.testName,
        variant: selectedVariant,
        userId,
      },
    });

  }, [config]);

  return assignment;
}
```

#### A/B Test Implementation Example
```tsx
// A/B test different hero headlines
export function ABTestHeroSection() {
  const { variant, data } = useABTest({
    testName: 'hero_headline_test',
    variants: {
      A: {
        headline: "Instant Fact-Checking with Dated Evidence",
        subtitle: "Get explainable verdicts on claims from articles, images, videos, and text.",
      },
      B: {
        headline: "Professional Fact-Checking in Under 10 Seconds",
        subtitle: "Verify any claim with transparent sources and publication dates.",
      },
    },
    defaultVariant: 'A',
    trafficSplit: { A: 50, B: 50 },
  });

  return (
    <section className="hero-section" data-ab-test="hero_headline_test" data-ab-variant={variant}>
      <div className="container">
        <h1 className="heading-hero gradient-text-hero">
          {data.headline}
        </h1>
        <p className="hero-subtitle">
          {data.subtitle}
        </p>

        <TrackedCTAButton
          href="/sign-up"
          ctaType="primary"
          location="hero"
          className="btn-primary"
        >
          Start Fact-Checking Now
        </TrackedCTAButton>
      </div>
    </section>
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