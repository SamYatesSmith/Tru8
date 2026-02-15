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

  if (!isCompleted) {
    return null;
  }

  return (
    <div className="border-b border-zinc-100 mb-6">
      <div className="flex gap-8">
        <Link
          href={`/dashboard/check/${checkId}`}
          className={`
            relative pb-3 px-1 text-[10px] font-bold tracking-[0.2em] uppercase transition-colors
            ${!isSourcesTab
              ? 'text-black border-b-2 border-accent'
              : 'text-zinc-400 hover:text-zinc-900'
            }
          `}
        >
          EVIDENCE MAP
        </Link>

        <Link
          href={isPro ? `/dashboard/check/${checkId}/sources` : `/dashboard/check/${checkId}?upgrade=sources`}
          className={`
            relative pb-3 px-1 text-[10px] font-bold tracking-[0.2em] uppercase transition-colors flex items-center gap-2
            ${isSourcesTab
              ? 'text-black border-b-2 border-accent'
              : 'text-zinc-400 hover:text-zinc-900'
            }
          `}
          onClick={(e) => {
            if (!isPro) {
              e.preventDefault();
              window.history.pushState({}, '', `/dashboard/check/${checkId}?upgrade=sources`);
              window.dispatchEvent(new CustomEvent('show-upgrade-modal', { detail: 'sources' }));
            }
          }}
        >
          SOURCES ({sourcesCount})
          {!isPro && <Lock className="w-3.5 h-3.5 text-amber-500" />}
        </Link>
      </div>
    </div>
  );
}
