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
    <Link href={`/dashboard/check/${check.id}`}>
      <div className="bg-[#1a1f2e] border border-slate-700 rounded-xl p-6 hover:border-slate-600 transition-colors cursor-pointer">
        <div className="flex items-start justify-between gap-6">
          {/* Left: Claim info */}
          <div className="flex-1 min-w-0">
            {/* Verdict + Date */}
            <div className="flex items-center gap-3 mb-3">
              <VerdictPill verdict={firstClaim.verdict} />
              <span className="text-slate-400 text-sm">
                {formatDate(check.createdAt)}
              </span>
            </div>

            {/* Claim text */}
            <p className="text-white mb-2 line-clamp-2">
              {firstClaim.text}
            </p>

            {/* URL if exists */}
            {check.inputUrl && (
              <a
                href={check.inputUrl}
                target="_blank"
                rel="noopener noreferrer"
                onClick={(e) => e.stopPropagation()}
                className="text-slate-400 text-sm flex items-center gap-1 hover:text-slate-300"
              >
                <ExternalLink size={14} />
                <span className="truncate">{check.inputUrl}</span>
              </a>
            )}
          </div>

          {/* Right: Confidence */}
          <div className="flex-shrink-0 text-right">
            <div className="text-3xl font-bold text-[#f57a07]">
              {Math.round(firstClaim.confidence)}%
            </div>
            <div className="text-slate-400 text-sm">Confidence</div>
          </div>
        </div>
      </div>
    </Link>
  );
}
