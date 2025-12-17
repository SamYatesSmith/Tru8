import Link from 'next/link';
import { Plus, Lock } from 'lucide-react';
import { GlowingBorderCard } from './glowing-border-card';

interface QuickActionCardProps {
  used?: number;
  limit?: number;
}

export function QuickActionCard({ used = 0, limit = 3 }: QuickActionCardProps) {
  const isLimitReached = used >= limit;

  return (
    <GlowingBorderCard className="h-full">
      <div className="p-8 h-full">
        <h3 className="text-xl font-bold text-white mb-2">Quick Action</h3>
        <p className="text-slate-400 mb-6">Start a new fact-check verification</p>

        {isLimitReached ? (
          <div className="space-y-4">
            <div className="bg-amber-900/20 border border-amber-700 rounded-lg px-4 py-3 text-amber-400 text-sm flex items-start gap-2">
              <Lock size={16} className="flex-shrink-0 mt-0.5" />
              <span>Monthly limit reached ({used}/{limit} checks). Upgrade to continue.</span>
            </div>
            <Link
              href="/dashboard/settings?tab=subscription"
              className="w-full bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 text-white font-bold py-4 rounded-xl flex items-center justify-center gap-2 transition-all"
            >
              Upgrade Now
            </Link>
          </div>
        ) : (
          <Link
            href="/dashboard/new-check"
            className="w-full bg-[#f57a07] hover:bg-[#e06a00] text-white font-bold py-4 rounded-xl flex items-center justify-center gap-2 transition-colors"
          >
            <Plus size={20} />
            New Check
          </Link>
        )}
      </div>
    </GlowingBorderCard>
  );
}
