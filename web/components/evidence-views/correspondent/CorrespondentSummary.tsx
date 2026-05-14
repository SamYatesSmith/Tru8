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
      {/* Domain counts — unit-consistent (all four are domain counts) */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="flex flex-col items-center gap-1">
          <span className="font-mono text-[9px] uppercase tracking-widest text-zinc-400">Unique Domains</span>
          <span className="font-mono text-2xl font-semibold text-zinc-900">{uniqueDomains}</span>
        </div>
        <div className="flex flex-col items-center gap-1">
          <span className="font-mono text-[9px] uppercase tracking-widest text-zinc-400">Primary</span>
          <span className="font-mono text-2xl font-semibold" style={{ color: '#EA580C' }}>{primaryDomains}</span>
        </div>
        <div className="flex flex-col items-center gap-1">
          <span className="font-mono text-[9px] uppercase tracking-widest text-zinc-400">Reporting</span>
          <span className="font-mono text-2xl font-semibold" style={{ color: '#3F3F46' }}>{reportingDomains}</span>
        </div>
        <div className="flex flex-col items-center gap-1">
          <span className="font-mono text-[9px] uppercase tracking-widest text-zinc-400">Commentary</span>
          <span className="font-mono text-2xl font-semibold" style={{ color: '#A1A1AA' }}>{commentaryDomains}</span>
        </div>
      </div>
      {/* Secondary metric — total pieces, deliberately understated to avoid the units-mixed footgun */}
      <p className="text-center font-mono text-[10px] uppercase tracking-widest text-zinc-400 mt-4">
        Across {totalEvidence} {totalEvidence === 1 ? 'piece' : 'pieces'} of evidence
      </p>
      <div className="mt-4">
        <ConcentrationBar domains={domains} />
      </div>
    </div>
  );
}
