'use client';

import { useState } from 'react';
import { ChevronDown, ChevronUp, ExternalLink } from 'lucide-react';
import { VerdictPill } from '@/app/dashboard/components/verdict-pill';
import { ConfidenceBar } from '@/app/dashboard/components/confidence-bar';
import { formatMonthYear } from '@/lib/utils';

interface Claim {
  id: string;
  text: string;
  verdict: 'supported' | 'contradicted' | 'uncertain';
  confidence: number;
  rationale: string;
  position: number;
  evidence: Evidence[];
}

interface Evidence {
  id: string;
  source: string;
  url: string;
  title: string;
  snippet: string;
  publishedDate?: string;
  relevanceScore: number;
  credibilityScore?: number;
}

interface ClaimsSectionProps {
  claims: Claim[];
}

export function ClaimsSection({ claims }: ClaimsSectionProps) {
  const [expandedClaim, setExpandedClaim] = useState<string | null>(null);

  const toggleEvidence = (claimId: string) => {
    setExpandedClaim(expandedClaim === claimId ? null : claimId);
  };

  return (
    <div className="space-y-6">
      <h3 className="text-2xl font-bold text-white">Claims Analyzed ({claims.length})</h3>

      {claims.map((claim) => {
        const isExpanded = expandedClaim === claim.id;
        // Sort evidence by relevance score
        const sortedEvidence = [...claim.evidence].sort(
          (a, b) => b.relevanceScore - a.relevanceScore
        );

        return (
          <div
            key={claim.id}
            className="bg-slate-800/50 border border-slate-700 rounded-xl p-6"
          >
            {/* Header: Verdict + Confidence */}
            <div className="flex items-start justify-between mb-4">
              <VerdictPill verdict={claim.verdict} />
              <span className="text-2xl font-bold text-white">
                {Math.round(claim.confidence)}%
              </span>
            </div>

            {/* Confidence Bar */}
            <ConfidenceBar
              confidence={claim.confidence}
              verdict={claim.verdict}
              className="mb-4"
            />

            {/* Claim Text */}
            <p className="text-lg font-medium text-white mb-4">&quot;{claim.text}&quot;</p>

            {/* Rationale */}
            {claim.rationale && (
              <p className="text-sm text-slate-400 mb-4">{claim.rationale}</p>
            )}

            {/* Evidence Toggle Button */}
            {claim.evidence.length > 0 && (
              <button
                onClick={() => toggleEvidence(claim.id)}
                className="flex items-center gap-2 text-sm text-[#f57a07] hover:text-[#ff8c1a] transition-colors font-medium"
              >
                <span>Evidence Sources ({claim.evidence.length})</span>
                {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
              </button>
            )}

            {/* Evidence List (Collapsible) */}
            {isExpanded && (
              <div className="mt-4 space-y-3">
                {sortedEvidence.map((evidence) => (
                  <a
                    key={evidence.id}
                    href={evidence.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-start gap-3 p-4 bg-slate-900/50 border border-slate-700 rounded-lg hover:border-slate-600 transition-colors group"
                  >
                    <div className="flex-1 min-w-0">
                      {/* Title */}
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-sm font-medium text-white truncate">
                          {evidence.title}
                        </span>
                        <ExternalLink
                          size={14}
                          className="text-slate-400 group-hover:text-white transition-colors flex-shrink-0"
                        />
                      </div>

                      {/* Snippet */}
                      <p className="text-xs text-slate-400 mb-2 line-clamp-4">
                        {evidence.snippet}
                      </p>

                      {/* Metadata: Source · Date · Credibility */}
                      <div className="flex items-center gap-2 text-xs text-slate-500">
                        <span className="font-medium">{evidence.source}</span>
                        <span>·</span>
                        <span>{formatMonthYear(evidence.publishedDate || null)}</span>
                        <span>·</span>
                        <span className="font-medium">
                          {evidence.credibilityScore
                            ? `${(evidence.credibilityScore * 10).toFixed(1)}/10`
                            : `${(evidence.relevanceScore * 10).toFixed(1)}/10`}
                        </span>
                      </div>
                    </div>
                  </a>
                ))}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
