'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { useAuth } from '@clerk/nextjs';
import { useRouter, useSearchParams } from 'next/navigation';
import { apiClient } from '@/lib/api';
import { useCheckProgress } from '@/hooks/use-check-progress';
import { ClaimSelectionView } from '@/components/claim-selection';
import { CheckMetadataCard } from './components/check-metadata-card';
import { ProgressSection } from './components/progress-section';
import { ShareSection } from './components/share-section';
import { NavigationSection } from './components/navigation-section';
import { ErrorState } from './components/error-state';
import { ClarityResponseCard } from './components/clarity-response-card';
import { UpgradeModal } from './components/upgrade-modal';
import { ClaimSectionStack } from '@/components/evidence-views/overview';
import { ViewSelector, ViewGuide, EvidenceMetaStrip } from '@/components/evidence-views';
import { LibrarianView } from '@/components/evidence-views/librarian';
import { CartographerView } from '@/components/evidence-views/cartographer';
import { ProjectionistView } from '@/components/evidence-views/projectionist';
import { ChronologistView } from '@/components/evidence-views/chronologist';
import { ClaimHeader } from '@/components/evidence-views/detail/ClaimHeader';
import { CorrespondentView } from '@/components/evidence-views/correspondent';
import { SeekerView } from '@/components/evidence-views/seeker';
import { useVideoRecommendations } from '@/hooks/use-video-recommendations';

interface CheckDetailClientProps {
  initialData: any;
  checkId: string;
  isPro?: boolean;
  rawSourcesCount?: number;
  initialClaim?: number;
}

