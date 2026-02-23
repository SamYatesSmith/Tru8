'use client';

import { useEffect, useState, useCallback, useRef } from 'react';
import Link from 'next/link';
import { Twitter, Linkedin, MessageCircle, Link as LinkIcon, Check, Reply, ChevronLeft, ChevronRight } from 'lucide-react';
import { isTweetUrl, extractTweetId, buildTwitterReplyUrl } from '@/lib/twitter-utils';
import { ViewSelector, EvidenceMetaStrip } from '@/components/evidence-views';
import { ClaimOverviewCard } from '@/components/evidence-views/overview';
import { CartographerView } from '@/components/evidence-views/cartographer';
import { LibrarianView } from '@/components/evidence-views/librarian';
import { InterpreterView } from '@/components/evidence-views/interpreter';
import { ProjectionistView } from '@/components/evidence-views/projectionist';
import { ChronologistView } from '@/components/evidence-views/chronologist';
import { SeekerView } from '@/components/evidence-views/seeker';

interface PublicReportClientProps {
  check: any;
  highlightClaim?: number;
  highlightView?: string;
}

const VALID_OVERVIEW_VIEWS = ['cartographer', 'librarian', 'projectionist', 'chronologist'];
const VALID_DETAIL_VIEWS = ['cartographer', 'librarian', 'interpreter', 'seeker', 'projectionist', 'chronologist'];

