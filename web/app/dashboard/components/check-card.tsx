'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { ExternalLink, ChevronDown, ChevronUp, CheckCircle, XCircle, HelpCircle } from 'lucide-react';
import { formatDate } from '@/lib/utils';

interface CheckCardProps {
  check: {
    id: string;
    status: string;
    inputUrl: string | null;
    createdAt: string;
    claimsCount: number;
    overallSummary: string | null;
    credibilityScore: number | null;
    claimsSupported: number;
    claimsContradicted: number;
    claimsUncertain: number;
    articleDomain: string | null;
    claims: Array<{
      text: string;
      verdict: 'supported' | 'contradicted' | 'uncertain';
      confidence: number;
    }>;
  };
  isNew?: boolean;  // Highlight as newest check with rotating border
}

export function CheckCard({ check, isNew = false }: CheckCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [showNewHighlight, setShowNewHighlight] = useState(isNew);

  // Auto-dismiss the highlight after animation completes (5 rotations = 5 seconds)
  useEffect(() => {
    if (isNew) {
      const timer = setTimeout(() => {
        setShowNewHighlight(false);
      }, 5000);
      return () => clearTimeout(timer);
    }
  }, [isNew]);

  // Only show completed checks with claims
  if (check.status !== 'completed' || !check.claims || check.claims.length === 0) {
    return null;
  }

  const firstClaim = check.claims[0];

  // Get display text: overall summary > first claim > URL
  const displayText = check.overallSummary || firstClaim.text;
  const isLongText = displayText.length > 150;

  // Calculate score from verdict breakdown (supported percentage)
  const getDisplayScore = () => {
    const { claimsSupported, claimsContradicted, claimsUncertain } = check;
    const total = claimsSupported + claimsContradicted + claimsUncertain;

    if (total > 0) {
      return Math.round((claimsSupported / total) * 100);
    }

    // Fallback to first claim confidence only if no verdict breakdown
    return Math.round(firstClaim.confidence);
  };

  const displayScore = getDisplayScore();

  // Score color based on score value
  const getScoreColor = () => {
    if (displayScore >= 70) return 'text-emerald-400';
    if (displayScore >= 40) return 'text-amber-400';
    return 'text-red-400';
  };

  return (
    <div className={`border rounded-xl hover:border-slate-600 transition-colors relative ${
      showNewHighlight
        ? 'border-transparent overflow-hidden p-[2px]'
        : 'border-slate-700 bg-[#1a1f2e]'
    }`}>
      {/* Rotating gradient border for new checks */}
      {showNewHighlight && (
        <>
          <div
            className="absolute -inset-[150%] rounded-xl"
            style={{
              background: 'conic-gradient(from 0deg, transparent 0deg, transparent 60deg, #f57a07 120deg, #ff9d4d 180deg, #f57a07 240deg, transparent 300deg, transparent 360deg)',
              animation: 'gradient-rotate 1s linear infinite'
            }}
          />
          <div
            className="absolute -inset-[150%] rounded-xl opacity-60"
            style={{
              background: 'conic-gradient(from 0deg, transparent 0deg, transparent 60deg, #f57a07 120deg, #ff9d4d 180deg, #f57a07 240deg, transparent 300deg, transparent 360deg)',
              animation: 'gradient-rotate 1s linear infinite',
              filter: 'blur(20px)'
            }}
          />
        </>
      )}
      {/* Inner content wrapper */}
      <div className={`relative bg-[#1a1f2e] rounded-xl ${showNewHighlight ? 'z-10' : ''}`}>
      <Link
        href={`/dashboard/check/${check.id}`}
        className="block p-6"
      >
        <div className="flex items-start justify-between gap-6">
          {/* Left: Synopsis info */}
          <div className="flex-1 min-w-0">
            {/* Date + Domain + Verdict indicators */}
            <div className="flex items-center flex-wrap gap-x-3 gap-y-1 mb-3">
              <span className="text-slate-400 text-sm">
                {formatDate(check.createdAt)}
              </span>
              {/* Domain pill */}
              {check.articleDomain && (
                <span className="text-xs px-2 py-0.5 bg-slate-700/50 text-slate-300 rounded-full">
                  {check.articleDomain}
                </span>
              )}
              {/* Mini verdict breakdown */}
              <div className="flex items-center gap-2 text-xs">
                {check.claimsSupported > 0 && (
                  <span className="flex items-center gap-0.5 text-emerald-400">
                    <CheckCircle size={12} />
                    <span>{check.claimsSupported}</span>
                  </span>
                )}
                {check.claimsContradicted > 0 && (
                  <span className="flex items-center gap-0.5 text-red-400">
                    <XCircle size={12} />
                    <span>{check.claimsContradicted}</span>
                  </span>
                )}
                {check.claimsUncertain > 0 && (
                  <span className="flex items-center gap-0.5 text-amber-400">
                    <HelpCircle size={12} />
                    <span>{check.claimsUncertain}</span>
                  </span>
                )}
              </div>
            </div>

            {/* Synopsis text */}
            <p className={`text-white mb-2 ${!isExpanded && isLongText ? 'line-clamp-2' : ''}`}>
              {displayText}
            </p>

            {/* URL if exists */}
            {check.inputUrl && (
              <span
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  window.open(check.inputUrl!, '_blank', 'noopener,noreferrer');
                }}
                className="text-slate-400 text-sm flex items-center gap-1 hover:text-slate-300 cursor-pointer mt-2"
              >
                <ExternalLink size={14} />
                <span className="truncate max-w-[300px]">{check.inputUrl}</span>
              </span>
            )}
          </div>

          {/* Right: Score */}
          <div className="flex-shrink-0 text-right">
            <span className={`text-3xl font-bold ${getScoreColor()} block`}>
              {displayScore}%
            </span>
            <span className="text-slate-400 text-sm block">Supported</span>
          </div>
        </div>
      </Link>

      {/* Expand/collapse button for long text */}
      {isLongText && (
        <button
          onClick={(e) => {
            e.preventDefault();
            setIsExpanded(!isExpanded);
          }}
          className="w-full px-6 py-2 border-t border-slate-700/50 flex items-center justify-center gap-1 text-slate-400 hover:text-slate-300 text-sm transition-colors"
        >
          {isExpanded ? (
            <>
              <ChevronUp size={16} />
              <span>Show less</span>
            </>
          ) : (
            <>
              <ChevronDown size={16} />
              <span>Show more</span>
            </>
          )}
        </button>
      )}
      </div>
    </div>
  );
}
