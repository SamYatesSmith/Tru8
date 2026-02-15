'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { FileQuestion } from 'lucide-react';
import { CheckCard } from './check-card';
import { EmptyState } from './empty-state';

const LAST_SEEN_CHECK_KEY = 'tru8_last_seen_check';

interface Check {
  id: string;
  status: string;
  inputUrl: string | null;
  createdAt: string;
  claimsCount: number;
  overallSummary: string | null;
  articleDomain: string | null;
  claims: Array<{
    text: string;
    claimMap?: {
      elements: Array<{
        state: 'supported' | 'disputed' | 'unresolved' | null;
      }>;
    };
  }>;
}

interface RecentChecksListProps {
  checks: Check[];
}

export function RecentChecksList({ checks }: RecentChecksListProps) {
  const [newCheckId, setNewCheckId] = useState<string | null>(null);

  useEffect(() => {
    if (checks.length === 0) return;

    const firstCompletedCheck = checks.find(c => c.status === 'completed' && c.claims?.length > 0);
    if (!firstCompletedCheck) return;

    const lastSeenCheckId = localStorage.getItem(LAST_SEEN_CHECK_KEY);

    if (lastSeenCheckId !== firstCompletedCheck.id) {
      setNewCheckId(firstCompletedCheck.id);
      localStorage.setItem(LAST_SEEN_CHECK_KEY, firstCompletedCheck.id);
    }
  }, [checks]);

  return (
    <div className="mb-12">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-lg font-bold text-zinc-900">Recent Checks</h2>
          <p className="text-zinc-500 text-sm">Your latest analyses</p>
        </div>

        <Link
          href="/dashboard/history"
          className="text-xs font-bold uppercase tracking-[0.2em] text-zinc-500 hover:text-zinc-900 px-4 py-2 border border-zinc-200 hover:border-zinc-900 transition-colors"
        >
          View All
        </Link>
      </div>

      {checks.length === 0 ? (
        <EmptyState
          icon={<FileQuestion size={48} className="text-zinc-300" />}
          message="No checks yet"
          submessage="Start your first evidence check!"
        />
      ) : (
        <div className="space-y-4">
          {checks.map(check => (
            <CheckCard key={check.id} check={check} isNew={check.id === newCheckId} />
          ))}
        </div>
      )}
    </div>
  );
}
