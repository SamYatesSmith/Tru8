import Link from 'next/link';
import { ArrowUpRight } from 'lucide-react';

import { ScrollReveal } from './scroll-reveal';
import { SheetHeader } from './sheet-header';

/**
 * Homepage — Sheet 04, For developers (renumbered 2026-09-01) (C1 entry-point clarity, 2026-07-09).
 *
 * Condensed to one dark band: the landing page platforms the HUMAN start; the
 * developer pitch gets a headline, four capability chips, one CTA and a price
 * line — the full pitch (code samples, tiers, MCP config, 14-section reference)
 * lives on /developers. The former JSON/curl disclosures and the /compare link
 * moved there with it.
 */

const CHIPS: ReadonlyArray<{ key: string; description: string }> = [
  { key: 'claimMap', description: 'elements, states, evidence refs' },
  { key: '_manifest', description: 'signed, verifiable' },
  { key: 'MCP server', description: 'pip install tru8-mcp' },
  { key: 'webhooks', description: 'check.completed' },
];

export function StitchDeveloperShowcase() {
  return (
    <section id="developer-showcase" className="py-20 md:py-28 bg-zinc-950 text-zinc-100">
      <div className="max-w-7xl mx-auto px-6">
        <SheetHeader number="04" label="For developers" refText="POST /agent/*" tone="dark" />
        <ScrollReveal>
          <div className="mb-10 md:mb-12 max-w-3xl">
            <h2 className="text-3xl md:text-5xl font-normal tracking-[-0.02em] text-zinc-50 leading-[1.0]">
              The same record,<br />
              <span className="font-bold">structured for agents.</span>
            </h2>
            <p className="text-sm md:text-base text-zinc-400 leading-relaxed mt-6 max-w-2xl">
              Everything above ships as JSON — one call, a signed evidence
              landscape your agent can act on.{' '}
              <span className="text-zinc-100">Your agent decides what matters.</span>
            </p>
          </div>
        </ScrollReveal>

        <ScrollReveal delay={120}>
          {/* Capability chips — mono, no code walls on the landing page */}
          <div className="flex flex-wrap gap-3 mb-10 md:mb-12">
            {CHIPS.map((chip) => (
              <span
                key={chip.key}
                className="border border-zinc-800 px-4 py-2.5 font-mono text-[11px] tracking-tight text-zinc-300"
              >
                <span className="text-accent">{chip.key}</span>
                <span className="text-zinc-500"> — {chip.description}</span>
              </span>
            ))}
          </div>

          <div className="flex flex-col sm:flex-row gap-5 items-start sm:items-center">
            <Link
              href="/developers"
              className="group inline-flex items-center justify-between gap-6 bg-white text-zinc-950 px-8 py-5 text-xs font-bold tracking-[0.3em] uppercase transition-colors hover:bg-zinc-100"
            >
              <span>Read the docs</span>
              <ArrowUpRight
                size={18}
                className="transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5"
              />
            </Link>
            <div className="font-mono text-[10px] tracking-[0.3em] uppercase text-zinc-500 leading-relaxed">
              From £0.02 per call · async · batch · webhooks
            </div>
          </div>
          <div className="mt-4">
            <Link
              href="/blog/evidence-research-for-agents"
              className="font-mono text-[10px] tracking-[0.3em] uppercase text-zinc-500 hover:text-zinc-300 transition-colors"
            >
              Evidence research for AI agents →
            </Link>
          </div>
        </ScrollReveal>
      </div>
    </section>
  );
}
