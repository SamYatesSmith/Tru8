'use client';

import { useState, useCallback, useEffect } from 'react';
import { useAuth } from '@clerk/nextjs';
import { useRouter, useSearchParams } from 'next/navigation';
import { Claim } from '@shared/types';
import { BackToOverview } from '@/components/evidence-views/detail/BackToOverview';
import { ClaimHeader } from '@/components/evidence-views/detail/ClaimHeader';
import { ViewSelector } from '@/components/evidence-views';
import { CartographerView } from '@/components/evidence-views/cartographer';
import { LibrarianView } from '@/components/evidence-views/librarian';
import { InterpreterView } from '@/components/evidence-views/interpreter';
import { ProjectionistView } from '@/components/evidence-views/projectionist';
import { ChronologistView } from '@/components/evidence-views/chronologist';
import { SeekerView } from '@/components/evidence-views/seeker';
import { useVideoRecommendations } from '@/hooks/use-video-recommendations';

interface ClaimDetailClientProps {
  checkId: string;
  claim: Claim;
  position: number;
}

export function ClaimDetailClient({ checkId, claim, position }: ClaimDetailClientProps) {
  const { getToken } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const [activeTab, setActiveTab] = useState(() => {
    const viewParam = searchParams?.get('view');
    const validViews = ['cartographer', 'librarian', 'interpreter', 'seeker', 'projectionist', 'chronologist'];
    return viewParam && validViews.includes(viewParam) ? viewParam : 'cartographer';
  });
  const [token, setToken] = useState<string | null>(null);

  useEffect(() => {
    getToken().then(setToken);
  }, [getToken]);

  // F07: Sync active tab to URL for shareability
  const handleTabChange = useCallback((tab: string) => {
    setActiveTab(tab);
    const url = new URL(window.location.href);
    if (tab !== 'cartographer') {
      url.searchParams.set('view', tab);
    } else {
      url.searchParams.delete('view');
    }
    window.history.replaceState({}, '', url.toString());
  }, []);

  const handleSwitchToLibrarian = useCallback(() => handleTabChange('librarian'), [handleTabChange]);
  const handleSwitchToInterpreter = useCallback(() => handleTabChange('interpreter'), [handleTabChange]);

  // G02: Refresh page data after element re-search completes
  const handleResearchComplete = useCallback(() => {
    router.refresh();
  }, [router]);

  // Video recommendations — only fetch when Projectionist tab is active
  const { videos: claimVideos, isLoading: videosLoading } = useVideoRecommendations(
    checkId,
    claim.id,
    token,
    activeTab === 'projectionist',
  );

  return (
    <div className="max-w-7xl mx-auto px-6 py-8 space-y-6">
      <BackToOverview checkId={checkId} />
      <ClaimHeader claim={claim} position={position} />
      <ViewSelector mode="detail" activeTab={activeTab} onTabChange={handleTabChange} />

      {/* View content */}
      {activeTab === 'cartographer' && (
        <CartographerView
          scope="claim"
          claims={[claim]}
          onSwitchToLibrarian={handleSwitchToLibrarian}
          onSwitchToInterpreter={handleSwitchToInterpreter}
        />
      )}
      {activeTab === 'librarian' && (
        <LibrarianView scope="claim" claims={[claim]} />
      )}
      {activeTab === 'interpreter' && (
        <InterpreterView claim={claim} />
      )}
      {activeTab === 'projectionist' && (
        <ProjectionistView
          scope="claim"
          claims={[claim]}
          videos={claimVideos}
          isLoading={videosLoading}
        />
      )}
      {activeTab === 'chronologist' && (
        <ChronologistView
          scope="claim"
          claims={[claim]}
          onSwitchToLibrarian={handleSwitchToLibrarian}
        />
      )}
      {activeTab === 'seeker' && (
        <SeekerView
          claim={claim}
          checkId={checkId}
          token={token}
          onResearchComplete={handleResearchComplete}
        />
      )}
    </div>
  );
}
