'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { ArrowLeft, Twitter, Linkedin, MessageCircle, Link as LinkIcon, Check, ExternalLink, ChevronDown, Reply } from 'lucide-react';
import { isTweetUrl, extractTweetId, buildTwitterReplyUrl } from '@/lib/twitter-utils';
import { ClaimMapView, OrientationLine } from '@/components/claim-map';
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

  // Detect if source is a tweet
  const isSourceTweet = isTweetUrl(check.inputUrl);
  const tweetId = isSourceTweet ? extractTweetId(check.inputUrl) : null;

  // Scroll to highlighted claim on mount
  useEffect(() => {
    if (highlightClaim !== undefined) {
      const element = document.getElementById(`claim-${highlightClaim}`);
      if (element) {
        setTimeout(() => {
          element.scrollIntoView({ behavior: 'smooth', block: 'center' });
          element.classList.add('ring-2', 'ring-accent');
          setTimeout(() => {
            element.classList.remove('ring-2', 'ring-accent');
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

  const handleReplyOnTwitter = () => {
    if (!tweetId) return;
    const replyUrl = buildTwitterReplyUrl(tweetId, shareUrl, shareText);
    window.open(replyUrl, '_blank', 'width=600,height=400');
  };

  const toggleEvidence = (claimId: string) => {
    setExpandedClaim(expandedClaim === claimId ? null : claimId);
  };

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
        className="inline-flex items-center gap-2 text-zinc-400 hover:text-zinc-900 transition-colors"
      >
        <ArrowLeft size={20} />
        <span className="text-sm font-medium">Back to Home</span>
      </Link>

      {/* Header with grid-dot background */}
      <div className="mb-6 bg-grid-dot py-8">
        <p className="font-mono text-[10px] tracking-[0.3em] uppercase text-zinc-400 mb-3">PUBLIC REPORT</p>
        <h1 className="text-3xl font-bold text-zinc-900 mb-4">
          Evidence Report
        </h1>
        {check.title && (
          <p className="text-lg text-zinc-500">{check.title}</p>
        )}
        <div className="mt-4 font-mono text-[10px] tracking-widest uppercase text-zinc-400">
          REF: {check.id?.slice(0, 8)} / SOURCES: {check.sourcesCount ?? '—'} / GENERATED: {check.createdAt ? new Date(check.createdAt).toLocaleDateString('en-GB') : '—'}
        </div>
      </div>

      {/* Metadata Card */}
      <div className="bg-white border border-zinc-200 p-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Input Type */}
          <div>
            <p className="font-mono text-[10px] tracking-widest uppercase text-zinc-400 mb-1">Input Type</p>
            <p className="text-zinc-900 font-medium uppercase">{check.inputType}</p>
          </div>

          {/* Created */}
          <div>
            <p className="font-mono text-[10px] tracking-widest uppercase text-zinc-400 mb-1">Analyzed</p>
            <p className="text-zinc-900 font-medium">
              {check.createdAt ? formatRelativeTime(check.createdAt) : 'Recently'}
            </p>
          </div>

          {/* Content */}
          {getContentDisplay() && (
            <div className="md:col-span-2">
              <p className="font-mono text-[10px] tracking-widest uppercase text-zinc-400 mb-1">Content</p>
              <p className="text-zinc-900 font-medium break-words whitespace-pre-wrap leading-relaxed line-clamp-3">
                {getContentDisplay()}
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Overall Summary Card */}
      {check.claims && check.claims.length > 0 && (
        <div className="bg-white border border-zinc-200 p-6 md:p-8">
          <div className="mb-6">
            <h2 className="text-2xl font-bold text-zinc-900 mb-2">Overall Assessment</h2>
            <div className="flex flex-wrap items-center gap-2">
              {check.articleDomain && (
                <div className="bg-zinc-100 text-zinc-600 px-3 py-2 font-medium text-sm inline-flex items-center gap-1.5">
                  <span className="text-zinc-400 font-mono text-[10px] uppercase">Genre:</span>
                  <span className="text-zinc-900">{check.articleDomain}</span>
                  {check.articleJurisdiction && check.articleJurisdiction !== 'Global' && (
                    <span className="text-zinc-400">({check.articleJurisdiction})</span>
                  )}
                </div>
              )}
            </div>
          </div>

          {(() => {
            const firstOrientation = check.claims.find((c: any) => c.claimMap?.orientation)?.claimMap?.orientation ?? null;
            return firstOrientation ? (
              <div className="bg-zinc-50 p-6 mb-6">
                <OrientationLine orientation={firstOrientation} />
              </div>
            ) : null;
          })()}

          {(() => {
            let supported = 0;
            let disputed = 0;
            let unresolved = 0;
            for (const claim of check.claims) {
              if (!claim.claimMap?.elements) continue;
              for (const el of claim.claimMap.elements) {
                if (el.state === 'supported') supported++;
                else if (el.state === 'disputed') disputed++;
                else unresolved++;
              }
            }
            const total = supported + disputed + unresolved;
            if (total === 0) return null;
            return (
              <div className="grid grid-cols-3 gap-4">
                <div className="bg-state-supported/10 border border-state-supported/20 p-4 text-center">
                  <div className="text-3xl font-black text-state-supported">{supported}</div>
                  <div className="text-sm text-state-supported/70 font-medium">Supported</div>
                </div>
                <div className="bg-state-disputed/10 border border-state-disputed/20 p-4 text-center">
                  <div className="text-3xl font-black text-state-disputed">{disputed}</div>
                  <div className="text-sm text-state-disputed/70 font-medium">Disputed</div>
                </div>
                <div className="bg-state-unresolved/10 border border-state-unresolved/20 p-4 text-center">
                  <div className="text-3xl font-black text-state-unresolved">{unresolved}</div>
                  <div className="text-sm text-state-unresolved/70 font-medium">Unresolved</div>
                </div>
              </div>
            );
          })()}
        </div>
      )}

      {/* Claims Section */}
      {check.claims && check.claims.length > 0 && (
        <div className="space-y-6">
          <div className="space-y-2">
            <h3 className="text-2xl font-bold text-zinc-900">Claims Analyzed ({check.claims.length})</h3>
            <p className="text-xs text-zinc-400">
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
                className="bg-white border border-zinc-200 p-6 space-y-4 scroll-mt-4 relative transition-all duration-300"
              >
                {/* Claim Number */}
                <span className="absolute top-4 right-6 font-mono text-[10px] text-zinc-400">
                  {String(index + 1).padStart(2, '0')} / {String(check.claims.length).padStart(2, '0')}
                </span>

                {/* Claim Type & Time Sensitivity Indicators */}
                {(claim.claimType || claim.isTimeSensitive) && (
                  <div className="flex flex-wrap gap-2">
                    {claim.isTimeSensitive && claim.timeReference && (
                      <TimeSensitiveIndicator timeReference={claim.timeReference} />
                    )}
                    {claim.claimType && claim.claimType !== 'factual' && (
                      <span className="px-2 py-1 bg-zinc-100 text-zinc-500 text-xs font-medium">
                        {claim.claimType.replace('_', ' ')}
                      </span>
                    )}
                  </div>
                )}

                {/* Claim Text */}
                <p className="text-lg font-medium text-zinc-900">&quot;{claim.text}&quot;</p>

                <ClaimMapView claim={claim} />

                {/* Evidence Toggle Button */}
                {claim.evidence && claim.evidence.length > 0 ? (
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
                  <div className="mt-2 p-4 bg-amber-50 border border-amber-200">
                    <div className="flex items-start gap-3">
                      <div className="flex-shrink-0 w-8 h-8 bg-amber-100 flex items-center justify-center">
                        <span className="text-amber-600 text-sm">!</span>
                      </div>
                      <div className="flex-1">
                        <h4 className="text-sm font-semibold text-amber-700">
                          Unsupported Claim
                        </h4>
                        <p className="mt-1 text-xs text-amber-600 leading-relaxed">
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

                          {/* NLI Stance Badge */}
                          {evidence.nliStance && (
                            <div className="mb-2">
                              {evidence.nliStance === 'supporting' && (
                                <span className="px-3 py-1 bg-emerald-50 text-emerald-700 border border-emerald-200 text-xs font-bold">
                                  SUPPORTS CLAIM
                                </span>
                              )}
                              {evidence.nliStance === 'contradicting' && (
                                <span className="px-3 py-1 bg-red-50 text-red-700 border border-red-200 text-xs font-bold">
                                  CONTRADICTS CLAIM
                                </span>
                              )}
                              {evidence.nliStance === 'neutral' && (
                                <span className="px-3 py-1 bg-zinc-100 text-zinc-500 border border-zinc-200 text-xs font-bold">
                                  NEUTRAL
                                </span>
                              )}
                            </div>
                          )}

                          {/* Snippet */}
                          <div className="p-3 bg-orange-50 border-l-4 border-accent">
                            <p className="text-sm text-zinc-900 leading-relaxed">
                              {evidence.snippet}
                            </p>
                          </div>

                          {/* Metadata */}
                          <div className="flex items-center gap-2 font-mono text-[10px] text-zinc-400 flex-wrap">
                            <span className="font-medium">{evidence.source}</span>
                            {evidence.isFactcheck && (
                              <span className="px-1.5 py-0.5 bg-blue-50 text-blue-700 border border-blue-200 font-bold uppercase">
                                Fact-Check
                              </span>
                            )}
                            <span>&middot;</span>
                            <span>{formatMonthYear(evidence.publishedDate || null)}</span>
                            {evidence.credibilityScore && (
                              <>
                                <span>&middot;</span>
                                <span className={`font-medium ${
                                  evidence.credibilityScore >= 0.9 ? 'text-emerald-600' :
                                  evidence.credibilityScore >= 0.8 ? 'text-blue-600' :
                                  evidence.credibilityScore >= 0.6 ? 'text-zinc-500' :
                                  'text-amber-600'
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
      <div className="bg-white border border-zinc-200 p-6">
        <h3 className="font-mono text-[10px] font-bold tracking-[0.3em] uppercase text-zinc-400 mb-4">Share This Report</h3>

        {/* Reply on X Section (only when source is a tweet) */}
        {isSourceTweet && tweetId && (
          <div className="mb-6">
            <p className="text-sm text-zinc-500 mb-3">Reply to the original post:</p>
            <button
              onClick={handleReplyOnTwitter}
              className="w-full flex items-center justify-center gap-3 px-6 py-3 bg-zinc-900 hover:bg-zinc-800 text-white text-xs font-bold uppercase tracking-[0.2em] transition-colors"
            >
              <Reply size={20} />
              Reply on X
            </button>
            <p className="text-xs text-zinc-400 mt-2">Post your findings in the original thread</p>
          </div>
        )}

        {/* Share Icons Section */}
        <p className="text-sm text-zinc-500 mb-3">
          {isSourceTweet ? 'Share as a new post:' : 'Share your findings:'}
        </p>
        <div className="flex items-center gap-3 flex-wrap">
          {/* X (Twitter) */}
          <button
            onClick={() => handleShare('x')}
            className="flex items-center justify-center w-10 h-10 border border-zinc-200 hover:bg-zinc-50 text-zinc-500 hover:text-zinc-900 transition-colors"
            aria-label="Share on X"
          >
            <Twitter size={20} />
          </button>

          {/* LinkedIn */}
          <button
            onClick={() => handleShare('linkedin')}
            className="flex items-center justify-center w-10 h-10 border border-zinc-200 hover:bg-zinc-50 text-zinc-500 hover:text-zinc-900 transition-colors"
            aria-label="Share on LinkedIn"
          >
            <Linkedin size={20} />
          </button>

          {/* WhatsApp */}
          <button
            onClick={() => handleShare('whatsapp')}
            className="flex items-center justify-center w-10 h-10 border border-zinc-200 hover:bg-zinc-50 text-zinc-500 hover:text-zinc-900 transition-colors"
            aria-label="Share on WhatsApp"
          >
            <MessageCircle size={20} />
          </button>

          {/* Copy Link */}
          <button
            onClick={handleCopyLink}
            className="flex items-center gap-2 px-4 py-2 border border-zinc-200 hover:bg-zinc-50 text-zinc-500 hover:text-zinc-900 transition-colors"
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

      {/* CTA Section — Dark inverse card per W-10 */}
      <div className="text-center bg-zinc-900 p-8 md:p-12">
        <h3 className="text-2xl md:text-3xl font-bold text-white mb-4">
          Get Started
        </h3>
        <p className="text-zinc-400 mb-6 max-w-lg mx-auto">
          Analyse claims with AI-powered evidence research. Your first 3 checks are free.
        </p>
        <Link
          href="/"
          className="inline-flex items-center gap-2 px-8 py-4 bg-white text-zinc-900 text-xs font-bold uppercase tracking-[0.2em] hover:bg-zinc-100 transition-colors"
        >
          Get Started Free
        </Link>
      </div>
    </div>
  );
}
