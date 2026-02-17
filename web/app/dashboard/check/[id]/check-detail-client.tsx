'use client';

import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@clerk/nextjs';
import { useSearchParams } from 'next/navigation';
import { apiClient } from '@/lib/api';
import { useCheckProgress } from '@/hooks/use-check-progress';
import { ClaimSelectionView } from '@/components/claim-selection';
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

  const [isSubmittingSelection, setIsSubmittingSelection] = useState(false);

  // Real-time progress updates via SSE
  const {
    progress: sseProgress,
    currentStage: sseStage,
    isConnected,
    isCompleted: sseCompleted,
    isAwaitingSelection,
    claimsForSelection,
    message: sseMessage,
    timeEstimate,
  } = useCheckProgress(
    checkId,
    token,
    checkData.status === 'processing' || checkData.status === 'waiting_for_selection'
  );

  // When SSE indicates completion, immediately fetch updated data (don't wait for 3s poll)
  useEffect(() => {
    if (sseCompleted && checkData.status === 'processing') {
      console.log('[CHECK DETAIL] SSE reported completion, fetching updated data');
      const fetchUpdatedData = async () => {
        try {
          const currentToken = await getToken();
          const updated = await apiClient.getCheckById(checkId, currentToken) as any;
          setCheckData(updated);
        } catch (error) {
          console.error('Failed to fetch updated check data:', error);
        }
      };
      fetchUpdatedData();
    }
  }, [sseCompleted, checkData.status, checkId, getToken]);

  // Use the best available progress data:
  // 1. If SSE has meaningful data (progress > 0), use it (even if disconnected - preserves last known state)
  // 2. Otherwise fall back to polling data from checkData
  // 3. Finally fall back to SSE values (which start at 0)
  const progress = sseProgress > 0 ? sseProgress : (checkData.progress ?? sseProgress);
  const currentStage = sseStage ? sseStage : (checkData.currentStage ?? sseStage);
  const message = sseMessage ? sseMessage : (checkData.progressMessage ?? sseMessage);

  // Calculate time estimate based on progress (fallback when SSE isn't connected)
  const getTimeEstimateFromProgress = (prog: number): string => {
    if (prog < 25) return 'within 2 minutes';
    if (prog < 50) return 'within 90 seconds';
    if (prog < 70) return 'within 1 minute';
    if (prog < 90) return 'within 30 seconds';
    return 'momentarily';
  };
  const effectiveTimeEstimate = timeEstimate ?? (progress > 0 ? getTimeEstimateFromProgress(progress) : 'within 2 minutes');

  // Derive claims for selection: prefer SSE data, fall back to checkData.claims on page refresh
  const effectiveClaimsForSelection = claimsForSelection ?? (
    checkData.status === 'waiting_for_selection' && checkData.claims
      ? checkData.claims.map((c: any) => ({
          position: c.position,
          text: c.text,
          claimType: c.claimType || 'empirical',
          significanceRank: c.significanceRank ?? c.position,
        }))
      : null
  );

  const showSelectionUI = (checkData.status === 'waiting_for_selection' || isAwaitingSelection)
    && effectiveClaimsForSelection && effectiveClaimsForSelection.length > 0;

  // Handle claim selection submission
  const handleSelectionSubmit = useCallback(async (selectedPositions: number[]) => {
    setIsSubmittingSelection(true);
    try {
      const currentToken = await getToken();
      await apiClient.selectClaims(checkId, selectedPositions, currentToken);
      // Refetch check data — status will now be 'processing'
      const updated = await apiClient.getCheckById(checkId, currentToken) as any;
      setCheckData(updated);
    } catch (error) {
      console.error('Failed to submit claim selection:', error);
    } finally {
      setIsSubmittingSelection(false);
    }
  }, [checkId, getToken]);

  // Poll for updates when pending or processing
  useEffect(() => {
    if (checkData.status !== 'processing' && checkData.status !== 'pending' && checkData.status !== 'waiting_for_selection') {
      return;
    }

    const interval = setInterval(async () => {
      try {
        const currentToken = await getToken();
        const updated = await apiClient.getCheckById(checkId, currentToken) as any;
        setCheckData(updated);

        // Stop polling when completed, failed, or waiting_for_selection (user action needed)
        if (updated.status === 'completed' || updated.status === 'failed' || updated.status === 'waiting_for_selection') {
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

      {/* Tab Toggle for Evidence Map/Sources (only shown when completed) */}
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
      {checkData.status === 'processing' && !isAwaitingSelection && (
        <ProgressSection progress={progress} currentStage={currentStage} isConnected={isConnected} message={message} timeEstimate={effectiveTimeEstimate} />
      )}

      {/* Claim Selection UI — shown when awaiting user selection */}
      {showSelectionUI && (
        <ClaimSelectionView
          claims={effectiveClaimsForSelection}
          checkId={checkId}
          referenceId={checkId.slice(0, 8).toUpperCase()}
          extractionTime={new Date(checkData.createdAt).toLocaleString()}
          onSubmit={handleSelectionSubmit}
          isSubmitting={isSubmittingSelection}
        />
      )}

      {checkData.status === 'completed' && checkData.claims && checkData.claims.length > 0 && (
        <>
          {checkData.userQuery && (
            <ClarityResponseCard
              userQuery={checkData.userQuery}
              queryResponse={checkData.queryResponse}
              querySources={checkData.querySources}
              relatedClaims={checkData.queryRelatedClaims}
              claims={checkData.claims}
            />
          )}
          <ClaimsSection claims={checkData.claims} checkId={checkId} />
          <OverallSummaryCard
            claims={checkData.claims}
            checkId={checkId}
            sourcesCount={sourcesCount}
            processingTimeMs={checkData.processingTimeMs}
          />
          <ShareSection checkId={checkId} inputUrl={checkData.inputUrl} title={checkData.title} />
          <NavigationSection />
        </>
      )}

      {checkData.status === 'failed' && (
        <ErrorState errorMessage={checkData.errorMessage} checkId={checkId} />
      )}

      {checkData.status === 'pending' && (
        <div className="text-center py-12 bg-white border border-zinc-200">
          <p className="text-zinc-500 text-lg">
            Your check is queued and will begin processing soon...
          </p>
        </div>
      )}

      {checkData.status === 'completed' && (!checkData.claims || checkData.claims.length === 0) && (
        <div className="text-center py-12 bg-white border border-zinc-200">
          <p className="text-zinc-500 text-lg">No claims were found in this check.</p>
        </div>
      )}
    </div>
  );
}
