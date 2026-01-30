'use client';

import { useState } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { Twitter, Linkedin, MessageCircle, ChevronLeft } from 'lucide-react';

interface PageHeaderProps {
  title: string;
  subtitle: string;
  ctaText?: string;
  ctaHref?: string;
  graphic?: React.ReactNode;
  graphicScale?: number; // Optional custom scale for graphic (default 2)
  titleSize?: 'normal' | 'large'; // Optional size variant (default large)
}

export function PageHeader({
  title,
  subtitle,
  ctaText,
  ctaHref,
  graphic,
  graphicScale = 2,
  titleSize = 'large'
}: PageHeaderProps) {
  const [socialsOpen, setSocialsOpen] = useState(false);

  const handleShare = async (platform: string) => {
    const url = window.location.origin;
    const titleText = 'Tru8 - Claim Verification Platform';
    const text = 'Check out Tru8 - See what the sources say with professional verification';

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
      x: `https://twitter.com/intent/tweet?url=${encodeURIComponent(url)}&text=${encodeURIComponent(text)}`,
      linkedin: `https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(url)}`,
      whatsapp: `https://wa.me/?text=${encodeURIComponent(text + ' ' + url)}`,
    };

    const shareUrl = shareUrls[platform];
    if (shareUrl) {
      window.open(shareUrl, '_blank', 'width=600,height=400');
    }
  };

  // Dynamic classes based on titleSize - mobile-first with progressive enhancement
  const titleClasses = titleSize === 'normal'
    ? 'text-3xl sm:text-4xl md:text-5xl lg:text-6xl font-black text-white mb-6 md:mb-8 leading-tight'
    : 'text-4xl sm:text-5xl md:text-6xl lg:text-7xl font-black text-white mb-6 md:mb-8 leading-tight';

  return (
    <div className="relative mb-6 md:mb-20 py-4 md:py-20">
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 lg:gap-8">
        {/* Left content - Mobile: Logo + CTA, Desktop: Title + Subtitle + CTA */}
        <div className="flex-1 max-w-3xl">
          {/* Mobile: Show logo */}
          <div className="md:hidden flex flex-col items-center gap-4 mb-2">
            <Image
              src="/logo.proper.png"
              alt="Tru8"
              width={160}
              height={160}
              className="object-contain"
            />
            {ctaText && ctaHref && (
              <div className="white-rotating-border w-full">
                <Link
                  href={ctaHref}
                  className="white-rotating-border-content flex items-center justify-center text-white font-bold px-8 py-4 transition-colors text-base"
                >
                  {ctaText}
                </Link>
              </div>
            )}
          </div>

          {/* Mobile: Expandable socials drawer - aligned top right */}
          <div className="md:hidden fixed right-0 top-20 z-40 flex items-center">
            {/* Expanded social icons panel */}
            <div
              className={`flex items-center gap-3 bg-[#1a1f2e] border border-slate-700 rounded-l-lg py-3 px-4 transition-all duration-300 ease-out ${
                socialsOpen ? 'opacity-100 translate-x-0' : 'opacity-0 translate-x-full pointer-events-none'
              }`}
            >
              <button
                onClick={() => handleShare('x')}
                className="text-slate-400 hover:text-white transition-colors p-2"
                aria-label="Share on X"
              >
                <Twitter size={20} />
              </button>
              <div className="w-px h-5 bg-slate-700"></div>
              <button
                onClick={() => handleShare('linkedin')}
                className="text-slate-400 hover:text-white transition-colors p-2"
                aria-label="Share on LinkedIn"
              >
                <Linkedin size={20} />
              </button>
              <div className="w-px h-5 bg-slate-700"></div>
              <button
                onClick={() => handleShare('whatsapp')}
                className="text-slate-400 hover:text-[#25D366] transition-colors p-2"
                aria-label="Share on WhatsApp"
              >
                <MessageCircle size={20} />
              </button>
            </div>

            {/* Toggle button with vertical "Socials" text */}
            <button
              onClick={() => setSocialsOpen(!socialsOpen)}
              className="bg-[#1a1f2e] border border-slate-700 border-r-0 rounded-l-lg py-3 px-2 flex flex-col items-center gap-1"
              aria-label={socialsOpen ? 'Close socials' : 'Open socials'}
            >
              {/* Vertical "Socials" text */}
              <div className="flex flex-col items-center text-slate-400 text-xs font-medium leading-none tracking-tight">
                <span>S</span>
                <span>o</span>
                <span>c</span>
                <span>i</span>
                <span>a</span>
                <span>l</span>
                <span>s</span>
              </div>
              {/* Arrow pointing left */}
              <ChevronLeft
                size={16}
                className={`text-[#f57a07] mt-1 transition-transform duration-300 ${socialsOpen ? 'rotate-180' : ''}`}
              />
            </button>
          </div>

          {/* Desktop: Show title and subtitle */}
          <h1 className={`hidden md:block ${titleClasses}`}>
            {title}
          </h1>
          <p className="hidden md:block text-lg sm:text-xl md:text-2xl lg:text-3xl text-slate-300 mb-6 md:mb-10 leading-relaxed">
            {subtitle}
          </p>
          {ctaText && ctaHref && (
            <Link
              href={ctaHref}
              className="hidden md:inline-block bg-[#f57a07] hover:bg-[#e06a00] text-white font-bold px-8 md:px-12 py-4 md:py-5 rounded-xl transition-colors text-base md:text-xl"
            >
              {ctaText}
            </Link>
          )}
        </div>

        {/* Right graphic - size controlled by graphicScale prop */}
        {graphic && (
          <div
            className="hidden lg:block flex-shrink-0 ml-20 mr-32"
            style={{ transform: `scale(${graphicScale})` }}
          >
            {graphic}
          </div>
        )}
      </div>

      {/* Social icons with vertical connecting lines - positioned further right */}
      <div className="hidden md:flex absolute right-0 top-1/2 -translate-y-1/2 flex-col items-center">
        <button
          onClick={() => handleShare('x')}
          className="text-slate-400 hover:text-white transition-colors relative z-10"
          aria-label="Share on X"
        >
          <Twitter size={20} />
        </button>

        {/* Vertical line */}
        <div className="w-px h-8 bg-slate-700 my-1"></div>

        <button
          onClick={() => handleShare('linkedin')}
          className="text-slate-400 hover:text-white transition-colors relative z-10"
          aria-label="Share on LinkedIn"
        >
          <Linkedin size={20} />
        </button>

        {/* Vertical line */}
        <div className="w-px h-8 bg-slate-700 my-1"></div>

        <button
          onClick={() => handleShare('whatsapp')}
          className="text-slate-400 hover:text-[#25D366] transition-colors relative z-10"
          aria-label="Share on WhatsApp"
        >
          <MessageCircle size={20} />
        </button>
      </div>
    </div>
  );
}
