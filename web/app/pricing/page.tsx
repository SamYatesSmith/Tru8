import type { Metadata } from 'next';

import { Navigation } from '@/components/layout/navigation';
import { MobileNav } from '@/components/layout/mobile-nav';
import { Footer } from '@/components/layout/footer';
import { StitchPricing } from '@/components/marketing/stitch-pricing';

export const metadata: Metadata = {
  title: 'Pricing — Console & API',
  description:
    'Tru8 Console: fair-use unlimited evidence research in the browser for £20/month. Plus a metered API for systems and agents. We organize; you decide.',
  alternates: { canonical: '/pricing' },
};

/**
 * /pricing — Direction B. The pricing section (StitchPricing) is self-contained:
 * numbered SheetHeader → headline → Console hero artifact + Free/Teams rail →
 * quiet API band. The previous "Two ways to use Tru8" split block is retired —
 * the new structure expresses the two-product split itself.
 */
export default function PricingPage() {
  return (
    <>
      <Navigation />
      <MobileNav />

      <main id="main-content" className="relative pt-24 md:pt-32">
        <StitchPricing />
      </main>

      <Footer />
    </>
  );
}
