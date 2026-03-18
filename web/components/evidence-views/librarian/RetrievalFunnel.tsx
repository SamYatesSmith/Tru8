'use client';

import { useState } from 'react';
import { Evidence } from '@shared/types';

function extractDomain(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, '');
  } catch {
    return url;
  }
}

function getExclusionReason(ev: Evidence): { badge: string; explanation: string } {
  if (ev.receiptStatus === 'excluded') {
    if (ev.sourceType === 'duplicate' || ev.corroborationGroupId) {
      return { badge: 'Duplicate', explanation: 'Identical or near-identical content to another source' };
    }
    if (ev.sourceType === 'satire') {
      return { badge: 'Satire', explanation: 'Intentionally fictional source' };
    }
    if (!ev.snippet || ev.snippet.length < 20) {
      return { badge: 'Extraction Failed', explanation: 'Page returned no readable text (paywall or blocked)' };
    }
    return { badge: 'Excluded', explanation: 'Did not meet inclusion criteria' };
  }
  return { badge: 'Excluded', explanation: '' };
}

interface RetrievalFunnelProps {
  reviewedCount: number;
  includedCount: number;
  excludedEvidence: Evidence[];
}

export function RetrievalFunnel({ reviewedCount, includedCount, excludedEvidence }: RetrievalFunnelProps) {
  const [isOpen, setIsOpen] = useState(false);
  const excludedCount = excludedEvidence.length;

  if (excludedCount === 0 && !reviewedCount) return null;

  const showReviewed = reviewedCount > 0;
  const total = includedCount + excludedCount;

  // Group excluded by reason
  const reasonGroups = new Map<string, number>();
  for (const ev of excludedEvidence) {
    const { badge } = getExclusionReason(ev);
    reasonGroups.set(badge, (reasonGroups.get(badge) || 0) + 1);
  }

  return (
    <div className="border border-zinc-100 mb-16">
      {/* Header */}
      <div className="px-4 py-3">
        <div className="font-mono text-sm font-bold uppercase tracking-[0.3em] text-zinc-600 border-b border-zinc-200 pb-2 mb-3">
          Retrieval Transparency
        </div>

        {/* Summary line */}
        <div className="font-mono text-[11px] text-zinc-500 mb-3">
          {showReviewed && <span>Examined {reviewedCount} &middot; </span>}
          Organised {includedCount} &middot; Excluded {excludedCount}
        </div>

        {/* Proportional bar */}
        {total > 0 && (
          <div className="h-2 flex overflow-hidden border border-zinc-200 mb-3">
            <div
              className="bg-zinc-900"
              style={{ width: `${(includedCount / total) * 100}%` }}
            />
            <div
              className="bg-zinc-200"
              style={{ width: `${(excludedCount / total) * 100}%` }}
            />
          </div>
        )}

        {/* Exclusion reason pills */}
        {reasonGroups.size > 0 && (
          <div className="flex flex-wrap gap-2 mb-2">
            {Array.from(reasonGroups.entries()).map(([reason, count]) => (
              <span
                key={reason}
                className="px-2 py-0.5 bg-zinc-100 text-zinc-500 text-[9px] font-mono font-bold uppercase tracking-wider"
              >
                {reason} ({count})
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Collapsible detail */}
      {excludedCount > 0 && (
        <>
          <button
            onClick={() => setIsOpen(!isOpen)}
            className="w-full flex items-center justify-between px-4 py-2 border-t border-zinc-100 hover:bg-zinc-50 transition-colors"
          >
            <span className="font-mono text-[10px] uppercase tracking-widest text-zinc-400">
              Show excluded items
            </span>
            <span className="text-zinc-300 text-sm">{isOpen ? '\u2191' : '\u2193'}</span>
          </button>

          {isOpen && (
            <div className="border-t border-zinc-100 px-4 py-3 space-y-2">
              {excludedEvidence.map((ev) => {
                const { badge, explanation } = getExclusionReason(ev);
                const domain = extractDomain(ev.url);

                return (
                  <div key={ev.id} className="flex items-center gap-4">
                    <span className="px-2 py-0.5 bg-zinc-100 text-zinc-500 text-[9px] font-mono font-bold uppercase tracking-wider shrink-0">
                      {badge}
                    </span>
                    <span className="font-mono text-[11px] text-zinc-500">{domain}</span>
                    <span className="text-[11px] text-zinc-400">{explanation}</span>
                  </div>
                );
              })}
            </div>
          )}
        </>
      )}
    </div>
  );
}
