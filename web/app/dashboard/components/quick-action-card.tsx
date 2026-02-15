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
      <p className="text-zinc-500 text-sm mb-6">Start a new evidence check</p>

      {isLimitReached ? (
        <div className="space-y-4">
          <div className="bg-amber-50 border border-amber-200 px-4 py-3 text-amber-800 text-sm flex items-start gap-2">
            <Lock size={16} className="flex-shrink-0 mt-0.5" />
            <span>Monthly limit reached ({used}/{limit} checks). Upgrade to continue.</span>
          </div>
          <Link
            href="/dashboard/settings?tab=subscription"
            className="w-full bg-zinc-900 hover:bg-zinc-800 text-white text-xs font-bold uppercase tracking-[0.2em] py-4 flex items-center justify-center gap-2 transition-colors"
          >
            Upgrade Now
          </Link>
        </div>
      ) : (
        <Link
          href="/dashboard/new-check"
          className="w-full bg-zinc-900 hover:bg-zinc-800 text-white text-xs font-bold uppercase tracking-[0.2em] py-4 flex items-center justify-center gap-2 transition-colors"
        >
          <Plus size={16} />
          New Check
        </Link>
      )}
    </div>
  );
}
