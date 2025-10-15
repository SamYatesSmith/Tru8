'use client';

import { useEffect, useState } from 'react';

interface ConfidenceBarProps {
  confidence: number; // 0-100
  verdict?: 'supported' | 'contradicted' | 'uncertain';
  showLabel?: boolean;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export function ConfidenceBar({
  confidence,
  verdict,
  showLabel = false,
  size = 'md',
  className = '',
}: ConfidenceBarProps) {
  const [animatedWidth, setAnimatedWidth] = useState(0);

  useEffect(() => {
    // Animate width on mount
    const timer = setTimeout(() => {
      setAnimatedWidth(confidence);
    }, 100);

    return () => clearTimeout(timer);
  }, [confidence]);

  const sizeConfig = {
    sm: 'h-1',
    md: 'h-2',
    lg: 'h-3',
  };

  const getBarColor = () => {
    if (!verdict) {
      return 'bg-[#f57a07]'; // Default orange
    }

    switch (verdict) {
      case 'supported':
        return 'bg-emerald-500';
      case 'contradicted':
        return 'bg-red-500';
      case 'uncertain':
        return 'bg-amber-500';
      default:
        return 'bg-[#f57a07]';
    }
  };

  const barColor = getBarColor();
  const heightClass = sizeConfig[size];

  return (
    <div className={`space-y-1 ${className}`}>
      {/* Progress Bar Container */}
      <div className={`w-full bg-slate-700 rounded-full overflow-hidden ${heightClass}`}>
        <div
          className={`${heightClass} ${barColor} rounded-full transition-all duration-1000 ease-out`}
          style={{ width: `${animatedWidth}%` }}
        />
      </div>

      {/* Optional Label */}
      {showLabel && (
        <div className="flex justify-between items-center text-xs">
          <span className="text-slate-400 font-medium">Confidence</span>
          <span className="text-slate-200 font-semibold">{Math.round(confidence)}%</span>
        </div>
      )}
    </div>
  );
}
