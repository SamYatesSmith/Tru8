'use client';

import { useEffect, useCallback } from 'react';
import { ClaimElement } from '@shared/types';

interface ElementNavigationProps {
  elements: ClaimElement[];
  activeIndex: number;
  onNavigate: (index: number) => void;
}

export function ElementNavigation({ elements, activeIndex, onNavigate }: ElementNavigationProps) {
  const hasPrev = activeIndex > 0;
  const hasNext = activeIndex < elements.length - 1;

  const prevLabel = hasPrev
    ? `${String(activeIndex).padStart(2, '0')}: ${elements[activeIndex - 1].description.slice(0, 40)}${elements[activeIndex - 1].description.length > 40 ? '...' : ''}`
    : null;

  const nextLabel = hasNext
    ? `${String(activeIndex + 2).padStart(2, '0')}: ${elements[activeIndex + 1].description.slice(0, 40)}${elements[activeIndex + 1].description.length > 40 ? '...' : ''}`
    : null;

  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (e.key === 'ArrowLeft' && hasPrev) onNavigate(activeIndex - 1);
    if (e.key === 'ArrowRight' && hasNext) onNavigate(activeIndex + 1);
  }, [activeIndex, hasPrev, hasNext, onNavigate]);

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  return (
    <div className="flex items-center justify-between border-t border-zinc-100 pt-6">
      {hasPrev ? (
        <button
          onClick={() => onNavigate(activeIndex - 1)}
          className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-widest text-zinc-400 hover:text-zinc-900 transition-colors group"
        >
          <span className="group-hover:-translate-x-1 transition-transform">&larr;</span>
          <span>{prevLabel}</span>
        </button>
      ) : (
        <span className="font-mono text-[10px] text-zinc-300">No previous element</span>
      )}

      {hasNext ? (
        <button
          onClick={() => onNavigate(activeIndex + 1)}
          className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-widest text-zinc-400 hover:text-zinc-900 transition-colors group"
        >
          <span>{nextLabel}</span>
          <span className="group-hover:translate-x-1 transition-transform">&rarr;</span>
        </button>
      ) : (
        <span className="font-mono text-[10px] text-zinc-300">No next element</span>
      )}
    </div>
  );
}
