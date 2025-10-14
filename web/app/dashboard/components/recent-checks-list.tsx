import Link from 'next/link';
import { FileQuestion } from 'lucide-react';
import { CheckCard } from './check-card';
import { EmptyState } from './empty-state';

interface Check {
  id: string;
  status: string;
  inputUrl: string | null;
  createdAt: string;
  claims: Array<{
    text: string;
    verdict: 'supported' | 'contradicted' | 'uncertain';
    confidence: number;
  }>;
}

interface RecentChecksListProps {
  checks: Check[];
}

export function RecentChecksList({ checks }: RecentChecksListProps) {
  return (
    <div className="mb-12">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold text-white">Recent Checks</h2>
          <p className="text-slate-400">Your latest fact-checking verifications</p>
        </div>

        <Link href="/dashboard/history">
          <button className="bg-slate-700 hover:bg-slate-600 text-white px-4 py-2 rounded-lg transition-colors">
            View All
          </button>
        </Link>
      </div>

      {checks.length === 0 ? (
        <EmptyState
          icon={<FileQuestion size={48} className="text-slate-600" />}
          message="No checks yet"
          submessage="Start your first verification!"
        />
      ) : (
        <div className="space-y-4">
          {checks.map(check => (
            <CheckCard key={check.id} check={check} />
          ))}
        </div>
      )}
    </div>
  );
}
