import Link from 'next/link';
import { ArrowUpRight } from 'lucide-react';

/**
 * Stitch W-01 API Band
 *
 * Sits between Features and ProductPreview. Single-row callout
 * surfacing the developer/agent API surface. Stitch theme: white,
 * 1px zinc border, mono micro-label, light headline with bold accent.
 */
export function StitchApiBand() {
  return (
    <section className="py-16 md:py-20 bg-white border-y border-zinc-100">
      <div className="max-w-7xl mx-auto px-6">
        <div className="grid grid-cols-1 md:grid-cols-[1fr_auto] gap-10 md:gap-16 items-end">
          <div className="max-w-2xl">
            <span className="font-mono text-[10px] tracking-[0.3em] uppercase text-accent mb-4 block">
              Module — For AI Agents
            </span>
            <h2 className="text-2xl md:text-3xl lg:text-4xl font-light tracking-tight text-zinc-900 mb-5">
              Also available as a <span className="font-bold">structured API</span>.
            </h2>
            <p className="text-sm md:text-base text-zinc-500 leading-relaxed">
              One endpoint, multi-source evidence, classified by tier and type. MCP server for Claude
              and other agents. Per-call pricing from £0.02, plus signed manifests so your
              downstream callers can verify what you sent them.
            </p>
          </div>

          <Link
            href="/developers"
            className="group inline-flex items-center justify-between gap-6 bg-black text-white px-8 py-5 text-xs font-bold tracking-[0.3em] uppercase transition-colors hover:bg-zinc-900 self-start md:self-end whitespace-nowrap"
          >
            <span>Developer Docs</span>
            <ArrowUpRight
              size={18}
              className="transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5"
            />
          </Link>
        </div>
      </div>
    </section>
  );
}
