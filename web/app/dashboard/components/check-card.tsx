'use client';

import Link from 'next/link';
import { ExternalLink } from 'lucide-react';
import { VerdictPill } from './verdict-pill';
import { formatDate } from '@/lib/utils';

interface CheckCardProps {
  check: {
    id: string;
    status: string;
    inputUrl: string | null;
    createdAt: string;
    claims: Array<{
      text: string;
      verdict: 'supported' | 'contradicted' | 'uncertain';
      confidence: number;
    }>;
  };
}

export function CheckCard({ check }: CheckCardProps) {
  // Only show completed checks with claims
  if (check.status !== 'completed' || !check.claims || check.claims.length === 0) {
    return null;
  }

  const firstClaim = check.claims[0];

  return (
    <Link
      href={`/dashboard/check/${check.id}`}
      className="block bg-[#1a1f2e] border border-slate-700 rounded-xl p-6 hover:border-slate-600 transition-colors cursor-pointer"
    >
      <span className="flex items-start justify-between gap-6">
        {/* Left: Claim info */}
        <span className="flex-1 min-w-0 block">
          {/* Verdict + Date */}
          <span className="flex items-center gap-3 mb-3">
            <VerdictPill verdict={firstClaim.verdict} />
            <span className="text-slate-400 text-sm">
              {formatDate(check.createdAt)}
            </span>
          </span>

          {/* Claim text */}
          <span className="text-white mb-2 line-clamp-2 block">
            {firstClaim.text}
          </span>

          {/* URL if exists */}
          {check.inputUrl && (
            <span
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                window.open(check.inputUrl!, '_blank', 'noopener,noreferrer');
              }}
              className="text-slate-400 text-sm flex items-center gap-1 hover:text-slate-300 cursor-pointer"
            >
              <ExternalLink size={14} />
              <span className="truncate">{check.inputUrl}</span>
            </span>
          )}
        </span>

        {/* Right: Confidence */}
        <span className="flex-shrink-0 text-right block">
          <span className="text-3xl font-bold text-[#f57a07] block">
            {Math.round(firstClaim.confidence)}%
          </span>
          <span className="text-slate-400 text-sm block">Confidence</span>
        </span>
      </span>
    </Link>
  );
}
