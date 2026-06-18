import type { Metadata } from 'next';
import Link from 'next/link';
import { ArrowRight } from 'lucide-react';

import { Navigation } from '@/components/layout/navigation';
import { MobileNav } from '@/components/layout/mobile-nav';
import { Footer } from '@/components/layout/footer';
import { StitchFeatures } from '@/components/marketing/stitch-features';

export const metadata: Metadata = {
  title: 'Research App — Review the Evidence in Your Browser',
  description:
    'Research the evidence behind any claim in your browser. Tru8 organizes external published sources into a structured, inspectable record across six views. We organize; you decide.',
  alternates: { canonical: '/research' },
};

/**
 * /research — the human review console pitch (secondary surface in the
 * asymmetric dev-led repositioning). Funnels into the existing /dashboard.
 */
export default function ResearchPage() {
  return (
    <>
      <Navigation />
      <MobileNav />

      <main id="main-content" className="relative">
        <section className="pt-24 pb-16 md:pt-40 md:pb-24 bg-grid-dot border-b border-zinc-100">
          <div className="max-w-7xl mx-auto px-6">
            <div className="max-w-3xl">
              <div className="font-mono text-[10px] tracking-[0.3em] uppercase text-zinc-400 mb-6">
                Tru8 Research Console
              </div>
              <h1 className="text-3xl sm:text-5xl md:text-7xl font-normal tracking-[-0.03em] text-zinc-900 leading-[0.95] mb-6">
                Research the evidence
                <br />
                <span className="font-bold">behind any claim.</span>
              </h1>
              <p className="text-sm md:text-lg text-zinc-500 leading-relaxed max-w-xl mb-8">
                Paste a headline, article, or claim. Tru8 organizes external published
                sources into a structured record — classified by tier and type, mapped to
                what each supports or challenges, with the gaps named. Read it six ways, in
                your browser. We organize; you decide.
              </p>
              <Link
                href="/dashboard"
                className="group inline-flex items-center justify-center gap-4 bg-black text-white px-10 py-5 text-xs md:text-sm font-bold tracking-[0.3em] uppercase transition-all hover:bg-zinc-900"
              >
                <span>Start in the browser</span>
                <ArrowRight
                  size={16}
                  className="transition-transform group-hover:translate-x-0.5"
                />
              </Link>
            </div>
          </div>
        </section>

        <StitchFeatures />
      </main>

      <Footer />
    </>
  );
}
