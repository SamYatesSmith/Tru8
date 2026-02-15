'use client';

import { XCircle } from 'lucide-react';
import Link from 'next/link';

interface ErrorStateProps {
  errorMessage: string | null;
  checkId: string;
}

export function ErrorState({ errorMessage, checkId }: ErrorStateProps) {
  return (
    <div className="bg-red-50 border border-red-200 p-12 text-center">
      <XCircle size={64} className="text-red-400 mx-auto mb-4" />

      <h3 className="text-2xl font-bold text-zinc-900 mb-2">Check Failed</h3>

      <p className="text-zinc-500 mb-6">We encountered an error processing this check.</p>

      {errorMessage && (
        <div className="bg-white border border-zinc-200 p-4 mb-6 max-w-2xl mx-auto">
          <p className="text-sm text-zinc-600 text-left">
            <span className="font-medium text-red-600">Error:</span> {errorMessage}
          </p>
        </div>
      )}

      <div className="flex items-center justify-center gap-4">
        <Link
          href="/dashboard/new-check"
          className="px-6 py-3 bg-zinc-900 hover:bg-zinc-800 text-white text-xs font-bold uppercase tracking-[0.2em] transition-colors"
        >
          Try Again
        </Link>

        <a
          href="mailto:support@tru8.com"
          className="px-6 py-3 border border-zinc-200 hover:bg-zinc-50 text-zinc-600 text-xs font-bold uppercase tracking-[0.2em] transition-colors"
        >
          Contact Support
        </a>
      </div>
    </div>
  );
}
