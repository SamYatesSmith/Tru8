import type { Metadata } from 'next';

import { Navigation } from '@/components/layout/navigation';
import { MobileNav } from '@/components/layout/mobile-nav';
import { Footer } from '@/components/layout/footer';
import { StitchPricing } from '@/components/marketing/stitch-pricing';

export const metadata: Metadata = {
  title: 'Pricing — API & Console',
  description:
    'Two ways to use Tru8: a metered verification API for systems and agents, and the Tru8 Console subscription for human review. We organize; you decide.',
  alternates: { canonical: '/pricing' },
};

/**
 * /pricing — two-product framing (API + Console) above the existing pricing
 * component. Price numbers are unchanged here (gated on COGS telemetry); this
 * route only gives pricing a home and sets the two-product context.
 */
export default function PricingPage() {
  return (
    <>
      <Navigation />
      <MobileNav />

      <main id="main-content" className="relative pt-24 md:pt-32">
        <section className="pb-8 md:pb-12">
          <div className="max-w-7xl mx-auto px-6">
            <div className="max-w-4xl">
              <div className="font-mono text-[10px] tracking-[0.3em] uppercase text-zinc-400 mb-6">
                Pricing
              </div>
              <h1 className="text-3xl sm:text-5xl md:text-6xl font-normal tracking-[-0.03em] text-zinc-900 leading-[0.95] mb-8">
                Two ways to <span className="font-bold">use Tru8.</span>
              </h1>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-px bg-zinc-200 border border-zinc-200">
                <div className="bg-white p-8">
                  <span className="font-mono text-[10px] tracking-[0.2em] uppercase text-accent font-bold">
                    Tru8 API
                  </span>
                  <p className="text-sm text-zinc-500 leading-relaxed mt-3">
                    Metered verification for systems and agents — Standard analysis and
                    deep Verification Records, billed per call from a prepaid balance.{' '}
                    <a
                      href="/developers"
                      className="text-zinc-900 underline underline-offset-2 hover:text-accent"
                    >
                      See the API →
                    </a>
                  </p>
                </div>
                <div className="bg-white p-8">
                  <span className="font-mono text-[10px] tracking-[0.2em] uppercase text-zinc-900 font-bold">
                    Tru8 Console
                  </span>
                  <p className="text-sm text-zinc-500 leading-relaxed mt-3">
                    A subscription for human review in the browser — Standard analysis by
                    default, with a monthly allowance of deep Verification Records.
                  </p>
                </div>
              </div>

              <p className="text-xs text-zinc-400 mt-6 max-w-2xl">
                Tru8 for Teams — workspaces, retention and policy controls — is in
                design-partner preview.{' '}
                <a
                  href="/contact"
                  className="underline underline-offset-2 hover:text-zinc-900"
                >
                  Get in touch
                </a>
                .
              </p>
            </div>
          </div>
        </section>

        <StitchPricing />
      </main>

      <Footer />
    </>
  );
}
