'use client';

interface OverallSummaryCardProps {
  check: {
    overall_summary: string;
    credibility_score: number;
    claims_supported: number;
    claims_contradicted: number;
    claims_uncertain: number;
  };
}

export function OverallSummaryCard({ check }: OverallSummaryCardProps) {
  // Calculate credibility level
  const getCredibilityLevel = (score: number) => {
    if (score >= 80) return { label: 'High Credibility', color: 'text-emerald-400', bg: 'bg-emerald-500/20' };
    if (score >= 60) return { label: 'Moderate Credibility', color: 'text-amber-400', bg: 'bg-amber-500/20' };
    return { label: 'Low Credibility', color: 'text-red-400', bg: 'bg-red-500/20' };
  };

  const credibility = getCredibilityLevel(check.credibility_score);

  return (
    <div className="bg-gradient-to-br from-blue-950/50 to-purple-950/50 border-2 border-blue-500/30 rounded-xl p-8 mb-8">
      {/* Header with Score */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <h2 className="text-2xl font-black text-white mb-2">Overall Assessment</h2>
          <div className="flex items-center gap-3">
            <div className={`${credibility.bg} ${credibility.color} px-4 py-2 rounded-lg font-bold text-sm`}>
              {credibility.label}
            </div>
            <div className="text-white/60 text-sm">
              Credibility Score: <span className="text-white font-bold text-lg">{check.credibility_score}/100</span>
            </div>
          </div>
        </div>

        {/* Score Gauge */}
        <div className="relative w-24 h-24">
          <svg className="w-24 h-24 transform -rotate-90">
            <circle
              cx="48"
              cy="48"
              r="40"
              stroke="currentColor"
              strokeWidth="8"
              fill="none"
              className="text-slate-700"
            />
            <circle
              cx="48"
              cy="48"
              r="40"
              stroke="currentColor"
              strokeWidth="8"
              fill="none"
              strokeDasharray={`${2 * Math.PI * 40}`}
              strokeDashoffset={`${2 * Math.PI * 40 * (1 - check.credibility_score / 100)}`}
              className={credibility.color}
              strokeLinecap="round"
            />
          </svg>
          <div className="absolute inset-0 flex items-center justify-center">
            <span className="text-2xl font-black text-white">{check.credibility_score}</span>
          </div>
        </div>
      </div>

      {/* Summary Text */}
      <div className="bg-slate-900/50 rounded-lg p-6 mb-6">
        <p className="text-white/90 text-lg leading-relaxed">
          {check.overall_summary}
        </p>
      </div>

      {/* Claims Breakdown */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-lg p-4 text-center">
          <div className="text-3xl font-black text-emerald-400">{check.claims_supported}</div>
          <div className="text-sm text-emerald-400/70 font-medium">Supported</div>
        </div>
        <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-4 text-center">
          <div className="text-3xl font-black text-amber-400">{check.claims_uncertain}</div>
          <div className="text-sm text-amber-400/70 font-medium">Uncertain</div>
        </div>
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 text-center">
          <div className="text-3xl font-black text-red-400">{check.claims_contradicted}</div>
          <div className="text-sm text-red-400/70 font-medium">Contradicted</div>
        </div>
      </div>
    </div>
  );
}
