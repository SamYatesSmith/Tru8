'use client';

type EvidenceType = 'data' | 'official_statement' | 'news_reporting' | 'analysis' | 'opinion' | 'academic';

interface TypeBadgeProps {
  type: EvidenceType;
}

const TYPE_LABELS: Record<EvidenceType, string> = {
  data: 'Data',
  official_statement: 'Official',
  news_reporting: 'News',
  analysis: 'Analysis',
  opinion: 'Opinion',
  academic: 'Academic',
};

export function TypeBadge({ type }: TypeBadgeProps) {
  return (
    <span className="px-2 py-0.5 border border-zinc-200 text-[9px] font-mono uppercase tracking-wider text-zinc-500">
      {TYPE_LABELS[type]}
    </span>
  );
}
