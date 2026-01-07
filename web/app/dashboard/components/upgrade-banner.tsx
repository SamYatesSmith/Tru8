'use client';

import Link from 'next/link';
import { Sparkles, ArrowRight, Clock } from 'lucide-react';

interface UpgradeBannerProps {
  currentPlan: string;
  subscriptionsEnabled?: boolean;
}

export function UpgradeBanner({ currentPlan, subscriptionsEnabled = false }: UpgradeBannerProps) {
  const features = [
    '40 fact-checks per month',
    'Priority verification processing',
    'Advanced source analysis',
    'Export reports and citations',
  ];

  return (
    <div className="bg-[#1a1f2e] border border-slate-700 rounded-xl p-8 mb-8">
      <div className="flex items-start justify-between mb-6">
        <div className="flex items-center gap-3">
          <Sparkles className="text-[#f57a07]" size={28} />
          <div>
            <h3 className="text-xl font-bold text-white">
              {subscriptionsEnabled ? 'Unlock Premium Features' : 'Pro Features Coming Soon'}
            </h3>
            <p className="text-slate-400">
              Current Plan: <span className="font-semibold">{currentPlan} (3 checks)</span>
              {!subscriptionsEnabled && (
                <span className="ml-2 inline-flex items-center gap-1 text-amber-400 text-sm">
                  <Clock size={14} />
                  Beta
                </span>
              )}
            </p>
          </div>
        </div>

        <Link
          href="/dashboard/settings?tab=subscription"
          className="bg-[#f57a07] hover:bg-[#e06a00] text-white font-bold px-6 py-3 rounded-lg flex items-center gap-2 transition-colors"
        >
          {subscriptionsEnabled ? 'Upgrade Now' : 'Join Waitlist'}
          <ArrowRight size={18} />
        </Link>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {features.map((feature, index) => (
          <div key={index} className="flex items-center gap-2 text-slate-300">
            <span className="text-[#f57a07]">•</span>
            {feature}
          </div>
        ))}
      </div>
    </div>
  );
}
