'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Sparkles, ArrowRight, X } from 'lucide-react';

interface UpgradeBannerProps {
  currentPlan: string;
  subscriptionsEnabled?: boolean;
}

export function UpgradeBanner({ currentPlan, subscriptionsEnabled = false }: UpgradeBannerProps) {
  const [isDismissed, setIsDismissed] = useState(false);

  const features = [
    '40 checks per month',
    'Priority processing',
    'Advanced source analysis',
    'Export reports and citations',
  ];

  if (isDismissed) {
    return null;
  }

  return (
    <>
      {/* Mobile: Slim dismissible banner */}
      <div className="md:hidden bg-zinc-50 border border-zinc-200 px-4 py-3 mb-4">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2 flex-1 min-w-0">
            <Sparkles className="text-accent flex-shrink-0" size={18} />
            <span className="text-sm text-zinc-900 font-medium truncate">
              {subscriptionsEnabled ? 'Unlock Pro' : 'Pro Coming Soon'}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <Link
              href="/dashboard/settings?tab=subscription"
              className="bg-zinc-900 hover:bg-zinc-800 text-white text-[10px] font-bold uppercase tracking-[0.2em] px-3 py-1.5 flex items-center gap-1 transition-colors"
            >
              {subscriptionsEnabled ? 'Upgrade' : 'Waitlist'}
              <ArrowRight size={14} />
            </Link>
            <button
              onClick={() => setIsDismissed(true)}
              className="text-zinc-400 hover:text-zinc-900 p-1 transition-colors"
              aria-label="Dismiss"
            >
              <X size={16} />
            </button>
          </div>
        </div>
      </div>

      {/* Desktop: Full banner */}
      <div className="hidden md:block bg-zinc-50 border border-zinc-200 p-8 mb-8">
        <div className="flex items-start justify-between mb-6">
          <div className="flex items-center gap-3">
            <Sparkles className="text-accent" size={28} />
            <div>
              <h3 className="text-lg font-bold text-zinc-900">
                {subscriptionsEnabled ? 'Unlock Premium Features' : 'Pro Features Coming Soon'}
              </h3>
              <p className="text-zinc-500 text-sm">
                Current Plan: <span className="font-semibold">{currentPlan}</span>
              </p>
            </div>
          </div>

          <Link
            href="/dashboard/settings?tab=subscription"
            className="bg-zinc-900 hover:bg-zinc-800 text-white text-xs font-bold uppercase tracking-[0.2em] px-6 py-3 flex items-center gap-2 transition-colors"
          >
            {subscriptionsEnabled ? 'Upgrade Now' : 'Join Waitlist'}
            <ArrowRight size={18} />
          </Link>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {features.map((feature, index) => (
            <div key={index} className="flex items-center gap-2 text-zinc-600 text-sm">
              <span className="text-accent">•</span>
              {feature}
            </div>
          ))}
        </div>
      </div>
    </>
  );
}
