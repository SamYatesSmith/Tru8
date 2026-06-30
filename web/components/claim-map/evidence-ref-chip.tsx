'use client';

import type { EvidenceRelationship } from '@shared/types';

interface EvidenceRefChipProps {
  evidenceId: string;
  relationship: EvidenceRelationship;
  onClick?: () => void;
}

// Neutral — stance by word, never verdict colour (no-verdict lock).
const RELATIONSHIP_CLASSES: Record<EvidenceRelationship, string> = {
  supports: 'text-zinc-600',
  challenges: 'text-zinc-600',
  context: 'text-zinc-400',
};

export function EvidenceRefChip({ evidenceId, relationship, onClick }: EvidenceRefChipProps) {
  const shortId = evidenceId.slice(0, 8);
  const baseClasses =
    'bg-white border border-zinc-200 px-3 py-1 text-[10px] font-mono text-zinc-500 inline-flex items-center gap-1 rounded';
  const interactiveClasses = onClick ? 'hover:bg-zinc-50 cursor-pointer' : '';

  const content = (
    <>
      <span className={RELATIONSHIP_CLASSES[relationship]}>{relationship}</span>
      <span>{shortId}</span>
    </>
  );

  if (onClick) {
    return (
      <button type="button" onClick={onClick} className={`${baseClasses} ${interactiveClasses}`}>
        {content}
      </button>
    );
  }

  return <span className={baseClasses}>{content}</span>;
}
