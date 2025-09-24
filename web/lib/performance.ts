'use client';

import { getCLS, getFID, getFCP, getLCP, getTTFB } from 'web-vitals';

/**
 * Sends Core Web Vitals metrics to analytics provider
 * Phase 01: Performance & SEO Foundation
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

  // Also log to console in development
  if (process.env.NODE_ENV === 'development') {
    console.log(`[Performance Metric] ${metric.name}:`, metric.value, 'ms');
  }

  // Could also send to custom monitoring endpoint
  // Example: sendToCustomEndpoint(metric);
}

/**
 * Initialize Core Web Vitals monitoring
 * Tracks: CLS, FID, FCP, LCP, TTFB
 */
export function initPerformanceMonitoring() {
  if (typeof window !== 'undefined') {
    getCLS(sendToAnalytics);
    getFID(sendToAnalytics);
    getFCP(sendToAnalytics);
    getLCP(sendToAnalytics);
    getTTFB(sendToAnalytics);
  }
}

/**
 * Performance budget checker
 * Alerts if metrics exceed defined thresholds
 */
export function checkPerformanceBudget(metric: any) {
  const budgets = {
    LCP: 2500,    // 2.5s
    FID: 100,     // 100ms
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