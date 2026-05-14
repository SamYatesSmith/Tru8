import type { ReactNode } from 'react';

interface DiagnosticFlagProps {
  label: string;
  children: ReactNode;
}

export function DiagnosticFlag({ label, children }: DiagnosticFlagProps) {
  return (
    <div className="border-l-2 border-zinc-400 pl-4 py-1.5">
      <div className="font-mono text-[9px] font-bold uppercase tracking-[0.25em] text-zinc-500 mb-1">
        {label}
      </div>
      <p className="text-sm text-zinc-700 leading-relaxed">
        {children}
      </p>
    </div>
  );
}
