'use client';

import { useState } from 'react';
import { ArrowRight } from 'lucide-react';
import { AuthModal } from '@/components/auth/auth-modal';
import { Tru8Mark } from '@/components/brand/tru8-mark';
import { capture } from '@/lib/analytics';

/**
 * Stitch W-01 Hero Section
 *
 * Grid-dot background, mono product eyebrow, large definitive headline,
 * black primary CTA with orange diamond accent + quiet secondary CTA.
 */
export function StitchHero() {
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);

  return (
    <>
      <section className="relative pt-12 pb-16 md:pt-32 md:pb-40 bg-grid-dot overflow-hidden border-b border-zinc-100">
        <div className="max-w-7xl mx-auto px-5 md:px-6 relative z-10">
          <div className="max-w-4xl">
            {/* Mobile-only masthead: a single brand lockup (mark + wordmark together).
                The desktop nav supplies branding >= 768px, so this renders on mobile only.
                The product descriptor lives in the eyebrow below — no longer squeezed
                between two competing brand signals. */}
            <div className="md:hidden flex items-center gap-2.5 mb-10">
              <Tru8Mark size={36} />
              <span className="text-2xl font-bold tracking-tighter uppercase leading-none">
                TRU<span className="text-zinc-400 font-normal">8</span>
              </span>
            </div>

            {/* Product eyebrow — shown on all sizes; tells a first-time visitor what this is */}
            <div className="font-mono text-[10px] tracking-[0.3em] uppercase text-zinc-400 mb-5 md:mb-6">
              News Evidence Research Platform
            </div>

            <h1 className="text-3xl sm:text-5xl md:text-7xl lg:text-[84px] font-normal tracking-[-0.03em] text-zinc-900 leading-[0.95] mb-5 md:mb-8">
              The evidence landscape<br />
              <span className="font-bold">behind any claim.</span>
            </h1>

            <p className="text-sm md:text-base lg:text-lg text-zinc-500 mb-8 md:mb-12 max-w-xl leading-relaxed">
              Paste a headline, article, or claim. Tru8 maps the full evidence landscape — every source classified by tier and type, mapped to what it supports or challenges, with the gaps named. We organise; you decide.
            </p>

            <div className="flex flex-col sm:flex-row sm:items-stretch gap-4">
              <button
                onClick={() => {
                  capture('try_in_browser_click', { surface: 'hero' });
                  setIsAuthModalOpen(true);
                }}
                className="group inline-flex items-center justify-center gap-4 bg-black text-white px-8 py-4 md:px-12 md:py-6 text-xs md:text-sm font-bold tracking-[0.3em] uppercase w-full sm:w-auto transition-all hover:bg-zinc-900"
              >
                <span>Start Analysing</span>
                {/* Orange diamond signature — kept inside the button bounds so it never clips */}
                <span className="w-2.5 h-2.5 bg-accent rotate-45 transition-transform group-hover:translate-x-1" />
              </button>
              <a
                href="#preview"
                className="group inline-flex items-center justify-center gap-2 border border-zinc-200 px-8 py-4 md:px-10 md:py-6 text-xs md:text-sm font-bold tracking-[0.3em] uppercase text-zinc-900 w-full sm:w-auto transition-colors hover:border-zinc-900"
              >
                <span>See a Sample</span>
                <ArrowRight size={14} className="transition-transform group-hover:translate-x-0.5" />
              </a>
            </div>

            {/* Developer aside — decoupled from the consumer pitch and visually quieter,
                so it no longer splits the audience inside the main paragraph. */}
            <p className="mt-7 md:mt-8 text-xs md:text-sm text-zinc-400 max-w-xl leading-relaxed">
              Building an agent? The same landscape is one API call —{' '}
              <a href="/compare" className="underline underline-offset-2 hover:text-zinc-900 transition-colors">
                see how it compares to grounding APIs
              </a>
              .
            </p>
          </div>
        </div>
      </section>

      <AuthModal
        isOpen={isAuthModalOpen}
        onClose={() => setIsAuthModalOpen(false)}
      />
    </>
  );
}
