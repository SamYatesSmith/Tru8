'use client';

import { EvidenceTier } from '@shared/types';
import { ConcentrationBar } from './ConcentrationBar';

interface DomainSegment {
  name: string;
  count: number;
  tier: EvidenceTier;
}

interface CorrespondentSummaryProps {
  uniqueDomains: number;
  totalEvidence: number;
  primaryDomains: number;
  reportingDomains: number;
  commentaryDomains: number;
  domains: DomainSegment[];
}

export function CorrespondentSummary({
  uniqueDomains,
  totalEvidence,
  primaryDomains,
  reportingDomains,
  commentaryDomains,
  domains,
}: CorrespondentSummaryProps) {
  return (
    <div className="border border-zinc-200 bg-[var(--surface-raised)] p-5 mb-8">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="flex flex-col items-center gap-1">
          <span className="font-mono text-[9px] uppercase tracking-widest text-zinc-400">Unique Domains</span>
          <span className="font-mono text-2xl font-semibold text-zinc-900">{uniqueDomains}</span>
        </div>
        <div className="flex flex-col items-center gap-1">
          <span className="font-mono text-[9px] uppercase tracking-widest text-zinc-400">Total Evidence</span>
          <span className="font-mono text-2xl font-semibold text-zinc-900">{totalEvidence}</span>
        </div>
        <div className="flex flex-col items-center gap-1">
          <span className="font-mono text-[9px] uppercase tracking-widest text-zinc-400">Primary</span>
          <span className="font-mono text-2xl font-semibold" style={{ color: '#EA580C' }}>{primaryDomains}</span>
        </div>
        <div className="flex flex-col items-center gap-1">
          <span className="font-mono text-[9px] uppercase tracking-widest text-zinc-400">Reporting + Commentary</span>
          <span className="font-mono text-2xl font-semibold text-zinc-700">{reportingDomains + commentaryDomains}</span>
        </div>
      </div>
      <div className="mt-4">
        <ConcentrationBar domains={domains} />
      </div>
    </div>
  );
}
