import { ScrollReveal } from './scroll-reveal';
import { SheetHeader } from './sheet-header';

/**
 * Homepage — The Verification Record ("Artifact" archetype).
 *
 * Leads with the hard-to-copy mechanics (D16), not generic "record" words.
 * One framed record object — spec-sheet header bar, an emphasised differentiators
 * ledger, a subordinate structure register, and a signed-manifest signature footer
 * — distinct from the Process grid below and the dark dev-showcase panel later.
 *
 * Constraints: no verdict language (object is the record, never "the claim is…");
 * no "policy" noun (D15); manifest is a "signed record", not "tamper-evident" — HMAC
 * self-signed today, so verify confirms the signed fields haven't changed since signing;
 * an independent timestamp + content hashing (release-plan item 6) is the path to a true
 * tamper-evident claim. US spelling (D13). Accent budget: eyebrow + 5 numbers + 1 seal only.
 */

// Group A — what makes the record hard to copy (lead, emphasised).
const DIFFERENTIATORS: ReadonlyArray<{ n: string; k: string; d: string }> = [
  {
    n: '01',
    k: 'Echo detection',
    d: 'Sources that merely repeat one original are grouped — not counted as independent corroboration.',
  },
  {
    n: '02',
    k: 'Source diversity, measured',
    d: 'Unique domains, tier spread and type coverage — independence you can quantify, not assert.',
  },
  {
    n: '03',
    k: 'Per-source provenance',
    d: 'How each source was classified and scored, and from what — full text, snippet or API.',
  },
  {
    n: '04',
    k: 'Four states, incl. contextual',
    d: 'Supported, disputed, unresolved — and contextual: related evidence that doesn’t directly substantiate, kept distinct from a true gap.',
  },
  {
    n: '05',
    k: 'Exclusion receipts',
    d: 'Every source set aside carries a reason. No silent curation.',
  },
];

// Group B — the structure (table-stakes, subordinate register).
const STRUCTURE: ReadonlyArray<{ n: string; k: string; d: string }> = [
  {
    n: '06',
    k: 'Element decomposition',
    d: 'Each claim broken into 1–5 checkable factual elements.',
  },
  {
    n: '07',
    k: 'Supports / challenges / context',
    d: 'Every source mapped to an element by relationship, with a one-line reason.',
  },
  {
    n: '08',
    k: 'Tier × type classification',
    d: 'Primary / reporting / commentary, across data, official, news, analysis, opinion and academic.',
  },
  {
    n: '09',
    k: 'Gaps, named',
    d: 'What evidence is missing, surfaced explicitly — not hidden behind a score.',
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
        <SheetHeader number="01" label="Record" refText="30+ SOURCES · SIGNED" />
        <ScrollReveal>
          <div className="max-w-3xl mb-12 md:mb-14">
            <h2 className="text-3xl md:text-5xl font-normal tracking-[-0.02em] text-zinc-900 leading-[1.05]">
              Not a verdict. A structured evidence record.
            </h2>
            <p className="text-sm md:text-base text-zinc-500 leading-relaxed mt-6 max-w-2xl">
              Every check returns the same inspectable structure — the evidence behind
              each claim, classified and mapped. You decide what to publish, escalate,
              re-check or block.
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

            {/* Group A — the differentiators (emphasised ledger) */}
            <div className="px-6 pt-6 pb-1">
              <span className="block font-mono text-[10px] tracking-[0.3em] uppercase text-zinc-400">
                The Differentiators
              </span>
            </div>
            <div>
              {DIFFERENTIATORS.map((row) => (
                <div
                  key={row.n}
                  className="px-6 py-4 border-t border-zinc-100 md:grid md:grid-cols-12 md:gap-6 md:items-baseline"
                >
                  <div className="flex items-center gap-3 mb-1.5 md:mb-0 md:col-span-4">
                    <span className="font-mono text-xs text-accent w-5 shrink-0">
                      {row.n}
                    </span>
                    <h3 className="font-mono text-[11px] tracking-[0.15em] uppercase font-bold text-zinc-900">
                      {row.k}
                    </h3>
                  </div>
                  <p className="text-sm text-zinc-500 leading-relaxed md:col-span-8">
                    {row.d}
                  </p>
                </div>
              ))}
            </div>

            {/* Group B — the structure (subordinate register, no dividers) */}
            <div className="border-t border-zinc-200 px-6 py-6">
              <span className="block font-mono text-[10px] tracking-[0.3em] uppercase text-zinc-400 mb-5">
                The Structure
              </span>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-x-8 gap-y-6">
                {STRUCTURE.map((row) => (
                  <div key={row.n} className="flex gap-4">
                    <span className="font-mono text-[11px] text-zinc-400 w-6 shrink-0 pt-0.5">
                      {row.n}
                    </span>
                    <div>
                      <h3 className="font-mono text-[10px] tracking-[0.15em] uppercase font-semibold text-zinc-700 mb-1">
                        {row.k}
                      </h3>
                      <p className="text-xs text-zinc-500 leading-relaxed">{row.d}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Signature footer — divider on white (no fill); one mono line + one seal */}
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
        </ScrollReveal>
      </div>
    </section>
  );
}