export function CheckDetailClient({ initialData, checkId, isPro = false, rawSourcesCount = 0, initialClaim }: CheckDetailClientProps) {
  const { getToken } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  // Fresh submission: force processing view even if server-side fetch returned 'completed'
  // (in production, the pipeline can finish before the page renders server-side)
  const isFreshSubmission = searchParams?.get('fresh') === 'true';
  const [showFreshProcessing, setShowFreshProcessing] = useState(isFreshSubmission && initialData.status === 'completed');

  const [checkData, setCheckData] = useState(() => {
    if (isFreshSubmission && initialData.status === 'completed') {
      // Override to show progress screen — will transition to completed after animation
      return { ...initialData, status: 'processing' as string };
    }
    return initialData;
  });
  const [token, setToken] = useState<string | null>(null);
  const [showUpgradeModal, setShowUpgradeModal] = useState(false);
  const [sourcesCount, setSourcesCount] = useState(rawSourcesCount);
  const [isProUser, setIsProUser] = useState(isPro);
  const claimDetailRef = useRef<HTMLDivElement>(null);

  // Single-claim checks pre-focus the only claim (no overview grid needed)
  const isSingleClaim = checkData.status === 'completed' && checkData.claims?.length === 1;

  const [activeClaimIndex, setActiveClaimIndex] = useState<number | null>(
    initialClaim !== undefined ? initialClaim : (isSingleClaim ? 0 : null)
  );
  const [claimView, setClaimView] = useState<string>(() => {
    // If a claim is focused, read ?view= as the claim-level tab
    if (initialClaim !== undefined || isSingleClaim) {
      const viewParam = searchParams?.get('view');
      const validViews = ['cartographer', 'librarian', 'correspondent', 'seeker', 'projectionist', 'chronologist'];
      return viewParam && validViews.includes(viewParam) ? viewParam : 'cartographer';
    }
    return 'cartographer';
  });


  // Fresh submission: animate progress to 100% then reveal results
  useEffect(() => {
    if (!showFreshProcessing) return;
    // Show progress briefly (2.5s), then transition to completed
    const timer = setTimeout(() => {
      setCheckData(initialData); // Restore real completed data
      setShowFreshProcessing(false);
      // Clean up the ?fresh param from URL
      const url = new URL(window.location.href);
      url.searchParams.delete('fresh');
      window.history.replaceState({}, '', url.toString());
    }, 2500);
    return () => clearTimeout(timer);
  }, [showFreshProcessing, initialData]);

  // Auto-focus the only claim when a single-claim check completes
  // (handles SSE race: initial render may have status='processing')
  useEffect(() => {
    if (isSingleClaim && activeClaimIndex === null) {
      setActiveClaimIndex(0);
    }
  }, [isSingleClaim, activeClaimIndex]);


  // Claim-level tab change — syncs ?claim=N&view=X to URL
  const handleClaimTabChange = useCallback((tab: string) => {
    setClaimView(tab);
    const url = new URL(window.location.href);
    if (activeClaimIndex !== null) {
      url.searchParams.set('claim', String(activeClaimIndex));
    }
    if (tab !== 'cartographer') {
      url.searchParams.set('view', tab);
    } else {
      url.searchParams.delete('view');
    }
    window.history.replaceState({}, '', url.toString());
  }, [activeClaimIndex]);

  // Focus a claim (from grid click or prev/next)
  const handleClaimSelect = useCallback((position: number) => {
    setActiveClaimIndex(position);
    setClaimView('cartographer');
    const url = new URL(window.location.href);
    url.searchParams.set('claim', String(position));
    url.searchParams.delete('view');
    window.history.replaceState({}, '', url.toString());
    // Scroll to detail section
    setTimeout(() => {
      claimDetailRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 50);
  }, []);

  // Claim navigation: prev/next + keyboard arrows
  const claims = checkData.claims || [];
  const handlePrevClaim = useCallback(() => {
    if (activeClaimIndex !== null && activeClaimIndex > 0) {
      handleClaimSelect(activeClaimIndex - 1);
    }
  }, [activeClaimIndex, handleClaimSelect]);

  const handleNextClaim = useCallback(() => {
    if (activeClaimIndex !== null && activeClaimIndex < claims.length - 1) {
      handleClaimSelect(activeClaimIndex + 1);
    }
  }, [activeClaimIndex, claims.length, handleClaimSelect]);

  // Keyboard navigation for claim prev/next
  useEffect(() => {
    if (activeClaimIndex === null || isSingleClaim) return;
    const handler = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;
      if (e.key === 'ArrowLeft') handlePrevClaim();
      if (e.key === 'ArrowRight') handleNextClaim();
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [activeClaimIndex, isSingleClaim, handlePrevClaim, handleNextClaim]);

  const handleSwitchToLibrarian = useCallback(() => handleClaimTabChange('librarian'), [handleClaimTabChange]);

  // G02: Refresh page data after element re-search completes
  const handleResearchComplete = useCallback(() => {
    router.refresh();
  }, [router]);

  // Video recommendations — per-claim (detail Projectionist tab)
  const focusedClaim = activeClaimIndex !== null ? claims[activeClaimIndex] : null;
  const { videos: claimVideos, isLoading: claimVideosLoading } = useVideoRecommendations(
    checkId,
    focusedClaim?.id || null,
    token,
    checkData.status === 'completed' && claimView === 'projectionist' && activeClaimIndex !== null,
  );

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

  // Track when SSE has delivered final data so polling can stop early
  const sseDeliveredRef = useRef(false);

  // When SSE indicates completion, immediately fetch updated data (don't wait for poll)
  useEffect(() => {
    if (sseCompleted && checkData.status === 'processing') {
      sseDeliveredRef.current = true;
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
  // 1. If SSE is connected and has data, prefer it (real-time)
  // 2. If SSE is disconnected, prefer polling data (SSE values may be stale)
  // 3. Finally fall back to SSE values (which start at 0)
  const pollingProgress = checkData.progress ?? 0;
  const progress = isConnected && sseProgress > 0
    ? sseProgress
    : pollingProgress > sseProgress ? pollingProgress : sseProgress;
  const currentStage = isConnected && sseStage
    ? sseStage
    : (checkData.currentStage || sseStage);
  const message = isConnected && sseMessage
    ? sseMessage
    : (checkData.progressMessage || sseMessage);

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

  const showSelectionUI = checkData.status === 'waiting_for_selection'
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

  // Poll for updates when pending or processing (with backoff)
  useEffect(() => {
    if (checkData.status !== 'processing' && checkData.status !== 'pending' && checkData.status !== 'waiting_for_selection') {
      return;
    }

    let delay = 3000;
    const MAX_DELAY = 15000;
    let timeoutId: NodeJS.Timeout;

    const poll = async () => {
      // SSE already delivered final data — no need to poll
      if (sseDeliveredRef.current) return;

      try {
        const currentToken = await getToken();
        const updated = await apiClient.getCheckById(checkId, currentToken) as any;
        setCheckData(updated);

        // Stop polling when completed, failed, or waiting_for_selection (user action needed)
        if (updated.status === 'completed' || updated.status === 'failed' || updated.status === 'waiting_for_selection') {
          return;
        }
      } catch (error) {
        console.error('Failed to poll check status:', error);
      }

      delay = Math.min(delay * 1.5, MAX_DELAY);
      timeoutId = setTimeout(poll, delay);
    };

    timeoutId = setTimeout(poll, delay);
    return () => clearTimeout(timeoutId);
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

          {/* Evidence Meta Strip */}
          <EvidenceMetaStrip
            referenceId={checkData.id}
            claimsCount={checkData.claims.length}
            sourcesCount={checkData.claims.reduce((sum: number, c: any) => sum + (c.evidence?.length || 0), 0)}
            sourcesFoundCount={checkData.totalSearchResults || sourcesCount}
            processingTimeMs={checkData.processingTimeMs}
          />

          {/* Multi-claim: Claim-Sectioned Overview */}
          {!isSingleClaim && (
            <ClaimSectionStack
              claims={checkData.claims}
              onExplore={handleClaimSelect}
              inputType={checkData.inputType}
            />
          )}

          {/* Per-Claim Detail Section */}
          {focusedClaim && (
            <div ref={claimDetailRef} className="pt-8 border-t-2 border-zinc-200">
              {!isSingleClaim && (
                <div className="font-mono text-sm font-bold uppercase tracking-[0.3em] text-zinc-600 mb-6">
                  Claim Detail
                </div>
              )}
              {/* Claim header with prev/next (multi-claim only) */}
              <div className="flex flex-col-reverse lg:flex-row lg:items-start lg:justify-between gap-4 mb-6">
                <ClaimHeader claim={focusedClaim} position={activeClaimIndex!} inputType={checkData.inputType} />
                {!isSingleClaim && claims.length > 1 && (
                  <div className="flex items-center gap-2 shrink-0 lg:ml-6">
                    <button
                      onClick={handlePrevClaim}
                      disabled={activeClaimIndex === 0}
                      className="font-mono text-[10px] uppercase tracking-widest text-zinc-400 hover:text-zinc-900 disabled:text-zinc-200 disabled:cursor-default transition-colors px-2 py-1"
                    >
                      &larr; Prev
                    </button>
                    <span className="font-mono text-[10px] text-zinc-300">
                      {(activeClaimIndex! + 1)}/{claims.length}
                    </span>
                    <button
                      onClick={handleNextClaim}
                      disabled={activeClaimIndex === claims.length - 1}
                      className="font-mono text-[10px] uppercase tracking-widest text-zinc-400 hover:text-zinc-900 disabled:text-zinc-200 disabled:cursor-default transition-colors px-2 py-1"
                    >
                      Next &rarr;
                    </button>
                  </div>
                )}
              </div>

              <ViewSelector mode="detail" activeTab={claimView} onTabChange={handleClaimTabChange} />
              <ViewGuide activeView={claimView} />

              {claimView === 'cartographer' && (
                <CartographerView
                  scope="claim"
                  claims={[focusedClaim]}
                  onSwitchToLibrarian={handleSwitchToLibrarian}
                />
              )}
              {claimView === 'librarian' && (
                <LibrarianView scope="claim" claims={[focusedClaim]} />
              )}
              {claimView === 'correspondent' && (
                <CorrespondentView scope="claim" claims={[focusedClaim]} />
              )}
              {claimView === 'projectionist' && (
                <ProjectionistView
                  scope="claim"
                  claims={[focusedClaim]}
                  videos={claimVideos}
                  isLoading={claimVideosLoading}
                />
              )}
              {claimView === 'chronologist' && (
                <ChronologistView
                  scope="claim"
                  claims={[focusedClaim]}
                  onSwitchToLibrarian={handleSwitchToLibrarian}
                />
              )}
              {claimView === 'seeker' && (
                <SeekerView
                  claim={focusedClaim}
                  checkId={checkId}
                  token={token}
                  onResearchComplete={handleResearchComplete}
                />
              )}
            </div>
          )}

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
