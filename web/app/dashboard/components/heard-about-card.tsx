'use client';

import { useState } from 'react';
import { useAuth } from '@clerk/nextjs';
import { apiClient } from '@/lib/api';

// Codes are stored server-side (app/core/attribution.py HEARD_ABOUT_CODES);
// labels live here. Keep the two lists in step.
export const HEARD_ABOUT_OPTIONS = [
  { value: 'search', label: 'Search engine' },
  { value: 'ai_assistant', label: 'AI assistant (ChatGPT, Claude etc.)' },
  { value: 'bluesky', label: 'Bluesky' },
  { value: 'linkedin', label: 'LinkedIn' },
  { value: 'newsletter', label: 'A newsletter or Substack' },
  { value: 'colleague', label: 'A colleague' },
  { value: 'shared_record', label: 'A Tru8 record someone shared' },
  { value: 'mcp_directory', label: 'An MCP directory or registry' },
  { value: 'other', label: 'Other' },
] as const;

/**
 * Optional, asked once on the dashboard first run (2026-10-01). Answering or
 * skipping both close it for good; a failed save closes it for this visit only.
 */
export function HeardAboutCard() {
  const { getToken } = useAuth();
  const [answer, setAnswer] = useState('');
  const [detail, setDetail] = useState('');
  const [state, setState] = useState<'open' | 'saving' | 'done' | 'hidden'>('open');

  if (state === 'hidden') return null;

  const send = async (value: string) => {
    setState('saving');
    try {
      const token = await getToken();
      await apiClient.recordHeardAbout(value, value === 'other' ? detail : null, token);
      setState(value === 'skipped' ? 'hidden' : 'done');
    } catch {
      setState('hidden');
    }
  };

  if (state === 'done') {
    return (
      <div className="bg-white border border-zinc-200 p-4 md:p-6 text-sm text-zinc-600" role="status">
        Thank you. That helps us know where to look for the next reader.
      </div>
    );
  }

  return (
    <form
      className="bg-white border border-zinc-200 p-4 md:p-6"
      onSubmit={(e) => {
        e.preventDefault();
        if (answer) send(answer);
      }}
    >
      <label htmlFor="heard-about" className="block text-sm font-bold uppercase tracking-wider text-zinc-900 mb-1">
        How did you hear about Tru8?
      </label>
      <p className="text-zinc-500 text-sm mb-4">Optional. One question, asked once.</p>
      <div className="flex flex-col md:flex-row gap-3 md:items-center">
        <select
          id="heard-about"
          value={answer}
          onChange={(e) => setAnswer(e.target.value)}
          className="w-full md:w-auto md:min-w-[18rem] border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900"
        >
          <option value="">Choose one…</option>
          {HEARD_ABOUT_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
        {answer === 'other' && (
          <input
            type="text"
            aria-label="Where did you hear about Tru8?"
            maxLength={200}
            value={detail}
            onChange={(e) => setDetail(e.target.value)}
            placeholder="Where?"
            className="w-full md:flex-1 border border-zinc-300 px-3 py-2 text-sm text-zinc-900"
          />
        )}
        <div className="flex gap-3">
          <button
            type="submit"
            disabled={!answer || state === 'saving'}
            className="bg-[var(--accent)] text-white px-4 py-2 text-sm font-bold disabled:opacity-50"
          >
            Send
          </button>
          <button
            type="button"
            disabled={state === 'saving'}
            onClick={() => send('skipped')}
            className="px-4 py-2 text-sm text-zinc-600 underline underline-offset-2 disabled:opacity-50"
          >
            Skip
          </button>
        </div>
      </div>
    </form>
  );
}
