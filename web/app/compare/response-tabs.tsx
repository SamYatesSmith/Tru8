'use client';

import { useState } from 'react';
import { JsonPanel } from './json-panel';
import {
  CAPTURE_DATE,
  CAPTURE_SECONDS,
  CHECK_ID,
  GOOGLE_FACTS_COUNT,
  GOOGLE_RESPONSE,
  PARALLEL_RESPONSE,
  PARALLEL_TASK_SPEC,
  PERPLEXITY_RESPONSE,
  TRU8_RESPONSE,
} from './demo-data';

const TABS = [
  { id: 'tru8', label: 'Tru8 (live)' },
  { id: 'perplexity', label: 'Perplexity Search' },
  { id: 'google', label: 'Google check-grounding' },
  { id: 'parallel', label: 'Parallel Task' },
  { id: 'webiq', label: 'Web IQ' },
] as const;

type TabId = (typeof TABS)[number]['id'];

function docsLink(href: string, label: string) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="underline underline-offset-2 hover:text-zinc-300 transition-colors"
    >
      {label}
    </a>
  );
}

export function ResponseTabs() {
  const [active, setActive] = useState<TabId>('tru8');

  return (
    <div>
      {/* Tab switcher */}
      <div className="flex flex-wrap gap-2 mb-8" role="tablist" aria-label="API responses">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            role="tab"
            aria-selected={active === tab.id}
            onClick={() => setActive(tab.id)}
            className={`px-4 py-2.5 font-mono text-[10px] tracking-[0.2em] uppercase border transition-colors ${
              active === tab.id
                ? 'border-accent text-accent bg-zinc-900'
                : 'border-zinc-800 text-zinc-500 hover:text-zinc-300 hover:border-zinc-600'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {active === 'tru8' && (
        <JsonPanel
          label="POST /agent/full — Response"
          json={TRU8_RESPONSE}
          capturedIn={CAPTURE_SECONDS.tru8}
          highlight
          footer={
            <>
              Live response from POST /agent/full, captured {CAPTURE_DATE}. Full report:{' '}
              <a
                href={`/r/${CHECK_ID}`}
                className="underline underline-offset-2 hover:text-zinc-300 transition-colors"
              >
                /r/{CHECK_ID}
              </a>{' '}
              · Verify:{' '}
              <a
                href={`https://api.trueight.com/verify/${CHECK_ID}`}
                className="underline underline-offset-2 hover:text-zinc-300 transition-colors"
              >
                api.trueight.com/verify/{CHECK_ID}
              </a>
            </>
          }
        />
      )}

      {active === 'perplexity' && (
        <JsonPanel
          label="Perplexity Search API — Response"
          json={PERPLEXITY_RESPONSE}
          capturedIn={CAPTURE_SECONDS.perplexity}
          footer={
            <>
              Live response, captured {CAPTURE_DATE}. Same claim, same day.{' '}
              {docsLink('https://docs.perplexity.ai', 'API documentation')}
            </>
          }
        />
      )}

      {active === 'google' && (
        <JsonPanel
          label="Google check-grounding — Response"
          json={GOOGLE_RESPONSE}
          capturedIn={CAPTURE_SECONDS.google}
          footer={
            <>
              Live response, captured {CAPTURE_DATE}. Same claim, same day. Check-grounding is a
              verification API: the caller supplies an answer candidate and the facts to check it
              against. Facts supplied here: the {GOOGLE_FACTS_COUNT} sources Tru8&apos;s run
              retrieved.{' '}
              {docsLink(
                'https://cloud.google.com/generative-ai-app-builder/docs/check-grounding',
                'API documentation'
              )}
            </>
          }
        />
      )}

      {active === 'parallel' && (
        <JsonPanel
          label="Parallel Task API — Response"
          json={PARALLEL_RESPONSE}
          capturedIn={CAPTURE_SECONDS.parallel}
          footer={
            <>
              Live response, captured {CAPTURE_DATE}. Same claim, same day. The Task API requires
              an output spec, which shapes what Basis returns. Spec used, verbatim: &ldquo;
              {PARALLEL_TASK_SPEC}&rdquo;. Processor: core — a deeper tier than the cheapest,
              chosen deliberately. Time shown is task creation to completion.{' '}
              {docsLink('https://docs.parallel.ai', 'API documentation')}
            </>
          }
        />
      )}

      {active === 'webiq' && (
        <div className="border border-zinc-800 bg-black">
          <div className="flex items-center justify-between px-5 py-3 border-b border-zinc-800">
            <span className="font-mono text-[10px] tracking-[0.3em] uppercase text-zinc-500">
              Microsoft Web IQ — No response available
            </span>
          </div>
          <div className="px-5 py-10 md:py-14 max-w-xl">
            <p className="text-sm md:text-base text-zinc-400 leading-relaxed mb-6">
              No public response schema. The API reference is waitlist-gated as of {CAPTURE_DATE}.
            </p>
            <p className="text-sm md:text-base text-zinc-400 leading-relaxed mb-6">
              Vendor describes: &ldquo;titles, URLs, snippets, timestamps, and provenance&rdquo;.
              Ranked by an undisclosed authority metric.
            </p>
            <p className="font-mono text-[10px] tracking-wider uppercase text-zinc-600">
              We&apos;ll replace this panel with a live capture as soon as the API is publicly
              available.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
