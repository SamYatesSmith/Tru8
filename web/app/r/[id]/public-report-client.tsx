'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { ArrowLeft, Twitter, Linkedin, MessageCircle, Link as LinkIcon, Check, ExternalLink, ChevronDown } from 'lucide-react';
import { VerdictPill } from '@/app/dashboard/components/verdict-pill';
import { ConfidenceBar } from '@/app/dashboard/components/confidence-bar';
import { DecisionTrail } from '@/app/dashboard/components/decision-trail';
import { ConfidenceBreakdown } from '@/app/dashboard/components/confidence-breakdown';
import { UncertaintyExplanation } from '@/app/dashboard/components/uncertainty-explanation';
import { NonVerifiableNotice } from '@/app/dashboard/components/non-verifiable-notice';
import { FactCheckBadge } from '@/app/dashboard/components/fact-check-badge';
import { TimeSensitiveIndicator } from '@/app/dashboard/components/time-sensitive-indicator';
import { formatMonthYear, formatRelativeTime } from '@/lib/utils';

interface PublicReportClientProps {
  check: any;
  highlightClaim?: number;
}

// Helper function for NLI explanations
function generateNliExplanation(stance: string, confidence?: number): string {
  const confidenceLevel = (confidence || 0) >= 0.8 ? 'strongly' :
                          (confidence || 0) >= 0.6 ? 'moderately' : 'weakly';

  if (stance === 'supporting') {
    return `This evidence ${confidenceLevel} confirms key aspects of the claim.`;
  } else if (stance === 'contradicting') {
    return `This evidence ${confidenceLevel} disputes the claim.`;
  }
  return 'This evidence provides context but neither clearly supports nor contradicts the claim.';
}

