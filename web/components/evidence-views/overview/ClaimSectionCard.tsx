'use client';

import { Claim, EvidenceTier, InputType } from '@shared/types';
import { ElementStateBadge, ElementStateKey } from '../ElementStateBadge';
import { isOrientationSuppressed } from '@/lib/orientation';

const TYPE_LABELS: Record<string, string> = {
  empirical: 'Empirical',
  definitional: 'Definitional',
  causal_interpretive: 'Causal',
  predictive: 'Predictive',
  normative_flagged: 'Normative',
};


interface ClaimSectionCardProps {
  claim: Claim;
  position: number;
  onExplore: (position: number) => void;
  inputType?: InputType;
}

export function ClaimSectionCard({ claim, position, onExplore, inputType }: ClaimSectionCardProps) {
  const claimMap = claim.claimMap;
  const elements = claimMap?.elements || [];
  const evidence = claim.evidence || [];
  const orientation = claimMap?.orientation;
  const orientationSuppressed = isOrientationSuppressed(claimMap);
  const claimType = claimMap?.claimType || claim.claimType;
  const rankLabel = String(position + 1).padStart(2, '0');
  // C2 R1 (mirrors ClaimSummaryPanel): the provenance chip only where it
  // informs — URL checks EXTRACTED the claim; on text checks "Submitted
  // Claim" restates the obvious.
  const contextLabel = inputType === 'url' ? 'Extracted Claim' : null;

  // Count element states
  const stateCounts = { supported: 0, disputed: 0, unresolved: 0 };
  for (const el of elements) {
    const state = el.state || 'unresolved';
    if (state in stateCounts) stateCounts[state as keyof typeof stateCounts]++;
  }

  // Count evidence by tier
  const tierCounts: Record<string, number> = { primary: 0, reporting: 0, commentary: 0 };
  for (const ev of evidence) {
    const tier = (ev as any).tier as EvidenceTier | undefined;
    if (tier && tier in tierCounts) tierCounts[tier]++;
  }

  const isGap = evidence.length === 0;

  return (
    <div
      className={`border cursor-pointer transition-all duration-200 hover:scale-[1.01] hover:shadow-lg hover:border-zinc-300 hover:z-10 relative ${isGap ? 'border-dashed border-zinc-200 bg-zinc-50/30' : 'border-zinc-200 bg-white'}`}
      onClick={() => onExplore(position)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => { if (e.key === 'Enter') onExplore(position); }}
    >
      {/* Claim header */}
      <div className="p-5 pb-4">
        <div className="flex items-start justify-between mb-2">
          <div className="flex items-center gap-3">
            <span className="font-mono text-xs font-bold text-zinc-300">{rankLabel}</span>
            {contextLabel && (
              <span className="px-2.5 py-0.5 bg-zinc-50 border border-zinc-200 text-[9px] font-mono font-bold uppercase tracking-wider text-zinc-500">
                {contextLabel}
              </span>
            )}
            {claimType && (
              <span className="px-2.5 py-0.5 bg-zinc-50 border border-zinc-200 text-[9px] font-mono font-bold uppercase tracking-wider text-zinc-500">
                {TYPE_LABELS[claimType] || claimType}
              </span>
            )}
          </div>
          <div className="flex items-center gap-3 font-mono text-[10px] text-zinc-500">
            <span>{elements.length} elements</span>
            <span className="text-zinc-200">&middot;</span>
            <span>{evidence.length} sources</span>
          </div>
        </div>
        <h3 className={`text-[15px] font-medium leading-relaxed ${isGap ? 'text-zinc-400' : 'text-zinc-900'}`}>
          {claim.text}
        </h3>
      </div>

      {/* Tier strip */}
      {evidence.length > 0 && (
        <div className="px-5 pb-3 flex items-center gap-5 font-mono text-[12px] font-semibold uppercase tracking-[0.15em]">
          {tierCounts.primary > 0 && (
            <span className="text-zinc-700">{tierCounts.primary} Primary</span>
          )}
          {tierCounts.reporting > 0 && (
            <span className="text-zinc-500">{tierCounts.reporting} Reporting</span>
          )}
          {tierCounts.commentary > 0 && (
            <span className="text-zinc-400">{tierCounts.commentary} Commentary</span>
          )}
        </div>
      )}

      {/* Compact element roster */}
      {elements.length > 0 && (
        <div className="border-t border-zinc-100 px-5 py-3 space-y-1.5">
          {elements.map((element, i) => {
            const sourceCount = element.evidenceRefs?.length || 0;
            const state = (element.state || 'unresolved') as ElementStateKey;
            const elIsGap = sourceCount === 0;

            return (
              <div key={element.elementId} className="flex items-center gap-3 py-1">
                <span className="font-mono text-[10px] text-zinc-400 w-4 shrink-0">
                  {String(i + 1).padStart(2, '0')}
                </span>
                <span className={`text-[13px] flex-grow truncate ${elIsGap ? 'text-zinc-400' : 'text-zinc-700'}`}>
                  {element.description}
                </span>
                <span className={`font-mono text-[10px] shrink-0 ${elIsGap ? 'text-zinc-400' : 'text-zinc-500'}`}>
                  {sourceCount}
                </span>
                <ElementStateBadge
                  state={elIsGap ? 'unresolved' : state}
                  label={elIsGap ? 'Gap' : undefined}
                  basis={element.basis}
                />
              </div>
            );
          })}
        </div>
      )}

      {/* Orientation + arrow */}
      <div className="border-t border-zinc-100 px-5 py-4 flex items-end justify-between gap-4">
        {/* Suppressed (opinion claim) renders NOTHING — not the fallback copy.
            Summing question-shaped elements would read as a verdict on the
            opinion. Spacer keeps "Explore" right-aligned. */}
        {orientationSuppressed ? (
          <span className="flex-grow" />
        ) : (
          <p className={`text-[12px] leading-relaxed flex-grow ${isGap ? 'text-zinc-400' : 'text-zinc-500'}`}>
            {orientation || 'No orientation available.'}
          </p>
        )}
        <span className="font-mono text-[10px] uppercase tracking-widest text-zinc-400 shrink-0 flex items-center gap-1.5 transition-colors group-hover:text-zinc-900">
          Explore &rarr;
        </span>
      </div>
    </div>
  );
}
