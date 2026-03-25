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


export function UserInsightsCard({ stats }: UserInsightsCardProps) {
  // All 5 claim types, sorted by count descending
  const allClaimTypes = Object.entries(stats.claimTypeBreakdown || {})
    .sort(([, a], [, b]) => b - a);
  const topClaimType = allClaimTypes.length > 0 ? allClaimTypes[0][0] : null;

  const sortedDomains = Object.entries(stats.domainBreakdown)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 4);
  const maxDomainCount = sortedDomains.length > 0 ? sortedDomains[0][1] : 1;

  const avgSources = stats.totalChecks > 0
    ? Math.round(stats.totalSourcesAnalyzed / stats.totalChecks)
    : 0;

  return (
    <div className="mb-12">
      <div className="mb-6">
        <h2 className="font-mono text-lg md:text-xl tracking-[0.15em] uppercase text-zinc-400 mb-1">
          Your Insights
        </h2>
        <p className="text-sm font-bold text-zinc-900">Track your analysis patterns</p>
      </div>

      <div className="bg-white border border-zinc-200 p-6 space-y-6">
        {/* Activity Stats Row — metrics NOT in the hero */}
        <div className="grid grid-cols-2 gap-4">
          <StatBox value={stats.checksThisMonth} label="Checks This Month" />
          <StatBox value={avgSources} label="Avg Sources / Check" />
        </div>

        {/* Two Column Layout */}
        <div className="grid md:grid-cols-2 gap-6">
          <div className="space-y-3">
            <h4 className="font-mono text-[10px] font-bold tracking-widest uppercase text-zinc-400">
              Claim Types
            </h4>
            {allClaimTypes.length > 0 ? (
              <div>
                <div className="grid grid-cols-2 gap-1.5">
                  {allClaimTypes.slice(0, 4).map(([type, count]) => (
                    <ClaimTypeTile
                      key={type}
                      label={CLAIM_TYPE_LABELS[type] || type}
                      count={count}
                      isTop={type === topClaimType}
                    />
                  ))}
                </div>
                {allClaimTypes.length > 4 && (
                  <div className="flex justify-center mt-1.5">
                    <div className="w-[calc(50%-0.25rem)]">
                      <ClaimTypeTile
                        label={CLAIM_TYPE_LABELS[allClaimTypes[4][0]] || allClaimTypes[4][0]}
                        count={allClaimTypes[4][1]}
                        isTop={allClaimTypes[4][0] === topClaimType}
                      />
                    </div>
                  </div>
                )}
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

function ClaimTypeTile({
  label,
  count,
  isTop,
}: {
  label: string;
  count: number;
  isTop: boolean;
}) {
  return (
    <div
      className={`px-2 py-1.5 text-center border ${
        isTop
          ? 'border-accent bg-accent/5'
          : 'border-zinc-200 bg-zinc-50'
      }`}
    >
      <div className={`text-sm font-mono font-light ${isTop ? 'text-accent' : 'text-zinc-900'}`}>
        {count}
      </div>
      <div className={`text-[9px] font-mono uppercase tracking-widest mt-0.5 ${isTop ? 'text-accent' : 'text-zinc-400'}`}>
        {label}
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
