'use client';

import { useCallback } from 'react';
import type { ClaimForSelection } from './types';

interface ClaimSelectionCardProps {
  claim: ClaimForSelection;
  isSelected: boolean;
  onToggle: () => void;
}

export function ClaimSelectionCard({
  claim,
  isSelected,
  onToggle,
}: ClaimSelectionCardProps) {
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === ' ' || e.key === 'Enter') {
        e.preventDefault();
        onToggle();
      }
    },
    [onToggle]
  );

  const rankLabel = String(claim.significanceRank).padStart(2, '0');

  return (
    <div
      role="checkbox"
      aria-checked={isSelected}
      tabIndex={0}
      onClick={onToggle}
      onKeyDown={handleKeyDown}
      className={`claim-select-card px-6 py-5${isSelected ? ' selected' : ''}`}
    >
      <div className="flex items-start justify-between gap-4 mb-3">
        <span className="rank-num font-mono text-sm font-bold">{rankLabel}</span>
        <div className="flex items-center gap-3">
          <span className="type-badge px-2.5 py-0.5 bg-zinc-50 border border-zinc-200 text-[9px] font-mono font-bold uppercase tracking-wider text-zinc-500">
            {claim.claimType}
          </span>
          <div className="select-indicator">
            {isSelected && (
              <svg
                width="10"
                height="10"
                viewBox="0 0 10 10"
                fill="none"
                aria-hidden="true"
              >
                <path
                  d="M2 5L4.5 7.5L8 3"
                  stroke="white"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            )}
          </div>
        </div>
      </div>
      <p className="claim-text text-[15px] font-medium leading-relaxed">
        {claim.text}
      </p>
    </div>
  );
}
