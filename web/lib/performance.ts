'use client';

import { onCLS, onINP, onFCP, onLCP, onTTFB } from 'web-vitals';

/**
 * Sends Core Web Vitals metrics to analytics providers
 * Phase 01: Performance & SEO Foundation
 * Phase 04: PostHog Integration
 */
function sendToAnalytics(metric: any) {
  // Send to Google Analytics if available
  if (typeof window !== 'undefined' && (window as any).gtag) {
    (window as any).gtag('event', metric.name, {
      value: Math.round(metric.name === 'CLS' ? metric.value * 1000 : metric.value),
      event_label: metric.id,
      non_interaction: true,
    });
  }

  // PHASE 04: Send to PostHog analytics (only if initialized/consented)
  if (typeof window !== 'undefined') {
    import('@/lib/analytics').then(({ analytics }) => {
      // Only track if analytics is initialized (user consented)
      analytics.trackPerformance(metric);
    });
  }

  // Also log to console in development
  if (process.env.NODE_ENV === 'development') {
    console.log(`[Performance Metric] ${metric.name}:`, metric.value, 'ms');
  }

  // Could also send to custom monitoring endpoint
  // Example: sendToCustomEndpoint(metric);
}

/**
 * Initialize Core Web Vitals monitoring
 * Tracks: CLS, INP (replaced FID), FCP, LCP, TTFB
 */
export function initPerformanceMonitoring() {
  if (typeof window !== 'undefined') {
    onCLS(sendToAnalytics);
    onINP(sendToAnalytics);  // INP replaces FID in Web Vitals v5
    onFCP(sendToAnalytics);
    onLCP(sendToAnalytics);
    onTTFB(sendToAnalytics);
  }
}

/**
 * Performance budget checker
 * Alerts if metrics exceed defined thresholds
 */
export function checkPerformanceBudget(metric: any) {
  const budgets = {
    LCP: 2500,    // 2.5s
    INP: 200,     // 200ms (INP replaces FID)
    CLS: 0.1,     // 0.1
    FCP: 1800,    // 1.8s
    TTFB: 800,    // 800ms
  };

  const threshold = budgets[metric.name as keyof typeof budgets];

  if (threshold && metric.value > threshold) {
    console.warn(
      `⚠️ Performance Budget Exceeded: ${metric.name} (${metric.value}ms) exceeds budget (${threshold}ms)`
    );

    // Could trigger alerts or monitoring notifications
    // Example: notifyPerformanceIssue(metric);
  }
}