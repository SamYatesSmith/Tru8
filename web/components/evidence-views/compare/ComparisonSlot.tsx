'use client';

import type { Evidence, EvidenceTier } from '@shared/types';
import { TierBadge } from '../TierBadge';
import { TypeBadge } from '../TypeBadge';
import { DateHint } from '../DateHint';
import { cleanTitle, extractDomain } from '../shared-utils';

/**
 * One of the two comparison slots. Slots are A and B — deliberately NOT
 * "supports" and "challenges": nothing constrains what may enter either
 * (two supporting primaries disagreeing on magnitude is a fine comparison).
 * Each filled slot DISPLAYS its source's badges; nothing enforces them.
 *
 * Empty slot = dashed border + click target (click-to-place is the primary
 * path; drag is desktop sugar via the onDragOver/onDrop handlers). Filled
 * slot reuses the SourceCard header composition: tier-ringed favicon,
 * domain, cleaned title (the "…" stays — a cut title must look cut), date,
 * badges, and the ReadingTable close idiom for Remove.
 */

const TIER_BORDER_COLOURS: Record<EvidenceTier, string> = {
  primary: '#EA580C',
  reporting: '#3F3F46',
  commentary: '#A1A1AA',
};

function getFaviconUrl(url: string): string {
  const domain = extractDomain(url);
  return domain ? `https://www.google.com/s2/favicons?domain=${domain}&sz=32` : '';
}

function formatDate(dateStr?: string): string {
  if (!dateStr) return '';
  try {
    return new Date(dateStr).toLocaleDateString('en-GB', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
    });
  } catch {
    return '';
  }
}

interface ComparisonSlotProps {
  slot: 'A' | 'B';
  evidence: Evidence | null;
  onRemove: () => void;
  /** Click on an EMPTY slot — focuses placement (next picker click lands here). */
  onSelectEmpty: () => void;
  onDropEvidence: (evidenceId: string) => void;
  disabled?: boolean;
}

export function ComparisonSlot({
  slot,
  evidence,
  onRemove,
  onSelectEmpty,
  onDropEvidence,
  disabled,
}: ComparisonSlotProps) {
  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const id = e.dataTransfer.getData('text/tru8-evidence-id');
    if (id) onDropEvidence(id);
  };

  if (!evidence) {
    return (
      <button
        type="button"
        onClick={onSelectEmpty}
        disabled={disabled}
        aria-label={`Place a source in slot ${slot}`}
        onDragOver={(e) => e.preventDefault()}
        onDrop={handleDrop}
        className="w-full min-h-[108px] border border-dashed border-zinc-300 flex flex-col items-center justify-center gap-1 hover:border-[var(--accent)] transition-colors cursor-pointer disabled:cursor-default"
      >
        <span className="font-mono text-[10px] uppercase tracking-widest text-zinc-400">
          Slot {slot}
        </span>
        <span className="text-[11px] text-zinc-400">Click a source below</span>
      </button>
    );
  }

  const domain = extractDomain(evidence.url);
  const tier = evidence.tier || 'commentary';
  const date = formatDate(evidence.publishedDate);

  return (
    <section
      aria-label={`Slot ${slot}: ${domain}`}
      onDragOver={(e) => e.preventDefault()}
      onDrop={handleDrop}
      className="relative w-full min-h-[108px] border border-zinc-300 bg-[#FAFAF8] p-4"
    >
      <button
        type="button"
        onClick={onRemove}
        className="absolute top-3 right-3 font-mono text-[10px] text-zinc-400 hover:text-zinc-900 transition-colors"
      >
        Remove &times;
      </button>

      <div className="font-mono text-[10px] uppercase tracking-widest text-zinc-400 mb-2">
        Slot {slot}
      </div>

      <div className="flex items-center gap-3 mb-2">
        <div
          className="relative w-8 h-8 rounded-full border-2 flex items-center justify-center overflow-hidden shrink-0 bg-white"
          style={{ borderColor: TIER_BORDER_COLOURS[tier] }}
        >
          <span className="absolute font-mono font-semibold text-zinc-300 text-[11px]">
            {domain[0]?.toUpperCase() || '?'}
          </span>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={getFaviconUrl(evidence.url)}
            alt=""
            className="w-full h-full object-cover relative z-10"
            onError={(e) => {
              (e.target as HTMLImageElement).style.display = 'none';
            }}
          />
        </div>
        <span className="text-sm font-medium text-zinc-900 min-w-0 pr-16">
          {domain}
        </span>
      </div>

      <div className="text-sm text-zinc-700 leading-snug break-words mb-2">
        {cleanTitle(evidence.title) || 'Untitled source'}
      </div>

      <div className="flex flex-wrap items-center gap-2">
        {evidence.tier && <TierBadge tier={evidence.tier} />}
        {evidence.evidenceType && <TypeBadge type={evidence.evidenceType} />}
        {date && (
          <span className="font-mono text-[10px] text-zinc-400">
            {date}
            <DateHint evidence={evidence} />
          </span>
        )}
      </div>
    </section>
  );
}
