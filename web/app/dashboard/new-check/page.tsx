'use client';

import { useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useAuth } from '@clerk/nextjs';
import { Loader2, Twitter, Linkedin, MessageCircle, Lock } from 'lucide-react';
import Link from 'next/link';
import { apiClient } from '@/lib/api';
import { PageHeader } from '../components/page-header';
import { SubscriptionsComingSoon } from '@/components/subscriptions/coming-soon';

type TabType = 'url' | 'text';

export default function NewCheckPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { getToken } = useAuth();

  const [activeTab, setActiveTab] = useState<TabType>('url');
  const [urlInput, setUrlInput] = useState('');
  const [textInput, setTextInput] = useState('');
  const [queryInput, setQueryInput] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const urlParam = searchParams.get('url');
    if (urlParam) {
      setUrlInput(urlParam);
      setActiveTab('url');
    }
  }, [searchParams]);

  const [isLimitReached, setIsLimitReached] = useState(false);
  const [usageInfo, setUsageInfo] = useState<{ used: number; limit: number } | null>(null);
  const [showBetaWaitlist, setShowBetaWaitlist] = useState(false);

  useEffect(() => {
    const checkUsage = async () => {
      try {
        const token = await getToken();
        const usage = await apiClient.getUsage(token) as any;
        const used = usage.periodCreditsUsed || 0;
        const limit = usage.creditsPerPeriod || 3;
        setUsageInfo({ used, limit });
        if (used >= limit) {
          setIsLimitReached(true);
        }
      } catch (err) {
        // Ignore errors - backend will enforce limits anyway
      }
    };
    checkUsage();
  }, [getToken]);

  const isValidUrl = (url: string): boolean => {
    try {
      new URL(url);
      return true;
    } catch {
      return false;
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (activeTab === 'url') {
      if (!urlInput.trim()) {
        setError('Please enter a URL');
        return;
      }
      if (!isValidUrl(urlInput)) {
        setError('Please enter a valid URL (e.g., https://example.com)');
        return;
      }
    }

    if (activeTab === 'text') {
      if (!textInput.trim()) {
        setError('Please enter some text');
        return;
      }
      if (textInput.length < 10) {
        setError('Text must be at least 10 characters');
        return;
      }
      if (textInput.length > 5000) {
        setError('Text must be less than 5000 characters');
        return;
      }
    }

    setIsSubmitting(true);

    try {
      const token = await getToken();

      const result = await apiClient.createCheckStreaming({
        input_type: activeTab,
        url: activeTab === 'url' ? urlInput.trim() : undefined,
        content: activeTab === 'text' ? textInput.trim() : undefined,
        user_query: queryInput.trim() || undefined,
      }, token, {
        onConnected: (checkId) => {
          window.location.href = `/dashboard/check/${checkId}`;
        },
        onProgress: (event) => {
          console.log('[NEW-CHECK] onProgress:', event.stage, event.progress);
        },
        onComplete: (checkId) => {
          if (checkId) {
            window.location.href = `/dashboard/check/${checkId}`;
          }
        },
        onError: (errorMsg, checkId) => {
          console.error('[NEW-CHECK] onError:', errorMsg, checkId);
          if (checkId) {
            window.location.href = `/dashboard/check/${checkId}`;
          } else {
            setError(errorMsg || 'Failed to create check. Please try again.');
            setIsSubmitting(false);
          }
        },
      });

      if (result?.checkId) {
        window.location.href = `/dashboard/check/${result.checkId}`;
      }
    } catch (err: any) {
      if (err.message?.includes('403') || err.message?.includes('closed beta') || err.message?.includes('BETA_ACCESS_REQUIRED')) {
        setShowBetaWaitlist(true);
        setError(null);
      } else if (err.message?.includes('402') || err.message?.includes('limit')) {
        setIsLimitReached(true);
        setError('Monthly limit reached. Please upgrade to continue.');
      } else {
        setError(err.message || 'Failed to create check. Please try again.');
      }
      setIsSubmitting(false);
    }
  };

  const handleShare = (platform: string) => {
    const url = window.location.origin;
    const text = 'Check out Tru8 — AI-powered evidence research';

    const shareUrls: Record<string, string> = {
      x: `https://twitter.com/intent/tweet?url=${encodeURIComponent(url)}&text=${encodeURIComponent(text)}`,
      linkedin: `https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(url)}`,
      whatsapp: `https://wa.me/?text=${encodeURIComponent(text + ' ' + url)}`,
    };

    const shareUrl = shareUrls[platform];
    if (shareUrl) {
      window.open(shareUrl, '_blank', 'width=600,height=400');
    }
  };

  const charCount = textInput.length;
  const maxChars = 5000;

  return (
    <div className="space-y-8">
      <PageHeader
        title="New Evidence Check"
        subtitle="Submit a claim, URL, or article for multi-source analysis."
      />

      {/* Limit Reached Banner */}
      {isLimitReached && (
        <div className="bg-amber-50 border-b border-amber-200 p-4 md:p-6">
          <div className="flex flex-col sm:flex-row items-start gap-3 sm:gap-4">
            <Lock className="text-amber-600 flex-shrink-0" size={20} />
            <div className="flex-1">
              <h3 className="font-mono text-[11px] font-bold tracking-wider uppercase text-amber-800 mb-2">Monthly Limit Reached</h3>
              <p className="text-amber-600 text-sm md:text-base mb-4">
                You&apos;ve used all {usageInfo?.limit || 3} checks available on your free plan this month.
                Upgrade to Pro for 40 checks per month and advanced features.
              </p>
              <Link
                href="/dashboard/settings?tab=subscription"
                className="inline-flex items-center gap-2 bg-zinc-900 hover:bg-zinc-800 text-white text-xs font-bold uppercase tracking-[0.2em] py-3 px-6 transition-colors"
              >
                Upgrade to Pro
              </Link>
            </div>
          </div>
        </div>
      )}

      {/* Submit Content Card */}
      <div className="bg-white border border-zinc-200 p-4 sm:p-6 md:p-8">
        <div className="mb-4 md:mb-6">
          <div className="font-mono text-[10px] tracking-[0.3em] uppercase text-zinc-400 mb-2">
            Module W-09 — Research Initiation
          </div>
          <h3 className="text-lg font-bold text-zinc-900">Submit Content</h3>
          <p className="text-zinc-500 text-sm mt-1">
            Enter a URL or paste text to analyse
          </p>
        </div>

        {/* Tab Selector */}
        <div className="flex gap-6 mb-6 border-b border-zinc-100">
          <button
            type="button"
            onClick={() => setActiveTab('url')}
            className={`pb-2 text-[10px] font-bold tracking-[0.2em] uppercase transition-colors ${
              activeTab === 'url'
                ? 'text-black border-b-2 border-accent'
                : 'text-zinc-400 hover:text-zinc-600'
            }`}
          >
            URL
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('text')}
            className={`pb-2 text-[10px] font-bold tracking-[0.2em] uppercase transition-colors ${
              activeTab === 'text'
                ? 'text-black border-b-2 border-accent'
                : 'text-zinc-400 hover:text-zinc-600'
            }`}
          >
            TEXT
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* URL Tab Content */}
          {activeTab === 'url' && (
            <div>
              <label htmlFor="url-input" className="block text-zinc-400 font-mono text-[9px] font-bold uppercase tracking-[0.2em] mb-2">
                Target Evidence URL
              </label>
              <input
                id="url-input"
                type="text"
                value={urlInput}
                onChange={(e) => setUrlInput(e.target.value)}
                placeholder="https://example.com/article"
                className="w-full bg-zinc-50 border border-zinc-200 px-4 py-3 text-zinc-900 placeholder:text-zinc-300 focus:border-black focus:outline-none focus:ring-0 transition-colors"
                disabled={isSubmitting}
              />
            </div>
          )}

          {/* TEXT Tab Content */}
          {activeTab === 'text' && (
            <div>
              <label htmlFor="text-input" className="block text-zinc-400 font-mono text-[9px] font-bold uppercase tracking-[0.2em] mb-2">
                Text Content
              </label>
              <textarea
                id="text-input"
                value={textInput}
                onChange={(e) => setTextInput(e.target.value)}
                placeholder="Paste or type the text you want to analyse..."
                rows={8}
                className="w-full bg-zinc-50 border border-zinc-200 px-4 py-3 text-zinc-900 placeholder:text-zinc-300 focus:border-black focus:outline-none focus:ring-0 transition-colors resize-vertical"
                disabled={isSubmitting}
              />
              <div className="flex justify-between items-center mt-2">
                <p className="text-sm text-zinc-400">
                  {textInput.trim().endsWith('?')
                    ? "Questions accepted — we'll extract the implied claim automatically"
                    : 'Enter text containing claims you want to analyse'}
                </p>
                <p className="text-sm font-mono text-zinc-400">
                  {charCount} / {maxChars}
                </p>
              </div>
            </div>
          )}

          {/* Search Clarity Field */}
          <div className="border-t border-zinc-100 pt-6 mt-2">
            <label htmlFor="query-input" className="block font-mono text-[10px] font-bold uppercase tracking-wider text-zinc-400 mb-2">
              Help us understand what you&apos;re looking for <span className="text-zinc-300">(Optional)</span>
            </label>
            <textarea
              id="query-input"
              value={queryInput}
              onChange={(e) => setQueryInput(e.target.value)}
              placeholder="Have a specific question about the content? Ask here and we'll focus the analysis accordingly. Leave blank for a standard check."
              maxLength={200}
              rows={3}
              className="w-full bg-zinc-50 border border-zinc-200 px-4 py-3 text-zinc-900 placeholder:text-zinc-300 focus:border-black focus:outline-none focus:ring-0 transition-colors resize-vertical"
              disabled={isSubmitting}
            />
            <div className="flex justify-between items-center mt-2">
              <p className="text-sm text-zinc-400">
                Optional: Focus the analysis on a specific question
              </p>
              <p className={`text-sm font-mono ${queryInput.length > 200 ? 'text-red-600' : 'text-zinc-400'}`}>
                {queryInput.length} / 200
              </p>
            </div>
          </div>

          {/* Error Message */}
          {error && (
            <div className="bg-red-50 border border-red-200 px-4 py-3 text-red-800 text-sm">
              {error}
            </div>
          )}

          {/* Submit Button */}
          <button
            type="submit"
            disabled={isSubmitting || isLimitReached}
            className="group relative w-full bg-black text-white py-6 text-sm font-bold tracking-[0.4em] uppercase transition-all hover:bg-zinc-900 flex items-center justify-center disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isSubmitting ? (
              <>
                <Loader2 className="animate-spin mr-3" size={20} />
                ANALYSING...
              </>
            ) : isLimitReached ? (
              <>
                <Lock size={20} className="mr-3" />
                LIMIT REACHED — UPGRADE TO CONTINUE
              </>
            ) : (
              'START ANALYSIS'
            )}
            {!isSubmitting && !isLimitReached && (
              <div className="w-2.5 h-2.5 bg-accent absolute right-0 top-1/2 -translate-y-1/2 translate-x-1 rotate-45" />
            )}
          </button>
        </form>
      </div>

      {/* Share Card */}
      <div className="bg-white border border-zinc-200 p-4 sm:p-6 md:p-8 text-center">
        <h3 className="text-[11px] font-bold tracking-wider uppercase text-zinc-900 mb-1">Share your results</h3>
        <p className="font-mono text-[10px] text-zinc-400 uppercase tracking-widest mb-4">
          Encourage peer review of findings
        </p>

        <div className="flex flex-wrap items-center justify-center gap-3">
          <button
            onClick={() => handleShare('x')}
            className="w-10 h-10 border border-zinc-100 hover:bg-zinc-50 text-zinc-400 hover:text-zinc-900 flex items-center justify-center transition-colors"
            aria-label="Share on X"
          >
            <Twitter size={18} />
          </button>
          <button
            onClick={() => handleShare('linkedin')}
            className="w-10 h-10 border border-zinc-100 hover:bg-zinc-50 text-zinc-400 hover:text-zinc-900 flex items-center justify-center transition-colors"
            aria-label="Share on LinkedIn"
          >
            <Linkedin size={18} />
          </button>
          <button
            onClick={() => handleShare('whatsapp')}
            className="w-10 h-10 border border-zinc-100 hover:bg-zinc-50 text-zinc-400 hover:text-zinc-900 flex items-center justify-center transition-colors"
            aria-label="Share on WhatsApp"
          >
            <MessageCircle size={18} />
          </button>
        </div>
      </div>

      {/* Beta Access Required Modal */}
      {showBetaWaitlist && (
        <SubscriptionsComingSoon
          source="upgrade-modal"
          variant="modal"
          onDismiss={() => setShowBetaWaitlist(false)}
        />
      )}
    </div>
  );
}
