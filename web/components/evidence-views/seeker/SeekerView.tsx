'use client';

import { useMemo } from 'react';
import { Claim } from '@shared/types';
import { UnknownsSummaryStrip } from './UnknownsSummaryStrip';
import { UnknownElementCard } from './UnknownElementCard';
import { CoverageMap } from './CoverageMap';
import { SeekerProvenanceNote } from './SeekerProvenanceNote';

interface SeekerViewProps {
  claim: Claim;
  readOnly?: boolean;
  checkId?: string;
  token?: string | null;
}

export function SeekerView({ claim, readOnly, checkId, token }: SeekerViewProps) {
  const elements = useMemo(() => claim.claimMap?.elements || [], [claim.claimMap?.elements]);
  const evidence = useMemo(() => claim.evidence || [], [claim.evidence]);

  const metrics = useMemo(() => {
    let supported = 0;
    let disputed = 0;
    let unresolved = 0;
    let gaps = 0;

    for (const el of elements) {
      if (el.state === 'supported') supported++;
      else if (el.state === 'disputed') disputed++;
      else unresolved++;

      if (!el.evidenceRefs || el.evidenceRefs.length === 0) gaps++;
    }

    const withEvidence = elements.filter(el => el.evidenceRefs && el.evidenceRefs.length > 0).length;
    const coverage = elements.length > 0 ? Math.round((withEvidence / elements.length) * 100) : 0;

    return { total: elements.length, supported, disputed, unresolved, gaps, coverage };
  }, [elements]);

  if (elements.length === 0) {
    return (
      <div className="py-12 text-center border border-dashed border-zinc-200 bg-zinc-50/30">
        <p className="font-mono text-[11px] uppercase tracking-widest text-zinc-400">
          No elements available for this claim
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <UnknownsSummaryStrip {...metrics} />
      <CoverageMap elements={elements} />

      <div className="space-y-3">
        {elements.map((element, index) => (
          <UnknownElementCard
            key={element.elementId}
            element={element}
            index={index}
            evidence={evidence}
            readOnly={readOnly}
            checkId={checkId}
            claimId={claim.id}
            token={token}
          />
        ))}
      </div>

      <SeekerProvenanceNote />
    </div>
  );
}
