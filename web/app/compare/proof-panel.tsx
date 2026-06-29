/**
 * /compare — human-readable proof panel.
 *
 * Shows the killer researcher proof (the disputed element, with the
 * for-and-against split and the uncertainty left visible) in plain Stitch
 * tokens BEFORE the raw JSON band, so a journalist/analyst can read the
 * structure without parsing JSON. Neutral zinc throughout — the for/against
 * is carried by labels, never by verdict colour (Stitch colour lock).
 */

import Link from 'next/link';
import { TRU8_PROOF, CHECK_ID } from './demo-data';

export function ProofPanel() {
  const { claim, disputed: d } = TRU8_PROOF;

  return (
    <section className="py-16 md:py-24 border-b border-zinc-100">
      <div className="container mx-auto px-4 md:px-6 max-w-5xl">
        <div className="font-mono text-[10px] tracking-[0.3em] uppercase text-zinc-500 mb-4">
          Module — What Tru8 returns
        </div>
        <h2 className="text-2xl md:text-4xl font-normal tracking-[-0.02em] text-zinc-900 mb-3 max-w-3xl">
          The structure, in human form.
        </h2>
        <p className="text-base text-zinc-600 leading-relaxed max-w-3xl mb-10">
          Before the raw JSON below, here is the part a search API has no field for. Tru8
          decomposed the claim into checkable elements; one is disputed, and the conflict is left
          visible — not collapsed into a score.
        </p>

        <div className="border border-zinc-200 bg-white">
          <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between px-6 py-3 border-b border-zinc-200">
            <span className="font-mono text-[10px] tracking-[0.2em] uppercase text-zinc-500">
              Disputed element
            </span>
            <span className="font-mono text-[10px] tracking-[0.2em] uppercase text-zinc-500">
              left unresolved · close split
            </span>
          </div>

          <div className="px-6 py-6">
            <p className="font-mono text-[10px] tracking-[0.2em] uppercase text-zinc-500 mb-2">Claim</p>
            <p className="text-zinc-900 mb-6">{claim}</p>

            <p className="font-mono text-[10px] tracking-[0.2em] uppercase text-zinc-500 mb-2">
              The disputed element
            </p>
            <p className="text-zinc-900 mb-6 leading-relaxed">{d.description}</p>

            {/* For / against split — neutral counts, no verdict colour. */}
            <div className="flex flex-wrap items-center gap-x-5 gap-y-2 font-mono text-sm text-zinc-700 mb-8">
              <span>{d.supports} support</span>
              <span className="text-zinc-300">·</span>
              <span>{d.challenges} challenge</span>
              <span className="text-zinc-300">·</span>
              <span>{d.context} context</span>
              <span className="text-zinc-400 text-xs">
                (weighted {d.weightedSupports} vs {d.weightedChallenges})
              </span>
            </div>

            {/* One real source for, one against. */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-px bg-zinc-200 border border-zinc-200 mb-8">
              <div className="bg-white p-5">
                <p className="font-mono text-[10px] tracking-[0.2em] uppercase text-zinc-500 mb-2">
                  A source that supports
                </p>
                <p className="text-sm text-zinc-600 leading-relaxed">{d.support}</p>
              </div>
              <div className="bg-white p-5">
                <p className="font-mono text-[10px] tracking-[0.2em] uppercase text-zinc-500 mb-2">
                  A source that challenges
                </p>
                <p className="text-sm text-zinc-600 leading-relaxed">{d.challenge}</p>
              </div>
            </div>

            <div className="border-l-2 border-zinc-300 pl-4">
              <p className="font-mono text-[10px] tracking-[0.2em] uppercase text-zinc-500 mb-1">
                Uncertainty
              </p>
              <p className="text-sm text-zinc-600 leading-relaxed">{d.uncertainty}</p>
            </div>
          </div>

          <div className="border-t border-zinc-200 px-6 py-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <span className="font-mono text-[10px] tracking-[0.2em] uppercase text-zinc-500">
              Receipts for every exclusion · archived sources · signed manifest
            </span>
            <div className="flex items-center gap-4">
              <Link
                href={`/r/${CHECK_ID}`}
                className="font-mono text-[10px] tracking-[0.2em] uppercase text-zinc-900 hover:text-accent transition-colors"
              >
                See the full record →
              </Link>
              <Link
                href={`/verify/${CHECK_ID}`}
                className="font-mono text-[10px] tracking-[0.2em] uppercase text-zinc-500 hover:text-zinc-900 transition-colors"
              >
                Verify →
              </Link>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
