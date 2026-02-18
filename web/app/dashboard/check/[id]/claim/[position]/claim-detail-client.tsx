'use client';

import { useState, useCallback } from 'react';
import { Claim } from '@shared/types';
import { BackToOverview } from '@/components/evidence-views/detail/BackToOverview';
import { ClaimHeader } from '@/components/evidence-views/detail/ClaimHeader';
import { ViewSelector } from '@/components/evidence-views';
import { CartographerView } from '@/components/evidence-views/cartographer';
import { LibrarianView } from '@/components/evidence-views/librarian';
import { InterpreterView } from '@/components/evidence-views/interpreter';

interface ClaimDetailClientProps {
  checkId: string;
  claim: Claim;
  position: number;
}

export function ClaimDetailClient({ checkId, claim, position }: ClaimDetailClientProps) {
  const [activeTab, setActiveTab] = useState('cartographer');

  const handleSwitchToLibrarian = useCallback(() => setActiveTab('librarian'), []);
  const handleSwitchToInterpreter = useCallback(() => setActiveTab('interpreter'), []);

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
      {activeTab !== 'cartographer' && activeTab !== 'librarian' && activeTab !== 'interpreter' && (
        <div className="py-12 text-center border border-dashed border-zinc-200 bg-zinc-50/30">
          <p className="font-mono text-[11px] uppercase tracking-widest text-zinc-400">
            {activeTab} view — coming in E14-E15
          </p>
        </div>
      )}
    </div>
  );
}
