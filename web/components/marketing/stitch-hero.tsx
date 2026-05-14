'use client';

import { useState } from 'react';
import { AuthModal } from '@/components/auth/auth-modal';
import { Tru8Mark } from '@/components/brand/tru8-mark';

/**
 * Stitch W-01 Hero Section
 *
 * Grid-dot background, mono micro-label, large headline,
 * black CTA with orange diamond accent.
 */
export function StitchHero() {
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);

  return (
    <>
      <section className="relative pt-16 pb-16 md:pt-32 md:pb-40 bg-grid-dot overflow-hidden border-b border-zinc-100">
        <div className="max-w-7xl mx-auto px-5 md:px-6 relative z-10">
          <div className="max-w-4xl">
            {/* Mobile-only brand anchor — desktop has the Navigation bar, mobile shows nothing
                up top because the bottom nav handles links. Subtle inline logo + wordmark
                so the page still says "Tru8" before the copy starts. */}
            <div className="md:hidden flex items-center gap-2 mb-6">
              <Tru8Mark size={28} />
              <span className="text-lg font-bold tracking-tighter uppercase">
                TRU<span className="text-zinc-400 font-normal">8</span>
              </span>
            </div>
            <div className="font-mono text-[10px] tracking-[0.3em] uppercase text-zinc-400 mb-4 md:mb-6">
              News Evidence Research Platform
            </div>
            <h1 className="text-3xl sm:text-5xl md:text-7xl lg:text-[84px] font-normal tracking-[-0.03em] text-zinc-900 leading-[0.95] mb-6 md:mb-8">
              Look behind the headlines.<br />
              <span className="font-bold">Form your view.</span>
            </h1>
            <p className="text-sm md:text-base lg:text-lg text-zinc-500 mb-8 md:mb-12 max-w-xl leading-relaxed">
              Tru8 isn&apos;t a fact checker. Headlines make claims every day, and the evidence behind them is scattered across dozens of sources. Tru8 gathers that evidence, classifies it by proximity and type, and organises the full landscape — so you don&apos;t have to. We organise. You decide.
              <span className="block mt-3 text-zinc-400">
                Building an agent? The same evidence research is available as a structured API — <a href="/developers" className="underline underline-offset-2 hover:text-zinc-900 transition-colors">read the dev docs</a>.
              </span>
            </p>
            <div className="flex flex-col sm:flex-row gap-4">
              <button
                onClick={() => setIsAuthModalOpen(true)}
                className="group relative flex items-center justify-between bg-black text-white px-6 py-3 md:px-10 md:py-6 text-xs md:text-sm font-bold tracking-[0.3em] uppercase w-[65%] sm:w-72 transition-all hover:bg-zinc-900"
              >
                <span>Start Analysing</span>
                <div className="w-3 h-3 bg-accent absolute right-0 top-1/2 -translate-y-1/2 translate-x-1.5 rotate-45" />
              </button>
            </div>
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
