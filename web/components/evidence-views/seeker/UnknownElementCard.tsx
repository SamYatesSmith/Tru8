'use client';

import { ClaimElement, Evidence } from '@shared/types';
import { ElementStateBadge } from '@/components/claim-map/element-state-badge';
import { EvidenceRefChip } from '@/components/claim-map/evidence-ref-chip';
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
}

export function UnknownElementCard({
  element,
  index,
  evidence,
  readOnly,
  checkId,
  claimId,
  token,
}: UnknownElementCardProps) {
  const isKnown = element.state === 'supported' || element.state === 'disputed';
  const isGap = !element.evidenceRefs || element.evidenceRefs.length === 0;
  const refCount = element.evidenceRefs?.length || 0;
  const label = String(index + 1).padStart(2, '0');

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
        <GapHighlight />
      ) : (
        <p className="font-mono text-[10px] text-zinc-400 mb-3">
          {refCount} {refCount === 1 ? 'source' : 'sources'} mapped
        </p>
      )}

      {/* Evidence ref chips */}
      {refCount > 0 && (
        <div className="flex flex-wrap gap-1.5 mb-3">
          {element.evidenceRefs.map((ref) => (
            <EvidenceRefChip
              key={ref.evidenceId}
              evidenceId={ref.evidenceId}
              relationship={ref.relationship}
            />
          ))}
        </div>
      )}

      {/* Uncertainty note */}
      {element.uncertainty && (
        <div className="border-l-2 border-amber-400 bg-amber-50/50 px-3 py-2 mb-3">
          <p className="text-[11px] text-amber-700 leading-relaxed">{element.uncertainty}</p>
        </div>
      )}

      {/* Bounty field */}
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
