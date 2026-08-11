'use client';

import { useState, useCallback } from 'react';
import type { ClaimForSelection } from './types';
import { MAX_SELECTABLE_CLAIMS } from './types';
import { ExtractionSummaryStrip } from './ExtractionSummaryStrip';
import { ClaimSelectionToolbar } from './ClaimSelectionToolbar';
import { ClaimSelectionCard } from './ClaimSelectionCard';

interface ClaimSelectionViewProps {
  claims: ClaimForSelection[];
  checkId: string;
  referenceId: string;
  extractionTime: string;
  onSubmit: (selectedPositions: number[]) => void;
  isSubmitting: boolean;
}

export function ClaimSelectionView({
  claims,
  checkId,
  referenceId,
  extractionTime,
  onSubmit,
  isSubmitting,
}: ClaimSelectionViewProps) {
  // Pre-select the top-ranked claim so the default path through the gate is
  // one click. Half the external news-URL checks were abandoned here when the
  // gate opened empty (2026-08-11 usage audit). Rank is used, not array
  // order — the page-refresh fallback maps claims in position order.
  const [selected, setSelected] = useState<Set<number>>(() => {
    if (claims.length === 0) return new Set();
    const top = claims.reduce((a, b) =>
      a.significanceRank <= b.significanceRank ? a : b
    );
    return new Set([top.position]);
  });

  const capExceedsClaims = claims.length > MAX_SELECTABLE_CLAIMS;
  const isAtCap = selected.size >= MAX_SELECTABLE_CLAIMS;

  const toggleClaim = useCallback((position: number) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(position)) {
        next.delete(position);
      } else if (next.size >= MAX_SELECTABLE_CLAIMS) {
        // At cap — additions are no-ops. User must deselect first
        // to swap. The card itself renders disabled state so this
        // path is reached only via keyboard / programmatic toggle.
        return prev;
      } else {
        next.add(position);
      }
      return next;
    });
  }, []);

  const selectAll = useCallback(() => {
    // Cap-respecting: select up to MAX_SELECTABLE_CLAIMS by current
    // ordering (claims arrive pre-sorted by significance rank).
    const top = claims.slice(0, MAX_SELECTABLE_CLAIMS).map((c) => c.position);
    setSelected(new Set(top));
  }, [claims]);

  const clearAll = useCallback(() => {
    setSelected(new Set());
  }, []);

  const handleSubmit = useCallback(() => {
    if (selected.size === 0 || isSubmitting) return;
    onSubmit(Array.from(selected));
  }, [selected, isSubmitting, onSubmit]);

  const selectedCount = selected.size;

  return (
    <div className="max-w-3xl mx-auto">
      <ExtractionSummaryStrip
        referenceId={referenceId}
        claimsFound={claims.length}
        extractionTime={extractionTime}
      />

      <p className="text-sm text-zinc-500 mb-8">
        The top claim is pre-selected. Adjust or add up to {MAX_SELECTABLE_CLAIMS}.
      </p>

      <ClaimSelectionToolbar
        count={claims.length}
        selectAllLabel={capExceedsClaims ? `Select top ${MAX_SELECTABLE_CLAIMS}` : 'Select all'}
        onSelectAll={selectAll}
        onClear={clearAll}
      />

      <div className="space-y-3 mb-4">
        {claims.map((claim) => {
          const isSelected = selected.has(claim.position);
          return (
            <ClaimSelectionCard
              key={claim.position}
              claim={claim}
              isSelected={isSelected}
              isDisabled={isAtCap && !isSelected}
              onToggle={() => toggleClaim(claim.position)}
            />
          );
        })}
      </div>

      <div className="mb-12 min-h-[1.25rem]">
        {isAtCap && capExceedsClaims && (
          <p className="font-mono text-[10px] uppercase tracking-widest text-zinc-400">
            {MAX_SELECTABLE_CLAIMS} of {MAX_SELECTABLE_CLAIMS} selected &middot;
            deselect one to swap
          </p>
        )}
      </div>

      <div>
        <div className="flex items-center justify-end gap-6 mb-4">
          <span className="font-mono text-[10px] text-zinc-400">
            {selectedCount} of {Math.min(claims.length, MAX_SELECTABLE_CLAIMS)} claims selected
          </span>
        </div>
        <div className="flex justify-end">
          <button
            type="button"
            onClick={handleSubmit}
            disabled={selectedCount === 0 || isSubmitting}
            className={`px-8 py-3 text-[11px] font-bold tracking-[0.2em] uppercase transition-colors flex items-center gap-3 ${
              selectedCount > 0 && !isSubmitting
                ? 'bg-zinc-900 text-white hover:bg-black cursor-pointer'
                : 'bg-zinc-200 text-zinc-500 cursor-not-allowed'
            }`}
          >
            {isSubmitting
              ? 'Submitting...'
              : `Investigate ${selectedCount} Claim${selectedCount !== 1 ? 's' : ''}`}
            <span className="text-sm">&rarr;</span>
          </button>
        </div>
      </div>

      <div className="mt-6">
        <a
          href={`/dashboard`}
          className="font-mono text-[10px] uppercase tracking-widest text-zinc-400 hover:text-zinc-900 transition-colors inline-flex items-center gap-2"
        >
          <span>&larr;</span> Back to dashboard
        </a>
      </div>
    </div>
  );
}
