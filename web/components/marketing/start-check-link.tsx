'use client';

import Link from 'next/link';
import { ArrowRight } from 'lucide-react';
import { capture } from '@/lib/analytics';

/**
 * Quiet "start" text link for server-rendered marketing sections
 * (C1 entry-point clarity, 2026-07-09). One label, one destination,
 * one analytics event — matching the filled CTAs.
 */
export function StartCheckLink({
  surface,
  label = 'Start a check',
}: {
  surface: string;
  label?: string;
}) {
  return (
    <Link
      href="/dashboard/new-check"
      onClick={() => capture('start_check_click', { surface })}
      className="group inline-flex items-center gap-2 font-mono text-[10px] tracking-[0.3em] uppercase text-zinc-900 hover:text-accent transition-colors"
    >
      <span>{label}</span>
      <ArrowRight size={14} className="transition-transform group-hover:translate-x-0.5" />
    </Link>
  );
}
