'use client';

import Link from 'next/link';
import { Home, PlusCircle, History } from 'lucide-react';

export function NavigationSection() {
  return (
    <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
      <div className="grid grid-cols-3 gap-4">
        {/* Home Button */}
        <Link
          href="/dashboard"
          className="flex items-center justify-center gap-2 px-4 py-3 bg-[#f57a07] hover:bg-[#e06a00] text-white rounded-lg font-bold transition-all shadow-lg hover:shadow-xl"
        >
          <Home size={20} />
          <span>Home</span>
        </Link>

        {/* New Check Button */}
        <Link
          href="/dashboard/new-check"
          className="flex items-center justify-center gap-2 px-4 py-3 bg-[#f57a07] hover:bg-[#e06a00] text-white rounded-lg font-bold transition-all shadow-lg hover:shadow-xl"
        >
          <PlusCircle size={20} />
          <span>New Check</span>
        </Link>

        {/* History Button */}
        <Link
          href="/dashboard/history"
          className="flex items-center justify-center gap-2 px-4 py-3 bg-[#f57a07] hover:bg-[#e06a00] text-white rounded-lg font-bold transition-all shadow-lg hover:shadow-xl"
        >
          <History size={20} />
          <span>History</span>
        </Link>
      </div>
    </div>
  );
}
