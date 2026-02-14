import { UserStats } from '@/lib/api';

interface UserInsightsCardProps {
  stats: UserStats;
}

export function UserInsightsCard({ stats }: UserInsightsCardProps) {
  const breakdown = stats.elementStateBreakdown;
  const totalElements = breakdown
    ? breakdown.supported + breakdown.disputed + breakdown.unresolved
    : 0;

  // Calculate percentages for element state breakdown
  const supportedPct = totalElements > 0
    ? Math.round((breakdown.supported / totalElements) * 100)
    : 0;
  const disputedPct = totalElements > 0
    ? Math.round((breakdown.disputed / totalElements) * 100)
    : 0;
  const unresolvedPct = totalElements > 0
    ? Math.round((breakdown.unresolved / totalElements) * 100)
    : 0;

  // Get top 4 domains sorted by count
  const sortedDomains = Object.entries(stats.domainBreakdown)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 4);
  const maxDomainCount = sortedDomains.length > 0 ? sortedDomains[0][1] : 1;

  // Format member since date
  const memberSince = stats.memberSince
    ? new Date(stats.memberSince).toLocaleDateString('en-GB', {
        month: 'short',
        year: 'numeric'
      })
    : 'Unknown';

  return (
    <div className="mb-12">
      {/* Header outside container - matches Recent Checks styling */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold text-white">Your Insights</h2>
          <p className="text-slate-400">Track your analysis patterns</p>
        </div>
      </div>

      {/* Content container */}
      <div className="bg-[#1a1f2e] border border-slate-700 rounded-xl p-6 space-y-6">
        {/* Top Stats Row */}
      <div className="grid grid-cols-3 gap-4">
        <StatBox
          value={stats.totalChecks}
          label="Total Checks"
        />
        <StatBox
          value={stats.totalSourcesAnalyzed}
          label="Sources Analyzed"
        />
        <StatBox
          value={stats.totalElementsAnalysed ?? totalElements}
          label="Elements Analysed"
        />
      </div>

      {/* Two Column Layout */}
      <div className="grid md:grid-cols-2 gap-6">
        {/* Analysis Insights */}
        <div className="space-y-3">
          <h4 className="text-sm font-semibold text-slate-400 uppercase tracking-wide">
            Analysis Insights
          </h4>
          {totalElements > 0 ? (
            <div className="space-y-2">
              <StateBar
                label="Supported"
                count={breakdown.supported}
                percentage={supportedPct}
                barClass="bg-state-supported"
                textClass="text-state-supported"
              />
              <StateBar
                label="Disputed"
                count={breakdown.disputed}
                percentage={disputedPct}
                barClass="bg-state-disputed"
                textClass="text-state-disputed"
              />
              <StateBar
                label="Unresolved"
                count={breakdown.unresolved}
                percentage={unresolvedPct}
                barClass="bg-state-unresolved"
                textClass="text-state-unresolved"
              />
            </div>
          ) : (
            <p className="text-sm text-slate-500">No element data yet</p>
          )}
        </div>

        {/* Domain Breakdown */}
        <div className="space-y-3">
          <h4 className="text-sm font-semibold text-slate-400 uppercase tracking-wide">
            Top Domains
          </h4>
          {sortedDomains.length > 0 ? (
            <div className="space-y-2">
              {sortedDomains.map(([domain, count]) => (
                <DomainBar
                  key={domain}
                  domain={domain}
                  count={count}
                  maxCount={maxDomainCount}
                />
              ))}
            </div>
          ) : (
            <p className="text-sm text-slate-500">No domain data yet</p>
          )}
        </div>
      </div>

        {/* Footer Stats */}
        <div className="flex items-center justify-between pt-4 border-t border-slate-700/50 text-sm text-slate-400">
          <span>Member since {memberSince}</span>
        </div>
      </div>
    </div>
  );
}

// Stat Box Component
function StatBox({ value, label }: { value: string | number; label: string }) {
  return (
    <div className="bg-slate-800/50 rounded-lg p-4 text-center">
      <div className="text-3xl font-bold text-white">{value}</div>
      <div className="text-xs text-slate-400 mt-1">{label}</div>
    </div>
  );
}

// Element State Progress Bar Component
function StateBar({
  label,
  count,
  percentage,
  barClass,
  textClass
}: {
  label: string;
  count: number;
  percentage: number;
  barClass: string;
  textClass: string;
}) {
  return (
    <div className="flex items-center gap-3">
      <span className={`w-2 h-2 rounded-full ${barClass} flex-shrink-0`} />
      <div className="flex-1">
        <div className="flex items-center justify-between mb-1">
          <span className="text-sm text-slate-300">{label}</span>
          <span className="text-xs text-slate-500">{count} ({percentage}%)</span>
        </div>
        <div className="h-1.5 bg-slate-700 rounded-full overflow-hidden">
          <div
            className={`h-full ${barClass} transition-all duration-500`}
            style={{ width: `${percentage}%` }}
          />
        </div>
      </div>
    </div>
  );
}

// Domain Progress Bar Component
function DomainBar({
  domain,
  count,
  maxCount
}: {
  domain: string;
  count: number;
  maxCount: number;
}) {
  const percentage = Math.round((count / maxCount) * 100);

  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <span className="text-sm text-slate-300">{domain}</span>
        <span className="text-xs text-slate-500">{count}</span>
      </div>
      <div className="h-1.5 bg-slate-700 rounded-full overflow-hidden">
        <div
          className="h-full bg-blue-500 transition-all duration-500"
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}
