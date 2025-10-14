'use client';

import Link from 'next/link';
import { Facebook, Instagram, Twitter, Youtube } from 'lucide-react';

interface PageHeaderProps {
  title: string;
  subtitle: string;
  ctaText?: string;
  ctaHref?: string;
  graphic?: React.ReactNode;
}

export function PageHeader({ title, subtitle, ctaText, ctaHref, graphic }: PageHeaderProps) {
  const handleShare = async (platform: string) => {
    const url = window.location.origin;
    const titleText = 'Tru8 - Fact-Checking Platform';
    const text = 'Check out Tru8 for instant fact verification with dated evidence';

    // Try native Web Share API first
    if (navigator.share && platform === 'native') {
      try {
        await navigator.share({ title: titleText, text, url });
        return;
      } catch (err) {
        console.log('Share cancelled or failed');
      }
    }

    // Fallback to platform-specific URLs
    const shareUrls: Record<string, string> = {
      facebook: `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(url)}`,
      twitter: `https://twitter.com/intent/tweet?url=${encodeURIComponent(url)}&text=${encodeURIComponent(text)}`,
      instagram: url,
      youtube: url,
    };

    const shareUrl = shareUrls[platform];
    if (shareUrl) {
      window.open(shareUrl, '_blank', 'width=600,height=400');
    }
  };

  return (
    <div className="relative mb-12">
      <div className="flex items-center justify-between">
        {/* Left content */}
        <div className="flex-1 max-w-2xl">
          <h1 className="text-4xl md:text-5xl font-black text-white mb-4 leading-tight">
            {title}
          </h1>
          <p className="text-lg text-slate-300 mb-6">
            {subtitle}
          </p>
          {ctaText && ctaHref && (
            <Link href={ctaHref}>
              <button className="bg-[#f57a07] hover:bg-[#e06a00] text-white font-bold px-8 py-3 rounded-xl transition-colors">
                {ctaText}
              </button>
            </Link>
          )}
        </div>

        {/* Right graphic */}
        {graphic && (
          <div className="hidden lg:block flex-shrink-0 ml-12">
            {graphic}
          </div>
        )}
      </div>

      {/* Social icons (absolute positioned) */}
      <div className="hidden xl:flex absolute right-0 top-0 flex-col gap-4">
        <button
          onClick={() => handleShare('facebook')}
          className="text-slate-400 hover:text-white transition-colors"
          aria-label="Share on Facebook"
        >
          <Facebook size={24} />
        </button>
        <button
          onClick={() => handleShare('instagram')}
          className="text-slate-400 hover:text-white transition-colors"
          aria-label="Share on Instagram"
        >
          <Instagram size={24} />
        </button>
        <button
          onClick={() => handleShare('twitter')}
          className="text-slate-400 hover:text-white transition-colors"
          aria-label="Share on Twitter"
        >
          <Twitter size={24} />
        </button>
        <button
          onClick={() => handleShare('youtube')}
          className="text-slate-400 hover:text-white transition-colors"
          aria-label="Share on YouTube"
        >
          <Youtube size={24} />
        </button>
      </div>
    </div>
  );
}
