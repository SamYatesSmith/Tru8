'use client';

import Link from 'next/link';
import { Home, PlusCircle, History } from 'lucide-react';

export function NavigationSection() {
  return (
    <div className="bg-white border border-zinc-200 p-6">
      <div className="grid grid-cols-3 gap-4">
        <Link
          href="/dashboard"
          className="flex items-center justify-center gap-2 px-4 py-3 bg-zinc-900 hover:bg-zinc-800 text-white text-xs font-bold uppercase tracking-[0.2em] transition-colors"
        >
          <Home size={18} />
          <span>Home</span>
        </Link>

        <Link
          href="/dashboard/new-check"
          className="flex items-center justify-center gap-2 px-4 py-3 bg-zinc-900 hover:bg-zinc-800 text-white text-xs font-bold uppercase tracking-[0.2em] transition-colors"
        >
          <PlusCircle size={18} />
          <span>New Check</span>
        </Link>

        <Link
          href="/dashboard/history"
          className="flex items-center justify-center gap-2 px-4 py-3 bg-zinc-900 hover:bg-zinc-800 text-white text-xs font-bold uppercase tracking-[0.2em] transition-colors"
        >
          <History size={18} />
          <span>History</span>
        </Link>
      </div>
    </div>
  );
}
