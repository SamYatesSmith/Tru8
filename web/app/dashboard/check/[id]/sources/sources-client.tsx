'use client';

import { useState, useEffect } from 'react';
import { useAuth } from '@clerk/nextjs';
import { CheckTabs } from '../components/check-tabs';
import { apiClient } from '@/lib/api';
import {
  ChevronDown,
  ChevronUp,
  ExternalLink,
  Check,
  X,
  Download,
  Filter
} from 'lucide-react';
import { SourceAnalytics } from './components/source-analytics';

interface Source {
  id: string;
  source: string;
  title: string;
  url: string;
  publishedDate: string | null;
  relevanceScore: number;
  isIncluded: boolean;
  filterStage: string | null;
  filterReason: string | null;
  isFactcheck: boolean;
  externalSourceProvider: string | null;
}

interface ClaimSources {
  claimPosition: number;
  claimText: string;
  sourcesCount: number;
  sources: Source[];
}

interface SourcesData {
  checkId: string;
  totalSources: number;
  includedCount: number;
  filteredCount: number;
  legacyCheck: boolean;
  claims: ClaimSources[];
  filterBreakdown: Record<string, number>;
}

interface SourcesClientProps {
  checkId: string;
  initialData: SourcesData;
}

export function SourcesClient({ checkId, initialData }: SourcesClientProps) {
  const { getToken } = useAuth();
  const [sourcesData] = useState(initialData);
  const [expandedClaims, setExpandedClaims] = useState<Set<number>>(new Set([0]));
  const [showFiltered, setShowFiltered] = useState(true);
  const [sortBy, setSortBy] = useState<'relevance' | 'credibility' | 'date'>('relevance');
  const [exporting, setExporting] = useState(false);

  // Handle deep linking: auto-expand and scroll to claim from URL hash
  useEffect(() => {
    const hash = window.location.hash;
    if (hash && hash.startsWith('#claim-')) {
      const claimPosition = parseInt(hash.replace('#claim-', ''), 10);
      if (!isNaN(claimPosition)) {
        setExpandedClaims(new Set([claimPosition]));
        setTimeout(() => {
          const element = document.getElementById(`claim-${claimPosition}`);
          element?.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }, 100);
      }
    }
  }, []);

  const toggleClaim = (position: number) => {
    const newExpanded = new Set(expandedClaims);
    if (newExpanded.has(position)) {
      newExpanded.delete(position);
    } else {
      newExpanded.add(position);
    }
    setExpandedClaims(newExpanded);
  };

  const handleExport = async (format: 'csv' | 'bibtex' | 'apa') => {
    setExporting(true);
    try {
      const token = await getToken();
      const blob = await apiClient.exportCheckSources(checkId, format, showFiltered, token);

      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `tru8-sources-${checkId.slice(0, 8)}.${format === 'bibtex' ? 'bib' : format === 'apa' ? 'txt' : format}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Export failed:', error);
    } finally {
      setExporting(false);
    }
  };

  const filterSources = (sources: Source[]): Source[] => {
    let filtered = sources;

    if (!showFiltered) {
      filtered = filtered.filter(s => s.isIncluded);
    }

    return [...filtered].sort((a, b) => {
      if (a.isIncluded !== b.isIncluded) {
        return a.isIncluded ? -1 : 1;
      }

      if (sortBy === 'date') {
        if (!a.publishedDate) return 1;
        if (!b.publishedDate) return -1;
        return new Date(b.publishedDate).getTime() - new Date(a.publishedDate).getTime();
      }
      return b.relevanceScore - a.relevanceScore;
    });
  };

  return (
    <div className="space-y-6">
      {/* Tab Toggle */}
      <CheckTabs
        checkId={checkId}
        sourcesCount={sourcesData.totalSources}
        isPro={true}
        isCompleted={true}
      />

      {/* Stats Bar */}
      <div className="flex flex-wrap items-center gap-4 p-4 bg-white border border-zinc-200">
        <div className="flex items-center gap-2">
          <Check className="w-4 h-4 text-emerald-500" />
          <span className="text-sm text-zinc-500">
            <span className="font-semibold text-zinc-900">{sourcesData.includedCount}</span> included
          </span>
        </div>
        <div className="flex items-center gap-2">
          <X className="w-4 h-4 text-red-400" />
          <span className="text-sm text-zinc-500">
            <span className="font-semibold text-zinc-900">{sourcesData.filteredCount}</span> filtered
          </span>
        </div>
        <div className="flex-1" />

        {/* Filters */}
        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowFiltered(!showFiltered)}
            className={`flex items-center gap-2 px-3 py-1.5 text-sm transition-colors border ${
              showFiltered
                ? 'bg-zinc-900 text-white border-zinc-900'
                : 'bg-white text-zinc-500 border-zinc-200 hover:text-zinc-900'
            }`}
          >
            <Filter className="w-4 h-4" />
            {showFiltered ? 'Showing All' : 'Included Only'}
          </button>

          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as typeof sortBy)}
            className="px-3 py-1.5 bg-white border border-zinc-200 text-sm text-zinc-900"
          >
            <option value="relevance">Sort: Relevance</option>
            <option value="date">Sort: Date</option>
          </select>

          {/* Export dropdown */}
          <div className="relative group">
            <button
              disabled={exporting}
              className="flex items-center gap-2 px-3 py-1.5 bg-zinc-900 hover:bg-zinc-800 text-white text-xs font-bold uppercase tracking-[0.2em] transition-colors disabled:opacity-50"
            >
              <Download className="w-4 h-4" />
              {exporting ? 'Exporting...' : 'Export'}
            </button>
            <div className="absolute right-0 mt-2 w-40 bg-white border border-zinc-200 shadow-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-10">
              <button
                onClick={() => handleExport('csv')}
                className="w-full px-4 py-2 text-left text-sm text-zinc-600 hover:bg-zinc-50 hover:text-zinc-900"
              >
                CSV
              </button>
              <button
                onClick={() => handleExport('bibtex')}
                className="w-full px-4 py-2 text-left text-sm text-zinc-600 hover:bg-zinc-50 hover:text-zinc-900"
              >
                BibTeX
              </button>
              <button
                onClick={() => handleExport('apa')}
                className="w-full px-4 py-2 text-left text-sm text-zinc-600 hover:bg-zinc-50 hover:text-zinc-900"
              >
                APA
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Source Analytics */}
      {sourcesData.totalSources > 0 && (
        <SourceAnalytics
          totalReviewed={sourcesData.totalSources}
          totalCited={sourcesData.includedCount}
          claims={sourcesData.claims}
        />
      )}

      {/* Claims with Sources */}
      <div className="space-y-4">
        {sourcesData.claims.map((claim) => {
          const isExpanded = expandedClaims.has(claim.claimPosition);
          const filteredSources = filterSources(claim.sources);

          return (
            <div
              key={claim.claimPosition}
              id={`claim-${claim.claimPosition}`}
              className="bg-white border border-zinc-200 overflow-hidden scroll-mt-4"
            >
              {/* Claim Header */}
              <button
                onClick={() => toggleClaim(claim.claimPosition)}
                className="w-full px-6 py-4 flex items-start gap-4 text-left hover:bg-zinc-50 transition-colors"
              >
                <span className="flex-shrink-0 w-8 h-8 bg-zinc-100 flex items-center justify-center font-mono text-sm font-bold text-zinc-900">
                  {String(claim.claimPosition + 1).padStart(2, '0')}
                </span>
                <div className="flex-1 min-w-0">
                  <p className="text-zinc-900 font-medium line-clamp-2">{claim.claimText}</p>
                  <p className="text-sm text-zinc-400 mt-1 font-mono text-[10px] tracking-widest uppercase">
                    {filteredSources.length} sources {!showFiltered && `(${claim.sourcesCount} total)`}
                  </p>
                </div>
                {isExpanded ? (
                  <ChevronUp className="w-5 h-5 text-zinc-400 flex-shrink-0" />
                ) : (
                  <ChevronDown className="w-5 h-5 text-zinc-400 flex-shrink-0" />
                )}
              </button>

              {/* Sources List */}
              {isExpanded && (
                <div className="border-t border-zinc-100 divide-y divide-zinc-100">
                  {filteredSources.map((source) => (
                    <div
                      key={source.id}
                      className={`px-6 py-4 ${
                        source.isIncluded ? 'bg-white' : 'bg-zinc-50 opacity-70'
                      }`}
                    >
                      <div className="flex items-start gap-4">
                        <div className="flex-shrink-0 mt-1">
                          {source.isIncluded ? (
                            <Check className="w-4 h-4 text-emerald-500" />
                          ) : (
                            <X className="w-4 h-4 text-red-400" />
                          )}
                        </div>

                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            <a
                              href={source.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-zinc-900 hover:text-accent font-medium flex items-center gap-1"
                            >
                              {source.title.length > 80
                                ? source.title.slice(0, 80) + '...'
                                : source.title}
                              <ExternalLink className="w-3 h-3" />
                            </a>
                          </div>

                          <div className="flex items-center gap-3 mt-1 font-mono text-[10px] text-zinc-400">
                            <span>{source.source}</span>
                            {source.publishedDate && (
                              <>
                                <span>&middot;</span>
                                <span>{new Date(source.publishedDate).toLocaleDateString()}</span>
                              </>
                            )}
                            {source.isFactcheck && (
                              <span className="px-1.5 py-0.5 bg-amber-50 text-amber-700 border border-amber-200 font-bold uppercase">
                                Fact-check
                              </span>
                            )}
                            {source.externalSourceProvider && (
                              <span className="px-1.5 py-0.5 bg-emerald-50 text-emerald-700 border border-emerald-200 font-bold uppercase">
                                {source.externalSourceProvider}
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
