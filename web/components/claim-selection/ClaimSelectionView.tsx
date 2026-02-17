'use client';

import { useState, useCallback } from 'react';
import type { ClaimForSelection } from './types';
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
  const [selected, setSelected] = useState<Set<number>>(new Set());

  const toggleClaim = useCallback((position: number) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(position)) {
        next.delete(position);
      } else {
        next.add(position);
      }
      return next;
    });
  }, []);

  const selectAll = useCallback(() => {
    setSelected(new Set(claims.map((c) => c.position)));
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
        Select the claims you&apos;d like to investigate. We&apos;ll gather evidence for each.
      </p>

      <ClaimSelectionToolbar
        count={claims.length}
        onSelectAll={selectAll}
        onClear={clearAll}
      />

      <div className="space-y-3 mb-12">
        {claims.map((claim) => (
          <ClaimSelectionCard
            key={claim.position}
            claim={claim}
            isSelected={selected.has(claim.position)}
            onToggle={() => toggleClaim(claim.position)}
          />
        ))}
      </div>

      <div>
        <div className="flex items-center justify-end gap-6 mb-4">
          <span className="font-mono text-[10px] text-zinc-400">
            {selectedCount} of {claims.length} claims selected
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
