'use client';

import { useMemo } from 'react';
import { ClaimElement, Evidence } from '@shared/types';
import { ElementStateBadge } from '@/components/claim-map/element-state-badge';
import { GapHighlight } from './GapHighlight';
import { BountyField } from './BountyField';

interface UnknownElementCardProps {
  element: ClaimElement;
  index: number;
  evidence: Evidence[];
  readOnly?: boolean;
  checkId?: string;
  claimId?: string;
  token?: string | null;
  gapIndex?: number;
  totalGaps?: number;
}

const RELATIONSHIP_COLOURS: Record<string, string> = {
  supports: 'text-emerald-600',
  challenges: 'text-amber-600',
  context: 'text-zinc-400',
};

function truncateTitle(title: string, maxLen = 40): string {
  if (title.length <= maxLen) return title;
  return title.slice(0, maxLen) + '\u2026';
}

export function UnknownElementCard({
  element,
  index,
  evidence,
  readOnly,
  checkId,
  claimId,
  token,
  gapIndex,
  totalGaps,
}: UnknownElementCardProps) {
  // 2026-05-12: contextual elements have evidence in the pool; render
  // them in the collapsed (known) layout alongside supported/disputed.
  // They are not Seeker "unknowns" — direct substantiation may be
  // absent but context-tier sources are mapped.
  const isKnown = element.state === 'supported' || element.state === 'disputed' || element.state === 'contextual';
  const isGap = !element.evidenceRefs || element.evidenceRefs.length === 0;
  const refCount = element.evidenceRefs?.length || 0;
  const label = String(index + 1).padStart(2, '0');

  // Build evidence lookup by ID for title display
  const evidenceById = useMemo(() => {
    const map = new Map<string, Evidence>();
    for (const ev of evidence) {
      map.set(ev.id, ev);
    }
    return map;
  }, [evidence]);

  // Known elements: collapsed single line
  if (isKnown) {
    return (
      <div className="flex items-center gap-3 px-4 py-2.5 bg-zinc-50/50 border border-zinc-100">
        <span className="font-mono text-[10px] text-zinc-300 font-bold">{label}</span>
        {element.state && <ElementStateBadge state={element.state} size="sm" />}
        <span className="text-sm text-zinc-500 truncate">{element.description}</span>
        <span className="ml-auto font-mono text-[10px] text-zinc-300 whitespace-nowrap">
          {refCount} {refCount === 1 ? 'source' : 'sources'}
        </span>
      </div>
    );
  }

  // Unknown elements: expanded card
  return (
    <div
      className={`border-l-4 ${
        isGap ? 'border-l-zinc-300 border border-dashed border-zinc-300' : 'border-l-zinc-400 border border-zinc-200'
      } p-5`}
    >
      {/* Header */}
      <div className="flex items-center gap-3 mb-3">
        <span className="font-mono text-xs font-bold text-zinc-400">{label}</span>
        {element.state && <ElementStateBadge state={element.state} size="md" />}
      </div>

      {/* Description */}
      <p className="text-sm text-zinc-900 leading-relaxed mb-3">
        {element.description}
      </p>

      {/* Gap callout or evidence count */}
      {isGap ? (
        <GapHighlight gapIndex={gapIndex} totalGaps={totalGaps} />
      ) : (
        <p className="font-mono text-[10px] text-zinc-400 mb-3">
          {refCount} {refCount === 1 ? 'source' : 'sources'} mapped
        </p>
      )}

      {/* Evidence ref chips — show titles instead of opaque IDs */}
      {refCount > 0 && (
        <div className="flex flex-wrap gap-1.5 mb-3">
          {element.evidenceRefs.map((ref) => {
            const ev = evidenceById.get(ref.evidenceId);
            const title = ev?.title || ev?.url || ref.evidenceId;
            const relColour = RELATIONSHIP_COLOURS[ref.relationship] || 'text-zinc-400';
            return (
              <span
                key={ref.evidenceId}
                className="inline-flex items-center gap-1 border border-zinc-200 bg-white px-2 py-0.5 text-[10px]"
              >
                <span className={`font-mono uppercase font-bold ${relColour}`}>
                  {ref.relationship === 'supports' ? 'sup' : ref.relationship === 'challenges' ? 'chl' : 'ctx'}
                </span>
                <span className="text-zinc-500">{truncateTitle(title)}</span>
              </span>
            );
          })}
        </div>
      )}

      {/* Uncertainty note */}
      {/* Filter "null"/"none"/"n/a" string leakage from the mapper at the UI boundary */}
      {element.uncertainty && element.uncertainty.trim() && !['null', 'none', 'n/a'].includes(element.uncertainty.trim().toLowerCase()) && (
        <div className="border-l-2 border-amber-400 bg-amber-50/50 px-3 py-2 mb-3">
          <p className="text-[11px] text-amber-700 leading-relaxed">{element.uncertainty}</p>
        </div>
      )}

      {/* Bounty field — research brief for optional query refinement */}
      <BountyField
        elementId={element.elementId}
        initialText={element.bountyText || ''}
        readOnly={readOnly}
        checkId={checkId}
        claimId={claimId}
        token={token}
      />
    </div>
  );
}
