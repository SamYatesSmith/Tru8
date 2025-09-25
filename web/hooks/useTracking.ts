'use client';

import { useEffect } from 'react';
import { analytics } from '@/lib/analytics';

/**
 * Simple Tracking Hook - MVP Version
 * Phase 04: Marketing Analytics Integration
 *
 * Basic wrapper for analytics tracking focused on marketing conversion events.
 * Automatically initializes analytics and tracks page view on mount.
 */
export function useTracking(pageName: string = 'marketing_home') {
  useEffect(() => {
    // Initialize analytics on page load
    analytics.initialize();
    analytics.trackPageView(pageName);
  }, [pageName]);

  return {
    trackCTA: analytics.trackCTAClick,
    trackSignupStart: analytics.trackSignupStart,
    trackSignupComplete: analytics.trackSignupComplete,
  };
}