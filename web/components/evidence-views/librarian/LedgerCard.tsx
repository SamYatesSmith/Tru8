'use client';

import { Evidence } from '@shared/types';
import { TypeStamp } from './TypeStamp';
import { ElementRefs } from '../ElementRefs';

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
  callNumber?: string;
  elementIds?: string[];
  claimLabel?: string;
  diagnosticValue?: number;
  diagnosticActive?: boolean;
  isActive?: boolean;
  onClick?: () => void;
}

export function LedgerCard({ evidence, callNumber, elementIds, claimLabel, diagnosticValue, diagnosticActive, isActive, onClick }: LedgerCardProps) {
  const domain = extractDomain(evidence.url);
  const date = formatDate(evidence.publishedDate);

  const isHighDiag = diagnosticActive && diagnosticValue != null && diagnosticValue > 0.7;
  const isLowDiag = diagnosticActive && diagnosticValue != null && diagnosticValue < 0.3;

  return (
    <div
      className={`border transition-colors cursor-pointer p-4 ${
        isActive
          ? 'border-zinc-300 bg-[#FAFAF8]'
          : isLowDiag
            ? 'border-zinc-100 opacity-40'
            : 'border-zinc-100 hover:border-zinc-300'
      }`}
      style={isHighDiag ? { borderLeft: '4px solid var(--accent)' } : undefined}
      onClick={onClick}
    >
      {/* Call number */}
      {callNumber && (
        <div className="font-mono text-[10px] text-zinc-400 tracking-widest mb-2">{callNumber}</div>
      )}

      <div className="flex items-start gap-3">
        <div className="flex flex-col gap-1.5 pt-0.5 shrink-0">
          {evidence.evidenceType && <TypeStamp type={evidence.evidenceType} />}
        </div>
        <div className="flex-grow min-w-0">
          <div className="text-sm font-medium text-zinc-900 mb-1">
            {evidence.title || 'Untitled source'}
          </div>
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
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
                <ElementRefs elementIds={elementIds} />
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
        </div>
      </div>
    </div>
  );
}
