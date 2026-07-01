'use client';

import { Evidence, EvidenceRelationship } from '@shared/types';
import { TypeStamp } from './TypeStamp';
import { ElementRefs } from '../ElementRefs';
import { FactCheckRating } from '../FactCheckRating';
import { getFaviconUrl, cleanTitle } from '../shared-utils';

// Disposition labels — an organising axis (how the source relates to the
// claim), never an argument. Colour-restrained on purpose (no traffic light).
const RELATIONSHIP_LABELS: Record<EvidenceRelationship, string> = {
  supports: 'supports',
  challenges: 'challenges',
  context: 'context',
};

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
  /** Distinct dispositions of this source toward the claim (Slice 0b). */
  relationships?: EvidenceRelationship[];
  /** elementId → description, so element refs read as meaning, not "E01". */
  elementDescriptions?: Map<string, string>;
  diagnosticValue?: number;
  diagnosticActive?: boolean;
  isActive?: boolean;
  onClick?: () => void;
}

export function LedgerCard({ evidence, callNumber, elementIds, claimLabel, relationships, elementDescriptions, diagnosticValue, diagnosticActive, isActive, onClick }: LedgerCardProps) {
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
            {cleanTitle(evidence.title) || 'Untitled source'}
          </div>
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
            <span className="inline-flex items-center gap-1 font-mono text-[10px] text-zinc-500">
              <img
                src={getFaviconUrl(evidence.url)}
                alt=""
                width={12}
                height={12}
                loading="lazy"
                className="w-3 h-3 shrink-0 rounded-sm"
                onError={(e) => { e.currentTarget.style.visibility = 'hidden'; }}
              />
              {domain}
            </span>
            {date && (
              <>
                <span className="font-mono text-[10px] text-zinc-300">&middot;</span>
                <span className="font-mono text-[10px] text-zinc-400">{date}</span>
              </>
            )}
            {elementIds && elementIds.length > 0 && (
              <>
                <span className="font-mono text-[10px] text-zinc-300">&middot;</span>
                <ElementRefs elementIds={elementIds} descriptions={elementDescriptions} />
              </>
            )}
            {relationships && relationships.length > 0 && (
              <>
                <span className="font-mono text-[10px] text-zinc-300">&middot;</span>
                <span className="font-mono text-[10px] italic text-zinc-500">
                  {relationships.map((r) => RELATIONSHIP_LABELS[r]).join(' / ')}
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
          <FactCheckRating evidence={evidence} />
        </div>
      </div>
    </div>
  );
}
