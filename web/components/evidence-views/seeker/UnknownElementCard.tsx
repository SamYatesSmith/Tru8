'use client';

import { useMemo } from 'react';
import { ClaimElement, Evidence } from '@shared/types';
import { ElementStateBadge } from '@/components/claim-map/element-state-badge';
import { ElementBadge } from '../ElementBadge';
import { GapHighlight } from './GapHighlight';
import { BountyField } from './BountyField';
import { cleanTitle } from '../shared-utils';

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

// Neutral — stance is conveyed by the word, never by a verdict colour
// (no green/red/amber on supports/challenges). No-verdict lock.
const RELATIONSHIP_LABELS: Record<string, string> = {
  supports: 'supports',
  challenges: 'challenges',
  context: 'context',
};


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

  // Build evidence lookup by ID for title display
  const evidenceById = useMemo(() => {
    const map = new Map<string, Evidence>();
    for (const ev of evidence) {
      map.set(ev.id, ev);
    }
    return map;
  }, [evidence]);

  // Known elements: collapsed single line
  // Order: number → description → state badge → source count.
  // Content leads, qualifier trails (marketing review).
  if (isKnown) {
    return (
      <div className="flex items-center gap-3 px-4 py-2.5 bg-zinc-50/50 border border-zinc-100">
        <ElementBadge n={index + 1} size="sm" />
        <span className="text-sm text-zinc-700 truncate flex-grow min-w-0">{element.description}</span>
        {element.state && <ElementStateBadge state={element.state} size="sm" basis={element.basis} />}
        <span className="font-mono text-[10px] text-zinc-400 whitespace-nowrap">
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
        <ElementBadge n={index + 1} size="md" />
        {element.state && <ElementStateBadge state={element.state} size="md" basis={element.basis} />}
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
            return (
              <span
                key={ref.evidenceId}
                className="inline-flex max-w-full items-center gap-1.5 border border-zinc-200 bg-white px-2 py-0.5 text-[10px]"
              >
                <span className="shrink-0 font-mono lowercase text-zinc-600">
                  {RELATIONSHIP_LABELS[ref.relationship] || ref.relationship}
                </span>
                <span className="shrink-0 text-zinc-300">·</span>
                {/* Let the chip breathe with the viewport rather than cutting
                    at a fixed character count — a 40-char slice showed the same
                    stub on a 1440px desktop as on a phone. CSS truncates only
                    when it actually has to, and the full title stays reachable
                    on hover. */}
                <span
                  className="truncate text-zinc-500 max-w-[14rem] sm:max-w-[22rem] lg:max-w-[34rem]"
                  title={cleanTitle(title) || title}
                >
                  {cleanTitle(title) || title}
                </span>
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
