'use client';

import { useState, useMemo } from 'react';
import Link from 'next/link';
import { ExternalLink, ChevronDown, ChevronUp, RefreshCw } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { formatDate } from '@/lib/utils';
import type { ElementState } from '@shared/types';

interface CheckCardProps {
  check: {
    id: string;
    status: string;
    inputUrl: string | null;
    createdAt: string;
    claimsCount: number;
    articleDomain: string | null;
    claims: Array<{
      text: string;
      claimMap?: {
        elements: Array<{
          state: ElementState | null;
        }>;
      };
    }>;
  };
  isNew?: boolean;
}

export function CheckCard({ check, isNew = false }: CheckCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const router = useRouter();

  const handleRecheck = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (check.inputUrl) {
      router.push(`/dashboard/new-check?url=${encodeURIComponent(check.inputUrl)}`);
    }
  };

  const stateCounts = useMemo(() => {
    let supported = 0;
    let disputed = 0;
    let unresolved = 0;

    if (check.claims) {
      for (const claim of check.claims) {
        if (claim.claimMap?.elements) {
          for (const el of claim.claimMap.elements) {
            if (el.state === 'supported') supported++;
            else if (el.state === 'disputed') disputed++;
            else unresolved++;
          }
        }
      }
    }

    return { supported, disputed, unresolved };
  }, [check.claims]);

  if (check.status !== 'completed' || !check.claims || check.claims.length === 0) {
    return null;
  }

  const firstClaim = check.claims[0];
  const displayText = firstClaim.text;
  const isLongText = displayText.length > 150;
  const hasElements = stateCounts.supported + stateCounts.disputed + stateCounts.unresolved > 0;

  return (
    <div className={`border bg-white hover:border-black transition-colors ${
      isNew ? 'border-accent' : 'border-zinc-200'
    }`}>
      <Link
        href={`/dashboard/check/${check.id}`}
        className="block p-6"
      >
        <div className="flex items-start justify-between gap-6">
          <div className="flex-1 min-w-0">
            {/* Date + Domain + Element state indicators */}
            <div className="flex items-center flex-wrap gap-x-3 gap-y-1 mb-3">
              <span className="font-mono text-[10px] tracking-widest uppercase text-zinc-400">
                {formatDate(check.createdAt)}
              </span>
              {check.articleDomain && (
                <span className="text-[10px] px-2 py-0.5 bg-zinc-100 text-zinc-500 font-mono">
                  {check.articleDomain}
                </span>
              )}
              {hasElements && (
                <div className="flex items-center gap-3 text-xs font-mono">
                  {stateCounts.supported > 0 && (
                    <span className="inline-flex items-center gap-1">
                      <span className="w-2 h-2 rounded-full bg-state-supported" />
                      <span className="text-state-supported">{stateCounts.supported}</span>
                    </span>
                  )}
                  {stateCounts.disputed > 0 && (
                    <span className="inline-flex items-center gap-1">
                      <span className="w-2 h-2 rounded-full bg-state-disputed" />
                      <span className="text-state-disputed">{stateCounts.disputed}</span>
                    </span>
                  )}
                  {stateCounts.unresolved > 0 && (
                    <span className="inline-flex items-center gap-1">
                      <span className="w-2 h-2 rounded-full bg-state-unresolved" />
                      <span className="text-state-unresolved">{stateCounts.unresolved}</span>
                    </span>
                  )}
                </div>
              )}
            </div>

            <p className={`text-zinc-900 mb-2 ${!isExpanded && isLongText ? 'line-clamp-2' : ''}`}>
              {displayText}
            </p>

            {check.inputUrl && (
              <div className="flex items-center gap-3 mt-2">
                <span
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    window.open(check.inputUrl!, '_blank', 'noopener,noreferrer');
                  }}
                  className="text-zinc-400 text-sm flex items-center gap-1 hover:text-zinc-600 cursor-pointer"
                >
                  <ExternalLink size={14} />
                  <span className="truncate max-w-[250px]">{check.inputUrl}</span>
                </span>
                <button
                  onClick={handleRecheck}
                  className="flex items-center gap-1 text-xs text-zinc-400 hover:text-accent transition-colors px-2 py-1 hover:bg-zinc-50"
                  title="Run this check again with fresh evidence"
                >
                  <RefreshCw size={12} />
                  <span>Re-check</span>
                </button>
              </div>
            )}
          </div>

          <div className="flex-shrink-0 text-right">
            <span className="text-3xl font-mono font-light text-zinc-400 block">
              {check.claimsCount}
            </span>
            <span className="text-zinc-500 text-xs font-mono uppercase block">
              {check.claimsCount === 1 ? 'Claim' : 'Claims'}
            </span>
          </div>
        </div>
      </Link>

      {isLongText && (
        <button
          onClick={(e) => {
            e.preventDefault();
            setIsExpanded(!isExpanded);
          }}
          className="w-full px-6 py-2 border-t border-zinc-100 flex items-center justify-center gap-1 text-zinc-400 hover:text-zinc-600 text-sm transition-colors"
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
  );
}
