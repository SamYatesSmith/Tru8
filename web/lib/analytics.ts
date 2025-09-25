'use client';

import posthog from 'posthog-js';

/**
 * MVP Analytics - PostHog Only Implementation
 * Phase 04: Marketing Analytics Integration
 *
 * Simple, startup-appropriate analytics tracking focused on essential
 * conversion metrics and performance monitoring integration.
 */
class MVPAnalytics {
  private initialized = false;

  initialize() {
    if (typeof window === 'undefined' || this.initialized) return;

    // Check if PostHog key is available
    const posthogKey = process.env.NEXT_PUBLIC_POSTHOG_KEY;
    if (!posthogKey) {
      console.warn('[Analytics] PostHog key not found. Analytics disabled.');
      return;
    }

    try {
      posthog.init(posthogKey, {
        api_host: process.env.NEXT_PUBLIC_POSTHOG_HOST || 'https://us.i.posthog.com',
        person_profiles: 'identified_only', // Privacy-friendly
        capture_pageview: false, // We'll do manual pageviews
      });

      this.initialized = true;
    } catch (error) {
      console.error('[Analytics] Failed to initialize PostHog:', error);
    }
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
    if (!this.initialized) return;
    posthog.capture('cta_clicked', { location, ctaType });
  }

  trackSignupStart() {
    if (!this.initialized) return;
    posthog.capture('signup_started', {
      source: 'marketing_page',
      timestamp: Date.now()
    });
  }

  trackSignupComplete() {
    if (!this.initialized) return;
    posthog.capture('signup_completed', {
      source: 'marketing_page',
      timestamp: Date.now()
    });
  }

  // Integrate with existing Core Web Vitals (Phase 01)
  trackPerformance(metric: any) {
    if (!this.initialized) return;
    posthog.capture('performance_metric', {
      name: metric.name,
      value: Math.round(metric.value),
      rating: metric.rating,
    });
  }
}

export const analytics = new MVPAnalytics();