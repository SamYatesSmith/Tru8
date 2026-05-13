'use client';

import { useState } from 'react';
import { Check, Copy } from 'lucide-react';

interface CopyCodeButtonProps {
  value: string;
  label?: string;
}

export function CopyCodeButton({ value, label = 'Copy' }: CopyCodeButtonProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    if (typeof navigator === 'undefined' || !navigator.clipboard) return;
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch {
      setCopied(false);
    }
  };

  return (
    <button
      type="button"
      onClick={handleCopy}
      className="inline-flex items-center gap-2 font-mono text-[10px] tracking-[0.3em] uppercase text-zinc-400 hover:text-zinc-100 transition-colors"
      aria-label={copied ? 'Copied' : label}
    >
      {copied ? <Check size={12} className="text-emerald-400" /> : <Copy size={12} />}
      <span>{copied ? 'Copied' : label}</span>
    </button>
  );
}
