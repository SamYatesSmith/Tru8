'use client';

import { useState } from 'react';
import { ChevronDown, ExternalLink, RefreshCw } from 'lucide-react';
import { VerdictPill } from '@/app/dashboard/components/verdict-pill';
import { ConfidenceBar } from '@/app/dashboard/components/confidence-bar';
import { DecisionTrail } from '@/app/dashboard/components/decision-trail';
import { ConfidenceBreakdown } from '@/app/dashboard/components/confidence-breakdown';
import { UncertaintyExplanation } from '@/app/dashboard/components/uncertainty-explanation';
import { NonVerifiableNotice } from '@/app/dashboard/components/non-verifiable-notice';
import { FactCheckBadge } from '@/app/dashboard/components/fact-check-badge';
import { TimeSensitiveIndicator } from '@/app/dashboard/components/time-sensitive-indicator';
import { formatMonthYear } from '@/lib/utils';

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
  credibilityScore?: number;

  // Source type fields
  isFactcheck?: boolean;
  externalSourceProvider?: string;  // API name (e.g., "Semantic Scholar", "NOAA")
  sourceType?: string;  // 'factcheck', 'news', 'academic', 'government', 'general'

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
}

export function ClaimsSection({ claims }: ClaimsSectionProps) {
  const [expandedClaim, setExpandedClaim] = useState<string | null>(null);

  const toggleEvidence = (claimId: string) => {
    setExpandedClaim(expandedClaim === claimId ? null : claimId);
  };

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <h3 className="text-2xl font-bold text-white">Claims Analyzed ({claims.length})</h3>
        <p className="text-xs text-slate-500">
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
            className="bg-slate-800/50 border border-slate-700 rounded-xl p-6 space-y-4 scroll-mt-4 relative"
          >
            {/* Claim Number */}
            <span className="absolute top-4 right-6 text-xs text-slate-500 font-medium">
              Claim {index + 1} of {claims.length}
            </span>

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

                {/* Current Data Comparison - Show when temporal drift detected */}
                {claim.currentVerifiedData?.drift_detected && (
                  <div className="mt-3 p-4 bg-blue-900/20 border border-blue-600/30 rounded-lg">
                    <div className="flex items-center gap-2 text-sm text-blue-300 mb-3">
                      <RefreshCw size={14} className="animate-none" />
                      <span className="font-semibold">Data Has Changed Since Publication</span>
                      <span className="text-blue-500">·</span>
                      <span className="text-blue-400 text-xs">{claim.currentVerifiedData.source}</span>
                    </div>

                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div className="p-3 bg-slate-800/50 rounded-lg">
                        <span className="text-xs text-slate-500 uppercase tracking-wide">Article Claimed</span>
                        <div className="mt-1 text-slate-300 font-medium">
                          {Object.entries(claim.currentVerifiedData.claim_values).map(([k, v]) => (
                            <div key={k} className="flex justify-between">
                              <span className="capitalize">{k.replace('_', ' ')}:</span>
                              <span>{v}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                      <div className="p-3 bg-emerald-900/30 border border-emerald-600/20 rounded-lg">
                        <span className="text-xs text-emerald-400 uppercase tracking-wide">Current Data</span>
                        <div className="mt-1 text-emerald-300 font-semibold">
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
                        <span className={`px-2 py-1 rounded font-medium ${
                          claim.currentVerifiedData.drift_severity === 'minor'
                            ? 'bg-amber-500/20 text-amber-400'
                            : 'bg-orange-500/20 text-orange-400'
                        }`}>
                          {claim.currentVerifiedData.drift_severity === 'minor' ? 'Minor Update' : 'Significant Change'}
                        </span>
                        <span className="text-slate-400">
                          {claim.currentVerifiedData.drift_summary}
                        </span>
                      </div>
                    )}

                    <p className="mt-2 text-xs text-slate-500 italic">
                      The claim may have been accurate when published. Current data retrieved from {claim.currentVerifiedData.source}.
                    </p>
                  </div>
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
                <ChevronDown
                  size={16}
                  className={`transition-transform duration-300 ${isExpanded ? 'rotate-180' : ''}`}
                />
              </button>
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
                    className="flex items-start gap-3 p-4 bg-slate-900/50 border border-slate-700 rounded-lg hover:border-slate-600 transition-colors group cursor-pointer"
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

                      {/* NLI Stance Badge (Phase 2) */}
                      {evidence.nliStance && (
                        <div className="mb-2">
                          {evidence.nliStance === 'supporting' && (
                            <div className="flex items-center gap-2">
                              <span className="px-3 py-1 bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 rounded-full text-xs font-bold">
                                🟢 SUPPORTS CLAIM
                              </span>
                              <span className="text-xs text-emerald-400/70">
                                {Math.round((evidence.nliConfidence || 0) * 100)}% confident
                              </span>
                            </div>
                          )}
                          {evidence.nliStance === 'contradicting' && (
                            <div className="flex items-center gap-2">
                              <span className="px-3 py-1 bg-red-500/20 text-red-400 border border-red-500/30 rounded-full text-xs font-bold">
                                🔴 CONTRADICTS CLAIM
                              </span>
                              <span className="text-xs text-red-400/70">
                                {Math.round((evidence.nliConfidence || 0) * 100)}% confident
                              </span>
                            </div>
                          )}
                          {evidence.nliStance === 'neutral' && (
                            <div className="flex items-center gap-2">
                              <span className="px-3 py-1 bg-slate-500/20 text-slate-400 border border-slate-500/30 rounded-full text-xs font-bold">
                                ⚪ NEUTRAL
                              </span>
                              <span className="text-xs text-slate-400/70">
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
                          <p className="text-xs text-slate-500 italic line-clamp-2">
                            ...{evidence.contextBefore}
                          </p>
                        )}

                        {/* Main Snippet - Highlighted in Brand Orange */}
                        <div className="p-3 bg-orange-500/10 border-l-4 border-[#f57a07] rounded">
                          <p className="text-sm text-white leading-relaxed">
                            {evidence.snippet}
                          </p>
                        </div>

                        {/* Context After */}
                        {evidence.contextAfter && (
                          <p className="text-xs text-slate-500 italic line-clamp-2">
                            {evidence.contextAfter}...
                          </p>
                        )}
                      </div>

                      {/* Reasoning - Why this supports/contradicts (Phase 2) */}
                      {evidence.nliStance && evidence.nliStance !== 'neutral' && (
                        <div className="p-3 bg-slate-800/50 border border-slate-700 rounded text-xs text-slate-300 mb-2">
                          <span className="font-semibold text-slate-200">
                            💬 Why this {evidence.nliStance === 'supporting' ? 'supports' : 'contradicts'}:
                          </span>
                          <p className="mt-1">
                            {generateNliExplanation(evidence.nliStance, evidence.nliConfidence)}
                          </p>
                        </div>
                      )}

                      {/* Metadata: Source · Source Type · Date · Credibility Label */}
                      <div className="flex items-center gap-2 text-xs text-slate-500 flex-wrap">
                        <span className="font-medium">{evidence.source}</span>

                        {/* Source Type Badge */}
                        {evidence.externalSourceProvider && (
                          <span className="px-1.5 py-0.5 bg-emerald-500/20 text-emerald-400 rounded text-[10px] font-bold uppercase">
                            API
                          </span>
                        )}
                        {evidence.isFactcheck && !evidence.externalSourceProvider && (
                          <span className="px-1.5 py-0.5 bg-purple-500/20 text-purple-400 rounded text-[10px] font-bold uppercase">
                            Fact-Check
                          </span>
                        )}

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

                        {evidence.credibilityScore && (
                          <>
                            <span>·</span>
                            <span className={`font-medium ${
                              evidence.credibilityScore >= 0.9 ? 'text-emerald-400' :
                              evidence.credibilityScore >= 0.8 ? 'text-blue-400' :
                              evidence.credibilityScore >= 0.6 ? 'text-slate-400' :
                              'text-amber-400'
                            }`}>
                              {evidence.credibilityScore >= 0.9 ? 'Expert Source' :
                               evidence.credibilityScore >= 0.8 ? 'Verified Source' :
                               evidence.credibilityScore >= 0.6 ? 'General Source' :
                               'Unverified Source'}
                            </span>
                          </>
                        )}

                        {evidence.temporalRelevanceScore !== undefined && (
                          <>
                            <span>·</span>
                            <span title="Temporal Relevance" className="text-amber-400">
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
