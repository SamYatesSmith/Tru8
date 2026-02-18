'use client';

import { useState } from 'react';
import { Claim } from '@shared/types';
import { BackToOverview } from '@/components/evidence-views/detail/BackToOverview';
import { ClaimHeader } from '@/components/evidence-views/detail/ClaimHeader';
import { ViewSelector } from '@/components/evidence-views';

interface ClaimDetailClientProps {
  checkId: string;
  claim: Claim;
  position: number;
}

export function ClaimDetailClient({ checkId, claim, position }: ClaimDetailClientProps) {
  const [activeTab, setActiveTab] = useState('cartographer');

  return (
    <div className="max-w-7xl mx-auto px-6 py-8 space-y-6">
      <BackToOverview checkId={checkId} />
      <ClaimHeader claim={claim} position={position} />
      <ViewSelector mode="detail" activeTab={activeTab} onTabChange={setActiveTab} />

      {/* View content placeholder — actual views delivered in E10-E12 */}
      <div className="py-12 text-center border border-dashed border-zinc-200 bg-zinc-50/30">
        <p className="font-mono text-[11px] uppercase tracking-widest text-zinc-400">
          {activeTab} view — coming in E10-E12
        </p>
      </div>
    </div>
  );
}
