'use client';

import { useMemo } from 'react';
import { FileText, CheckCircle2, Filter } from 'lucide-react';

interface Source {
  id: string;
  source: string;
  isIncluded: boolean;
  externalSourceProvider: string | null;
  isFactcheck: boolean;
}

interface ClaimSources {
  claimPosition: number;
  sources: Source[];
}

interface SourceAnalyticsProps {
  totalReviewed: number;  // All sources reviewed during fact-check
  totalCited: number;     // Sources included in analysis
  claims: ClaimSources[];
}

interface PublisherCount {
  name: string;
  count: number;
  isApi: boolean;
}

interface SourceTypeCount {
  type: string;
  count: number;
  color: string;
}

export function SourceAnalytics({
  totalReviewed,
  totalCited,
  claims
}: SourceAnalyticsProps) {
  // Compute publisher distribution from included sources only
  const publisherDistribution = useMemo(() => {
    const counts: Record<string, { count: number; isApi: boolean }> = {};

    claims.forEach(claim => {
      claim.sources
        .filter(s => s.isIncluded)
        .forEach(source => {
          const name = source.source;
          if (!counts[name]) {
            counts[name] = { count: 0, isApi: !!source.externalSourceProvider };
          }
          counts[name].count++;
        });
    });

    // Sort by count descending, take top 8
    return Object.entries(counts)
      .map(([name, data]) => ({ name, count: data.count, isApi: data.isApi }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 8);
  }, [claims]);

  // Compute source type distribution from included sources
  const sourceTypeDistribution = useMemo(() => {
    let newsCount = 0;
    let officialDataCount = 0;
    let factCheckCount = 0;

    claims.forEach(claim => {
      claim.sources
        .filter(s => s.isIncluded)
        .forEach(source => {
          if (source.isFactcheck) {
            factCheckCount++;
          } else if (source.externalSourceProvider) {
            officialDataCount++;
          } else {
            newsCount++;
          }
        });
    });

    const types: SourceTypeCount[] = [];
    if (newsCount > 0) types.push({ type: 'News Articles', count: newsCount, color: 'bg-blue-500' });
    if (officialDataCount > 0) types.push({ type: 'Official Data', count: officialDataCount, color: 'bg-cyan-500' });
    if (factCheckCount > 0) types.push({ type: 'Fact-Checks', count: factCheckCount, color: 'bg-purple-500' });

    return types;
  }, [claims]);

  const maxPublisherCount = Math.max(...publisherDistribution.map(p => p.count), 1);
  const totalSourceTypes = sourceTypeDistribution.reduce((sum, t) => sum + t.count, 0);
  const filteredCount = totalReviewed - totalCited;

  return (
    <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6 mb-6">
      <h3 className="text-lg font-bold text-white mb-6">Source Analytics</h3>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: Evidence Funnel */}
        <div className="bg-slate-900/50 rounded-lg p-5">
          <h4 className="text-sm font-semibold text-slate-300 mb-4">Evidence Reviewed</h4>

          <div className="space-y-4">
            {/* Total Reviewed */}
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-2 text-slate-400">
                  <FileText className="w-4 h-4" />
                  <span>Sources Reviewed</span>
                </div>
                <span className="font-semibold text-white">{totalReviewed}</span>
              </div>
              <div className="h-3 bg-slate-700 rounded-full overflow-hidden">
                <div
                  className="h-full bg-slate-500 rounded-full transition-all duration-700"
                  style={{ width: '100%' }}
                />
              </div>
            </div>

            {/* Filtered Out */}
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-2 text-slate-400">
                  <Filter className="w-4 h-4" />
                  <span>Filtered Out</span>
                </div>
                <span className="font-semibold text-slate-400">{filteredCount}</span>
              </div>
              <div className="h-3 bg-slate-700 rounded-full overflow-hidden">
                <div
                  className="h-full bg-slate-600 rounded-full transition-all duration-700"
                  style={{ width: `${(filteredCount / totalReviewed) * 100}%` }}
                />
              </div>
            </div>

            {/* Cited */}
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-2 text-slate-400">
                  <CheckCircle2 className="w-4 h-4" />
                  <span>Sources Cited</span>
                </div>
                <span className="font-semibold text-emerald-400">{totalCited}</span>
              </div>
              <div className="h-3 bg-slate-700 rounded-full overflow-hidden">
                <div
                  className="h-full bg-emerald-500 rounded-full transition-all duration-700"
                  style={{ width: `${(totalCited / totalReviewed) * 100}%` }}
                />
              </div>
            </div>
          </div>

          {/* Summary text */}
          <p className="text-xs text-slate-500 mt-4 leading-relaxed">
            {totalReviewed} sources were reviewed. {totalCited} met the relevance criteria for citation.
          </p>
        </div>

        {/* Right: Publisher Distribution */}
        <div className="bg-slate-900/50 rounded-lg p-5">
          <h4 className="text-sm font-semibold text-slate-300 mb-4">Sources Cited</h4>

          {publisherDistribution.length > 0 ? (
            <div className="space-y-3">
              {publisherDistribution.map((publisher) => (
                <div key={publisher.name} className="space-y-1">
                  <div className="flex items-center justify-between text-sm">
                    <div className="flex items-center gap-2">
                      <span className="text-slate-300 truncate max-w-[180px]" title={publisher.name}>
                        {publisher.name}
                      </span>
                      {publisher.isApi && (
                        <span className="px-1.5 py-0.5 bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 rounded text-xs">
                          API
                        </span>
                      )}
                    </div>
                    <span className="text-slate-400 font-medium">{publisher.count}</span>
                  </div>
                  <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-500 ${
                        publisher.isApi ? 'bg-cyan-500' : 'bg-blue-500'
                      }`}
                      style={{ width: `${(publisher.count / maxPublisherCount) * 100}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-slate-500">No sources to display</p>
          )}
        </div>
      </div>

      {/* Source Types Row */}
      {sourceTypeDistribution.length > 1 && (
        <div className="mt-6 pt-6 border-t border-slate-700">
          <h4 className="text-sm font-semibold text-slate-300 mb-4">Source Types</h4>
          <div className="flex items-center gap-6">
            {sourceTypeDistribution.map((sourceType) => (
              <div key={sourceType.type} className="flex items-center gap-3">
                <div className={`w-3 h-3 rounded-full ${sourceType.color}`} />
                <div className="text-sm">
                  <span className="text-slate-300">{sourceType.type}</span>
                  <span className="text-slate-500 ml-2">
                    {sourceType.count} ({Math.round((sourceType.count / totalSourceTypes) * 100)}%)
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
