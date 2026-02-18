'use client';

import { useState } from 'react';
import { ChevronDown, ExternalLink, RefreshCw } from 'lucide-react';
import { ClaimMapView } from '@/components/claim-map';
import { FactCheckBadge } from '@/app/dashboard/components/fact-check-badge';
import { TimeSensitiveIndicator } from '@/app/dashboard/components/time-sensitive-indicator';
import { formatMonthYear } from '@/lib/utils';
import type { ClaimMap } from '@shared/types';

// Phase 2: Helper function for NLI explanations
function generateNliExplanation(stance: string, confidence?: number): string {
  const confidenceLevel = (confidence || 0) >= 0.8 ? 'strongly' :
                          (confidence || 0) >= 0.6 ? 'moderately' : 'weakly';

  if (stance === 'supporting') {
    return `This evidence ${confidenceLevel} confirms key aspects of the claim. The passage directly corroborates the claim's assertions.`;
  } else if (stance === 'contradicting') {
    return `This evidence ${confidenceLevel} disputes the claim. The passage contains information that conflicts with what the claim asserts.`;
  }
  return 'This evidence provides context but neither clearly supports nor contradicts the claim.';
}

// Temporal drift comparison data (API current values vs claimed values)
interface CurrentVerifiedData {
  source: string;
  retrieved_at: string;
  data_type?: string;
  claim_values: Record<string, number>;
  current_values: Record<string, number>;
  drift_detected: boolean;
  drift_summary?: string;
  drift_severity?: 'none' | 'minor' | 'significant';
  changes?: string[];
}

interface Claim {
  id: string;
  text: string;
  position: number;
  evidence: Evidence[];

  // Sources reviewed count (for "View sources" link when no evidence displayed)
  sourcesReviewedCount?: number;

  // Classification fields
  claimType?: string;

  // Temporal fields
  isTimeSensitive?: boolean;
  timeReference?: string;
  temporalMarkers?: any;

  // Claim Map (Track B)
  claimMap?: ClaimMap;

  // Temporal drift comparison (current API data vs claimed values)
  currentVerifiedData?: CurrentVerifiedData;
}

interface Evidence {
  id: string;
  source: string;
  url: string;
  title: string;
  snippet: string;
  publishedDate?: string;
  relevanceScore: number;

  // Source type fields
  isFactcheck?: boolean;
  externalSourceProvider?: string;
  sourceType?: string;

  // Fact-check fields
  factcheckPublisher?: string;
  factcheckRating?: string;

  // Source independence fields
  parentCompany?: string;
  independenceFlag?: string;

  // Temporal fields
  temporalRelevanceScore?: number;
  isTimeSensitive?: boolean;

  // Citation Precision (Phase 2)
  pageNumber?: number;
  contextBefore?: string;
  contextAfter?: string;

  // NLI Context Display (Phase 2)
  nliStance?: 'supporting' | 'contradicting' | 'neutral';
  nliConfidence?: number;
  nliEntailment?: number;
  nliContradiction?: number;
}

interface ClaimsSectionProps {
  claims: Claim[];
  checkId: string;
}

