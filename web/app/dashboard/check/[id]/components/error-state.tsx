'use client';

import { XCircle } from 'lucide-react';
import Link from 'next/link';

interface ErrorStateProps {
  errorMessage: string | null;
  checkId: string;
}

const GENERIC_FALLBACK = 'Something went wrong while processing this check. Please try again.';

function getSafeMessage(raw: string | null): string | null {
  if (!raw) return null;
  // Never show raw SQL, stack traces, or internal errors to users
  const toxic = /sqlalchemy|traceback|asyncpg|integrityerror|operationalerror|column .* does not exist|violates not-null|DETAIL: Failing row/i;
  if (toxic.test(raw)) return GENERIC_FALLBACK;
  // Cap length — legitimate messages are short
  if (raw.length > 300) return GENERIC_FALLBACK;
  return raw;
}

export function ErrorState({ errorMessage, checkId }: ErrorStateProps) {
  const safeMessage = getSafeMessage(errorMessage);

  return (
    <div className="bg-red-50 border border-red-200 p-12 text-center">
      <XCircle size={64} className="text-red-400 mx-auto mb-4" />

      <h3 className="text-2xl font-bold text-zinc-900 mb-2">Check Failed</h3>

      <p className="text-zinc-500 mb-6">We encountered an error processing this check.</p>

      {safeMessage && (
        <div className="bg-white border border-zinc-200 p-4 mb-6 max-w-2xl mx-auto">
          <p className="text-sm text-zinc-600 text-left">
            <span className="font-medium text-red-600">Error:</span> {safeMessage}
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
          href="mailto:hello@trueight.com"
          className="px-6 py-3 border border-zinc-200 hover:bg-zinc-50 text-zinc-600 text-xs font-bold uppercase tracking-[0.2em] transition-colors"
        >
          Contact Support
        </a>
      </div>
    </div>
  );
}
