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

  const getScoreColor = () => {
    if (score >= 0.8) return 'text-emerald-600';
    if (score >= 0.6) return 'text-amber-600';
    return 'text-red-600';
  };

  const getBarColor = () => {
    if (score >= 0.8) return 'bg-emerald-500';
    if (score >= 0.6) return 'bg-amber-500';
    return 'bg-red-500';
  };

  return (
    <div className={`bg-white border border-zinc-200 p-4 ${className}`}>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Eye size={18} className="text-zinc-400" />
          <span className="font-mono text-[10px] tracking-widest uppercase text-zinc-400">Transparency Score</span>
        </div>
        <span className={`text-2xl font-mono font-bold ${getScoreColor()}`}>
          {percentage}%
        </span>
      </div>

      <div className="w-full h-2 bg-zinc-100 overflow-hidden">
        <div
          className={`h-full ${getBarColor()} transition-all duration-1000 ease-out`}
          style={{ width: `${animatedWidth}%` }}
        />
      </div>

      <p className="text-xs text-zinc-400 mt-2">
        How transparent this analysis is based on evidence quality and consensus
      </p>
    </div>
  );
}
