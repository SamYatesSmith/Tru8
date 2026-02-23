'use client';

import { useState } from 'react';
import { Evidence, EvidenceTier } from '@shared/types';
import { TypeBadge } from '../TypeBadge';

function extractDomain(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, '');
  } catch {
    return url;
  }
}

function formatDate(dateStr?: string): string {
  if (!dateStr) return '';
  try {
    const d = new Date(dateStr);
    return d.toLocaleDateString('en-GB', { month: 'short', year: 'numeric' });
  } catch {
    return dateStr;
  }
}

const TIER_STYLES: Record<EvidenceTier, { border: string; fill: string; textSize: string; minWidth: string }> = {
  primary: {
    border: 'var(--tier1-accent)',
    fill: 'bg-white',
    textSize: 'text-sm font-semibold',
    minWidth: 'min-w-[220px]',
  },
  reporting: {
    border: 'var(--tier2-accent)',
    fill: 'bg-white',
    textSize: 'text-[13px] font-medium',
    minWidth: 'min-w-[180px]',
  },
  commentary: {
    border: 'var(--tier3-accent)',
    fill: 'bg-zinc-50/50',
    textSize: 'text-[12px]',
    minWidth: 'min-w-[170px]',
  },
};

interface CascadeNodeProps {
  evidence: Evidence;
  isDivergent?: boolean;
  showConnectionStub?: boolean;
  claimLabel?: string;
  diagnosticValue?: number;
  diagnosticActive?: boolean;
  onClick?: () => void;
}

export function CascadeNode({ evidence, isDivergent, showConnectionStub, claimLabel, diagnosticValue, diagnosticActive, onClick }: CascadeNodeProps) {
  const [isHovered, setIsHovered] = useState(false);
  const tier = evidence.tier || 'commentary';
  const style = TIER_STYLES[tier];
  const domain = extractDomain(evidence.url);
  const date = formatDate(evidence.publishedDate);

  // Diagnostic highlighting overrides
  const isHighDiag = diagnosticActive && diagnosticValue != null && diagnosticValue > 0.7;
  const isLowDiag = diagnosticActive && diagnosticValue != null && diagnosticValue < 0.3;

  return (
    <div
      className={`cascade-node relative border ${style.fill} px-4 py-3 ${style.minWidth} cursor-pointer ${
        isDivergent ? 'border-dashed border-amber-300 bg-amber-50/30' : isLowDiag ? 'border-zinc-100' : 'border-zinc-200'
      } ${isLowDiag ? 'opacity-40' : ''}`}
      style={{ borderLeft: isHighDiag ? '4px solid var(--accent)' : `3px solid ${isDivergent ? 'var(--divergence)' : style.border}` }}
      onClick={onClick}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {isDivergent && (
        <div className="flex items-center gap-1.5 mb-1">
          <div className="w-[6px] h-[6px] bg-[var(--divergence)] rotate-45" />
          <span className="font-mono text-[8px] uppercase tracking-widest text-amber-600 font-bold">Challenges</span>
        </div>
      )}

      {tier === 'primary' && evidence.evidenceType && (
        <div className="flex items-center gap-2 mb-2">
          <TypeBadge type={evidence.evidenceType} />
        </div>
      )}

      <div className={`${style.textSize} ${tier === 'commentary' ? 'text-zinc-600' : 'text-zinc-900'} mb-1`}>
        {evidence.title || 'Untitled source'}
      </div>

      <div className="font-mono text-[10px] text-zinc-400">
        {evidence.source || domain}
        {tier !== 'commentary' && evidence.evidenceType && ` \u00B7 ${evidence.evidenceType === 'news_reporting' ? 'News' : evidence.evidenceType === 'official_statement' ? 'Official' : evidence.evidenceType.charAt(0).toUpperCase() + evidence.evidenceType.slice(1)}`}
        {date && ` \u00B7 ${date}`}
      </div>

      {claimLabel && (
        <div className="font-mono text-[9px] text-zinc-300 mt-1">{claimLabel}</div>
      )}

      {/* Connection stub extending downward */}
      {showConnectionStub && (
        <div className="absolute -bottom-[2px] left-1/2 w-[1px] h-8 bg-zinc-300" />
      )}

      {/* Hover tooltip */}
      {isHovered && (
        <div className="absolute z-10 bottom-full left-1/2 -translate-x-1/2 mb-2 bg-zinc-900 text-white px-3 py-2 text-[10px] font-mono whitespace-nowrap pointer-events-none max-w-xs">
          <div className="truncate">{evidence.title}</div>
          {date && <div className="text-zinc-400">{date}</div>}
          {isLowDiag && (
            <div className="text-zinc-500 mt-1 whitespace-normal">
              This source supports all elements equally — it doesn&apos;t help distinguish between competing interpretations.
            </div>
          )}
        </div>
      )}
    </div>
  );
}
