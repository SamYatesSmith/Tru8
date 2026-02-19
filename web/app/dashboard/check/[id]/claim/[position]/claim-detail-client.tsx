'use client';

import { useState, useCallback, useEffect } from 'react';
import { useAuth } from '@clerk/nextjs';
import { Claim } from '@shared/types';
import { BackToOverview } from '@/components/evidence-views/detail/BackToOverview';
import { ClaimHeader } from '@/components/evidence-views/detail/ClaimHeader';
import { ViewSelector } from '@/components/evidence-views';
import { CartographerView } from '@/components/evidence-views/cartographer';
import { LibrarianView } from '@/components/evidence-views/librarian';
import { InterpreterView } from '@/components/evidence-views/interpreter';
import { ProjectionistView } from '@/components/evidence-views/projectionist';
import { useVideoRecommendations } from '@/hooks/use-video-recommendations';

interface ClaimDetailClientProps {
  checkId: string;
  claim: Claim;
  position: number;
}

export function ClaimDetailClient({ checkId, claim, position }: ClaimDetailClientProps) {
  const { getToken } = useAuth();
  const [activeTab, setActiveTab] = useState('cartographer');
  const [token, setToken] = useState<string | null>(null);

  useEffect(() => {
    getToken().then(setToken);
  }, [getToken]);

  const handleSwitchToLibrarian = useCallback(() => setActiveTab('librarian'), []);
  const handleSwitchToInterpreter = useCallback(() => setActiveTab('interpreter'), []);

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
      <ViewSelector mode="detail" activeTab={activeTab} onTabChange={setActiveTab} />

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
    </div>
  );
}
