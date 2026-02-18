'use client';

import { Evidence } from '@shared/types';
import { TierBadge } from '../TierBadge';
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

interface EvidenceGroupCardProps {
  evidence: Evidence;
  accentStyle?: string;
  onClick?: () => void;
}

export function EvidenceGroupCard({ evidence, accentStyle, onClick }: EvidenceGroupCardProps) {
  const domain = extractDomain(evidence.url);
  const date = formatDate(evidence.publishedDate);
  const excerpt = evidence.snippet
    ? evidence.snippet.length > 150
      ? `"${evidence.snippet.slice(0, 150)}..."`
      : `"${evidence.snippet}"`
    : null;

  return (
    <div
      className={`evidence-card border border-zinc-100 p-4 mb-3 cursor-pointer ${accentStyle || ''}`}
      onClick={onClick}
    >
      <div className="flex items-center gap-2 mb-2">
        {evidence.tier && <TierBadge tier={evidence.tier} />}
        {evidence.evidenceType && <TypeBadge type={evidence.evidenceType} />}
      </div>
      <div className="text-[13px] font-medium text-zinc-900 mb-1.5">
        {evidence.title || 'Untitled source'}
      </div>
      <div className="flex items-center gap-2 mb-2">
        <span className="font-mono text-[10px] text-zinc-400">{domain}</span>
        {date && (
          <>
            <span className="font-mono text-[10px] text-zinc-300">&middot;</span>
            <span className="font-mono text-[10px] text-zinc-400">{date}</span>
          </>
        )}
      </div>
      {excerpt && (
        <p className="text-[11px] text-zinc-500 italic leading-relaxed">{excerpt}</p>
      )}
    </div>
  );
}
