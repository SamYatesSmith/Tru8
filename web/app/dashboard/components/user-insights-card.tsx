import { UserStats } from '@/lib/api';
import { CheckCircle, XCircle, HelpCircle, BarChart3 } from 'lucide-react';

interface UserInsightsCardProps {
  stats: UserStats;
}

export function UserInsightsCard({ stats }: UserInsightsCardProps) {
  const totalClaims = stats.verdictBreakdown.supported +
    stats.verdictBreakdown.contradicted +
    stats.verdictBreakdown.uncertain;

  // Calculate percentages for verdict breakdown
  const supportedPct = totalClaims > 0
    ? Math.round((stats.verdictBreakdown.supported / totalClaims) * 100)
    : 0;
  const contradictedPct = totalClaims > 0
    ? Math.round((stats.verdictBreakdown.contradicted / totalClaims) * 100)
    : 0;
  const uncertainPct = totalClaims > 0
    ? Math.round((stats.verdictBreakdown.uncertain / totalClaims) * 100)
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
          <p className="text-slate-400">Track your fact-checking patterns</p>
        </div>
      </div>

      {/* Content container */}
      <div className="bg-[#1a1f2e] border border-slate-700 rounded-xl p-6 space-y-6">
        {/* Top Stats Row */}
      <div className="grid grid-cols-3 gap-4">
        <StatBox
          value={stats.totalChecks}
          label="Claims Verified"
        />
        <StatBox
          value={stats.totalSourcesAnalyzed}
          label="Sources Analyzed"
        />
        <StatBox
          value={`${Math.round(stats.averageConfidence)}%`}
          label="Avg Confidence"
        />
      </div>

      {/* Two Column Layout */}
      <div className="grid md:grid-cols-2 gap-6">
        {/* Verdict Breakdown */}
        <div className="space-y-3">
          <h4 className="text-sm font-semibold text-slate-400 uppercase tracking-wide">
            Verdict Breakdown
          </h4>
          <div className="space-y-2">
            <VerdictBar
              icon={<CheckCircle className="w-4 h-4 text-emerald-400" />}
              label="Supported"
              count={stats.verdictBreakdown.supported}
              percentage={supportedPct}
              color="bg-emerald-500"
            />
            <VerdictBar
              icon={<XCircle className="w-4 h-4 text-red-400" />}
              label="Contradicted"
              count={stats.verdictBreakdown.contradicted}
              percentage={contradictedPct}
              color="bg-red-500"
            />
            <VerdictBar
              icon={<HelpCircle className="w-4 h-4 text-amber-400" />}
              label="Uncertain"
              count={stats.verdictBreakdown.uncertain}
              percentage={uncertainPct}
              color="bg-amber-500"
            />
          </div>
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
          {stats.misinformationRate > 0 && (
            <span>
              <span className="text-red-400 font-medium">{stats.misinformationRate}%</span> misinformation detected
            </span>
          )}
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

// Verdict Progress Bar Component
function VerdictBar({
  icon,
  label,
  count,
  percentage,
  color
}: {
  icon: React.ReactNode;
  label: string;
  count: number;
  percentage: number;
  color: string;
}) {
  return (
    <div className="flex items-center gap-3">
      {icon}
      <div className="flex-1">
        <div className="flex items-center justify-between mb-1">
          <span className="text-sm text-slate-300">{label}</span>
          <span className="text-xs text-slate-500">{count} ({percentage}%)</span>
        </div>
        <div className="h-1.5 bg-slate-700 rounded-full overflow-hidden">
          <div
            className={`h-full ${color} transition-all duration-500`}
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
