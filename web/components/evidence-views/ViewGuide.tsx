'use client';

import { useState, useEffect } from 'react';

const VIEW_GUIDES: Record<string, string> = {
  cartographer:
    'This map shows how evidence flows from sources to claims. Nodes are grouped by source tier\u2009—\u2009primary (green), reporting (blue), commentary (grey). Lines connect evidence to the claim elements they address.',
  librarian:
    'Your complete evidence library, classified by source tier (rows) and content type (columns). Click any heatmap cell to filter. The ledger below shows every source with its full classification.',
  interpreter:
    'Each claim is decomposed into testable elements. Evidence is grouped by the element it addresses, showing whether it supports, challenges, or provides context for that element.',
  seeker:
    'Gaps in the evidence landscape. Elements with insufficient or missing evidence are surfaced here, along with suggested search queries to find what\u2019s missing.',
  projectionist:
    'Video sources related to this analysis. Each card links to the original video and shows how it connects to the claims being examined.',
  chronologist:
    'Evidence plotted on a timeline by publication date. Clusters show when evidence appeared\u2009—\u2009useful for spotting coordinated narratives or emerging stories.',
};

const STORAGE_KEY = 'tru8-view-guide-dismissed';

function getDismissed(): Set<string> {
  if (typeof window === 'undefined') return new Set();
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? new Set(JSON.parse(raw)) : new Set();
  } catch {
    return new Set();
  }
}

function setDismissed(dismissed: Set<string>) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(Array.from(dismissed)));
  } catch {
    // localStorage unavailable
  }
}

interface ViewGuideProps {
  activeView: string;
}

export function ViewGuide({ activeView }: ViewGuideProps) {
  const [dismissed, setDismissedState] = useState<Set<string>>(new Set());
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setDismissedState(getDismissed());
    setMounted(true);
  }, []);

  const guide = VIEW_GUIDES[activeView];
  if (!guide || !mounted || dismissed.has(activeView)) return null;

  const handleDismiss = () => {
    const next = new Set(dismissed);
    next.add(activeView);
    setDismissedState(next);
    setDismissed(next);
  };

  return (
    <div className="flex items-start gap-3 px-4 py-3 bg-zinc-50 border border-zinc-200 mb-6">
      <span className="font-mono text-[9px] uppercase tracking-widest text-zinc-400 shrink-0 pt-0.5">
        Guide
      </span>
      <p className="text-[12px] text-zinc-500 leading-relaxed flex-1">
        {guide}
      </p>
      <button
        onClick={handleDismiss}
        className="font-mono text-[9px] uppercase tracking-widest text-zinc-400 hover:text-zinc-600 transition-colors shrink-0 pt-0.5"
      >
        Got it
      </button>
    </div>
  );
}
