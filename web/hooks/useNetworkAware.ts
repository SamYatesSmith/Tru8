'use client';

import { useState, useEffect } from 'react';

/**
 * Network-aware hook for connection-based optimizations
 * Phase 02: Progressive Enhancement Strategy
 */
interface NetworkInfo {
  isOnline: boolean;
  connectionType: 'slow' | 'fast' | 'unknown';
  saveData: boolean;
}

export function useNetworkAware(): NetworkInfo {
  const [networkInfo, setNetworkInfo] = useState<NetworkInfo>({
    isOnline: true,
    connectionType: 'unknown',
    saveData: false,
  });

  useEffect(() => {
    if (typeof window === 'undefined') return;

    const updateNetworkInfo = () => {
      const navigator = window.navigator as any;
      const connection = navigator.connection || navigator.mozConnection || navigator.webkitConnection;

      setNetworkInfo({
        isOnline: navigator.onLine,
        connectionType: connection?.effectiveType === '2g' || connection?.effectiveType === 'slow-2g' ? 'slow' : 'fast',
        saveData: connection?.saveData || false,
      });
    };

    updateNetworkInfo();

    window.addEventListener('online', updateNetworkInfo);
    window.addEventListener('offline', updateNetworkInfo);

    return () => {
      window.removeEventListener('online', updateNetworkInfo);
      window.removeEventListener('offline', updateNetworkInfo);
    };
  }, []);

  return networkInfo;
}