export function ClaimsSection({ claims, checkId }: ClaimsSectionProps) {
  const [expandedClaim, setExpandedClaim] = useState<string | null>(null);

  const toggleEvidence = (claimId: string) => {
    setExpandedClaim(expandedClaim === claimId ? null : claimId);
  };

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <h3 className="text-2xl font-bold text-zinc-900">Claims Analyzed ({claims.length})</h3>
        <p className="text-xs text-zinc-500">
          AI-assisted analysis based on publicly available sources. Results should be used as a starting point for further research, not as definitive fact.
        </p>
      </div>

      {claims.map((claim, index) => {
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
            id={`claim-${claim.position}`}
            className="bg-white border border-zinc-200 p-6 space-y-4 scroll-mt-4 relative"
          >
            {/* Claim Number */}
            <span className="absolute top-4 right-6 font-mono text-[10px] tracking-widest uppercase text-zinc-400">
              {String(index + 1).padStart(2, '0')} / {String(claims.length).padStart(2, '0')}
            </span>

            {/* Claim Type & Time Sensitivity Indicators */}
            {(claim.claimType || claim.isTimeSensitive) && (
              <div className="flex flex-wrap gap-2">
                {claim.isTimeSensitive && claim.timeReference && (
                  <TimeSensitiveIndicator timeReference={claim.timeReference} />
                )}
                {claim.claimType && claim.claimType !== 'factual' && (
                  <span className="px-2 py-1 bg-zinc-50 text-zinc-500 text-xs font-medium border border-zinc-200">
                    {claim.claimType.replace('_', ' ')}
                  </span>
                )}
              </div>
            )}

            {/* Claim Text */}
            <p className="text-lg font-medium text-zinc-900">&quot;{claim.text}&quot;</p>

            <ClaimMapView claim={claim} />

            {/* Current Data Comparison - Show when temporal drift detected */}
            {claim.currentVerifiedData?.drift_detected && (
              <div className="mt-3 p-4 bg-blue-50 border border-blue-200">
                <div className="flex items-center gap-2 text-sm text-blue-700 mb-3">
                  <RefreshCw size={14} className="animate-none" />
                  <span className="font-semibold">Data Has Changed Since Publication</span>
                  <span className="text-blue-400">&middot;</span>
                  <span className="text-blue-500 text-xs">{claim.currentVerifiedData.source}</span>
                </div>

                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div className="p-3 bg-zinc-50 border border-zinc-200">
                    <span className="font-mono text-[10px] tracking-widest uppercase text-zinc-400">Article Claimed</span>
                    <div className="mt-1 text-zinc-700 font-medium">
                      {Object.entries(claim.currentVerifiedData.claim_values).map(([k, v]) => (
                        <div key={k} className="flex justify-between">
                          <span className="capitalize">{k.replace('_', ' ')}:</span>
                          <span>{v}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                  <div className="p-3 bg-emerald-50 border border-emerald-200">
                    <span className="font-mono text-[10px] tracking-widest uppercase text-emerald-600">Current Data</span>
                    <div className="mt-1 text-emerald-700 font-semibold">
                      {Object.entries(claim.currentVerifiedData.current_values).map(([k, v]) => (
                        <div key={k} className="flex justify-between">
                          <span className="capitalize">{k.replace('_', ' ')}:</span>
                          <span>{v}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>

                {claim.currentVerifiedData.drift_summary && (
                  <div className="mt-3 flex items-center gap-2 text-xs">
                    <span className={`px-2 py-1 font-medium ${
                      claim.currentVerifiedData.drift_severity === 'minor'
                        ? 'bg-amber-50 text-amber-700 border border-amber-200'
                        : 'bg-orange-50 text-orange-700 border border-orange-200'
                    }`}>
                      {claim.currentVerifiedData.drift_severity === 'minor' ? 'Minor Update' : 'Significant Change'}
                    </span>
                    <span className="text-zinc-500">
                      {claim.currentVerifiedData.drift_summary}
                    </span>
                  </div>
                )}

                <p className="mt-2 text-xs text-zinc-500 italic">
                  The claim may have been accurate when published. Current data retrieved from {claim.currentVerifiedData.source}.
                </p>
              </div>
            )}

            {/* Evidence Toggle Button OR Unsupported Notice */}
            {claim.evidence.length > 0 ? (
              <button
                onClick={() => toggleEvidence(claim.id)}
                className="flex items-center gap-2 text-sm text-accent hover:text-accent/80 transition-colors font-medium"
              >
                <span>Evidence Sources ({claim.evidence.length})</span>
                <ChevronDown
                  size={16}
                  className={`transition-transform duration-300 ${isExpanded ? 'rotate-180' : ''}`}
                />
              </button>
            ) : (
              /* Unsupported Claim Notice - No corroborating evidence found */
              <div className="mt-2 p-4 bg-amber-50 border border-amber-200">
                <div className="flex items-start gap-3">
                  <div className="flex-shrink-0 w-8 h-8 bg-amber-100 flex items-center justify-center">
                    <span className="text-amber-600 text-sm">&#x26A0;</span>
                  </div>
                  <div className="flex-1">
                    <h4 className="text-sm font-semibold text-amber-800">
                      Unsupported Claim
                    </h4>
                    {claim.sourcesReviewedCount && claim.sourcesReviewedCount > 0 ? (
                      <>
                        <p className="mt-1 text-xs text-amber-700 leading-relaxed">
                          {claim.sourcesReviewedCount} source{claim.sourcesReviewedCount !== 1 ? 's were' : ' was'} reviewed but none met the quality threshold for display as evidence.
                        </p>
                        <a
                          href={`/dashboard/check/${checkId}/sources#claim-${claim.position}`}
                          className="mt-2 inline-flex items-center gap-1.5 text-xs text-accent hover:text-accent/80 font-medium transition-colors"
                        >
                          <span>View {claim.sourcesReviewedCount} reviewed source{claim.sourcesReviewedCount !== 1 ? 's' : ''}</span>
                          <ExternalLink size={12} />
                        </a>
                      </>
                    ) : (
                      <>
                        <p className="mt-1 text-xs text-amber-700 leading-relaxed">
                          No credible sources were found to corroborate this claim. This suggests the assertion may be unfounded, inaccurate, or based on unreliable information.
                        </p>
                        <p className="mt-2 text-xs text-zinc-500 italic">
                          We searched multiple databases and news sources. The absence of supporting evidence is itself a significant finding.
                        </p>
                      </>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* Evidence List (Collapsible with Animation) */}
            <div
              className={`overflow-hidden transition-all duration-300 ease-out ${
                isExpanded ? 'max-h-[5000px] opacity-100' : 'max-h-0 opacity-0'
              }`}
            >
              <div className="pt-4 space-y-3">
                {sortedEvidence.map((evidence) => (
                  <div
                    key={evidence.id}
                    onClick={() => window.open(evidence.url, '_blank', 'noopener,noreferrer')}
                    className="flex items-start gap-3 p-4 bg-zinc-50 border border-zinc-200 hover:border-black transition-colors group cursor-pointer"
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
                        <span className="text-sm font-medium text-zinc-900 truncate">
                          {evidence.title}
                        </span>
                        <ExternalLink
                          size={14}
                          className="text-zinc-400 group-hover:text-zinc-900 transition-colors flex-shrink-0"
                        />
                      </div>

                      {/* NLI Stance Badge (Phase 2) */}
                      {evidence.nliStance && (
                        <div className="mb-2">
                          {evidence.nliStance === 'supporting' && (
                            <div className="flex items-center gap-2">
                              <span className="px-3 py-1 bg-emerald-50 text-emerald-700 border border-emerald-200 text-xs font-bold">
                                SUPPORTS CLAIM
                              </span>
                              <span className="text-xs text-emerald-600">
                                {Math.round((evidence.nliConfidence || 0) * 100)}% confident
                              </span>
                            </div>
                          )}
                          {evidence.nliStance === 'contradicting' && (
                            <div className="flex items-center gap-2">
                              <span className="px-3 py-1 bg-red-50 text-red-700 border border-red-200 text-xs font-bold">
                                CONTRADICTS CLAIM
                              </span>
                              <span className="text-xs text-red-600">
                                {Math.round((evidence.nliConfidence || 0) * 100)}% confident
                              </span>
                            </div>
                          )}
                          {evidence.nliStance === 'neutral' && (
                            <div className="flex items-center gap-2">
                              <span className="px-3 py-1 bg-zinc-100 text-zinc-600 border border-zinc-200 text-xs font-bold">
                                NEUTRAL
                              </span>
                              <span className="text-xs text-zinc-500">
                                {Math.round((evidence.nliConfidence || 0) * 100)}% confident
                              </span>
                            </div>
                          )}
                        </div>
                      )}

                      {/* Context Section with Highlighted Passage (Phase 2) */}
                      <div className="my-2 space-y-2">
                        {/* Context Before */}
                        {evidence.contextBefore && (
                          <p className="text-xs text-zinc-500 italic line-clamp-2">
                            ...{evidence.contextBefore}
                          </p>
                        )}

                        {/* Main Snippet - Highlighted with accent border */}
                        <div className="p-3 bg-orange-50 border-l-4 border-accent">
                          <p className="text-sm text-zinc-900 leading-relaxed">
                            {evidence.snippet}
                          </p>
                        </div>

                        {/* Context After */}
                        {evidence.contextAfter && (
                          <p className="text-xs text-zinc-500 italic line-clamp-2">
                            {evidence.contextAfter}...
                          </p>
                        )}
                      </div>

                      {/* Reasoning - Why this supports/contradicts (Phase 2) */}
                      {evidence.nliStance && evidence.nliStance !== 'neutral' && (
                        <div className="p-3 bg-zinc-50 border border-zinc-200 text-xs text-zinc-600 mb-2">
                          <span className="font-semibold text-zinc-700">
                            Why this {evidence.nliStance === 'supporting' ? 'supports' : 'contradicts'}:
                          </span>
                          <p className="mt-1">
                            {generateNliExplanation(evidence.nliStance, evidence.nliConfidence)}
                          </p>
                        </div>
                      )}

                      {/* Metadata: Source · Source Type · Date · Credibility Label */}
                      <div className="flex items-center gap-2 font-mono text-[10px] text-zinc-400 flex-wrap">
                        <span className="font-medium text-zinc-500">{evidence.source}</span>

                        {/* Source Type Badge */}
                        {evidence.externalSourceProvider && (
                          <span className="px-1.5 py-0.5 bg-emerald-50 text-emerald-700 border border-emerald-200 font-bold uppercase">
                            API
                          </span>
                        )}
                        {evidence.isFactcheck && !evidence.externalSourceProvider && (
                          <span className="px-1.5 py-0.5 bg-purple-50 text-purple-700 border border-purple-200 font-bold uppercase">
                            Fact-Check
                          </span>
                        )}

                        {evidence.parentCompany && (
                          <>
                            <span>&middot;</span>
                            <span title="Parent Company">
                              {evidence.parentCompany}
                            </span>
                          </>
                        )}

                        <span>&middot;</span>
                        <span>{formatMonthYear(evidence.publishedDate || null)}</span>

                        {evidence.temporalRelevanceScore !== undefined && (
                          <>
                            <span>&middot;</span>
                            <span title="Temporal Relevance" className="text-amber-600">
                              Time-Relevant
                            </span>
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
