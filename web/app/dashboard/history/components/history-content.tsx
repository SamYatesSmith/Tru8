'use client';

import { useState, useMemo, useEffect } from 'react';
import { useAuth } from '@clerk/nextjs';
import { Search } from 'lucide-react';
import { apiClient } from '@/lib/api';
import { CheckCard } from '../../components/check-card';
import { EmptyState } from '../../components/empty-state';
import { LoadingSpinner } from '../../components/loading-spinner';

const LAST_SEEN_CHECK_KEY = 'tru8_last_seen_check';

interface Check {
  id: string;
  status: string;
  inputUrl: string | null;
  createdAt: string;
  claimsCount: number;
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

interface HistoryContentProps {
  initialChecks: {
    checks: Check[];
    total: number;
  };
}

export function HistoryContent({ initialChecks }: HistoryContentProps) {
  const { getToken } = useAuth();
  const [checks, setChecks] = useState<Check[]>(initialChecks.checks);
  const [total] = useState(initialChecks.total);
  const [isLoading, setIsLoading] = useState(false);
  const [newCheckId, setNewCheckId] = useState<string | null>(null);

  // Filter states
  const [searchQuery, setSearchQuery] = useState('');
  const [elementStateFilter, setElementStateFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');

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

  // Load more checks
  const handleLoadMore = async () => {
    setIsLoading(true);
    try {
      const token = await getToken();
      const newChecks = await apiClient.getChecks(token, checks.length, 20) as any;
      setChecks([...checks, ...newChecks.checks]);
    } catch (error) {
      console.error('Failed to load more checks:', error);
    } finally {
      setIsLoading(false);
    }
  };

  // Apply filters
  const filteredChecks = useMemo(() => {
    return checks.filter(check => {
      // Search filter
      if (searchQuery) {
        const query = searchQuery.toLowerCase();
        const matchesText = check.claims?.some((claim) =>
          claim.text.toLowerCase().includes(query)
        );
        const matchesUrl = check.inputUrl?.toLowerCase().includes(query);
        if (!matchesText && !matchesUrl) return false;
      }

      // Element state filter
      if (elementStateFilter !== 'all') {
        const allElements = check.claims?.flatMap(
          (claim) => claim.claimMap?.elements ?? []
        ) ?? [];

        if (allElements.length === 0) return false;

        if (elementStateFilter === 'has_disputed') {
          const hasDisputed = allElements.some((el) => el.state === 'disputed');
          if (!hasDisputed) return false;
        } else if (elementStateFilter === 'has_unresolved') {
          const hasUnresolved = allElements.some(
            (el) => el.state === 'unresolved' || el.state === null
          );
          if (!hasUnresolved) return false;
        } else if (elementStateFilter === 'all_supported') {
          const allSupported = allElements.every((el) => el.state === 'supported');
          if (!allSupported) return false;
        }
      }

      // Status filter
      if (statusFilter !== 'all' && check.status !== statusFilter) {
        return false;
      }

      return true;
    });
  }, [checks, searchQuery, elementStateFilter, statusFilter]);

  const hasMore = checks.length < total;
  const isFiltering = searchQuery || elementStateFilter !== 'all' || statusFilter !== 'all';

  return (
    <div className="space-y-8">
      {/* Search & Filter Card */}
      <div className="bg-white border border-zinc-200 p-6">
        <h4 className="font-mono text-[10px] font-bold tracking-[0.3em] uppercase text-zinc-400 mb-4">Search &amp; Filter</h4>

        <div className="flex flex-col md:flex-row gap-4">
          {/* Search Input */}
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400" size={20} />
            <input
              type="text"
              placeholder="Search checks..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-white border border-zinc-200 pl-10 pr-4 py-2 text-zinc-900 placeholder:text-zinc-400 focus:outline-none focus:border-black transition-colors"
            />
          </div>

          {/* Element State Filter */}
          <select
            value={elementStateFilter}
            onChange={(e) => setElementStateFilter(e.target.value)}
            className="bg-white border border-zinc-200 px-4 py-2 text-zinc-900 focus:outline-none focus:border-black transition-colors"
          >
            <option value="all">All States</option>
            <option value="has_disputed">Has Disputed</option>
            <option value="has_unresolved">Has Unresolved</option>
            <option value="all_supported">All Supported</option>
          </select>

          {/* Status Filter */}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-white border border-zinc-200 px-4 py-2 text-zinc-900 focus:outline-none focus:border-black transition-colors"
          >
            <option value="all">All Status</option>
            <option value="completed">Completed</option>
            <option value="processing">Processing</option>
            <option value="pending">Pending</option>
            <option value="failed">Failed</option>
          </select>
        </div>
      </div>

      {/* Checks List */}
      {filteredChecks.length === 0 ? (
        <EmptyState
          icon={<Search size={48} className="text-zinc-300" />}
          message={isFiltering ? "No checks found" : "No checks yet"}
          submessage={isFiltering ? "Try adjusting your search or filters" : "Start your first analysis!"}
        />
      ) : (
        <div className="space-y-4">
          {filteredChecks.map(check => (
            <CheckCard key={check.id} check={check} isNew={check.id === newCheckId} />
          ))}
        </div>
      )}

      {/* Load More Button */}
      {hasMore && !isLoading && filteredChecks.length > 0 && (
        <div className="flex flex-col items-center gap-3">
          <button
            onClick={handleLoadMore}
            className="bg-zinc-900 hover:bg-zinc-800 text-white text-xs font-bold uppercase tracking-[0.2em] px-8 py-3 transition-colors"
          >
            Load More
          </button>
          <p className="text-sm text-zinc-400 font-mono">
            Showing {checks.length} of {total} checks
          </p>
        </div>
      )}

      {/* Loading State */}
      {isLoading && <LoadingSpinner message="Loading more checks..." />}
    </div>
  );
}
