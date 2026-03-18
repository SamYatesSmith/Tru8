'use client';

import { EvidenceTier } from '@shared/types';
import { TierStamp } from '../librarian/TierStamp';

const TIER_BORDER_COLOURS: Record<EvidenceTier, string> = {
  primary: '#EA580C',
  reporting: '#3F3F46',
  commentary: '#A1A1AA',
};

interface SourceCardProps {
  domain: string;
  faviconUrl: string;
  tier: EvidenceTier;
  evidenceCount: number;
  evidenceTitles: string[];
  claimCoverage: string;
  elementCoverage: string;
  dateRange: string;
  soleSourceFor: string[];
  isExpanded: boolean;
  onClick: () => void;
  scope: 'check' | 'claim';
}

export function SourceCard({
  domain,
  faviconUrl,
  tier,
  evidenceCount,
  evidenceTitles,
  claimCoverage,
  elementCoverage,
  dateRange,
  soleSourceFor,
  isExpanded,
  onClick,
  scope,
}: SourceCardProps) {
  const borderColour = TIER_BORDER_COLOURS[tier];
  const coverageText = scope === 'check' ? claimCoverage : elementCoverage;
  const fallbackLetter = domain[0]?.toUpperCase() || '?';

  return (
    <button
      onClick={onClick}
      className={`w-full text-left border p-4 transition-colors ${
        isExpanded
          ? 'border-zinc-300 bg-[#FAFAF8]'
          : 'border-zinc-100 hover:border-zinc-300'
      }`}
    >
      {/* Row 1: Favicon + domain + tier */}
      <div className="flex items-center gap-3">
        <div
          className="w-8 h-8 rounded-full border-2 flex items-center justify-center overflow-hidden shrink-0 bg-white"
          style={{ borderColor: borderColour }}
        >
          <span className="absolute font-mono font-semibold text-zinc-300 text-[11px]">
            {fallbackLetter}
          </span>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={faviconUrl}
            alt=""
            className="w-full h-full object-cover relative z-10"
            onError={(e) => {
              (e.target as HTMLImageElement).style.display = 'none';
            }}
          />
        </div>
        <span className="text-sm font-medium text-zinc-900 flex-1">{domain}</span>
        <TierStamp tier={tier} />
      </div>

      {/* Row 2: Count + date range */}
      <div className="flex items-center gap-3 mt-2">
        <span className="font-mono text-[10px] text-zinc-400">
          {evidenceCount} {evidenceCount === 1 ? 'piece of evidence' : 'pieces of evidence'}
        </span>
        {dateRange && (
          <>
            <span className="text-zinc-200">&middot;</span>
            <span className="font-mono text-[10px] text-zinc-400">{dateRange}</span>
          </>
        )}
      </div>

      {/* Row 3: Coverage */}
      {coverageText && (
        <div className="mt-1.5">
          <span className="font-mono text-[10px] text-zinc-400">{coverageText}</span>
        </div>
      )}

      {/* Row 4: Sole source warnings */}
      {soleSourceFor.length > 0 && (
        <div className="mt-2">
          {soleSourceFor.map((label) => (
            <div
              key={label}
              className="font-mono text-[9px] text-zinc-400 border-b border-dashed border-zinc-300 pb-0.5 mb-0.5"
            >
              Sole source for {label}
            </div>
          ))}
        </div>
      )}

      {/* Expanded: individual evidence titles */}
      {isExpanded && evidenceTitles.length > 0 && (
        <div className="border-t border-zinc-100 mt-3 pt-3">
          {evidenceTitles.map((title, i) => (
            <div key={i} className="text-[11px] text-zinc-500 mb-1">
              {title}
            </div>
          ))}
        </div>
      )}
    </button>
  );
}
