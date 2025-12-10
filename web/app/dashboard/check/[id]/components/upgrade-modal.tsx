'use client';

import { X, Lock, FileSearch, Download, Filter } from 'lucide-react';
import Link from 'next/link';

interface UpgradeModalProps {
  feature: 'sources';
  sourcesCount: number;
  onClose: () => void;
}

export function UpgradeModal({ feature, sourcesCount, onClose }: UpgradeModalProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/70 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative z-10 bg-slate-800 border border-slate-700 rounded-2xl p-8 max-w-lg mx-4 shadow-2xl">
        {/* Close button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-slate-400 hover:text-white transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Lock icon */}
        <div className="flex justify-center mb-6">
          <div className="w-16 h-16 rounded-full bg-amber-500/20 flex items-center justify-center">
            <Lock className="w-8 h-8 text-amber-400" />
          </div>
        </div>

        {/* Content */}
        <h2 className="text-2xl font-bold text-white text-center mb-3">
          Full Sources List
        </h2>

        <p className="text-slate-300 text-center mb-6">
          We reviewed <span className="font-bold text-white">{sourcesCount} sources</span> to verify this content.
          Upgrade to Pro to see the complete list with filtering details.
        </p>

        {/* Features list */}
        <div className="space-y-3 mb-8">
          <div className="flex items-start gap-3">
            <FileSearch className="w-5 h-5 text-blue-400 mt-0.5" />
            <div>
              <p className="text-white font-medium">See all sources reviewed</p>
              <p className="text-slate-400 text-sm">Every source our system checked, grouped by claim</p>
            </div>
          </div>

          <div className="flex items-start gap-3">
            <Filter className="w-5 h-5 text-purple-400 mt-0.5" />
            <div>
              <p className="text-white font-medium">Understand filtering decisions</p>
              <p className="text-slate-400 text-sm">See why sources were included or excluded</p>
            </div>
          </div>

          <div className="flex items-start gap-3">
            <Download className="w-5 h-5 text-emerald-400 mt-0.5" />
            <div>
              <p className="text-white font-medium">Export citations</p>
              <p className="text-slate-400 text-sm">Download as CSV, BibTeX, or APA format</p>
            </div>
          </div>
        </div>

        {/* CTA buttons */}
        <div className="flex gap-3">
          <button
            onClick={onClose}
            className="flex-1 px-4 py-3 text-slate-300 hover:text-white border border-slate-600 rounded-lg transition-colors"
          >
            Maybe Later
          </button>
          <Link
            href="/dashboard/settings"
            className="flex-1 px-4 py-3 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 text-white font-semibold rounded-lg text-center transition-all"
          >
            Upgrade to Pro
          </Link>
        </div>
      </div>
    </div>
  );
}
