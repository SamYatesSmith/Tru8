import { ClaimField } from './claim-field';

/**
 * Stitch Hero — the claim field IS the front door (2026-09-01).
 *
 * Rebuilt from the founder-approved canvas "Tru8 Landing Hero": the animated
 * mark, centred and large, leads; then the statement; then the lede; then the
 * field with the mark as its go button. No eyebrow, no button pair — the
 * category line now lives in <title>, JSON-LD and the FAQ, and the sample
 * record sits in the field's footer row. Review + decisions:
 * `audit/2026-09-01_claim_field_front_door_review.md`,
 * `audit/2026-09-01_landing_below_hero_review.md`.
 *
 * Statement styling is the founder's, set in the canvas editor and saved
 * twice: sentence case, medium weight, light grey (#B2B2BA), tight tracking.
 * ⚠️ That grey measures ~2.1:1 against white — under the 3:1 large-text floor.
 * Kept as approved; one token to change if it fails a review.
 *
 * History: 2026-07-09 human-first hero ("See the evidence for and against");
 * 2026-08-07 mark at hero scale replaced the record fragment; 2026-08-10 CTAs
 * retargeted at the form. All of that is superseded by the field itself.
 *
 * Locks: no "policy" (D15), UK spelling (D13), accent lives only in the marks
 * (and now the ring, which is the mark's colour in motion).
 */
export function StitchHero() {
  return (
    <section className="relative pt-24 md:pt-28 pb-24 md:pb-32 bg-grid-dot overflow-hidden">
      <div className="max-w-7xl mx-auto px-5 md:px-6 relative z-10 flex flex-col items-center">
        {/* The mark, animated (SMIL inside the SVG) — decorative; the h1 carries
            the meaning. Generated art: design/mobius-mark/build_assets.py. */}
        {/* eslint-disable-next-line @next/next/no-img-element -- generated SVG art */}
        <img
          src="/brand/tru8-hero.svg"
          alt=""
          aria-hidden="true"
          draggable={false}
          className="h-[200px] md:h-[260px] lg:h-[300px] w-auto mb-8 md:mb-10 motion-reduce:hidden"
        />
        {/* eslint-disable-next-line @next/next/no-img-element -- see above */}
        <img
          src="/brand/tru8-hero-static.svg"
          alt=""
          aria-hidden="true"
          draggable={false}
          className="h-[200px] md:h-[260px] lg:h-[300px] w-auto mb-8 md:mb-10 hidden motion-reduce:block"
        />

        <h1 className="text-center text-[44px] sm:text-6xl md:text-7xl lg:text-[104px] font-medium tracking-[-0.035em] leading-[0.95] text-[#B2B2BA] mb-5 md:mb-6 [text-wrap:balance]">
          Context, not verdicts.
        </h1>

        <p className="text-center text-sm md:text-lg text-zinc-500 leading-relaxed max-w-[680px] mb-10 md:mb-14 [text-wrap:pretty]">
          Paste a claim or a question. Tru8 breaks it into its checkable parts,
          gathers evidence from published sources, and returns a signed,
          organised evidence record.
        </p>

        <ClaimField surface="hero" />
      </div>
    </section>
  );
}