export function PublicReportClient({ check, highlightClaim, highlightView }: PublicReportClientProps) {
  const [copied, setCopied] = useState(false);
  const [activeClaimIndex, setActiveClaimIndex] = useState(0);
  const [checkWideView, setCheckWideView] = useState<string>(
    highlightView && VALID_OVERVIEW_VIEWS.includes(highlightView) ? highlightView : 'cartographer'
  );
  const [claimView, setClaimView] = useState<string>(
    highlightView && VALID_DETAIL_VIEWS.includes(highlightView) ? highlightView : 'cartographer'
  );
  const claimDetailRef = useRef<HTMLDivElement>(null);

  const claims = check.claims || [];
  const videos = check.videos || [];
  const isSingleClaim = claims.length === 1;

  // F07: Sync active view tab to URL for shareability
  const updateUrlViewParam = useCallback((view: string) => {
    if (typeof window === 'undefined') return;
    const url = new URL(window.location.href);
    if (view !== 'cartographer') {
      url.searchParams.set('view', view);
    } else {
      url.searchParams.delete('view');
    }
    window.history.replaceState({}, '', url.toString());
  }, []);

  // Detect if source is a tweet
  const isSourceTweet = isTweetUrl(check.inputUrl);
  const tweetId = isSourceTweet ? extractTweetId(check.inputUrl) : null;

  // Handle highlighted claim on mount
  useEffect(() => {
    if (highlightClaim !== undefined && highlightClaim >= 0 && highlightClaim < claims.length) {
      setActiveClaimIndex(highlightClaim);
      // Scroll to detail after a short delay
      setTimeout(() => {
        claimDetailRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }, 500);
    }
  }, [highlightClaim, claims.length]);

  // Keyboard navigation for claims
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (claims.length <= 1) return;
      if (e.key === 'ArrowLeft' && activeClaimIndex > 0) {
        setActiveClaimIndex(prev => prev - 1);
        claimDetailRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      } else if (e.key === 'ArrowRight' && activeClaimIndex < claims.length - 1) {
        setActiveClaimIndex(prev => prev + 1);
        claimDetailRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [activeClaimIndex, claims.length]);

  // F07: Share URL reads from browser URL (includes ?view= param set by replaceState)
  const shareUrl = typeof window !== 'undefined'
    ? window.location.href
    : `https://tru8.app/r/${check.id}`;

  const shareText = `Evidence Report: ${check.title || 'See the evidence landscape'}`;

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

  const handleClaimSelect = useCallback((position: number) => {
    setActiveClaimIndex(position);
    claimDetailRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }, []);

  const handleSwitchToLibrarian = useCallback(() => { setClaimView('librarian'); updateUrlViewParam('librarian'); }, [updateUrlViewParam]);
  const handleSwitchToInterpreter = useCallback(() => { setClaimView('interpreter'); updateUrlViewParam('interpreter'); }, [updateUrlViewParam]);
  const handleCheckSwitchToLibrarian = useCallback(() => { setCheckWideView('librarian'); updateUrlViewParam('librarian'); }, [updateUrlViewParam]);

  // Get content display for input context
  const getContentDisplay = () => {
    if (check.inputUrl || check.sourceUrl) {
      return { type: 'url' as const, value: check.inputUrl || check.sourceUrl };
    }
    if (check.inputContent?.content) {
      const content = check.inputContent.content;
      return { type: 'text' as const, value: content.length > 200 ? content.slice(0, 200) + '...' : content };
    }
    if (check.articleExcerpt) {
      const excerpt = check.articleExcerpt;
      return { type: 'text' as const, value: excerpt.length > 200 ? excerpt.slice(0, 200) + '...' : excerpt };
    }
    return null;
  };

  // Claim type labels
  const typeLabels: Record<string, string> = {
    empirical: 'Empirical',
    definitional: 'Definitional',
    causal_interpretive: 'Causal',
    predictive: 'Predictive',
    normative_flagged: 'Normative',
  };

  const activeClaim = claims[activeClaimIndex];
  const activeClaimType = activeClaim?.claimMap?.claimType || activeClaim?.claimType;
  const content = getContentDisplay();
  const totalSources = claims.reduce((sum: number, c: any) => sum + (c.evidence?.length || 0), 0);

  return (
    <div className="space-y-6">

      {/* Section 1: Report Header */}
      <header className="mb-2 bg-grid-dot py-8">
        <p className="font-mono text-[10px] tracking-[0.3em] uppercase text-zinc-400 mb-3">Evidence Report</p>
        <h1 className="text-2xl sm:text-3xl font-bold text-zinc-900 leading-tight mb-4">
          {check.title || 'Evidence Report'}
        </h1>
        <div className="flex flex-wrap items-center gap-4 font-mono text-[10px] tracking-widest uppercase text-zinc-400">
          <span>REF: TRU-{check.id?.slice(0, 4).toUpperCase()}-{check.id?.slice(4, 8).toUpperCase()}</span>
          <span>&middot;</span>
          <span>{check.createdAt ? new Date(check.createdAt).toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' }) : '—'}</span>
        </div>
      </header>

      {/* Section 2: Evidence Meta Strip */}
      {claims.length > 0 && (
        <EvidenceMetaStrip
          referenceId={check.id}
          claimsCount={claims.length}
          sourcesCount={totalSources}
          processingTimeMs={check.processingTimeMs}
        />
      )}

      {/* Section 3: Input Context */}
      {content && (
        <div className="border border-zinc-200 p-4">
          <p className="font-mono text-[10px] tracking-widest uppercase text-zinc-400 mb-1">Analysed</p>
          {content.type === 'url' ? (
            <a
              href={content.value}
              target="_blank"
              rel="noopener noreferrer"
              className="text-zinc-900 font-medium text-sm hover:text-[#EA580C] transition-colors break-all"
            >
              {content.value}
            </a>
          ) : (
            <p className="text-zinc-900 font-medium text-sm break-words whitespace-pre-wrap leading-relaxed">
              {content.value}
            </p>
          )}
        </div>
      )}

      {/* Claims + Views — only render if claims exist */}
      {claims.length > 0 && (
        <>
          {/* Section 4: Claim Grid (Multi-Claim Only) */}
          {!isSingleClaim && (
            <div className="mb-4">
              <div className="font-mono text-[10px] uppercase tracking-[0.3em] text-zinc-400 mb-6 border-b border-zinc-100 pb-2">
                Claims &middot; {claims.length}
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {claims.map((claim: any, index: number) => (
                  <ClaimOverviewCard
                    key={claim.id || index}
                    claim={claim}
                    position={index}
                    checkId={check.id}
                    isActive={activeClaimIndex === index}
                    onSelect={handleClaimSelect}
                  />
                ))}
              </div>
            </div>
          )}

          {/* Section 5: Check-Wide Views (Multi-Claim Only) */}
          {!isSingleClaim && (
            <div className="mb-4">
              <ViewSelector mode="overview" activeTab={checkWideView} onTabChange={(tab: string) => { setCheckWideView(tab); updateUrlViewParam(tab); }} />

              {checkWideView === 'cartographer' && (
                <CartographerView
                  scope="check"
                  claims={claims}
                  onSwitchToLibrarian={handleCheckSwitchToLibrarian}
                />
              )}
              {checkWideView === 'librarian' && (
                <LibrarianView scope="check" claims={claims} />
              )}
              {checkWideView === 'projectionist' && (
                <ProjectionistView
                  scope="check"
                  claims={claims}
                  videos={videos}
                  isLoading={false}
                />
              )}
              {checkWideView === 'chronologist' && (
                <ChronologistView
                  scope="check"
                  claims={claims}
                  onSwitchToLibrarian={handleCheckSwitchToLibrarian}
                />
              )}

              {/* Back to claims */}
              <div className="text-center pt-6 border-t border-zinc-100">
                <button
                  onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
                  className="font-mono text-[10px] uppercase tracking-widest text-zinc-400 hover:text-zinc-900 transition-colors inline-flex items-center gap-2"
                >
                  <span className="text-sm">&uarr;</span> Back to claims
                </button>
              </div>
            </div>
          )}

          {/* Section 6: Per-Claim Detail */}
          <div ref={claimDetailRef} id="claim-detail">

            {/* 6a: Claim Header */}
            {activeClaim && (
              <div className="bg-[#F9FAFB] border border-zinc-200 p-6 mb-6">
                <div className="flex items-start justify-between mb-3">
                  {!isSingleClaim && (
                    <span className="font-mono text-[9px] uppercase tracking-widest text-zinc-400">
                      Claim {activeClaimIndex + 1} of {claims.length}
                    </span>
                  )}
                  {activeClaimType && (
                    <span className="px-2.5 py-0.5 bg-zinc-50 border border-zinc-200 text-[9px] font-mono font-bold uppercase tracking-wider text-zinc-500 ml-auto">
                      {typeLabels[activeClaimType] || activeClaimType}
                    </span>
                  )}
                </div>
                <p className="text-base font-medium text-zinc-900 leading-relaxed">
                  {activeClaim.text}
                </p>

                {/* Prev/Next Navigation */}
                {!isSingleClaim && (
                  <div className="mt-4 pt-4 border-t border-zinc-200 flex items-center justify-between">
                    {activeClaimIndex > 0 ? (
                      <button
                        onClick={() => {
                          setActiveClaimIndex(prev => prev - 1);
                          claimDetailRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
                        }}
                        className="font-mono text-[10px] text-zinc-400 hover:text-zinc-900 transition-colors inline-flex items-center gap-1"
                      >
                        <ChevronLeft size={12} /> Previous claim
                      </button>
                    ) : (
                      <span className="font-mono text-[10px] text-zinc-300">No previous claim</span>
                    )}
                    {activeClaimIndex < claims.length - 1 ? (
                      <button
                        onClick={() => {
                          setActiveClaimIndex(prev => prev + 1);
                          claimDetailRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
                        }}
                        className="font-mono text-[10px] text-zinc-400 hover:text-zinc-900 transition-colors inline-flex items-center gap-1"
                      >
                        Next claim <ChevronRight size={12} />
                      </button>
                    ) : (
                      <span className="font-mono text-[10px] text-zinc-300">No next claim</span>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* 6b: Per-Claim View Selector */}
            <ViewSelector mode="detail" activeTab={claimView} onTabChange={(tab: string) => { setClaimView(tab); updateUrlViewParam(tab); }} />

            {/* 6c: Per-Claim View Content */}
            {activeClaim && (
              <>
                {claimView === 'cartographer' && (
                  <CartographerView
                    scope="claim"
                    claims={[activeClaim]}
                    onSwitchToLibrarian={handleSwitchToLibrarian}
                    onSwitchToInterpreter={handleSwitchToInterpreter}
                  />
                )}
                {claimView === 'librarian' && (
                  <LibrarianView scope="claim" claims={[activeClaim]} />
                )}
                {claimView === 'interpreter' && (
                  <InterpreterView claim={activeClaim} />
                )}
                {claimView === 'projectionist' && (
                  <ProjectionistView
                    scope="claim"
                    claims={[activeClaim]}
                    videos={videos.filter((v: any) => v.claimId === activeClaim.id)}
                    isLoading={false}
                  />
                )}
                {claimView === 'chronologist' && (
                  <ChronologistView
                    scope="claim"
                    claims={[activeClaim]}
                    onSwitchToLibrarian={handleSwitchToLibrarian}
                  />
                )}
                {claimView === 'seeker' && (
                  <SeekerView claim={activeClaim} readOnly />
                )}
              </>
            )}
          </div>
        </>
      )}

      {/* No claims state */}
      {claims.length === 0 && (
        <div className="text-center py-12 border border-zinc-200">
          <p className="text-zinc-500 text-lg">No claims were found in this check.</p>
        </div>
      )}

      {/* Section 7: Share Section */}
      <div className="border border-zinc-200 p-6">
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

        {/* Share Icons */}
        <p className="text-sm text-zinc-500 mb-3">
          {isSourceTweet ? 'Share as a new post:' : 'Share your findings:'}
        </p>
        <div className="flex items-center gap-3 flex-wrap">
          <button
            onClick={() => handleShare('x')}
            className="flex items-center justify-center w-10 h-10 border border-zinc-200 hover:bg-zinc-50 text-zinc-500 hover:text-zinc-900 transition-colors"
            aria-label="Share on X"
          >
            <Twitter size={20} />
          </button>
          <button
            onClick={() => handleShare('linkedin')}
            className="flex items-center justify-center w-10 h-10 border border-zinc-200 hover:bg-zinc-50 text-zinc-500 hover:text-zinc-900 transition-colors"
            aria-label="Share on LinkedIn"
          >
            <Linkedin size={20} />
          </button>
          <button
            onClick={() => handleShare('whatsapp')}
            className="flex items-center justify-center w-10 h-10 border border-zinc-200 hover:bg-zinc-50 text-zinc-500 hover:text-zinc-900 transition-colors"
            aria-label="Share on WhatsApp"
          >
            <MessageCircle size={20} />
          </button>
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

      {/* Section 8: Disclaimer */}
      <div className="pt-6 border-t border-zinc-100">
        <p className="text-[12px] text-zinc-400 leading-relaxed">
          This report was generated by Tru8, an evidence research platform. Sources are gathered from publicly available material and classified automatically. Results should be used as a starting point for further research, not as definitive fact.
        </p>
      </div>

      {/* Section 9: CTA */}
      <div className="text-center bg-zinc-900 p-8 md:p-12">
        <h3 className="text-2xl md:text-3xl font-bold text-white mb-4">
          Explore the evidence yourself
        </h3>
        <p className="text-zinc-400 mb-6 max-w-lg mx-auto">
          Submit a claim or article. Your first checks are free.
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
