'use client';

import { useEffect, useRef } from 'react';
import { Evidence, EvidenceTier, EvidenceRelationship } from '@shared/types';
import { TierStamp } from './TierStamp';
import { TypeStamp } from './TypeStamp';
import { FactCheckRating } from '../FactCheckRating';
import { DateHint } from '../DateHint';
import { cleanTitle, getFaviconUrl } from '../shared-utils';

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

const TIER_BORDER_COLORS: Record<EvidenceTier, string> = {
  primary: '#EA580C',
  reporting: '#3F3F46',
  commentary: '#A1A1AA',
};

interface ReadingTableProps {
  evidence: Evidence;
  callNumber: string;
  elementDescriptions: { elementId: string; description: string; relationship?: EvidenceRelationship; reasoning?: string; claimLabel?: string }[];
  claimLabel?: string;
  onClose: () => void;
}

export function ReadingTable({ evidence, callNumber, elementDescriptions, claimLabel, onClose }: ReadingTableProps) {
  const panel = useRef<HTMLDivElement>(null);
  useEffect(() => {
    panel.current?.focus({ preventScroll: true });
    panel.current?.scrollIntoView?.({ block: 'nearest', behavior: 'smooth' });
  }, [evidence.id]);
  const domain = extractDomain(evidence.url);
  const date = formatDate(evidence.publishedDate);
  const faviconUrl = getFaviconUrl(evidence.url);
  const tier = evidence.tier || 'commentary';
  const firstLetter = domain.charAt(0).toUpperCase();

  return (
    <div ref={panel} tabIndex={-1} aria-label="Source details" className="border border-zinc-200 bg-[#FAFAF8] p-5 relative">
      {/* Close button */}
      <button
        onClick={onClose}
        className="absolute top-3 right-3 font-mono text-[10px] text-zinc-400 hover:text-zinc-900 transition-colors"
      >
        Close &times;
      </button>

      {/* Header: favicon + domain + call number */}
      <div className="flex items-center gap-3 mb-3">
        <div
          className="relative w-6 h-6 rounded-full border flex items-center justify-center overflow-hidden bg-white shrink-0"
          style={{ borderColor: TIER_BORDER_COLORS[tier] }}
        >
          <span className="font-mono text-[9px] font-bold text-zinc-400">{firstLetter}</span>
          {faviconUrl && (
            <img
              src={faviconUrl}
              alt=""
              className="absolute inset-0 w-6 h-6 rounded-full"
              onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
            />
          )}
        </div>
        <span className="font-mono text-[10px] text-zinc-500">{domain}</span>
        <span className="ml-auto font-mono text-[10px] text-zinc-400 tracking-widest">{callNumber}</span>
      </div>

      {/* Title */}
      <div className="text-sm font-medium text-zinc-900 mb-1 leading-snug break-words">
        {cleanTitle(evidence.title) || 'Untitled source'}
      </div>

      {/* Date */}
      {date && (
        <div className="font-mono text-[10px] text-zinc-400 mb-3">
          {date}
          <DateHint evidence={evidence} />
        </div>
      )}

      {/* Stamps */}
      <div className="flex items-center gap-2 mb-4">
        {evidence.tier && <TierStamp tier={evidence.tier} />}
        {evidence.evidenceType && <TypeStamp type={evidence.evidenceType} />}
      </div>

      {/* Fact-check rating (attributed, only for a confirmed fact-check) */}
      <FactCheckRating evidence={evidence} />

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
            {elementDescriptions.map(({ elementId, description, relationship, reasoning, claimLabel }, index) => (
              <div key={`${claimLabel}-${elementId}-${index}`} className="text-[11px] text-zinc-600 pb-3">
                {claimLabel && <span>{claimLabel} · </span>}
                <span className="text-zinc-400">Element {elementId.replace('e', '')}</span>
                {description && <span> &mdash; {description}</span>}
                {relationship && <p className="font-mono uppercase mt-1">{relationship}</p>}
                <p className="mt-1">System interpretation: {reasoning || 'No relationship explanation was saved for this record.'}</p>
                <p className="text-zinc-400 mt-1">An exact supporting passage is not available in this record.</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {evidence.textProvenance?.version === 1 && (
        <section aria-label="Captured source text" className="mb-4 space-y-3 text-[11px] text-zinc-600">
          <h3 className="font-mono uppercase text-zinc-500">Captured source text</h3>
          <p>These excerpts are copied from the extracted text. Extraction may omit page content or tables. They have not been linked to the relationships above.</p>
          {evidence.textProvenance.passages.map((passage, index) => (
            <div key={passage.id}>
              <p className="text-zinc-400">Retained excerpt {index + 1}</p>
              <blockquote className="border-l-2 border-zinc-300 pl-3 whitespace-pre-wrap break-words">{passage.text}</blockquote>
            </div>
          ))}
          {evidence.textProvenance.original_snippet && (
            <details>
              <summary className="cursor-pointer">Original stored snippet</summary>
              <p className="mt-2 whitespace-pre-wrap">{evidence.textProvenance.original_snippet}</p>
            </details>
          )}
          {evidence.textProvenance.derived_text && (
            <details>
              <summary className="cursor-pointer">Model-generated facts — not quotations</summary>
              <p className="mt-2 whitespace-pre-wrap">{evidence.textProvenance.derived_text}</p>
            </details>
          )}
          <details>
            <summary className="cursor-pointer">Capture details</summary>
            <p className="mt-2">Captured {evidence.textProvenance.captured_at}. Retained {evidence.textProvenance.retained_characters} of {evidence.textProvenance.extraction_characters} extracted characters.</p>
            <p className="break-all">Extraction fingerprint (SHA-256): {evidence.textProvenance.extraction_sha256}</p>
          </details>
        </section>
      )}

      {/* Claim label (check-wide) */}
      {claimLabel && (
        <div className="font-mono text-[10px] text-zinc-400 mb-4">{claimLabel}</div>
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
