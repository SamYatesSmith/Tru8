'use client';

import { useState } from 'react';
import { AuthModal } from '@/components/auth/auth-modal';

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
      <section className="relative pt-20 pb-24 md:pt-32 md:pb-40 bg-grid-dot overflow-hidden border-b border-zinc-100">
        <div className="max-w-7xl mx-auto px-6 relative z-10">
          <div className="max-w-4xl">
            <div className="font-mono text-[10px] tracking-[0.3em] uppercase text-zinc-400 mb-6">
              Evidence Research Platform
            </div>
            <h1 className="text-4xl sm:text-5xl md:text-7xl lg:text-[84px] font-normal tracking-[-0.03em] text-zinc-900 leading-[0.95] mb-8">
              Research the evidence.<br />
              <span className="font-bold">Form your view.</span>
            </h1>
            <p className="text-lg md:text-xl text-zinc-500 mb-12 max-w-xl leading-relaxed">
              Submit a claim, URL, article, or image. Tru8 gathers evidence from government data, news, academic papers, and official records — then organises it so you can explore it six ways.
            </p>
            <div className="flex flex-col sm:flex-row gap-4">
              <button
                onClick={() => setIsAuthModalOpen(true)}
                className="group relative flex items-center justify-between bg-black text-white px-10 py-6 text-sm font-bold tracking-[0.3em] uppercase w-full sm:w-80 transition-all hover:bg-zinc-900"
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
