import Link from 'next/link';
import { Plus, Lock } from 'lucide-react';

interface QuickActionCardProps {
  used?: number;
  limit?: number;
}

export function QuickActionCard({ used = 0, limit = 3 }: QuickActionCardProps) {
  const isLimitReached = used >= limit;

  return (
    <div className="bg-white border border-zinc-200 p-8 h-full">
      <h3 className="text-sm font-bold uppercase tracking-wider text-zinc-900 mb-2">Quick Action</h3>
      <p className="text-zinc-500 text-sm mb-6">Research a news article or claim</p>

      {isLimitReached ? (
        <div className="space-y-4">
          <div className="bg-amber-50 border border-amber-200 px-4 py-3 text-amber-800 text-sm flex items-start gap-2">
            <Lock size={16} className="flex-shrink-0 mt-0.5" />
            <span>Monthly limit reached ({used}/{limit} checks). Upgrade to continue.</span>
          </div>
          <Link
            href="/dashboard/settings?tab=subscription"
            className="relative w-full bg-zinc-900 hover:bg-zinc-800 text-white text-xs font-bold uppercase tracking-[0.2em] py-4 flex items-center justify-center gap-2 transition-colors"
          >
            Upgrade Now
            <div className="w-2.5 h-2.5 bg-accent absolute right-0 top-1/2 -translate-y-1/2 translate-x-1 rotate-45" />
          </Link>
        </div>
      ) : (
        <Link
          href="/dashboard/new-check"
          className="relative w-full bg-zinc-900 hover:bg-zinc-800 text-white text-xs font-bold uppercase tracking-[0.2em] py-4 flex items-center justify-center gap-2 transition-colors"
        >
          <Plus size={16} />
          New Check
          <div className="w-2.5 h-2.5 bg-accent absolute right-0 top-1/2 -translate-y-1/2 translate-x-1 rotate-45" />
        </Link>
      )}
    </div>
  );
}
