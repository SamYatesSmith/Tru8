'use client';

import { useRouter } from 'next/navigation';

interface BackToOverviewProps {
  checkId: string;
}

export function BackToOverview({ checkId }: BackToOverviewProps) {
  const router = useRouter();

  return (
    <button
      onClick={() => router.push(`/dashboard/check/${checkId}`)}
      className="font-mono text-[10px] uppercase tracking-widest text-zinc-400 hover:text-zinc-900 transition-colors cursor-pointer inline-flex items-center gap-2"
    >
      <span className="text-sm">&uarr;</span> Back to claims
    </button>
  );
}
