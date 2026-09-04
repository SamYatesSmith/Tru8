'use client';

import { useEffect, useState, useCallback, useRef } from 'react';
import Link from 'next/link';
import { Linkedin, MessageCircle, Link as LinkIcon, Check, Reply, ChevronLeft, ChevronRight, Download } from 'lucide-react';
import { isTweetUrl, extractTweetId, buildTwitterReplyUrl } from '@/lib/twitter-utils';
import { ViewSelector, ViewGuide, EvidenceMetaStrip } from '@/components/evidence-views';
import { ClaimSectionStack } from '@/components/evidence-views/overview';
import { CartographerView } from '@/components/evidence-views/cartographer';
import { LibrarianView } from '@/components/evidence-views/librarian';
import { CompareView } from '@/components/evidence-views/compare';
import { apiClient } from '@/lib/api';
import { ProjectionistView } from '@/components/evidence-views/projectionist';
import { ChronologistView } from '@/components/evidence-views/chronologist';
import { SeekerView } from '@/components/evidence-views/seeker';
import { ClaimSummaryPanel } from '@/components/evidence-views/ClaimSummaryPanel';
import { capture } from '@/lib/analytics';
import { EvidenceRelationship } from '@shared/types';

interface PublicReportClientProps {
  check: any;
  highlightClaim?: number;
  highlightView?: string;
}

// 'correspondent' (the retired Sources view) deliberately absent: those deep
// links translate to librarian with a notice (COMPARE design §14.3) — the
// Evidence ledger absorbed the source-list job.
const VALID_DETAIL_VIEWS = ['cartographer', 'librarian', 'compare', 'seeker', 'projectionist', 'chronologist'];

