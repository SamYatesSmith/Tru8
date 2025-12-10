'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Lock } from 'lucide-react';

interface CheckTabsProps {
  checkId: string;
  sourcesCount: number;
  isPro: boolean;
  isCompleted?: boolean;
}

export function CheckTabs({ checkId, sourcesCount, isPro, isCompleted = true }: CheckTabsProps) {
  const pathname = usePathname();
  const isSourcesTab = pathname.includes('/sources');

  // Don't show tabs if check is not completed
  if (!isCompleted) {
    return null;
  }

  return (
    <div className="border-b border-slate-700 mb-6">
      <div className="flex gap-8">
        {/* Verdict Tab */}
        <Link
          href={`/dashboard/check/${checkId}`}
          className={`
            relative pb-4 px-1 text-sm font-semibold transition-colors
            ${!isSourcesTab
              ? 'text-white border-b-2 border-blue-500'
              : 'text-slate-400 hover:text-slate-300'
            }
          `}
        >
          VERDICT
        </Link>

        {/* Sources Tab */}
        <Link
          href={isPro ? `/dashboard/check/${checkId}/sources` : `/dashboard/check/${checkId}?upgrade=sources`}
          className={`
            relative pb-4 px-1 text-sm font-semibold transition-colors flex items-center gap-2
            ${isSourcesTab
              ? 'text-white border-b-2 border-blue-500'
              : 'text-slate-400 hover:text-slate-300'
            }
          `}
          onClick={(e) => {
            if (!isPro) {
              e.preventDefault();
              // Trigger upgrade modal by updating URL
              window.history.pushState({}, '', `/dashboard/check/${checkId}?upgrade=sources`);
              window.dispatchEvent(new CustomEvent('show-upgrade-modal', { detail: 'sources' }));
            }
          }}
        >
          SOURCES ({sourcesCount})
          {!isPro && <Lock className="w-3.5 h-3.5 text-amber-400" />}
        </Link>
      </div>
    </div>
  );
}
