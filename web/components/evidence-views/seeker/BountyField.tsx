'use client';

import { useState, useCallback, useRef } from 'react';
import { apiClient } from '@/lib/api';

interface BountyFieldProps {
  elementId: string;
  initialText: string;
  readOnly?: boolean;
  checkId?: string;
  claimId?: string;
  token?: string | null;
}

export function BountyField({
  elementId,
  initialText,
  readOnly,
  checkId,
  claimId,
  token,
}: BountyFieldProps) {
  const [text, setText] = useState(initialText);
  const [saveState, setSaveState] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle');
  const timeoutRef = useRef<ReturnType<typeof setTimeout>>();

  const handleSave = useCallback(async () => {
    if (!checkId || !claimId || !token) return;
    if (text === initialText) return;

    setSaveState('saving');
    try {
      await apiClient.updateBountyText(checkId, claimId, elementId, text || null, token);
      setSaveState('saved');
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
      timeoutRef.current = setTimeout(() => setSaveState('idle'), 2000);
    } catch {
      setSaveState('error');
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
      timeoutRef.current = setTimeout(() => setSaveState('idle'), 3000);
    }
  }, [checkId, claimId, elementId, token, text, initialText]);

  // Read-only: show saved bounty text or nothing
  if (readOnly) {
    if (!initialText) return null;
    return (
      <div className="mt-3 border border-zinc-100 bg-zinc-50/50 px-3 py-2">
        <p className="font-mono text-[9px] uppercase tracking-widest text-zinc-400 mb-1">Research Brief</p>
        <p className="text-sm text-zinc-600 leading-relaxed">{initialText}</p>
      </div>
    );
  }

  return (
    <div className="mt-3">
      <label className="font-mono text-[9px] uppercase tracking-widest text-zinc-400 block mb-1">
        Research Brief
      </label>
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value.slice(0, 200))}
        onBlur={handleSave}
        placeholder="What evidence would resolve this? e.g. 'Need Q3 2026 SEC filing for revenue figure'"
        className="w-full border border-zinc-200 bg-white px-3 py-2 text-sm text-zinc-900 placeholder:text-zinc-300 resize-none focus:outline-none focus:border-zinc-400 transition-colors"
        rows={2}
        maxLength={200}
      />
      <div className="flex items-center justify-between mt-1">
        <span className="font-mono text-[9px] text-zinc-300">{text.length} / 200</span>
        {saveState === 'saving' && <span className="font-mono text-[9px] text-zinc-400">Saving...</span>}
        {saveState === 'saved' && <span className="font-mono text-[9px] text-emerald-500">Saved</span>}
        {saveState === 'error' && <span className="font-mono text-[9px] text-red-500">Save failed</span>}
      </div>
    </div>
  );
}
