'use client';

import { CheckCircle2, XCircle, TrendingUp } from 'lucide-react';

interface ConfidenceFactor {
  factor: string;
  impact: 'positive' | 'negative' | 'neutral';
  description: string;
  score?: number;
}

interface ConfidenceBreakdownData {
  overall_confidence: number;
  factors: ConfidenceFactor[];
}

interface ConfidenceBreakdownProps {
  breakdown: ConfidenceBreakdownData;
  className?: string;
}

export function ConfidenceBreakdown({ breakdown, className = '' }: ConfidenceBreakdownProps) {
  const getImpactIcon = (impact: string) => {
    switch (impact) {
      case 'positive':
        return <CheckCircle2 size={16} className="text-emerald-400 flex-shrink-0" />;
      case 'negative':
        return <XCircle size={16} className="text-red-400 flex-shrink-0" />;
      default:
        return <TrendingUp size={16} className="text-amber-400 flex-shrink-0" />;
    }
  };

  return (
    <div className={`bg-slate-800/50 border border-slate-700 rounded-xl p-6 ${className}`}>
      <div className="flex items-center gap-2 mb-4">
        <TrendingUp size={18} className="text-[#f57a07]" />
        <h4 className="text-sm font-semibold text-white">Confidence Factors</h4>
      </div>

      <div className="space-y-3">
        {breakdown.factors.map((factor, idx) => (
          <div key={idx} className="flex items-start gap-3">
            {getImpactIcon(factor.impact)}
            <div className="flex-1 min-w-0">
              <p className="text-sm text-slate-200">{factor.description}</p>
              {factor.score !== undefined && (
                <p className="text-xs text-slate-500 mt-0.5">
                  Impact: {factor.score > 0 ? '+' : ''}{(factor.score * 100).toFixed(0)}%
                </p>
              )}
            </div>
          </div>
        ))}
      </div>

      {breakdown.factors.length === 0 && (
        <p className="text-sm text-slate-400 text-center py-4">
          No specific confidence factors available
        </p>
      )}
    </div>
  );
}
