'use client';

interface OverallSummaryCardProps {
  check: {
    overallSummary: string;
    credibilityScore: number;
    claimsSupported: number;
    claimsContradicted: number;
    claimsUncertain: number;
  };
}

export function OverallSummaryCard({ check }: OverallSummaryCardProps) {
  // Calculate credibility level
  const getCredibilityLevel = (score: number) => {
    if (score >= 80) return { label: 'High Credibility', color: 'text-emerald-400', bg: 'bg-emerald-500/20' };
    if (score >= 60) return { label: 'Moderate Credibility', color: 'text-amber-400', bg: 'bg-amber-500/20' };
    return { label: 'Low Credibility', color: 'text-red-400', bg: 'bg-red-500/20' };
  };

  const credibility = getCredibilityLevel(check.credibilityScore);

  return (
    <div className="bg-gradient-to-br from-blue-950/50 to-purple-950/50 border-2 border-blue-500/30 rounded-xl p-8 mb-8">
      {/* Header */}
      <div className="mb-6">
        <h2 className="text-2xl font-black text-white mb-2">Overall Assessment</h2>
        <div className={`${credibility.bg} ${credibility.color} px-4 py-2 rounded-lg font-bold text-sm inline-block`}>
          {credibility.label}
        </div>
      </div>

      {/* Summary Text */}
      <div className="bg-slate-900/50 rounded-lg p-6 mb-6">
        <p className="text-white/90 text-lg leading-relaxed">
          {check.overallSummary}
        </p>
      </div>

      {/* Claims Breakdown */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-lg p-4 text-center">
          <div className="text-3xl font-black text-emerald-400">{check.claimsSupported}</div>
          <div className="text-sm text-emerald-400/70 font-medium">Supported</div>
        </div>
        <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-4 text-center">
          <div className="text-3xl font-black text-amber-400">{check.claimsUncertain}</div>
          <div className="text-sm text-amber-400/70 font-medium">Uncertain</div>
        </div>
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 text-center">
          <div className="text-3xl font-black text-red-400">{check.claimsContradicted}</div>
          <div className="text-sm text-red-400/70 font-medium">Contradicted</div>
        </div>
      </div>
    </div>
  );
}
