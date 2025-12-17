'use client';

import { useState, useEffect } from 'react';
import { useAuth } from '@clerk/nextjs';
import { useSearchParams } from 'next/navigation';
import { apiClient } from '@/lib/api';
import { useCheckProgress } from '@/hooks/use-check-progress';
import { CheckMetadataCard } from './components/check-metadata-card';
import { OverallSummaryCard } from './components/overall-summary-card';
import { ProgressSection } from './components/progress-section';
import { ClaimsSection } from './components/claims-section';
import { ShareSection } from './components/share-section';
import { NavigationSection } from './components/navigation-section';
import { ErrorState } from './components/error-state';
import { ClarityResponseCard } from './components/clarity-response-card';
import { CheckTabs } from './components/check-tabs';
import { UpgradeModal } from './components/upgrade-modal';

interface CheckDetailClientProps {
  initialData: any;
  checkId: string;
  isPro?: boolean;
  rawSourcesCount?: number;
}

export function CheckDetailClient({ initialData, checkId, isPro = false, rawSourcesCount = 0 }: CheckDetailClientProps) {
  const { getToken } = useAuth();
  const searchParams = useSearchParams();
  const [checkData, setCheckData] = useState(initialData);
  const [token, setToken] = useState<string | null>(null);
  const [showUpgradeModal, setShowUpgradeModal] = useState(false);
  const [sourcesCount, setSourcesCount] = useState(rawSourcesCount);
  const [isProUser, setIsProUser] = useState(isPro);

  // Check for upgrade query param
  useEffect(() => {
    if (searchParams?.get('upgrade') === 'sources') {
      setShowUpgradeModal(true);
    }
  }, [searchParams]);

  // Listen for upgrade modal event
  useEffect(() => {
    const handler = () => setShowUpgradeModal(true);
    window.addEventListener('show-upgrade-modal', handler);
    return () => window.removeEventListener('show-upgrade-modal', handler);
  }, []);

  // Get token for SSE connection
  useEffect(() => {
    getToken().then(setToken);
  }, [getToken]);

  // Real-time progress updates via SSE
  const { progress, currentStage, isConnected, message } = useCheckProgress(
    checkId,
    token,
    checkData.status === 'processing'
  );

  // Poll for updates when pending or processing
  useEffect(() => {
    if (checkData.status !== 'processing' && checkData.status !== 'pending') {
      return;
    }

    const interval = setInterval(async () => {
      try {
        const currentToken = await getToken();
        const updated = await apiClient.getCheckById(checkId, currentToken) as any;
        setCheckData(updated);

        // Stop polling only when completed or failed (not pending or processing)
        if (updated.status === 'completed' || updated.status === 'failed') {
          clearInterval(interval);
        }
      } catch (error) {
        console.error('Failed to poll check status:', error);
      }
    }, 3000);

    return () => clearInterval(interval);
  }, [checkData.status, checkId, getToken]);

  // Fetch sources count when check completes (handles transition from processing to completed)
  useEffect(() => {
    if (checkData.status !== 'completed') {
      return;
    }

    // Only fetch if we don't have sources count yet (or it's 0 from initial load during processing)
    if (sourcesCount === 0 || sourcesCount !== rawSourcesCount) {
      const fetchSourcesCount = async () => {
        try {
          const currentToken = await getToken();
          const sourcesResult = await apiClient.getCheckSources(checkId, { includeFiltered: true }, currentToken);
          if (sourcesResult) {
            setSourcesCount(sourcesResult.totalSources || 0);
            setIsProUser(!sourcesResult.requiresUpgrade);
          }
        } catch (error) {
          console.error('Failed to fetch sources count:', error);
        }
      };
      fetchSourcesCount();
    }
  }, [checkData.status, checkId, getToken, sourcesCount, rawSourcesCount]);

  return (
    <div className="space-y-6">
      {/* Metadata Card - Always shown (now includes transparency score) */}
      <CheckMetadataCard check={checkData} />

      {/* Tab Toggle for Verdict/Sources (only shown when completed) */}
      {checkData.status === 'completed' && (
        <CheckTabs
          checkId={checkId}
          sourcesCount={sourcesCount}
          isPro={isProUser}
          isCompleted={checkData.status === 'completed'}
        />
      )}

      {/* Upgrade Modal for Sources */}
      {showUpgradeModal && (
        <UpgradeModal
          feature="sources"
          sourcesCount={sourcesCount}
          onClose={() => {
            setShowUpgradeModal(false);
            // Clear the URL param
            window.history.replaceState({}, '', `/dashboard/check/${checkId}`);
          }}
        />
      )}

      {/* Status-based Rendering */}
      {checkData.status === 'processing' && (
        <ProgressSection progress={progress} currentStage={currentStage} isConnected={isConnected} message={message} />
      )}

      {checkData.status === 'completed' && checkData.claims && checkData.claims.length > 0 && (
        <>
          {checkData.userQuery && (
            <ClarityResponseCard
              userQuery={checkData.userQuery}
              queryResponse={checkData.queryResponse}
              queryConfidence={checkData.queryConfidence}
              querySources={checkData.querySources}
              relatedClaims={checkData.queryRelatedClaims}
              claims={checkData.claims}
            />
          )}
          <ClaimsSection claims={checkData.claims} />
          {checkData.overallSummary && checkData.credibilityScore !== undefined && (
            <OverallSummaryCard check={checkData} />
          )}
          <ShareSection checkId={checkId} />
          <NavigationSection />
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
