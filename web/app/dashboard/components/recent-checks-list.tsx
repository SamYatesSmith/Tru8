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
  credibilityScore: number | null;
  claimsSupported: number;
  claimsContradicted: number;
  claimsUncertain: number;
  articleDomain: string | null;
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
  const [newCheckId, setNewCheckId] = useState<string | null>(null);

  // Track seen checks - highlight newest if it's different from last seen
  useEffect(() => {
    if (checks.length === 0) return;

    const firstCompletedCheck = checks.find(c => c.status === 'completed' && c.claims?.length > 0);
    if (!firstCompletedCheck) return;

    const lastSeenCheckId = localStorage.getItem(LAST_SEEN_CHECK_KEY);

    // If the first completed check is different from last seen, it's new
    if (lastSeenCheckId !== firstCompletedCheck.id) {
      setNewCheckId(firstCompletedCheck.id);
      // Update localStorage with the new first check
      localStorage.setItem(LAST_SEEN_CHECK_KEY, firstCompletedCheck.id);
    }
  }, [checks]);

  return (
    <div className="mb-12">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold text-white">Recent Checks</h2>
          <p className="text-slate-400">Your latest fact-checking verifications</p>
        </div>

        <Link
          href="/dashboard/history"
          className="bg-slate-700 hover:bg-slate-600 text-white px-4 py-2 rounded-lg transition-colors inline-block"
        >
          View All
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
            <CheckCard key={check.id} check={check} isNew={check.id === newCheckId} />
          ))}
        </div>
      )}
    </div>
  );
}
