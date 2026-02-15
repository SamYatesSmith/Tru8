'use client';

import { X, Lock, FileSearch, Download, Filter, Clock } from 'lucide-react';
import Link from 'next/link';

interface UpgradeModalProps {
  feature: 'sources';
  sourcesCount: number;
  onClose: () => void;
  subscriptionsEnabled?: boolean;
}

export function UpgradeModal({ feature, sourcesCount, onClose, subscriptionsEnabled = false }: UpgradeModalProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative z-10 bg-white border border-zinc-200 p-8 max-w-lg mx-4 shadow-lg">
        {/* Close button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-zinc-400 hover:text-zinc-900 transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Lock icon */}
        <div className="flex justify-center mb-6">
          <div className="w-16 h-16 bg-amber-50 flex items-center justify-center">
            {subscriptionsEnabled ? (
              <Lock className="w-8 h-8 text-amber-500" />
            ) : (
              <Clock className="w-8 h-8 text-amber-500" />
            )}
          </div>
        </div>

        {/* Content */}
        <h2 className="text-2xl font-bold text-zinc-900 text-center mb-3">
          {subscriptionsEnabled ? 'Full Sources List' : 'Pro Feature Coming Soon'}
        </h2>

        <p className="text-zinc-500 text-center mb-6">
          We reviewed <span className="font-bold text-zinc-900">{sourcesCount} sources</span> to analyse this content.
          {subscriptionsEnabled
            ? ' Upgrade to Pro to see the complete list with filtering details.'
            : ' This Pro feature will be available when we launch subscriptions.'}
        </p>

        {/* Features list */}
        <div className="space-y-3 mb-8">
          <div className="flex items-start gap-3">
            <FileSearch className="w-5 h-5 text-accent mt-0.5" />
            <div>
              <p className="text-zinc-900 font-medium">See all sources reviewed</p>
              <p className="text-zinc-500 text-sm">Every source our system checked, grouped by claim</p>
            </div>
          </div>

          <div className="flex items-start gap-3">
            <Filter className="w-5 h-5 text-accent mt-0.5" />
            <div>
              <p className="text-zinc-900 font-medium">Understand filtering decisions</p>
              <p className="text-zinc-500 text-sm">See why sources were included or excluded</p>
            </div>
          </div>

          <div className="flex items-start gap-3">
            <Download className="w-5 h-5 text-accent mt-0.5" />
            <div>
              <p className="text-zinc-900 font-medium">Export citations</p>
              <p className="text-zinc-500 text-sm">Download as CSV, BibTeX, or APA format</p>
            </div>
          </div>
        </div>

        {/* CTA buttons */}
        <div className="flex gap-3">
          <button
            onClick={onClose}
            className="flex-1 px-4 py-3 text-zinc-600 hover:text-zinc-900 border border-zinc-200 hover:bg-zinc-50 transition-colors text-sm font-bold uppercase tracking-[0.2em]"
          >
            {subscriptionsEnabled ? 'Maybe Later' : 'Got It'}
          </button>
          <Link
            href="/dashboard/settings?tab=subscription"
            className="flex-1 px-4 py-3 bg-zinc-900 hover:bg-zinc-800 text-white text-sm font-bold uppercase tracking-[0.2em] text-center transition-colors"
          >
            {subscriptionsEnabled ? 'Upgrade to Pro' : 'Join Waitlist'}
          </Link>
        </div>
      </div>
    </div>
  );
}
