import { ClaimField } from './claim-field';

/**
 * Homepage — closing section (2026-09-01): the field again.
 *
 * The page opens on the claim field, so it must end on it — not on a button
 * that sends a convinced visitor to a different page to find the same field.
 * Same component as the hero (ring, tile, footer row), so the sample-record
 * link is here too. UK spelling; no verdict language.
 */
export function StitchClosingCta() {
  return (
    <section className="py-20 md:py-28 bg-grid-dot border-t border-zinc-100">
      <div className="max-w-7xl mx-auto px-5 md:px-6 flex flex-col items-center">
        <h2 className="text-center text-3xl sm:text-4xl md:text-5xl font-normal tracking-[-0.02em] text-zinc-900 mb-4 leading-[1.05]">
          See the record for <span className="font-bold">your claim.</span>
        </h2>
        <p className="text-center text-sm md:text-base text-zinc-500 leading-relaxed max-w-xl mb-10 md:mb-12">
          Paste a claim and read the evidence for and against — in your browser.
        </p>
        <ClaimField surface="closing" />
      </div>
    </section>
  );
}
