'use client';

import { Evidence, EvidenceTier } from '@shared/types';
import { TierStamp } from '../librarian/TierStamp';
import { TypeStamp } from '../librarian/TypeStamp';
import { DateHint } from '../DateHint';
import { extractDomain, formatDateStr, getFaviconUrl, cleanTitle } from '../shared-utils';

const TIER_BORDER_COLORS: Record<EvidenceTier, string> = {
  primary: '#EA580C',
  reporting: '#3F3F46',
  commentary: '#A1A1AA',
};

interface EvidenceDetailCardProps {
  evidence: Evidence;
  elementDescriptions: { elementId: string; description: string }[];
  onClose: () => void;
}

export function EvidenceDetailCard({ evidence, elementDescriptions, onClose }: EvidenceDetailCardProps) {
  const domain = extractDomain(evidence.url);
  const date = formatDateStr(evidence.publishedDate);
  const faviconUrl = getFaviconUrl(evidence.url);
  const tier = evidence.tier || 'commentary';
  const firstLetter = domain.charAt(0).toUpperCase();
  const snippet = evidence.snippet
    ? evidence.snippet.length > 120
      ? evidence.snippet.slice(0, 120) + '\u2026'
      : evidence.snippet
    : null;

  return (
    <div className="border border-zinc-200 bg-[#FAFAF8] p-5 relative mt-6">
      {/* Close button */}
      <button
        onClick={onClose}
        className="absolute top-3 right-3 font-mono text-[10px] text-zinc-400 hover:text-zinc-900 transition-colors"
      >
        Close &times;
      </button>

      {/* Header: favicon + domain */}
      <div className="flex items-center gap-3 mb-3">
        <div
          className="w-6 h-6 rounded-full border flex items-center justify-center overflow-hidden bg-white shrink-0 relative"
          style={{ borderColor: TIER_BORDER_COLORS[tier] }}
        >
          <span className="font-mono text-[9px] font-bold text-zinc-400">{firstLetter}</span>
          {faviconUrl && (
            <img
              src={faviconUrl}
              alt=""
              className="w-6 h-6 rounded-full absolute inset-0"
              onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
            />
          )}
        </div>
        <span className="font-mono text-[10px] text-zinc-500">{domain}</span>
      </div>

      {/* Title */}
      <p className="text-sm font-medium text-zinc-900 mb-1">
        {cleanTitle(evidence.title) || 'Untitled source'}
      </p>

      {/* Date */}
      {date && (
        <p className="font-mono text-[10px] text-zinc-400 mb-3">
          {date}
          <DateHint evidence={evidence} />
        </p>
      )}

      {/* Stamps */}
      <div className="flex items-center gap-2 mb-4">
        {evidence.tier && <TierStamp tier={evidence.tier} />}
        {evidence.evidenceType && <TypeStamp type={evidence.evidenceType} />}
      </div>

      {/* Snippet */}
      {snippet && (
        <p className="text-[11px] text-zinc-600 leading-relaxed mb-4">{snippet}</p>
      )}

      {/* Addressed elements */}
      {elementDescriptions.length > 0 && (
        <div className="mb-4">
          <div className="flex items-center gap-2 mb-2">
            <span className="flex-1 h-px bg-zinc-200" />
            <span className="font-mono text-[10px] uppercase tracking-[0.25em] font-bold text-zinc-400">
              Addresses
            </span>
            <span className="flex-1 h-px bg-zinc-200" />
          </div>
          <div className="space-y-1">
            {elementDescriptions.map(({ elementId, description }) => (
              <div key={elementId} className="font-mono text-[11px] text-zinc-600">
                <span className="text-zinc-400">Element {elementId.replace('e', '')}</span>
                {description && <span> &mdash; {description}</span>}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Links */}
      <div className="flex items-center gap-4">
        {evidence.url && (
          <a
            href={evidence.url}
            target="_blank"
            rel="noopener noreferrer"
            className="font-mono text-[10px] uppercase tracking-widest text-zinc-500 hover:text-zinc-900 transition-colors"
          >
            Visit source &rarr;
          </a>
        )}
        {evidence.archivedUrl && (
          <a
            href={evidence.archivedUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="font-mono text-[10px] uppercase tracking-widest text-zinc-500 hover:text-zinc-900 transition-colors"
          >
            Archive &rarr;
          </a>
        )}
      </div>
    </div>
  );
}