export function PublicReportClient({ check, highlightClaim }: PublicReportClientProps) {
  const [expandedClaim, setExpandedClaim] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  // Scroll to highlighted claim on mount
  useEffect(() => {
    if (highlightClaim !== undefined) {
      const element = document.getElementById(`claim-${highlightClaim}`);
      if (element) {
        setTimeout(() => {
          element.scrollIntoView({ behavior: 'smooth', block: 'center' });
          element.classList.add('ring-2', 'ring-[#f57a07]');
          setTimeout(() => {
            element.classList.remove('ring-2', 'ring-[#f57a07]');
          }, 3000);
        }, 500);
      }
    }
  }, [highlightClaim]);

  const shareUrl = typeof window !== 'undefined'
    ? `${window.location.origin}/r/${check.id}`
    : `https://tru8.app/r/${check.id}`;

  const shareText = `Evidence Report: ${check.title || 'See what credible sources say'}`;

  const handleShare = (platform: string) => {
    const shareUrls: Record<string, string> = {
      x: `https://twitter.com/intent/tweet?url=${encodeURIComponent(shareUrl)}&text=${encodeURIComponent(shareText)}`,
      linkedin: `https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(shareUrl)}`,
      whatsapp: `https://wa.me/?text=${encodeURIComponent(shareText + ' ' + shareUrl)}`,
    };

    if (platform in shareUrls) {
      window.open(shareUrls[platform], '_blank', 'width=600,height=400');
    }
  };

  const handleCopyLink = async () => {
    try {
      await navigator.clipboard.writeText(shareUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (error) {
      console.error('Copy failed:', error);
    }
  };

  const toggleEvidence = (claimId: string) => {
    setExpandedClaim(expandedClaim === claimId ? null : claimId);
  };

  // Calculate credibility level
  const getCredibilityLevel = (score: number) => {
    if (score >= 80) return { label: 'High Credibility', color: 'text-emerald-400', bg: 'bg-emerald-500/20' };
    if (score >= 60) return { label: 'Moderate Credibility', color: 'text-amber-400', bg: 'bg-amber-500/20' };
    return { label: 'Low Credibility', color: 'text-red-400', bg: 'bg-red-500/20' };
  };

  const credibility = check.credibilityScore ? getCredibilityLevel(check.credibilityScore) : null;

  // Get content display
  const getContentDisplay = () => {
    if (check.inputUrl || check.sourceUrl) {
      return check.inputUrl || check.sourceUrl;
    }
    if (check.inputContent?.content) {
      return check.inputContent.content;
    }
    if (check.articleExcerpt) {
      return check.articleExcerpt;
    }
    return null;
  };

  return (
    <div className="space-y-6">
      {/* Back Button */}
      <Link
        href="/"
        className="inline-flex items-center gap-2 text-slate-400 hover:text-[#f57a07] transition-colors"
      >
        <ArrowLeft size={20} />
        <span className="text-sm font-medium">Back to Home</span>
      </Link>

      {/* Header */}
      <div className="mb-6">
        <h1 className="text-3xl sm:text-4xl md:text-5xl font-black text-white mb-4">
          Evidence Report
        </h1>
        {check.title && (
          <p className="text-lg text-slate-300">{check.title}</p>
        )}
      </div>

      {/* Metadata Card */}
      <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Input Type */}
          <div>
            <p className="text-slate-400 text-sm mb-1">Input Type</p>
            <p className="text-white font-medium uppercase">{check.inputType}</p>
          </div>

          {/* Created */}
          <div>
            <p className="text-slate-400 text-sm mb-1">Analyzed</p>
            <p className="text-white font-medium">
              {check.createdAt ? formatRelativeTime(check.createdAt) : 'Recently'}
            </p>
          </div>

          {/* Content */}
          {getContentDisplay() && (
            <div className="md:col-span-2">
              <p className="text-slate-400 text-sm mb-1">Content</p>
              <p className="text-white font-medium break-words whitespace-pre-wrap leading-relaxed line-clamp-3">
                {getContentDisplay()}
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Overall Summary Card */}
      {check.overallSummary && check.credibilityScore !== undefined && (
        <div className="bg-gradient-to-br from-blue-950/50 to-purple-950/50 border-2 border-blue-500/30 rounded-xl p-6 md:p-8">
          {/* Header */}
          <div className="mb-6">
            <h2 className="text-2xl font-black text-white mb-2">Overall Assessment</h2>
            <div className="flex flex-wrap items-center gap-2">
              {credibility && (
                <div className={`${credibility.bg} ${credibility.color} px-4 py-2 rounded-lg font-bold text-sm inline-block`}>
                  {credibility.label}
                </div>
              )}
              {check.articleDomain && (
                <div className="bg-slate-700/50 text-slate-300 px-3 py-2 rounded-lg font-medium text-sm inline-flex items-center gap-1.5">
                  <span className="text-slate-500">Genre:</span>
                  <span className="text-white">{check.articleDomain}</span>
                  {check.articleJurisdiction && check.articleJurisdiction !== 'Global' && (
                    <span className="text-slate-400">({check.articleJurisdiction})</span>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Summary Text */}
          <div className="bg-slate-900/50 rounded-lg p-6 mb-6">
            <p className="text-white/90 text-lg leading-relaxed">
              {check.overallSummary}
            </p>
          </div>

          {/* Claims Breakdown */}
          <div className="grid grid-cols-3 gap-4">
            <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-lg p-4 text-center">
              <div className="text-3xl font-black text-emerald-400">{check.claimsSupported || 0}</div>
              <div className="text-sm text-emerald-400/70 font-medium">Supported</div>
            </div>
            <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-4 text-center">
              <div className="text-3xl font-black text-amber-400">{check.claimsUncertain || 0}</div>
              <div className="text-sm text-amber-400/70 font-medium">Uncertain</div>
            </div>
            <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 text-center">
              <div className="text-3xl font-black text-red-400">{check.claimsContradicted || 0}</div>
              <div className="text-sm text-red-400/70 font-medium">Contradicted</div>
            </div>
          </div>
        </div>
      )}

      {/* Claims Section */}
      {check.claims && check.claims.length > 0 && (
        <div className="space-y-6">
          <div className="space-y-2">
            <h3 className="text-2xl font-bold text-white">Claims Analyzed ({check.claims.length})</h3>
            <p className="text-xs text-slate-500">
              AI-assisted analysis based on publicly available sources. Results should be used as a starting point for further research, not as definitive fact.
            </p>
          </div>

          {check.claims.map((claim: any, index: number) => {
            const isExpanded = expandedClaim === claim.id;

            // Sort evidence by relevance score, prioritize fact-checks
            const sortedEvidence = [...(claim.evidence || [])].sort((a: any, b: any) => {
              if (a.isFactcheck && !b.isFactcheck) return -1;
              if (!a.isFactcheck && b.isFactcheck) return 1;
              return (b.relevanceScore || 0) - (a.relevanceScore || 0);
            });

            return (
              <div
                key={claim.id}
                id={`claim-${claim.position}`}
                className="bg-slate-800/50 border border-slate-700 rounded-xl p-6 space-y-4 scroll-mt-4 relative transition-all duration-300"
              >
                {/* Claim Number */}
                <span className="absolute top-4 right-6 text-xs text-slate-500 font-medium">
                  Claim {index + 1} of {check.claims.length}
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
                {claim.evidence && claim.evidence.length > 0 ? (
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
                ) : (
                  <div className="mt-2 p-4 bg-amber-900/20 border border-amber-600/30 rounded-lg">
                    <div className="flex items-start gap-3">
                      <div className="flex-shrink-0 w-8 h-8 bg-amber-500/20 rounded-full flex items-center justify-center">
                        <span className="text-amber-400 text-sm">!</span>
                      </div>
                      <div className="flex-1">
                        <h4 className="text-sm font-semibold text-amber-300">
                          Unsupported Claim
                        </h4>
                        <p className="mt-1 text-xs text-amber-200/80 leading-relaxed">
                          No credible sources were found to corroborate this claim.
                        </p>
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
                    {sortedEvidence.map((evidence: any) => (
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

                          {/* NLI Stance Badge */}
                          {evidence.nliStance && (
                            <div className="mb-2">
                              {evidence.nliStance === 'supporting' && (
                                <span className="px-3 py-1 bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 rounded-full text-xs font-bold">
                                  SUPPORTS CLAIM
                                </span>
                              )}
                              {evidence.nliStance === 'contradicting' && (
                                <span className="px-3 py-1 bg-red-500/20 text-red-400 border border-red-500/30 rounded-full text-xs font-bold">
                                  CONTRADICTS CLAIM
                                </span>
                              )}
                              {evidence.nliStance === 'neutral' && (
                                <span className="px-3 py-1 bg-slate-500/20 text-slate-400 border border-slate-500/30 rounded-full text-xs font-bold">
                                  NEUTRAL
                                </span>
                              )}
                            </div>
                          )}

                          {/* Snippet */}
                          <div className="p-3 bg-orange-500/10 border-l-4 border-[#f57a07] rounded">
                            <p className="text-sm text-white leading-relaxed">
                              {evidence.snippet}
                            </p>
                          </div>

                          {/* Metadata */}
                          <div className="flex items-center gap-2 text-xs text-slate-500 flex-wrap">
                            <span className="font-medium">{evidence.source}</span>
                            {evidence.isFactcheck && (
                              <span className="px-1.5 py-0.5 bg-purple-500/20 text-purple-400 rounded text-[10px] font-bold uppercase">
                                Fact-Check
                              </span>
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
      )}

      {/* Share Section */}
      <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
        <h3 className="text-xl font-bold text-white mb-4">Share This Report</h3>

        <div className="flex items-center gap-3 flex-wrap">
          {/* X (Twitter) */}
          <button
            onClick={() => handleShare('x')}
            className="flex items-center justify-center w-10 h-10 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-colors"
            aria-label="Share on X"
          >
            <Twitter size={20} />
          </button>

          {/* LinkedIn */}
          <button
            onClick={() => handleShare('linkedin')}
            className="flex items-center justify-center w-10 h-10 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-colors"
            aria-label="Share on LinkedIn"
          >
            <Linkedin size={20} />
          </button>

          {/* WhatsApp */}
          <button
            onClick={() => handleShare('whatsapp')}
            className="flex items-center justify-center w-10 h-10 bg-slate-700 hover:bg-[#25D366] text-white rounded-lg transition-colors"
            aria-label="Share on WhatsApp"
          >
            <MessageCircle size={20} />
          </button>

          {/* Copy Link */}
          <button
            onClick={handleCopyLink}
            className="flex items-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-colors"
          >
            {copied ? (
              <>
                <Check size={18} />
                <span className="text-sm font-medium">Copied!</span>
              </>
            ) : (
              <>
                <LinkIcon size={18} />
                <span className="text-sm font-medium">Copy Link</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* CTA Section */}
      <div className="text-center bg-slate-800/30 border border-slate-700 rounded-xl p-8 md:p-12">
        <h3 className="text-2xl md:text-3xl font-bold text-white mb-4">
          Verify your own content
        </h3>
        <p className="text-slate-400 mb-6 max-w-lg mx-auto">
          See what credible sources say about any claim. Your first 3 checks are free.
        </p>
        <Link
          href="/"
          className="inline-flex items-center gap-2 px-8 py-4 bg-[#f57a07] hover:bg-[#e06a00] text-white rounded-xl font-bold transition-colors"
        >
          Get Started Free
        </Link>
      </div>
    </div>
  );
}
