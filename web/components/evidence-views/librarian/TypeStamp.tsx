'use client';

import { EvidenceType } from '@shared/types';

const TYPE_LABELS: Record<EvidenceType, string> = {
  data: 'Data',
  official_statement: 'Official',
  news_reporting: 'News',
  analysis: 'Analysis',
  opinion: 'Opinion',
  academic: 'Academic',
};

interface TypeStampProps {
  type: EvidenceType;
}

export function TypeStamp({ type }: TypeStampProps) {
  return (
    <span
      className="inline-block font-mono text-[9px] font-bold uppercase tracking-wider px-1.5 py-0.5 rotate-1 border border-zinc-300 text-zinc-500 bg-white"
      style={{ outline: '1px solid #d4d4d8', outlineOffset: '1px' }}
    >
      {TYPE_LABELS[type]}
    </span>
  );
}
