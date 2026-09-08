'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { useAuth } from '@clerk/nextjs';
import { apiClient } from '@/lib/api';

/** Update the client-owned report after research, with retry and stale-response protection. */
export function useReportRefresh(checkId: string, onUpdate: (report: any) => void) {
  const { getToken } = useAuth();
  const generation = useRef(0);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => () => { generation.current++; }, [checkId]);
  const refresh = useCallback(async () => {
    const request = ++generation.current;
    setError(null);
    try {
      const token = await getToken();
      if (!token) throw new Error('Authentication expired');
      const report = await apiClient.getCheckById(checkId, token);
      if (request === generation.current) onUpdate(report);
    } catch {
      if (request === generation.current) {
        setError('Research finished, but the updated report could not be loaded.');
      }
    }
  }, [checkId, getToken, onUpdate]);
  return { refresh, error };
}
