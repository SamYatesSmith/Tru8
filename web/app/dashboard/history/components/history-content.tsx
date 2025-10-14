'use client';

import { useState, useMemo } from 'react';
import { useAuth } from '@clerk/nextjs';
import { Search } from 'lucide-react';
import { apiClient } from '@/lib/api';
import { CheckCard } from '../../components/check-card';
import { EmptyState } from '../../components/empty-state';
import { LoadingSpinner } from '../../components/loading-spinner';

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

  // Filter states
  const [searchQuery, setSearchQuery] = useState('');
  const [verdictFilter, setVerdictFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');

  // Load more checks
  const handleLoadMore = async () => {
    setIsLoading(true);
    try {
      const token = await getToken();
      const newChecks = await apiClient.getChecks(token, checks.length, 20);
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

      // Verdict filter
      if (verdictFilter !== 'all') {
        const hasVerdict = check.claims?.some((claim) =>
          claim.verdict === verdictFilter
        );
        if (!hasVerdict) return false;
      }

      // Status filter
      if (statusFilter !== 'all' && check.status !== statusFilter) {
        return false;
      }

      return true;
    });
  }, [checks, searchQuery, verdictFilter, statusFilter]);

  const hasMore = checks.length < total;
  const isFiltering = searchQuery || verdictFilter !== 'all' || statusFilter !== 'all';

  return (
    <div className="space-y-8">
      {/* Search & Filter Card */}
      <div className="bg-[#1a1f2e] border border-slate-700 rounded-xl p-6">
        <div className="mb-4">
          <h3 className="text-xl font-bold text-white">Search & Filter</h3>
          <p className="text-slate-400 text-sm">Find specific verifications quickly</p>
        </div>

        <div className="flex flex-col md:flex-row gap-4">
          {/* Search Input */}
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={20} />
            <input
              type="text"
              placeholder="Search checks..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg pl-10 pr-4 py-2 text-white placeholder:text-slate-500 focus:outline-none focus:border-slate-600"
            />
          </div>

          {/* Verdict Filter */}
          <select
            value={verdictFilter}
            onChange={(e) => setVerdictFilter(e.target.value)}
            className="bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-slate-600"
          >
            <option value="all">All Verdicts</option>
            <option value="supported">Supported</option>
            <option value="contradicted">Contradicted</option>
            <option value="uncertain">Uncertain</option>
          </select>

          {/* Status Filter */}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-slate-600"
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
          icon={<Search size={48} className="text-slate-600" />}
          message={isFiltering ? "No checks found" : "No checks yet"}
          submessage={isFiltering ? "Try adjusting your search or filters" : "Start your first verification!"}
        />
      ) : (
        <div className="space-y-4">
          {filteredChecks.map(check => (
            <CheckCard key={check.id} check={check} />
          ))}
        </div>
      )}

      {/* Load More Button */}
      {hasMore && !isLoading && filteredChecks.length > 0 && (
        <div className="flex flex-col items-center gap-3">
          <button
            onClick={handleLoadMore}
            className="bg-slate-700 hover:bg-slate-600 text-white font-medium px-8 py-3 rounded-lg transition-colors"
          >
            Load More
          </button>
          <p className="text-sm text-slate-400">
            Showing {checks.length} of {total} checks
          </p>
        </div>
      )}

      {/* Loading State */}
      {isLoading && <LoadingSpinner message="Loading more checks..." />}
    </div>
  );
}
