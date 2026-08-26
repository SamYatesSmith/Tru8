'use client';

import type { Evidence, EvidenceTier } from '@shared/types';
import { ElementRefs } from '../ElementRefs';
import { cleanTitle, extractDomain, getFaviconUrl } from '../shared-utils';

/**
 * One selectable source in the picker. Click places it in the next empty
 * slot (or the focused one) — the primary path everywhere. Desktop may also
 * drag it onto a slot (draggable + the custom mime key the slots read).
 *
 * The row shows the source's relationship badges but never filters on them:
 * slots accept anything (design §5.3).
 */

const TIER_BORDER_COLOURS: Record<EvidenceTier, string> = {
  primary: '#EA580C',
  reporting: '#3F3F46',
  commentary: '#A1A1AA',
};

interface PickerRowProps {
  evidence: Evidence;
  elementIds: string[];
  elementDescriptions?: Map<string, string>;
  placed: boolean;
  disabled: boolean;
  onClick: () => void;
}

export function PickerRow({
  evidence,
  elementIds,
  elementDescriptions,
  placed,
  disabled,
  onClick,
}: PickerRowProps) {
  const domain = extractDomain(evidence.url);
  const tier = evidence.tier || 'commentary';

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled || placed}
      aria-pressed={placed}
      draggable={!placed && !disabled}
      onDragStart={(e) => {
        e.dataTransfer.setData(
          'text/tru8-evidence-id',
          evidence.evidenceId || evidence.id
        );
      }}
      className={`w-full text-left border p-3 transition-colors ${
        placed
          ? 'border-zinc-300 bg-[#FAFAF8] cursor-default'
          : disabled
            ? 'border-zinc-100 opacity-40 cursor-default'
            : 'border-zinc-100 hover:border-zinc-300 cursor-pointer'
      }`}
    >
      <div className="flex items-center gap-3">
        <div
          className="relative w-6 h-6 rounded-full border flex items-center justify-center overflow-hidden shrink-0 bg-white"
          style={{ borderColor: TIER_BORDER_COLOURS[tier] }}
        >
          <span className="absolute font-mono text-[9px] font-bold text-zinc-300">
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
        <div className="flex-grow min-w-0">
          <div className="text-[13px] font-medium text-zinc-900 leading-snug break-words">
            {cleanTitle(evidence.title) || 'Untitled source'}
          </div>
          <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5 mt-0.5">
            <span className="font-mono text-[10px] text-zinc-500">{domain}</span>
            {elementIds.length > 0 && (
              <>
                <span className="font-mono text-[10px] text-zinc-300">&middot;</span>
                <ElementRefs elementIds={elementIds} descriptions={elementDescriptions} />
              </>
            )}
          </div>
        </div>
        {placed && (
          <span className="font-mono text-[9px] uppercase tracking-widest text-zinc-400 shrink-0">
            Placed
          </span>
        )}
      </div>
    </button>
  );
}
