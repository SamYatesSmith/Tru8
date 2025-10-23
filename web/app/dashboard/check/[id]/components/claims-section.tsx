'use client';

import { useState } from 'react';
import { ChevronDown, ChevronUp, ExternalLink } from 'lucide-react';
import { VerdictPill } from '@/app/dashboard/components/verdict-pill';
import { ConfidenceBar } from '@/app/dashboard/components/confidence-bar';
import { DecisionTrail } from '@/app/dashboard/components/decision-trail';
import { ConfidenceBreakdown } from '@/app/dashboard/components/confidence-breakdown';
import { UncertaintyExplanation } from '@/app/dashboard/components/uncertainty-explanation';
import { NonVerifiableNotice } from '@/app/dashboard/components/non-verifiable-notice';
import { FactCheckBadge } from '@/app/dashboard/components/fact-check-badge';
import { TimeSensitiveIndicator } from '@/app/dashboard/components/time-sensitive-indicator';
import { formatMonthYear } from '@/lib/utils';

interface Claim {
  id: string;
  text: string;
  verdict: 'supported' | 'contradicted' | 'uncertain';
  confidence: number;
  rationale: string;
  position: number;
  evidence: Evidence[];

  // Classification fields (Phase 2)
  claimType?: string;
  isVerifiable?: boolean;
  verifiabilityReason?: string;

  // Temporal fields (Phase 1.5)
  isTimeSensitive?: boolean;
  timeReference?: string;
  temporalMarkers?: any;

  // Explainability fields (Phase 2)
  uncertaintyExplanation?: string;
  confidenceBreakdown?: any;
  decisionTrail?: any;
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

  // Fact-check fields
  isFactcheck?: boolean;
  factcheckPublisher?: string;
  factcheckRating?: string;

  // Source independence fields
  parentCompany?: string;
  independenceFlag?: string;

  // Temporal fields
  temporalRelevanceScore?: number;
  isTimeSensitive?: boolean;
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

        // Sort evidence by relevance score, prioritize fact-checks
        const sortedEvidence = [...claim.evidence].sort((a, b) => {
          // Fact-checks first
          if (a.isFactcheck && !b.isFactcheck) return -1;
          if (!a.isFactcheck && b.isFactcheck) return 1;
          // Then by relevance
          return b.relevanceScore - a.relevanceScore;
        });

        return (
          <div
            key={claim.id}
            className="bg-slate-800/50 border border-slate-700 rounded-xl p-6 space-y-4"
          >
            {/* Claim Type & Time Sensitivity Indicators */}
            {(claim.claimType || claim.isTimeSensitive) && (
              <div className="flex flex-wrap gap-2">
                {claim.isTimeSensitive && claim.timeReference && (
                  <TimeSensitiveIndicator timeReference={claim.timeReference} />
                )}
                {claim.claimType && claim.claimType !== 'factual' && (
                  <span className="px-2 py-1 bg-slate-700 text-slate-300 text-xs font-medium rounded">
                    {claim.claimType.replace('_', ' ')}
                  </span>
                )}
              </div>
            )}

            {/* Claim Text */}
            <p className="text-lg font-medium text-white">&quot;{claim.text}&quot;</p>

            {/* Non-Verifiable Notice OR Normal Verdict */}
            {claim.isVerifiable === false ? (
              <NonVerifiableNotice
                claimType={claim.claimType || 'unknown'}
                reason={claim.verifiabilityReason || 'This claim cannot be fact-checked.'}
              />
            ) : (
              <>
                {/* Header: Verdict + Confidence */}
                <div className="flex items-start justify-between">
                  <VerdictPill verdict={claim.verdict} />
                  <span className="text-2xl font-bold text-white">
                    {Math.round(claim.confidence)}%
                  </span>
                </div>

                {/* Confidence Bar */}
                <ConfidenceBar
                  confidence={claim.confidence}
                  verdict={claim.verdict}
                />

                {/* Rationale */}
                {claim.rationale && (
                  <p className="text-sm text-slate-400">{claim.rationale}</p>
                )}

                {/* Uncertainty Explanation (if uncertain) */}
                {claim.verdict === 'uncertain' && claim.uncertaintyExplanation && (
                  <UncertaintyExplanation explanation={claim.uncertaintyExplanation} />
                )}

                {/* Confidence Breakdown */}
                {claim.confidenceBreakdown && (
                  <ConfidenceBreakdown breakdown={claim.confidenceBreakdown} />
                )}

                {/* Decision Trail */}
                {claim.decisionTrail && (
                  <DecisionTrail decisionTrail={claim.decisionTrail} />
                )}
              </>
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
                    <div className="flex-1 min-w-0 space-y-2">
                      {/* Fact-Check Badge */}
                      {evidence.isFactcheck && evidence.factcheckPublisher && (
                        <FactCheckBadge
                          publisher={evidence.factcheckPublisher}
                          rating={evidence.factcheckRating}
                        />
                      )}

                      {/* Title */}
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-white truncate">
                          {evidence.title}
                        </span>
                        <ExternalLink
                          size={14}
                          className="text-slate-400 group-hover:text-white transition-colors flex-shrink-0"
                        />
                      </div>

                      {/* Snippet */}
                      <p className="text-xs text-slate-400 line-clamp-4">
                        {evidence.snippet}
                      </p>

                      {/* Metadata: Source · Date · Credibility */}
                      <div className="flex items-center gap-2 text-xs text-slate-500 flex-wrap">
                        <span className="font-medium">{evidence.source}</span>

                        {evidence.parentCompany && (
                          <>
                            <span>·</span>
                            <span title="Parent Company">
                              {evidence.parentCompany}
                            </span>
                          </>
                        )}

                        <span>·</span>
                        <span>{formatMonthYear(evidence.publishedDate || null)}</span>

                        <span>·</span>
                        <span className="font-medium">
                          {evidence.credibilityScore
                            ? `${(evidence.credibilityScore * 10).toFixed(1)}/10`
                            : `${(evidence.relevanceScore * 10).toFixed(1)}/10`}
                        </span>

                        {evidence.temporalRelevanceScore !== undefined && (
                          <>
                            <span>·</span>
                            <span title="Temporal Relevance" className="text-amber-400">
                              Time: {(evidence.temporalRelevanceScore * 10).toFixed(1)}/10
                            </span>
                          </>
                        )}
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
