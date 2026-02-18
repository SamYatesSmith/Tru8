'use client';

interface DispositionBarProps {
  supports: number;
  challenges: number;
  context: number;
}

export function DispositionBar({ supports, challenges, context }: DispositionBarProps) {
  const total = supports + challenges + context;

  if (total === 0) {
    return (
      <div className="mb-10">
        <div className="h-2 bg-zinc-100 mb-1"></div>
        <div className="font-mono text-[9px] uppercase tracking-widest text-zinc-400">
          No evidence mapped to this element
        </div>
      </div>
    );
  }

  const supPct = (supports / total) * 100;
  const chaPct = (challenges / total) * 100;
  const ctxPct = (context / total) * 100;

  return (
    <div>
      <div className="mb-1">
        <div className="flex h-2 overflow-hidden transition-all duration-300 ease-in-out">
          {supPct > 0 && (
            <div
              className="h-full transition-all duration-300 ease-in-out"
              style={{ width: `${supPct}%`, background: 'var(--disposition-supports)' }}
            />
          )}
          {chaPct > 0 && (
            <div
              className="h-full transition-all duration-300 ease-in-out"
              style={{ width: `${chaPct}%`, background: 'var(--disposition-challenges)' }}
            />
          )}
          {ctxPct > 0 && (
            <div
              className="h-full transition-all duration-300 ease-in-out bg-zinc-300"
              style={{ width: `${ctxPct}%` }}
            />
          )}
        </div>
      </div>

      <div className="flex items-center mb-10">
        <div className="flex items-center gap-2" style={{ width: `${supPct}%`, minWidth: 'fit-content' }}>
          <span className="font-mono text-[9px] uppercase tracking-widest font-bold" style={{ color: 'var(--disposition-supports)' }}>
            Supports
          </span>
          <span className="font-mono text-sm font-bold" style={{ color: 'var(--disposition-supports)' }}>
            {supports}
          </span>
        </div>
        <div className="flex items-center gap-2" style={{ width: `${chaPct}%`, minWidth: 'fit-content' }}>
          <span className="font-mono text-[9px] uppercase tracking-widest font-bold" style={{ color: 'var(--disposition-challenges)' }}>
            Challenges
          </span>
          <span className="font-mono text-sm font-bold" style={{ color: 'var(--disposition-challenges)' }}>
            {challenges}
          </span>
        </div>
        <div className="flex items-center gap-2" style={{ width: `${ctxPct}%`, minWidth: 'fit-content' }}>
          <span className="font-mono text-[9px] uppercase tracking-widest text-zinc-400 font-bold">
            Context
          </span>
          <span className="font-mono text-sm font-bold text-zinc-400">
            {context}
          </span>
        </div>
      </div>
    </div>
  );
}
