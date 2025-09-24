'use client';

import { useState, useEffect } from 'react';

/**
 * Feature detection hook for progressive enhancement
 * Phase 02: Progressive Enhancement Strategy
 */
interface FeatureSupport {
  backdropFilter: boolean;
  cssGrid: boolean;
  intersectionObserver: boolean;
  webp: boolean;
  reducedMotion: boolean;
}

export function useFeatureDetection(): FeatureSupport {
  const [features, setFeatures] = useState<FeatureSupport>({
    backdropFilter: false,
    cssGrid: false,
    intersectionObserver: false,
    webp: false,
    reducedMotion: false,
  });

  useEffect(() => {
    if (typeof window === 'undefined') return;

    setFeatures({
      backdropFilter: CSS.supports('backdrop-filter', 'blur(10px)'),
      cssGrid: CSS.supports('display', 'grid'),
      intersectionObserver: 'IntersectionObserver' in window,
      webp: (() => {
        const canvas = document.createElement('canvas');
        return canvas.toDataURL('image/webp').indexOf('data:image/webp') === 0;
      })(),
      reducedMotion: window.matchMedia('(prefers-reduced-motion: reduce)').matches,
    });
  }, []);

  return features;
}