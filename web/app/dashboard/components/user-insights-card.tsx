import { UserStats } from '@/lib/api';

interface UserInsightsCardProps {
  stats: UserStats;
}

const CLAIM_TYPE_LABELS: Record<string, string> = {
  empirical: 'Empirical',
  causal: 'Causal',
  evaluative: 'Evaluative',
  predictive: 'Predictive',
  prescriptive: 'Prescriptive',
};

const CLAIM_TYPE_COLORS: Record<string, string> = {
  empirical: 'bg-blue-500',
  causal: 'bg-amber-500',
  evaluative: 'bg-violet-500',
  predictive: 'bg-emerald-500',
  prescriptive: 'bg-rose-500',
};

export function UserInsightsCard({ stats }: UserInsightsCardProps) {
  const claimTypes = Object.entries(stats.claimTypeBreakdown || {})
    .sort(([, a], [, b]) => b - a);
  const totalClaims = claimTypes.reduce((sum, [, count]) => sum + count, 0);

  const sortedDomains = Object.entries(stats.domainBreakdown)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 4);
  const maxDomainCount = sortedDomains.length > 0 ? sortedDomains[0][1] : 1;

  const memberSince = stats.memberSince
    ? new Date(stats.memberSince).toLocaleDateString('en-GB', {
        month: 'short',
        year: 'numeric'
      })
    : 'Unknown';

  return (
    <div className="mb-12">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-lg font-bold text-zinc-900">Your Insights</h2>
          <p className="text-zinc-500 text-sm">Track your analysis patterns</p>
        </div>
      </div>

      <div className="bg-white border border-zinc-200 p-6 space-y-6">
        {/* Top Stats Row */}
        <div className="grid grid-cols-3 gap-4">
          <StatBox value={stats.totalChecks} label="Total Checks" />
          <StatBox value={stats.totalSourcesAnalyzed} label="Sources Analyzed" />
          <StatBox value={stats.totalClaimsAnalyzed ?? totalClaims} label="Claims Analysed" />
        </div>

        {/* Two Column Layout */}
        <div className="grid md:grid-cols-2 gap-6">
          <div className="space-y-3">
            <h4 className="font-mono text-[10px] font-bold tracking-widest uppercase text-zinc-400">
              Claim Types
            </h4>
            {claimTypes.length > 0 ? (
              <div className="space-y-2">
                {claimTypes.map(([type, count]) => {
                  const pct = totalClaims > 0 ? Math.round((count / totalClaims) * 100) : 0;
                  return (
                    <ClaimTypeBar
                      key={type}
                      label={CLAIM_TYPE_LABELS[type] || type}
                      count={count}
                      percentage={pct}
                      barClass={CLAIM_TYPE_COLORS[type] || 'bg-zinc-400'}
                    />
                  );
                })}
              </div>
            ) : (
              <p className="text-sm text-zinc-400">No claim data yet</p>
            )}
          </div>

          <div className="space-y-3">
            <h4 className="font-mono text-[10px] font-bold tracking-widest uppercase text-zinc-400">
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
              <p className="text-sm text-zinc-400">No domain data yet</p>
            )}
          </div>
        </div>

        {/* Footer Stats */}
        <div className="flex items-center justify-between pt-4 border-t border-zinc-100 font-mono text-[10px] tracking-widest uppercase text-zinc-400">
          <span>Member since {memberSince}</span>
        </div>
      </div>
    </div>
  );
}

function StatBox({ value, label }: { value: string | number; label: string }) {
  return (
    <div className="bg-zinc-50 p-4 text-center">
      <div className="text-3xl font-mono font-light text-zinc-900">{value}</div>
      <div className="text-[10px] font-mono uppercase tracking-widest text-zinc-400 mt-1">{label}</div>
    </div>
  );
}

function ClaimTypeBar({
  label,
  count,
  percentage,
  barClass,
}: {
  label: string;
  count: number;
  percentage: number;
  barClass: string;
}) {
  return (
    <div className="flex items-center gap-3">
      <span className={`w-2 h-2 rounded-full ${barClass} flex-shrink-0`} />
      <div className="flex-1">
        <div className="flex items-center justify-between mb-1">
          <span className="text-sm text-zinc-600">{label}</span>
          <span className="text-xs font-mono text-zinc-400">{count} ({percentage}%)</span>
        </div>
        <div className="h-1.5 bg-zinc-100 overflow-hidden">
          <div
            className={`h-full ${barClass} transition-all duration-500`}
            style={{ width: `${percentage}%` }}
          />
        </div>
      </div>
    </div>
  );
}

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
        <span className="text-sm text-zinc-600">{domain}</span>
        <span className="text-xs font-mono text-zinc-400">{count}</span>
      </div>
      <div className="h-1.5 bg-zinc-100 overflow-hidden">
        <div
          className="h-full bg-zinc-400 transition-all duration-500"
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}
