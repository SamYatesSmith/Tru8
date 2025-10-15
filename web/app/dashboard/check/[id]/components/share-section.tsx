'use client';

import { useState } from 'react';
import { Facebook, Twitter, Linkedin, Link as LinkIcon, Check } from 'lucide-react';

interface ShareSectionProps {
  checkId: string;
}

export function ShareSection({ checkId }: ShareSectionProps) {
  const [copied, setCopied] = useState(false);

  const shareUrl = typeof window !== 'undefined'
    ? `${window.location.origin}/dashboard/check/${checkId}`
    : '';
  const shareText = 'Check out this fact-check on Tru8';

  const handleShare = async (platform: string) => {
    // Try native Web Share API first
    if (platform === 'native' && navigator.share) {
      try {
        await navigator.share({
          title: 'Tru8 Fact-Check',
          text: shareText,
          url: shareUrl,
        });
      } catch (error) {
        console.error('Share failed:', error);
      }
      return;
    }

    // Platform-specific URLs
    const shareUrls: Record<string, string> = {
      facebook: `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(shareUrl)}`,
      twitter: `https://twitter.com/intent/tweet?url=${encodeURIComponent(shareUrl)}&text=${encodeURIComponent(shareText)}`,
      linkedin: `https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(shareUrl)}`,
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

  return (
    <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
      <h3 className="text-xl font-bold text-white mb-4">Share This Check</h3>

      <div className="flex items-center gap-3">
        {/* Facebook */}
        <button
          onClick={() => handleShare('facebook')}
          className="flex items-center justify-center w-10 h-10 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-colors"
          aria-label="Share on Facebook"
        >
          <Facebook size={20} />
        </button>

        {/* Twitter */}
        <button
          onClick={() => handleShare('twitter')}
          className="flex items-center justify-center w-10 h-10 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-colors"
          aria-label="Share on Twitter"
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
  );
}
