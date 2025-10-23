import Link from 'next/link';
import { Plus } from 'lucide-react';

export function QuickActionCard() {
  return (
    <div className="bg-[#1a1f2e] border border-slate-700 rounded-xl p-8">
      <h3 className="text-xl font-bold text-white mb-2">Quick Action</h3>
      <p className="text-slate-400 mb-6">Start a new fact-check verification</p>

      <Link
        href="/dashboard/new-check"
        className="w-full bg-[#f57a07] hover:bg-[#e06a00] text-white font-bold py-4 rounded-xl flex items-center justify-center gap-2 transition-colors"
      >
        <Plus size={20} />
        New Check
      </Link>
    </div>
  );
}
