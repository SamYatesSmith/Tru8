'use client';

import { XCircle } from 'lucide-react';
import Link from 'next/link';

interface ErrorStateProps {
  errorMessage: string | null;
  checkId: string;
}

export function ErrorState({ errorMessage, checkId }: ErrorStateProps) {
  return (
    <div className="bg-red-900/20 border border-red-700 rounded-xl p-12 text-center">
      <XCircle size={64} className="text-red-400 mx-auto mb-4" />

      <h3 className="text-2xl font-bold text-white mb-2">Check Failed</h3>

      <p className="text-slate-300 mb-6">We encountered an error processing this check.</p>

      {errorMessage && (
        <div className="bg-slate-900/50 border border-slate-700 rounded-lg p-4 mb-6 max-w-2xl mx-auto">
          <p className="text-sm text-slate-400 text-left">
            <span className="font-medium text-red-400">Error:</span> {errorMessage}
          </p>
        </div>
      )}

      <div className="flex items-center justify-center gap-4">
        <Link
          href="/dashboard/new-check"
          className="px-6 py-3 bg-gradient-to-r from-[#f57a07] to-[#ff8c1a] hover:from-[#ff8c1a] hover:to-[#f57a07] text-white font-medium rounded-lg transition-all"
        >
          Try Again
        </Link>

        <a
          href="mailto:support@tru8.com"
          className="px-6 py-3 bg-slate-700 hover:bg-slate-600 text-white font-medium rounded-lg transition-colors"
        >
          Contact Support
        </a>
      </div>
    </div>
  );
}
