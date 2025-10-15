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
    <div className="relative mb-20 py-20">
      <div className="flex items-center justify-between gap-8">
        {/* Left content */}
        <div className="flex-1 max-w-3xl">
          <h1 className="text-6xl md:text-7xl lg:text-8xl font-black text-white mb-8 leading-tight">
            {title}
          </h1>
          <p className="text-2xl md:text-3xl text-slate-300 mb-10 leading-relaxed">
            {subtitle}
          </p>
          {ctaText && ctaHref && (
            <Link href={ctaHref}>
              <button className="bg-[#f57a07] hover:bg-[#e06a00] text-white font-bold px-12 py-5 rounded-xl transition-colors text-xl">
                {ctaText}
              </button>
            </Link>
          )}
        </div>

        {/* Right graphic - much larger with better spacing */}
        {graphic && (
          <div className="hidden lg:block flex-shrink-0 ml-20 mr-16 scale-[2]">
            {graphic}
          </div>
        )}
      </div>

      {/* Social icons with vertical connecting lines - positioned further right */}
      <div className="hidden xl:flex absolute right-0 top-1/2 -translate-y-1/2 flex-col items-center">
        <button
          onClick={() => handleShare('facebook')}
          className="text-slate-400 hover:text-white transition-colors relative z-10"
          aria-label="Share on Facebook"
        >
          <Facebook size={20} />
        </button>

        {/* Vertical line */}
        <div className="w-px h-8 bg-slate-700 my-1"></div>

        <button
          onClick={() => handleShare('instagram')}
          className="text-slate-400 hover:text-white transition-colors relative z-10"
          aria-label="Share on Instagram"
        >
          <Instagram size={20} />
        </button>

        {/* Vertical line */}
        <div className="w-px h-8 bg-slate-700 my-1"></div>

        <button
          onClick={() => handleShare('twitter')}
          className="text-slate-400 hover:text-white transition-colors relative z-10"
          aria-label="Share on Twitter"
        >
          <Twitter size={20} />
        </button>

        {/* Vertical line */}
        <div className="w-px h-8 bg-slate-700 my-1"></div>

        <button
          onClick={() => handleShare('youtube')}
          className="text-slate-400 hover:text-white transition-colors relative z-10"
          aria-label="Share on YouTube"
        >
          <Youtube size={20} />
        </button>
      </div>
    </div>
  );
}
