import { ScrollReveal } from './scroll-reveal';
import { SheetHeader } from './sheet-header';
import { StartCheckLink } from './start-check-link';

/**
 * Homepage — Sheet 01, The Record ("Artifact" archetype).
 *
 * C1 simplification (2026-07-09): the two-register artifact (5 differentiators
 * + 4-item structure) collapsed into ONE six-item grid — say it once, at one
 * altitude. Echo detection kept in the six (hardest to copy, D16); the signed
 * manifest speaks once, in the footer. Gains the quiet start CTA the section
 * never had (the strongest reframing moment on the site was a dead end).
 *
 * Constraints: no verdict language (object is the record, never "the claim
 * is…"); no "policy" noun (D15); manifest is a "signed record", not
 * "tamper-evident" — HMAC self-signed today. UK spelling (D13, 2026-06-29).
 * Accent budget: eyebrow + 6 numbers + 1 seal only.
 */

const RECORD_ITEMS: ReadonlyArray<{ n: string; k: string; d: string }> = [
  {
    n: '01',
    k: 'Element decomposition',
    d: 'Each claim broken into the 1–5 checkable parts that can actually be examined.',
  },
  {
    n: '02',
    k: 'Supports / challenges / context',
    d: 'Every source mapped to the element it bears on, with a one-line reason — for, against, or framing.',
  },
  {
    n: '03',
    k: 'Tier × type classification',
    d: 'Primary / reporting / commentary, across data, official, news, analysis, opinion and academic. Classified, never scored.',
  },
  {
    n: '04',
    k: 'Echo detection',
    d: 'Sources that merely repeat one original are grouped — not counted as independent corroboration.',
  },
  {
    n: '05',
    k: 'Gaps, named',
    d: 'What the record could not establish, stated as a finding — not hidden behind a score.',
  },
  {
    n: '06',
    k: 'Exclusion receipts',
    d: 'Every source set aside carries a reason. No silent curation.',
  },
];

const MANIFEST_REF = 'landscapeHash · hmac-sha256 · /verify/{id}';

export function StitchRecord() {
  return (
    <section
      id="record"
      className="py-28 md:py-40 bg-zinc-50 border-t border-zinc-100 scroll-mt-24"
    >
      <div className="max-w-7xl mx-auto px-6">
        <SheetHeader number="01" label="The Record" refText="PUBLISHED SOURCES · SIGNED" />
        <ScrollReveal>
          <div className="max-w-3xl mb-12 md:mb-14">
            <h2 className="text-3xl md:text-5xl font-normal tracking-[-0.02em] text-zinc-900 leading-[1.05]">
              Not a verdict. A structured evidence record.
            </h2>
            <p className="text-sm md:text-base text-zinc-500 leading-relaxed mt-6 max-w-2xl">
              Every check returns the same inspectable structure — what supports
              each part of the claim, what challenges it, what&rsquo;s missing,
              and what was excluded and why.
            </p>
          </div>
        </ScrollReveal>

        {/* The record artifact — one framed object on the zinc-50 band */}
        <ScrollReveal>
          <div className="border border-zinc-200 bg-white overflow-hidden">
            {/* Panel header bar — light analogue of the dev-showcase header */}
            <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between border-b border-zinc-200 px-6 py-3">
              <span className="font-mono text-[10px] tracking-[0.2em] uppercase text-zinc-900">
                Record — what every check returns
              </span>
              <span className="font-mono text-[10px] text-zinc-400">
                claimMap · _meta · _manifest
              </span>
            </div>

            {/* One register, six items — two columns on md+ */}
            <div className="grid grid-cols-1 md:grid-cols-2">
              {RECORD_ITEMS.map((row, i) => (
                <div
                  key={row.n}
                  className={`flex gap-4 px-6 py-5 border-t border-zinc-100 ${
                    i % 2 === 1 ? 'md:border-l md:border-l-zinc-100' : ''
                  }`}
                >
                  <span className="font-mono text-xs text-accent w-6 shrink-0 pt-0.5">
                    {row.n}
                  </span>
                  <div>
                    <h3 className="font-mono text-[11px] tracking-[0.15em] uppercase font-bold text-zinc-900 mb-1.5">
                      {row.k}
                    </h3>
                    <p className="text-sm text-zinc-500 leading-relaxed">{row.d}</p>
                  </div>
                </div>
              ))}
            </div>

            {/* Signature footer — the manifest speaks once, here */}
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between border-t border-zinc-200 px-6 py-4">
              <div className="flex items-center gap-3 min-w-0">
                <span
                  aria-hidden="true"
                  className="w-2 h-2 bg-accent rotate-45 shrink-0"
                />
                <span className="font-mono text-[11px] text-zinc-900 shrink-0">
                  _manifest
                </span>
                <span className="font-mono text-[10px] text-zinc-400 break-all">
                  {MANIFEST_REF}
                </span>
              </div>
              <span className="text-xs text-zinc-500 sm:text-right">
                Signed record of exactly what was returned.
              </span>
            </div>
          </div>

          {/* The section's action — this moment used to be a dead end */}
          <div className="mt-10">
            <StartCheckLink surface="record" label="Start a check and see yours" />
          </div>
        </ScrollReveal>
      </div>
    </section>
  );
}
