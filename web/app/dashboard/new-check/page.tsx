'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@clerk/nextjs';
import { Loader2, Facebook, Instagram, Twitter, Youtube, MessageCircle, Lock } from 'lucide-react';
import Link from 'next/link';
import { apiClient } from '@/lib/api';
import { PageHeader } from '../components/page-header';
import { PrismGraphic } from '../components/prism-graphic';

type TabType = 'url' | 'text';

export default function NewCheckPage() {
  const router = useRouter();
  const { getToken } = useAuth();

  // Form state
  const [activeTab, setActiveTab] = useState<TabType>('url');
  const [urlInput, setUrlInput] = useState('');
  const [textInput, setTextInput] = useState('');
  const [queryInput, setQueryInput] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Usage limit state
  const [isLimitReached, setIsLimitReached] = useState(false);
  const [usageInfo, setUsageInfo] = useState<{ used: number; limit: number } | null>(null);

  // Check usage limits on page load
  useEffect(() => {
    const checkUsage = async () => {
      try {
        const token = await getToken();
        const usage = await apiClient.getUsage(token) as any;
        const used = usage.monthlyCreditsUsed || 0;
        const limit = usage.creditsPerMonth || 3;
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

  // Validation
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

    // Validate based on active tab
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

      const result = await apiClient.createCheck({
        input_type: activeTab,
        url: activeTab === 'url' ? urlInput.trim() : undefined,
        content: activeTab === 'text' ? textInput.trim() : undefined,
        user_query: queryInput.trim() || undefined,  // Search Clarity
      }, token) as any;

      // Redirect to check detail page
      router.push(`/dashboard/check/${result.check.id}`);
    } catch (err: any) {
      // Check for 402 (payment required / limit reached)
      if (err.message?.includes('402') || err.message?.includes('limit')) {
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
    const title = 'Tru8 - Fact-Checking Platform';
    const text = 'Check out Tru8 for instant fact verification';

    const shareUrls: Record<string, string> = {
      facebook: `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(url)}`,
      twitter: `https://twitter.com/intent/tweet?url=${encodeURIComponent(url)}&text=${encodeURIComponent(text)}`,
      instagram: url,
      youtube: url,
      message: `sms:?&body=${encodeURIComponent(text + ' ' + url)}`,
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
        title="Create New Claim Check"
        subtitle="Submit claims, URLs, or articles for instant verification"
        graphic={<PrismGraphic />}
      />

      {/* Limit Reached Banner */}
      {isLimitReached && (
        <div className="bg-amber-900/20 border border-amber-700 rounded-xl p-6">
          <div className="flex items-start gap-4">
            <Lock className="text-amber-400 flex-shrink-0 mt-1" size={24} />
            <div className="flex-1">
              <h3 className="text-amber-400 font-bold text-lg mb-2">Monthly Limit Reached</h3>
              <p className="text-amber-200 mb-4">
                You've used all {usageInfo?.limit || 3} checks available on your free plan this month.
                Upgrade to Pro for 40 checks per month and advanced features.
              </p>
              <Link
                href="/dashboard/settings?tab=subscription"
                className="inline-flex items-center gap-2 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 text-white font-bold py-3 px-6 rounded-xl transition-all"
              >
                Upgrade to Pro
              </Link>
            </div>
          </div>
        </div>
      )}

      {/* Submit Content Card */}
      <div className="bg-[#1a1f2e] border border-slate-700 rounded-xl p-8">
        <div className="mb-6">
          <h3 className="text-xl font-bold text-white">Submit Content</h3>
          <p className="text-slate-400 text-sm mt-1">
            Enter a URL or paste text to verify claims and check facts
          </p>
        </div>

        {/* Tab Selector */}
        <div className="flex gap-6 mb-6 border-b border-slate-700">
          <button
            type="button"
            onClick={() => setActiveTab('url')}
            className={`pb-2 font-bold uppercase text-sm transition-colors ${
              activeTab === 'url'
                ? 'text-[#f57a07] border-b-2 border-[#f57a07]'
                : 'text-slate-400 hover:text-slate-300'
            }`}
          >
            URL
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('text')}
            className={`pb-2 font-bold uppercase text-sm transition-colors ${
              activeTab === 'text'
                ? 'text-[#f57a07] border-b-2 border-[#f57a07]'
                : 'text-slate-400 hover:text-slate-300'
            }`}
          >
            TEXT
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* URL Tab Content */}
          {activeTab === 'url' && (
            <div>
              <label htmlFor="url-input" className="block text-sm font-semibold text-white mb-2">
                Website URL
              </label>
              <input
                id="url-input"
                type="text"
                value={urlInput}
                onChange={(e) => setUrlInput(e.target.value)}
                placeholder="https://example.com/article"
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-3 text-white placeholder:text-slate-500 focus:border-[#f57a07] focus:outline-none transition-colors"
                disabled={isSubmitting}
              />
              <p className="text-sm text-slate-400 mt-2">
                Enter the URL of an article, blog post, or webpage to verify
              </p>
            </div>
          )}

          {/* TEXT Tab Content */}
          {activeTab === 'text' && (
            <div>
              <label htmlFor="text-input" className="block text-sm font-semibold text-white mb-2">
                Text Content
              </label>
              <textarea
                id="text-input"
                value={textInput}
                onChange={(e) => setTextInput(e.target.value)}
                placeholder="Paste or type the text you want to fact-check..."
                rows={8}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-3 text-white placeholder:text-slate-500 focus:border-[#f57a07] focus:outline-none transition-colors resize-vertical"
                disabled={isSubmitting}
              />
              <div className="flex justify-between items-center mt-2">
                <p className="text-sm text-slate-400">
                  Enter text containing claims you want to verify
                </p>
                <p className="text-sm text-slate-400">
                  {charCount} / {maxChars} characters
                </p>
              </div>
            </div>
          )}

          {/* Search Clarity Field - Always visible after input selection */}
          <div className="border-t border-slate-700 pt-6 mt-2">
            <label htmlFor="query-input" className="block text-sm font-semibold text-white mb-2">
              💡 Search Clarity (Optional)
            </label>
            <textarea
              id="query-input"
              value={queryInput}
              onChange={(e) => setQueryInput(e.target.value)}
              placeholder="Have a Specific Question, relating to the article you've selected, text you've added or voice note that you recorded? Ask here, and we'll ensure that your query is clarified.

Leave this text field blank to proceed for a standard check on your article."
              maxLength={200}
              rows={3}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-3 text-white placeholder:text-slate-500 focus:border-[#f57a07] focus:outline-none transition-colors resize-vertical"
              disabled={isSubmitting}
            />
            <div className="flex justify-between items-center mt-2">
              <p className="text-sm text-slate-400">
                Optional: Ask what you want to know
              </p>
              <p className={`text-sm ${queryInput.length > 200 ? 'text-red-400' : 'text-slate-400'}`}>
                {queryInput.length} / 200 characters
              </p>
            </div>
          </div>

          {/* Error Message */}
          {error && (
            <div className="bg-red-900/20 border border-red-600 rounded-lg px-4 py-3 text-red-400 text-sm">
              {error}
            </div>
          )}

          {/* Submit Button */}
          <button
            type="submit"
            disabled={isSubmitting || isLimitReached}
            className="w-full bg-[#f57a07] hover:bg-[#e06a00] disabled:opacity-50 disabled:cursor-not-allowed text-white font-bold py-4 rounded-xl transition-all flex items-center justify-center gap-2"
          >
            {isSubmitting ? (
              <>
                <Loader2 className="animate-spin" size={20} />
                PROCESSING...
              </>
            ) : isLimitReached ? (
              <>
                <Lock size={20} />
                LIMIT REACHED - UPGRADE TO CONTINUE
              </>
            ) : (
              'START FACT CHECK'
            )}
          </button>
        </form>
      </div>

      {/* Share Your Results Card */}
      <div className="bg-[#1a1f2e] border border-slate-700 rounded-xl p-8 text-center">
        <h3 className="text-2xl font-bold text-white mb-3">Share Your Results</h3>
        <p className="text-slate-300 max-w-2xl mx-auto mb-6">
          Once your fact-check is complete, share the verified results with your network to help combat misinformation
        </p>

        {/* Social Icons */}
        <div className="flex items-center justify-center gap-4">
          <button
            onClick={() => handleShare('facebook')}
            className="bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white p-3 rounded-full transition-colors"
            aria-label="Share on Facebook"
          >
            <Facebook size={24} />
          </button>
          <button
            onClick={() => handleShare('instagram')}
            className="bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white p-3 rounded-full transition-colors"
            aria-label="Share on Instagram"
          >
            <Instagram size={24} />
          </button>
          <button
            onClick={() => handleShare('twitter')}
            className="bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white p-3 rounded-full transition-colors"
            aria-label="Share on Twitter"
          >
            <Twitter size={24} />
          </button>
          <button
            onClick={() => handleShare('youtube')}
            className="bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white p-3 rounded-full transition-colors"
            aria-label="Share on YouTube"
          >
            <Youtube size={24} />
          </button>
          <button
            onClick={() => handleShare('message')}
            className="bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white p-3 rounded-full transition-colors"
            aria-label="Share via Message"
          >
            <MessageCircle size={24} />
          </button>
        </div>
      </div>
    </div>
  );
}
