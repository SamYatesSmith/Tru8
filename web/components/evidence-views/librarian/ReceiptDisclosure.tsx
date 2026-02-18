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

interface ReceiptDisclosureProps {
  excludedEvidence: Evidence[];
}

export function ReceiptDisclosure({ excludedEvidence }: ReceiptDisclosureProps) {
  const [isOpen, setIsOpen] = useState(false);

  if (excludedEvidence.length === 0) return null;

  return (
    <div className="border border-zinc-100 mb-16">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-zinc-50 transition-colors"
      >
        <span className="font-mono text-[10px] uppercase tracking-widest text-zinc-400">
          What we didn&apos;t include ({excludedEvidence.length} {excludedEvidence.length === 1 ? 'item' : 'items'})
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
    </div>
  );
}
