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
    return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
  } catch {
    return dateStr;
  }
}

interface LedgerCardProps {
  evidence: Evidence;
  elementIds?: string[];
  claimLabel?: string;
  diagnosticValue?: number;
  diagnosticActive?: boolean;
  onClick?: () => void;
}

export function LedgerCard({ evidence, elementIds, claimLabel, diagnosticValue, diagnosticActive, onClick }: LedgerCardProps) {
  const domain = extractDomain(evidence.url);
  const date = formatDate(evidence.publishedDate);
  const excerpt = evidence.snippet
    ? evidence.snippet.length > 120
      ? `"${evidence.snippet.slice(0, 120)}..."`
      : `"${evidence.snippet}"`
    : null;

  const isHighDiag = diagnosticActive && diagnosticValue != null && diagnosticValue > 0.7;
  const isLowDiag = diagnosticActive && diagnosticValue != null && diagnosticValue < 0.3;

  return (
    <div
      className={`border transition-colors cursor-pointer p-4 ${
        isLowDiag ? 'border-zinc-100 opacity-40' : isHighDiag ? 'border-zinc-100 hover:border-zinc-300' : 'border-zinc-100 hover:border-zinc-300'
      }`}
      style={isHighDiag ? { borderLeft: '4px solid var(--accent)' } : undefined}
      onClick={onClick}
    >
      <div className="flex items-start gap-3">
        <div className="flex flex-col gap-1.5 pt-0.5 shrink-0">
          {evidence.tier && <TierBadge tier={evidence.tier} />}
          {evidence.evidenceType && <TypeBadge type={evidence.evidenceType} />}
        </div>
        <div className="flex-grow min-w-0">
          <div className="text-sm font-medium text-zinc-900 mb-1">
            {evidence.title || 'Untitled source'}
          </div>
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mb-2">
            <span className="font-mono text-[10px] text-zinc-400">{domain}</span>
            {date && (
              <>
                <span className="font-mono text-[10px] text-zinc-300">&middot;</span>
                <span className="font-mono text-[10px] text-zinc-400">{date}</span>
              </>
            )}
            {elementIds && elementIds.length > 0 && (
              <>
                <span className="font-mono text-[10px] text-zinc-300">&middot;</span>
                <span className="font-mono text-[10px] text-zinc-400">
                  Elements: {elementIds.map(id => id.replace('e', '')).join(', ')}
                </span>
              </>
            )}
            {claimLabel && (
              <>
                <span className="font-mono text-[10px] text-zinc-300">&middot;</span>
                <span className="font-mono text-[10px] text-zinc-400">{claimLabel}</span>
              </>
            )}
            {evidence.archivedUrl && (
              <>
                <span className="font-mono text-[10px] text-zinc-300">&middot;</span>
                <a
                  href={evidence.archivedUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="font-mono text-[9px] text-zinc-400 hover:text-zinc-600 transition-colors"
                  onClick={(e) => e.stopPropagation()}
                >
                  ARCHIVED
                </a>
              </>
            )}
          </div>
          {excerpt && (
            <p className="text-[12px] text-zinc-500 italic leading-relaxed">{excerpt}</p>
          )}
        </div>
      </div>
    </div>
  );
}