export function PublicReportClient({ check, highlightClaim, highlightView }: PublicReportClientProps) {
  const [copied, setCopied] = useState(false);
  const [activeClaimIndex, setActiveClaimIndex] = useState(0);
  const [claimView, setClaimView] = useState<string>(
    highlightView === 'correspondent'
      ? 'librarian'
      : highlightView && VALID_DETAIL_VIEWS.includes(highlightView)
        ? highlightView
        : 'librarian'
  );
  // A shared ?view=correspondent link landed here — say so rather than
  // silently swapping lenses.
  const [sourcesViewNotice, setSourcesViewNotice] = useState<boolean>(
    highlightView === 'correspondent'
  );
  // Stored comparisons per claim id, to decide COMPARE tab visibility
  // (§12.2b: a cold /r/ reader cannot create, so an empty tab is a dead
  // end — hide it, absent not disabled). null = not yet known → hidden.
  const [comparisonCounts, setComparisonCounts] = useState<Record<string, number>>({});
  const claimDetailRef = useRef<HTMLDivElement>(null);

  const claims = check.claims || [];
  const [videos, setVideos] = useState<any[]>(check.videos || []);
  const isSingleClaim = claims.length === 1;

  // COMPARE tab visibility: one public GET per claim (cached in state) for
  // its stored-comparison count. CompareView re-fetches on open — that
  // second request only happens when the tab is actually used.
  useEffect(() => {
    const activeClaim = claims[activeClaimIndex];
    if (!activeClaim || comparisonCounts[activeClaim.id] !== undefined) return;
    let cancelled = false;
    apiClient
      .getPublicComparisons(check.id, activeClaim.id)
      .then((data) => {
        if (cancelled) return;
        setComparisonCounts((prev) => ({
          ...prev,
          [activeClaim.id]: (data.comparisons || []).length,
        }));
      })
      .catch(() => {
        if (cancelled) return;
        setComparisonCounts((prev) => ({ ...prev, [activeClaim.id]: 0 }));
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeClaimIndex, check.id]);

  // If the active claim has no comparisons while COMPARE is selected (claim
  // navigation), snap to the default lens rather than showing a hidden tab's
  // empty content.
  useEffect(() => {
    const activeClaim = claims[activeClaimIndex];
    if (
      claimView === 'compare' &&
      activeClaim &&
      comparisonCounts[activeClaim.id] !== undefined &&
      (comparisonCounts[activeClaim.id] || 0) === 0
    ) {
      setClaimView('librarian');
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeClaimIndex, claimView, comparisonCounts]);

  // Re-poll for videos when the cached SSR render had none for the active claim.
  // Video recs are written by a fire-and-forget task ~1s after the check
  // completes — after the (60s-cached) report first renders — so the first view
  // can miss them. Public endpoint (no auth); stops the moment videos land.
  useEffect(() => {
    const activeClaim = claims[activeClaimIndex];
    if (!activeClaim) return;
    const haveFromSSR = (check.videos || []).filter((v: any) => v.claimId === activeClaim.id).length;
    if (haveFromSSR > 0) return;
    let cancelled = false;
    let attempt = 0;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    const poll = async () => {
      try {
        const res = await fetch(`${apiUrl}/api/v1/checks/public/${check.id}/videos`, { cache: 'no-store' });
        if (res.ok) {
          const data = await res.json();
          if (!cancelled && Array.isArray(data.videos) && data.videos.length > 0) {
            setVideos(data.videos);
            return;
          }
        }
      } catch {
        /* transient — retry below */
      }
      if (!cancelled && attempt < 4) {
        attempt += 1;
        timer = setTimeout(poll, 2500);
      }
    };
    poll();
    return () => { cancelled = true; if (timer) clearTimeout(timer); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeClaimIndex, check.id]);

  // F07: Sync active view tab to URL for shareability
  const updateUrlViewParam = useCallback((view: string) => {
    if (typeof window === 'undefined') return;
    const url = new URL(window.location.href);
    if (view !== 'librarian') {
      url.searchParams.set('view', view);
    } else {
      url.searchParams.delete('view');
    }
    window.history.replaceState({}, '', url.toString());
  }, []);

  // Detect if source is a tweet
  const isSourceTweet = isTweetUrl(check.inputUrl);
  const tweetId = isSourceTweet ? extractTweetId(check.inputUrl) : null;

  // Phase 1 instrumentation: report opened (public /r/), once per report.
  useEffect(() => {
    capture('report_viewed', { surface: 'public', claims: claims.length });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [check.id]);

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
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;
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
    : `https://www.trueight.com/r/${check.id}`;

  const shareText = `Evidence Report: ${check.title || 'See the evidence landscape'}`;

  const handleShare = (platform: string) => {
    const shareUrls: Record<string, string> = {
      x: `https://twitter.com/intent/tweet?url=${encodeURIComponent(shareUrl)}&text=${encodeURIComponent(shareText)}`,
      linkedin: `https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(shareUrl)}`,
      whatsapp: `https://wa.me/?text=${encodeURIComponent(shareText + ' ' + shareUrl)}`,
    };

    if (platform in shareUrls) {
      capture('share_clicked', { platform });
      window.open(shareUrls[platform], '_blank', 'noopener,noreferrer,width=600,height=400');
    }
  };

  const handleCopyLink = async () => {
    try {
      await navigator.clipboard.writeText(shareUrl);
      capture('share_clicked', { platform: 'copy' });
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (error) {
      console.error('Copy failed:', error);
    }
  };

  const handleDownloadPdf = () => {
    capture('export_clicked', { surface: 'public' });
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    window.open(`${apiUrl}/api/v1/checks/public/${check.id}/export/pdf`, '_blank');
  };

  const handleReplyOnTwitter = () => {
    if (!tweetId) return;
    const replyUrl = buildTwitterReplyUrl(tweetId, shareUrl, shareText);
    window.open(replyUrl, '_blank', 'noopener,noreferrer,width=600,height=400');
  };

  const handleClaimSelect = useCallback((position: number) => {
    setActiveClaimIndex(position);
    claimDetailRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }, []);

  const handleSwitchToLibrarian = useCallback(() => { setClaimView('librarian'); updateUrlViewParam('librarian'); }, [updateUrlViewParam]);

  // Slice 0a/0b — summary hub: switch lens (+ optional Evidence deep-link
  // filter), persist the filter to the URL, then scroll the lens into view.
  const lensSectionRef = useRef<HTMLDivElement>(null);
  const [evidenceFilter, setEvidenceFilter] = useState<{ rel?: EvidenceRelationship[]; element?: string }>(() => {
    if (typeof window === 'undefined') return {};
    const p = new URLSearchParams(window.location.search);
    const rel = p.get('rel');
    return { rel: rel ? (rel.split(',') as EvidenceRelationship[]) : undefined, element: p.get('element') || undefined };
  });
  const handleNavigateFromSummary = useCallback((view: string, params?: { rel?: EvidenceRelationship[]; element?: string }) => {
    setClaimView(view);
    updateUrlViewParam(view);
    const url = new URL(window.location.href);
    if (params?.rel && params.rel.length) url.searchParams.set('rel', params.rel.join(','));
    else url.searchParams.delete('rel');
    if (params?.element) url.searchParams.set('element', params.element);
    else url.searchParams.delete('element');
    window.history.replaceState({}, '', url.toString());
    setEvidenceFilter({ rel: params?.rel, element: params?.element });
    setTimeout(() => {
      lensSectionRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 50);
  }, [updateUrlViewParam]);

  // A focused element / disposition filter belongs to one claim — clear it when
  // the active claim changes (but NOT on mount, so a shared deep-link survives).
  const didMountClaim = useRef(false);
  useEffect(() => {
    if (!didMountClaim.current) { didMountClaim.current = true; return; }
    setEvidenceFilter({});
    if (typeof window !== 'undefined') {
      const url = new URL(window.location.href);
      url.searchParams.delete('rel');
      url.searchParams.delete('element');
      window.history.replaceState({}, '', url.toString());
    }
  }, [activeClaimIndex]);

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
  const activeClaim = claims[activeClaimIndex];
  const rawContent = getContentDisplay();
  // 2026-09-04: for a text check the title now IS the claim, whole (the API
  // used to cut it at 70 chars). Showing the same sentence again under
  // "Analysed" was the duplication the founder called out — drop the block
  // when it would only repeat the heading. URL checks (a link under a title)
  // and long pasted text (first sentence above, excerpt below) still show it.
  const analysedRepeatsTitle =
    rawContent?.type === 'text' &&
    (check.inputContent?.content || check.articleExcerpt || '').trim() === (check.title || '').trim();
  const content = analysedRepeatsTitle ? null : rawContent;
  const totalSources = claims.reduce((sum: number, c: any) => sum + (c.evidence?.length || 0), 0);

  return (
    <div className="space-y-6">

      {/* Section 1: Report Header */}
      <header className="mb-2 bg-grid-dot py-8">
        <p className="font-mono text-[10px] tracking-[0.3em] uppercase text-zinc-500 mb-3">Evidence Report</p>
        <h1 className="text-2xl sm:text-3xl font-bold text-zinc-900 leading-tight mb-4">
          {check.title || 'Evidence Report'}
        </h1>
        <div className="flex flex-wrap items-center gap-4 font-mono text-[10px] tracking-widest uppercase text-zinc-500">
          <span>{check.createdAt ? new Date(check.createdAt).toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' }) : '—'}</span>
        </div>
      </header>

      {/* Section 2: Evidence Meta Strip */}
      {claims.length > 0 && (
        <EvidenceMetaStrip
          referenceId={check.id}
          claimsCount={claims.length}
          sourcesCount={totalSources}
          sourcesFoundCount={check.totalSearchResults || check.rawSourcesCount}
          processingTimeMs={check.processingTimeMs}
        />
      )}

      {/* Section 3: Input Context */}
      {content && (
        <div className="border border-zinc-200 p-4">
          <p className="font-mono text-[10px] tracking-widest uppercase text-zinc-500 mb-1">Analysed</p>
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
          {/* Section 4: Claim-Sectioned Overview (Multi-Claim Only) */}
          {!isSingleClaim && (
            <ClaimSectionStack
              claims={claims}
              onExplore={handleClaimSelect}
              inputType={check.inputType}
            />
          )}

          {/* Section 6: Per-Claim Detail */}
          <div ref={claimDetailRef} id="claim-detail">

            {/* 6a: Claim Summary panel (framed; shared with the dashboard) */}
            {activeClaim && (
              <div className="mb-6">
                <ClaimSummaryPanel
                  claim={activeClaim}
                  position={activeClaimIndex}
                  inputType={check.inputType}
                  rankLabel={isSingleClaim ? null : `Claim ${activeClaimIndex + 1} of ${claims.length}`}
                  onNavigate={handleNavigateFromSummary}
                  hiddenViews={activeClaim && videos.filter((v: any) => v.claimId === activeClaim.id).length === 0 ? ['projectionist'] : []}
                />

                {/* Prev/Next Navigation — below the framed panel */}
                {!isSingleClaim && (
                  <div className="mt-4 flex items-center justify-between">
                    {activeClaimIndex > 0 ? (
                      <button
                        onClick={() => {
                          setActiveClaimIndex(prev => prev - 1);
                          claimDetailRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
                        }}
                        className="font-mono text-[10px] text-zinc-500 hover:text-zinc-900 transition-colors inline-flex items-center gap-1"
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
                        className="font-mono text-[10px] text-zinc-500 hover:text-zinc-900 transition-colors inline-flex items-center gap-1"
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
            <div ref={lensSectionRef} className="scroll-mt-4" />
            {/* Translated ?view=correspondent deep link — the Sources view is
                retired; silent fallback would land the reader on the wrong
                lens unexplained (COMPARE design §14.3). */}
            {sourcesViewNotice && (
              <div className="flex items-start gap-2 mb-4 border-l-2 border-zinc-300 pl-3 py-1">
                <span className="text-[11px] text-zinc-600 flex-grow">
                  The Sources view has been replaced. You&rsquo;re seeing Evidence.
                </span>
                <button
                  type="button"
                  onClick={() => setSourcesViewNotice(false)}
                  className="font-mono text-[9px] uppercase tracking-widest text-zinc-400 hover:text-zinc-900 transition-colors shrink-0 cursor-pointer"
                >
                  Dismiss
                </button>
              </div>
            )}
            <ViewSelector
              mode="detail"
              activeTab={claimView}
              onTabChange={(tab: string) => { setClaimView(tab); updateUrlViewParam(tab); }}
              hiddenTabs={[
                ...(activeClaim && videos.filter((v: any) => v.claimId === activeClaim.id).length === 0 ? (['projectionist'] as const) : []),
                // COMPARE on /r/ is read-only: hide unless this claim has
                // stored comparisons (§12.2b — a cold reader cannot create,
                // so an empty tab is a dead end, not an invitation).
                ...((activeClaim && (comparisonCounts[activeClaim.id] || 0) > 0) ? [] : (['compare'] as const)),
              ]}
            />
            <ViewGuide activeView={claimView} />

            {/* 6c: Per-Claim View Content */}
            {activeClaim && (
              <>
                {claimView === 'cartographer' && (
                  <CartographerView
                    scope="claim"
                    claims={[activeClaim]}
                    onSwitchToLibrarian={handleSwitchToLibrarian}
                  />
                )}
                {claimView === 'librarian' && (
                  <LibrarianView
                    scope="claim"
                    claims={[activeClaim]}
                    initialRelationships={evidenceFilter.rel}
                    focusElementId={evidenceFilter.element}
                  />
                )}
                {claimView === 'compare' && (
                  <CompareView claim={activeClaim} checkId={check.id} readOnly />
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
        <h3 className="font-mono text-[10px] font-bold tracking-[0.3em] uppercase text-zinc-500 mb-4">Share this record</h3>

        {/* Professional affordances first: a stable permalink and the full record. */}
        <div className="flex flex-col sm:flex-row gap-3 mb-4">
          <button
            onClick={handleCopyLink}
            className="flex-1 flex items-center justify-center gap-2 px-6 py-3 border border-zinc-300 hover:border-zinc-900 text-zinc-900 text-xs font-bold uppercase tracking-[0.2em] transition-colors"
          >
            {copied ? (<><Check size={16} /> Copied</>) : (<><LinkIcon size={16} /> Copy permalink</>)}
          </button>
          <button
            onClick={handleDownloadPdf}
            className="flex-1 flex items-center justify-center gap-2 px-6 py-3 bg-zinc-900 hover:bg-zinc-800 text-white text-xs font-bold uppercase tracking-[0.2em] transition-colors"
          >
            <Download size={16} />
            Download Evidence Record (PDF)
          </button>
        </div>

        {/* Reply in the original thread (only when the source is a tweet) */}
        {isSourceTweet && tweetId && (
          <button
            onClick={handleReplyOnTwitter}
            className="mb-4 inline-flex items-center gap-2 text-sm text-zinc-500 hover:text-zinc-900 transition-colors"
          >
            <Reply size={16} />
            Reply in the original thread
          </button>
        )}

        {/* Quieter social row */}
        <div className="flex items-center gap-3 flex-wrap pt-4 border-t border-zinc-100">
          <span className="font-mono text-[10px] tracking-[0.2em] uppercase text-zinc-500 mr-1">Share</span>
          <button
            onClick={() => handleShare('x')}
            className="flex items-center justify-center w-9 h-9 border border-zinc-200 hover:bg-zinc-50 text-zinc-500 hover:text-zinc-900 transition-colors"
            aria-label="Share on X"
          >
            <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor" aria-hidden="true">
              <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
            </svg>
          </button>
          <button
            onClick={() => handleShare('linkedin')}
            className="flex items-center justify-center w-9 h-9 border border-zinc-200 hover:bg-zinc-50 text-zinc-500 hover:text-zinc-900 transition-colors"
            aria-label="Share on LinkedIn"
          >
            <Linkedin size={18} />
          </button>
          <button
            onClick={() => handleShare('whatsapp')}
            className="flex items-center justify-center w-9 h-9 border border-zinc-200 hover:bg-zinc-50 text-zinc-500 hover:text-zinc-900 transition-colors"
            aria-label="Share on WhatsApp"
          >
            <MessageCircle size={18} />
          </button>
        </div>
      </div>

      {/* Section 8: Verify + Disclaimer */}
      <div className="pt-6 border-t border-zinc-100 flex flex-col gap-3">
        <Link
          href={`/verify/${check.id}`}
          className="inline-flex items-center gap-2 font-mono text-[10px] tracking-[0.2em] uppercase text-zinc-500 hover:text-zinc-900 transition-colors"
        >
          <span aria-hidden className="w-2 h-2 bg-accent rotate-45 shrink-0" />
          Signed record · verify integrity →
        </Link>
        <p className="text-[13px] text-zinc-500 leading-relaxed">
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
