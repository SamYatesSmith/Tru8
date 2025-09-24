'use client';

import { useEffect } from 'react';
import { initPerformanceMonitoring } from '@/lib/performance';

/**
 * Performance monitoring provider
 * Initializes Core Web Vitals tracking on client-side
 * Phase 01: Performance & SEO Foundation
 */
export function PerformanceProvider({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    // Initialize performance monitoring once on mount
    initPerformanceMonitoring();
  }, []);

  return <>{children}</>;
}