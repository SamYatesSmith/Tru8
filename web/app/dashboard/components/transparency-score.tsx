'use client';

import { useEffect, useState } from 'react';
import { Eye } from 'lucide-react';

interface TransparencyScoreProps {
  score: number; // 0-1
  className?: string;
}

export function TransparencyScore({ score, className = '' }: TransparencyScoreProps) {
  const [animatedWidth, setAnimatedWidth] = useState(0);
  const percentage = Math.round(score * 100);

  useEffect(() => {
    const timer = setTimeout(() => {
      setAnimatedWidth(score * 100);
    }, 100);
    return () => clearTimeout(timer);
  }, [score]);

  // Color based on score
  const getScoreColor = () => {
    if (score >= 0.8) return 'text-emerald-400';
    if (score >= 0.6) return 'text-amber-400';
    return 'text-red-400';
  };

  const getBarColor = () => {
    if (score >= 0.8) return 'bg-emerald-500';
    if (score >= 0.6) return 'bg-amber-500';
    return 'bg-red-500';
  };

  return (
    <div className={`bg-slate-800/50 border border-slate-700 rounded-xl p-4 ${className}`}>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Eye size={18} className="text-slate-400" />
          <span className="text-sm font-medium text-slate-300">Transparency Score</span>
        </div>
        <span className={`text-2xl font-bold ${getScoreColor()}`}>
          {percentage}%
        </span>
      </div>

      {/* Progress Bar */}
      <div className="w-full h-2 bg-slate-700 rounded-full overflow-hidden">
        <div
          className={`h-full ${getBarColor()} rounded-full transition-all duration-1000 ease-out`}
          style={{ width: `${animatedWidth}%` }}
        />
      </div>

      <p className="text-xs text-slate-400 mt-2">
        How explainable this verdict is based on evidence quality and consensus
      </p>
    </div>
  );
}
