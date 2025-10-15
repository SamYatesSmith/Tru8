'use client';

import { useState, useEffect } from 'react';
import { useAuth } from '@clerk/nextjs';
import { apiClient } from '@/lib/api';
import { useCheckProgress } from '@/hooks/use-check-progress';
import { CheckMetadataCard } from './components/check-metadata-card';
import { ProgressSection } from './components/progress-section';
import { ClaimsSection } from './components/claims-section';
import { ShareSection } from './components/share-section';
import { ErrorState } from './components/error-state';

interface CheckDetailClientProps {
  initialData: any;
  checkId: string;
}

export function CheckDetailClient({ initialData, checkId }: CheckDetailClientProps) {
  const { getToken } = useAuth();
  const [checkData, setCheckData] = useState(initialData);
  const [token, setToken] = useState<string | null>(null);

  // Get token for SSE connection
  useEffect(() => {
    getToken().then(setToken);
  }, [getToken]);

  // Real-time progress updates via SSE
  const { progress, currentStage, isConnected } = useCheckProgress(
    checkId,
    token,
    checkData.status === 'processing'
  );

  // Poll for updates when processing
  useEffect(() => {
    if (checkData.status !== 'processing') {
      return;
    }

    const interval = setInterval(async () => {
      try {
        const currentToken = await getToken();
        const updated = await apiClient.getCheckById(checkId, currentToken) as any;
        setCheckData(updated);

        // Stop polling if completed or failed
        if (updated.status !== 'processing') {
          clearInterval(interval);
        }
      } catch (error) {
        console.error('Failed to poll check status:', error);
      }
    }, 3000);

    return () => clearInterval(interval);
  }, [checkData.status, checkId, getToken]);

  return (
    <div className="space-y-6">
      {/* Metadata Card - Always shown */}
      <CheckMetadataCard check={checkData} />

      {/* Status-based Rendering */}
      {checkData.status === 'processing' && (
        <ProgressSection progress={progress} currentStage={currentStage} isConnected={isConnected} />
      )}

      {checkData.status === 'completed' && checkData.claims && checkData.claims.length > 0 && (
        <>
          <ClaimsSection claims={checkData.claims} />
          <ShareSection checkId={checkId} />
        </>
      )}

      {checkData.status === 'failed' && (
        <ErrorState errorMessage={checkData.errorMessage} checkId={checkId} />
      )}

      {checkData.status === 'pending' && (
        <div className="text-center py-12 bg-slate-800/50 border border-slate-700 rounded-xl">
          <p className="text-slate-400 text-lg">
            Your check is queued and will begin processing soon...
          </p>
        </div>
      )}

      {checkData.status === 'completed' && (!checkData.claims || checkData.claims.length === 0) && (
        <div className="text-center py-12 bg-slate-800/50 border border-slate-700 rounded-xl">
          <p className="text-slate-400 text-lg">No claims were found in this check.</p>
        </div>
      )}
    </div>
  );
}
