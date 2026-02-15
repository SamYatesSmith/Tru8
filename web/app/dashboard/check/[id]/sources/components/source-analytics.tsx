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
  totalReviewed: number;
  totalCited: number;
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

    return Object.entries(counts)
      .map(([name, data]) => ({ name, count: data.count, isApi: data.isApi }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 8);
  }, [claims]);

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
    if (newsCount > 0) types.push({ type: 'News Articles', count: newsCount, color: 'bg-zinc-400' });
    if (officialDataCount > 0) types.push({ type: 'Official Data', count: officialDataCount, color: 'bg-emerald-500' });
    if (factCheckCount > 0) types.push({ type: 'Fact-Checks', count: factCheckCount, color: 'bg-amber-500' });

    return types;
  }, [claims]);

  const maxPublisherCount = Math.max(...publisherDistribution.map(p => p.count), 1);
  const totalSourceTypes = sourceTypeDistribution.reduce((sum, t) => sum + t.count, 0);
  const filteredCount = totalReviewed - totalCited;

  return (
    <div className="bg-white border border-zinc-200 p-6 mb-6">
      <h3 className="text-lg font-bold text-zinc-900 mb-6">Source Analytics</h3>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: Evidence Funnel */}
        <div className="bg-zinc-50 p-5">
          <h4 className="font-mono text-[10px] font-bold tracking-widest uppercase text-zinc-400 mb-4">Evidence Reviewed</h4>

          <div className="space-y-4">
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-2 text-zinc-500">
                  <FileText className="w-4 h-4" />
                  <span>Sources Reviewed</span>
                </div>
                <span className="font-mono font-bold text-zinc-900">{totalReviewed}</span>
              </div>
              <div className="h-2 bg-zinc-200 overflow-hidden">
                <div
                  className="h-full bg-zinc-400 transition-all duration-700"
                  style={{ width: '100%' }}
                />
              </div>
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-2 text-zinc-500">
                  <Filter className="w-4 h-4" />
                  <span>Filtered Out</span>
                </div>
                <span className="font-mono font-bold text-zinc-500">{filteredCount}</span>
              </div>
              <div className="h-2 bg-zinc-200 overflow-hidden">
                <div
                  className="h-full bg-zinc-300 transition-all duration-700"
                  style={{ width: `${(filteredCount / totalReviewed) * 100}%` }}
                />
              </div>
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-2 text-zinc-500">
                  <CheckCircle2 className="w-4 h-4" />
                  <span>Sources Cited</span>
                </div>
                <span className="font-mono font-bold text-emerald-600">{totalCited}</span>
              </div>
              <div className="h-2 bg-zinc-200 overflow-hidden">
                <div
                  className="h-full bg-emerald-500 transition-all duration-700"
                  style={{ width: `${(totalCited / totalReviewed) * 100}%` }}
                />
              </div>
            </div>
          </div>

          <p className="text-xs text-zinc-400 mt-4 leading-relaxed">
            {totalReviewed} sources were reviewed. {totalCited} met the relevance criteria for citation.
          </p>
        </div>

        {/* Right: Publisher Distribution */}
        <div className="bg-zinc-50 p-5">
          <h4 className="font-mono text-[10px] font-bold tracking-widest uppercase text-zinc-400 mb-4">Sources Cited</h4>

          {publisherDistribution.length > 0 ? (
            <div className="space-y-3">
              {publisherDistribution.map((publisher) => (
                <div key={publisher.name} className="space-y-1">
                  <div className="flex items-center justify-between text-sm">
                    <div className="flex items-center gap-2">
                      <span className="text-zinc-600 truncate max-w-[180px]" title={publisher.name}>
                        {publisher.name}
                      </span>
                      {publisher.isApi && (
                        <span className="px-1.5 py-0.5 bg-emerald-50 text-emerald-700 border border-emerald-200 text-[10px] font-bold uppercase">
                          API
                        </span>
                      )}
                    </div>
                    <span className="text-zinc-400 font-mono font-medium">{publisher.count}</span>
                  </div>
                  <div className="h-1.5 bg-zinc-200 overflow-hidden">
                    <div
                      className={`h-full transition-all duration-500 ${
                        publisher.isApi ? 'bg-emerald-500' : 'bg-zinc-400'
                      }`}
                      style={{ width: `${(publisher.count / maxPublisherCount) * 100}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-zinc-400">No sources to display</p>
          )}
        </div>
      </div>

      {/* Source Types Row */}
      {sourceTypeDistribution.length > 1 && (
        <div className="mt-6 pt-6 border-t border-zinc-100">
          <h4 className="font-mono text-[10px] font-bold tracking-widest uppercase text-zinc-400 mb-4">Source Types</h4>
          <div className="flex items-center gap-6">
            {sourceTypeDistribution.map((sourceType) => (
              <div key={sourceType.type} className="flex items-center gap-3">
                <div className={`w-3 h-3 ${sourceType.color}`} />
                <div className="text-sm">
                  <span className="text-zinc-600">{sourceType.type}</span>
                  <span className="text-zinc-400 ml-2 font-mono">
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
