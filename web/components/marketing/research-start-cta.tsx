'use client';

import Link from 'next/link';
import { ArrowRight } from 'lucide-react';

import { capture } from '@/lib/analytics';

/**
 * /research primary CTA → /dashboard, instrumented for the researcher funnel
 * (item 2). Pairs with the nav's `research_app_click`: that event measures
 * arrival on /research, `research_start_click` measures the start-a-check step,
 * so the /research → console conversion is visible before any flip of `/`.
 *
 * A tiny client island so the otherwise-static /research page stays a server
 * component. No price, no verdict language — just the start action.
 */
export function ResearchStartCta({ surface = 'research_hero' }: { surface?: string }) {
  return (
    <Link
      href="/dashboard"
      onClick={() => capture('research_start_click', { surface })}
      className="group inline-flex items-center justify-center gap-4 bg-black text-white px-10 py-5 text-xs md:text-sm font-bold tracking-[0.3em] uppercase transition-all hover:bg-zinc-900"
    >
      <span>Start in the browser</span>
      <ArrowRight
        size={16}
        className="transition-transform group-hover:translate-x-0.5"
      />
    </Link>
  );
}
