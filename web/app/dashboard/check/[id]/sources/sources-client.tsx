'use client';

import { useState } from 'react';
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

interface Source {
  id: string;
  source: string;
  title: string;
  url: string;
  publishedDate: string | null;
  credibilityScore: number;
  relevanceScore: number;
  isIncluded: boolean;
  filterStage: string | null;
  filterReason: string | null;
  tier: string | null;
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
  const [expandedClaims, setExpandedClaims] = useState<Set<number>>(new Set([0])); // First claim expanded
  const [showFiltered, setShowFiltered] = useState(true);
  const [sortBy, setSortBy] = useState<'relevance' | 'credibility' | 'date'>('relevance');
  const [exporting, setExporting] = useState(false);

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

      // Create download link
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

    // Sort: included sources first, then filtered sources
    // Within each group, sort by relevance or date
    return [...filtered].sort((a, b) => {
      // Primary sort: included sources come first
      if (a.isIncluded !== b.isIncluded) {
        return a.isIncluded ? -1 : 1;
      }

      // Secondary sort: by date or relevance within each group
      if (sortBy === 'date') {
        if (!a.publishedDate) return 1;
        if (!b.publishedDate) return -1;
        return new Date(b.publishedDate).getTime() - new Date(a.publishedDate).getTime();
      }
      // Default: relevance (using internal score, not shown to user)
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
      <div className="flex flex-wrap items-center gap-4 p-4 bg-slate-800/50 border border-slate-700 rounded-xl">
        <div className="flex items-center gap-2">
          <Check className="w-4 h-4 text-emerald-400" />
          <span className="text-sm text-slate-300">
            <span className="font-semibold text-white">{sourcesData.includedCount}</span> included
          </span>
        </div>
        <div className="flex items-center gap-2">
          <X className="w-4 h-4 text-red-400" />
          <span className="text-sm text-slate-300">
            <span className="font-semibold text-white">{sourcesData.filteredCount}</span> filtered
          </span>
        </div>
        <div className="flex-1" />

        {/* Filters */}
        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowFiltered(!showFiltered)}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm transition-colors ${
              showFiltered
                ? 'bg-slate-700 text-white'
                : 'bg-slate-800 text-slate-400 hover:text-white'
            }`}
          >
            <Filter className="w-4 h-4" />
            {showFiltered ? 'Showing All' : 'Included Only'}
          </button>

          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as typeof sortBy)}
            className="px-3 py-1.5 bg-slate-800 border border-slate-600 rounded-lg text-sm text-white"
          >
            <option value="relevance">Sort: Relevance</option>
            <option value="date">Sort: Date</option>
          </select>

          {/* Export dropdown */}
          <div className="relative group">
            <button
              disabled={exporting}
              className="flex items-center gap-2 px-3 py-1.5 bg-blue-600 hover:bg-blue-500 rounded-lg text-sm text-white transition-colors disabled:opacity-50"
            >
              <Download className="w-4 h-4" />
              {exporting ? 'Exporting...' : 'Export'}
            </button>
            <div className="absolute right-0 mt-2 w-40 bg-slate-800 border border-slate-700 rounded-lg shadow-xl opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-10">
              <button
                onClick={() => handleExport('csv')}
                className="w-full px-4 py-2 text-left text-sm text-slate-300 hover:bg-slate-700 hover:text-white rounded-t-lg"
              >
                CSV
              </button>
              <button
                onClick={() => handleExport('bibtex')}
                className="w-full px-4 py-2 text-left text-sm text-slate-300 hover:bg-slate-700 hover:text-white"
              >
                BibTeX
              </button>
              <button
                onClick={() => handleExport('apa')}
                className="w-full px-4 py-2 text-left text-sm text-slate-300 hover:bg-slate-700 hover:text-white rounded-b-lg"
              >
                APA
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Summary note - no internal breakdown shown */}
      {sourcesData.filteredCount > 0 && (
        <div className="p-4 bg-slate-800/30 border border-slate-700/50 rounded-xl">
          <p className="text-sm text-slate-400">
            Sources are filtered based on relevance and editorial standards.
            Only high-quality, relevant sources are included in the analysis.
          </p>
        </div>
      )}

      {/* Claims with Sources */}
      <div className="space-y-4">
        {sourcesData.claims.map((claim) => {
          const isExpanded = expandedClaims.has(claim.claimPosition);
          const filteredSources = filterSources(claim.sources);

          return (
            <div
              key={claim.claimPosition}
              className="bg-slate-800/50 border border-slate-700 rounded-xl overflow-hidden"
            >
              {/* Claim Header */}
              <button
                onClick={() => toggleClaim(claim.claimPosition)}
                className="w-full px-6 py-4 flex items-start gap-4 text-left hover:bg-slate-800/70 transition-colors"
              >
                <span className="flex-shrink-0 w-8 h-8 bg-slate-700 rounded-full flex items-center justify-center text-sm font-semibold text-white">
                  {claim.claimPosition + 1}
                </span>
                <div className="flex-1 min-w-0">
                  <p className="text-white font-medium line-clamp-2">{claim.claimText}</p>
                  <p className="text-sm text-slate-400 mt-1">
                    {filteredSources.length} sources {!showFiltered && `(${claim.sourcesCount} total)`}
                  </p>
                </div>
                {isExpanded ? (
                  <ChevronUp className="w-5 h-5 text-slate-400 flex-shrink-0" />
                ) : (
                  <ChevronDown className="w-5 h-5 text-slate-400 flex-shrink-0" />
                )}
              </button>

              {/* Sources List */}
              {isExpanded && (
                <div className="border-t border-slate-700 divide-y divide-slate-700/50">
                  {filteredSources.map((source) => (
                    <div
                      key={source.id}
                      className={`px-6 py-4 ${
                        source.isIncluded ? 'bg-slate-800/30' : 'bg-slate-900/30 opacity-70'
                      }`}
                    >
                      <div className="flex items-start gap-4">
                        {/* Status icon */}
                        <div className="flex-shrink-0 mt-1">
                          {source.isIncluded ? (
                            <Check className="w-4 h-4 text-emerald-400" />
                          ) : (
                            <X className="w-4 h-4 text-red-400" />
                          )}
                        </div>

                        {/* Content */}
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            <a
                              href={source.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-blue-400 hover:text-blue-300 font-medium flex items-center gap-1"
                            >
                              {source.title.length > 80
                                ? source.title.slice(0, 80) + '...'
                                : source.title}
                              <ExternalLink className="w-3 h-3" />
                            </a>
                          </div>

                          <div className="flex items-center gap-3 mt-1 text-sm text-slate-400">
                            <span>{source.source}</span>
                            {source.publishedDate && (
                              <>
                                <span>·</span>
                                <span>{new Date(source.publishedDate).toLocaleDateString()}</span>
                              </>
                            )}
                            {source.isFactcheck && (
                              <span className="px-1.5 py-0.5 bg-amber-500/20 text-amber-400 border border-amber-500/30 rounded text-xs">
                                Fact-check
                              </span>
                            )}
                            {source.externalSourceProvider && (
                              <span className="px-1.5 py-0.5 bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 rounded text-xs">
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
