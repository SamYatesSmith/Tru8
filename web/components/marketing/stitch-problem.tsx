import { ScrollReveal } from './scroll-reveal';
import { SheetHeader } from './sheet-header';

/**
 * Homepage — The Problem (verification/dev-led repositioning).
 * Evidence-object framing per design-review B5 (never "check the claims").
 */
export function StitchProblem() {
  return (
    <section className="py-20 md:py-24 bg-white border-t border-zinc-100">
      <div className="max-w-7xl mx-auto px-6">
        <SheetHeader number="00" label="Problem" refText="THE GAP" />
        <ScrollReveal>
          <div className="max-w-4xl">
            <h2 className="text-4xl md:text-6xl lg:text-7xl font-normal tracking-[-0.02em] text-zinc-900 leading-[1.04]">
              AI ships factual claims faster than anyone can assemble the
              evidence behind them.
            </h2>
            <p className="text-base md:text-lg text-zinc-500 leading-relaxed mt-8 max-w-2xl">
              The systems producing them can&rsquo;t show what evidence supports
              each claim, what challenges it, or what was checked before it
              shipped.
            </p>
          </div>
        </ScrollReveal>
      </div>
    </section>
  );
}
