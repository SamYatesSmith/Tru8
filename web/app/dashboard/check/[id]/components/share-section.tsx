'use client';

import { useState } from 'react';
import { useAuth } from '@clerk/nextjs';
import { Twitter, Linkedin, MessageCircle, Link as LinkIcon, Check, Download, Reply } from 'lucide-react';
import { isTweetUrl, extractTweetId, buildTwitterReplyUrl } from '@/lib/twitter-utils';

interface ShareSectionProps {
  checkId: string;
  inputUrl?: string | null;
  title?: string | null;
}

export function ShareSection({ checkId, inputUrl, title }: ShareSectionProps) {
  const { getToken } = useAuth();
  const [copied, setCopied] = useState(false);
  const [downloadingPdf, setDownloadingPdf] = useState(false);

  const shareUrl = typeof window !== 'undefined'
    ? `${window.location.origin}/r/${checkId}`
    : '';
  const shareText = title
    ? `Evidence Report: ${title}`
    : 'Check out this evidence report on Tru8';

  const isSourceTweet = isTweetUrl(inputUrl);
  const tweetId = isSourceTweet ? extractTweetId(inputUrl) : null;

  const handleShare = async (platform: string) => {
    if (platform === 'native' && navigator.share) {
      try {
        await navigator.share({
          title: 'Tru8 Evidence Report',
          text: shareText,
          url: shareUrl,
        });
      } catch (error) {
        console.error('Share failed:', error);
      }
      return;
    }

    const shareUrls: Record<string, string> = {
      x: `https://twitter.com/intent/tweet?url=${encodeURIComponent(shareUrl)}&text=${encodeURIComponent(shareText)}`,
      linkedin: `https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(shareUrl)}`,
      whatsapp: `https://wa.me/?text=${encodeURIComponent(shareText + ' ' + shareUrl)}`,
    };

    if (platform in shareUrls) {
      window.open(shareUrls[platform], '_blank', 'width=600,height=400');
    }
  };

  const handleReplyOnTwitter = () => {
    if (!tweetId) return;
    const replyUrl = buildTwitterReplyUrl(tweetId, shareUrl, shareText);
    window.open(replyUrl, '_blank', 'width=600,height=400');
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

  const handleDownloadPDF = async () => {
    setDownloadingPdf(true);
    try {
      const token = await getToken();
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/api/v1/checks/${checkId}/export/pdf`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) {
        throw new Error('PDF generation failed');
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `tru8-report-${checkId.slice(0, 8)}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('PDF download failed:', error);
      alert('Failed to download PDF. Please try again.');
    } finally {
      setDownloadingPdf(false);
    }
  };

  return (
    <div className="bg-white border border-zinc-200 p-6">
      <h3 className="text-lg font-bold text-zinc-900 mb-4">Share &amp; Export</h3>

      {/* PDF Download Button */}
      <button
        onClick={handleDownloadPDF}
        disabled={downloadingPdf}
        className="w-full mb-6 flex items-center justify-center gap-3 px-6 py-3 bg-zinc-900 hover:bg-zinc-800 disabled:bg-zinc-300 disabled:cursor-not-allowed text-white text-xs font-bold uppercase tracking-[0.2em] transition-colors"
      >
        <Download size={18} />
        {downloadingPdf ? 'Generating PDF...' : 'Download PDF Report'}
      </button>

      {/* Reply on X Section (only when source is a tweet) */}
      {isSourceTweet && tweetId && (
        <div className="mb-6">
          <p className="text-sm text-zinc-500 mb-3">Reply to the original post:</p>
          <button
            onClick={handleReplyOnTwitter}
            className="w-full flex items-center justify-center gap-3 px-6 py-3 bg-zinc-900 hover:bg-zinc-800 text-white text-xs font-bold uppercase tracking-[0.2em] transition-colors"
          >
            <Reply size={18} />
            Reply on X
          </button>
          <p className="text-xs text-zinc-400 mt-2">Post your findings in the original thread</p>
        </div>
      )}

      {/* Share Section */}
      <p className="font-mono text-[10px] tracking-widest uppercase text-zinc-400 mb-3">
        {isSourceTweet ? 'Share as a new post' : 'Share your findings'}
      </p>
      <div className="flex items-center gap-3">
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

        <button
          onClick={handleCopyLink}
          className="flex items-center gap-2 px-4 py-2 border border-zinc-200 hover:bg-zinc-50 text-zinc-600 hover:text-zinc-900 transition-colors"
        >
          {copied ? (
            <>
              <Check size={16} />
              <span className="text-sm font-medium">Copied!</span>
            </>
          ) : (
            <>
              <LinkIcon size={16} />
              <span className="text-sm font-medium">Copy Link</span>
            </>
          )}
        </button>
      </div>
    </div>
  );
}
