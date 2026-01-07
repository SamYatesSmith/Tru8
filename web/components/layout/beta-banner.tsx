'use client';

import { useState, useEffect } from 'react';
import { X, FlaskConical } from 'lucide-react';

const BETA_BANNER_DISMISSED_KEY = 'tru8_beta_banner_dismissed';

export function BetaBanner() {
  const [isDismissed, setIsDismissed] = useState(true); // Start hidden to prevent flash
  const [isMounted, setIsMounted] = useState(false);

  useEffect(() => {
    setIsMounted(true);
    const dismissed = localStorage.getItem(BETA_BANNER_DISMISSED_KEY);
    setIsDismissed(dismissed === 'true');
  }, []);

  const handleDismiss = () => {
    setIsDismissed(true);
    localStorage.setItem(BETA_BANNER_DISMISSED_KEY, 'true');
  };

  // Don't render until mounted (prevents hydration mismatch)
  if (!isMounted || isDismissed) {
    return null;
  }

  return (
    <div className="fixed top-0 left-0 right-0 z-[60] bg-gradient-to-r from-amber-600 to-orange-500 text-white">
      <div className="container mx-auto px-4 py-2">
        <div className="flex items-center justify-center gap-3 text-sm">
          <FlaskConical size={16} className="flex-shrink-0" />
          <p className="text-center">
            <span className="font-semibold">Tru8 is in beta.</span>
            {' '}Results may vary and features are subject to change.
            {' '}
            <a
              href="mailto:feedback@tru8.ai"
              className="underline hover:no-underline font-medium"
            >
              Share feedback
            </a>
          </p>
          <button
            onClick={handleDismiss}
            className="flex-shrink-0 flex items-center gap-1 px-2 py-1 hover:bg-white/20 rounded transition-colors ml-2 text-xs opacity-80 hover:opacity-100"
            aria-label="Dismiss beta notice"
          >
            <span>Dismiss</span>
            <X size={14} />
          </button>
        </div>
      </div>
    </div>
  );
}

/**
 * Beta Badge Component
 * Small pill badge to display next to logos/titles
 */
export function BetaBadge({ className = '' }: { className?: string }) {
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-bold bg-amber-500/20 text-amber-400 border border-amber-500/30 ${className}`}
    >
      BETA
    </span>
  );
}
