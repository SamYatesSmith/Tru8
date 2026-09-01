'use client';

import { useEffect, useId, useState, type FormEvent, type KeyboardEvent } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useAuth } from '@clerk/nextjs';
import { ArrowUpRight } from 'lucide-react';
import { apiClient } from '@/lib/api';
import { capture } from '@/lib/analytics';
import { clearClaimIntent, saveClaimIntent } from '@/lib/claim-intent';
import { triageText, triageUrl } from '@/lib/input-triage';
import { SAMPLE_REPORT_PATH } from '@/lib/marketing';

/**
 * ClaimField — the front door (2026-09-01).
 *
 * The homepage entry is the claim itself, not a button that promises one.
 * Designed on the canvas "Tru8 Landing Hero" and built from it: a 960px
 * column; a 1.5px satin-orange ring with a travelling specular highlight and a
 * small warm halo OUTSIDE the box (never inside); an opaque white well with a
 * light 14px dot infill; the brand mark, animated, on a near-black tile as the
 * go button — the mark's own proportions (54×75), not a square. Beneath, one
 * mono row: free to try · the tagline · the sample record (the timing phrase
 * lives in the Edges sheet and the FAQ, not here — founder, 2026-09-01).
 *
 * What pressing the mark does, after client-side triage (same rules as the
 * console form):
 *
 * SIGNED IN → the check is created from HERE and the browser goes straight to
 * `/dashboard/check/<id>` — no visit to the console form. (The first build
 * hopped through `/dashboard/new-check?run=1`, which rendered the form for a
 * second before firing; founder: unprofessional and confusing. Same day.)
 *
 * SIGNED OUT (or Clerk not yet loaded) → the claim is written to a single-use,
 * tab-scoped intent (`lib/claim-intent.ts`) and the browser goes to
 * `/dashboard/new-check?run=1`; middleware bounces to `/` with that path as
 * `redirect_url`, the auth modal opens, and Clerk lands the visitor on the
 * same path after sign-in, where the console shows a "Starting your check"
 * panel — never the form — while it runs. One interruption, nothing retyped.
 *
 * Why the claim is NOT in the URL (security pass): a claim in the query string
 * reaches server logs, PostHog `$current_url`, Sentry breadcrumbs and Referers;
 * and `run=1` beside it would let any link spend a signed-in user's credit.
 * The console auto-runs only when `?run=1` meets an intent this tab wrote
 * itself. Anonymous runs are deliberately NOT offered yet
 * (`audit/2026-09-01_claim_field_front_door_review.md` §4 option B).
 *
 * Locks: no verdict language in placeholder or errors (D3); one start label
 * sitewide ("Start a check") lives in the button's accessible name; UK
 * spelling; the mark is the ONE logo (design/mobius-mark/build_assets.py
 * emits the dark build from the same object — never a redrawn cousin).
 */

const MIN_CHARS = 10;
const MAX_CHARS = 5000;

/** Signed-out destination. The claim itself travels via the intent. */
export const CLAIM_FIELD_DESTINATION = '/dashboard/new-check?run=1';

function looksLikeUrl(value: string): boolean {
  return /^https?:\/\/\S+$/i.test(value);
}

export function ClaimField({
  surface,
  autoFocus = false,
}: {
  /** Analytics surface: 'hero' | 'closing'. */
  surface: string;
  autoFocus?: boolean;
}) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { isSignedIn, getToken } = useAuth();
  const id = useId();
  const [value, setValue] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // A signed-out submit comes straight back to this page (middleware bounce →
  // auth modal) with the SAME component instance mounted; without this the
  // field stayed disabled behind the modal, and after a dismissed modal too.
  // Any change to the page's query (the bounce adds ?auth_redirect=true; the
  // modal's close strips it) re-arms the field. Found on the security pass.
  useEffect(() => {
    setBusy(false);
    setStatus(null);
  }, [searchParams]);

  const submit = async (e?: FormEvent) => {
    e?.preventDefault();
    if (busy) return;
    const v = value.trim();
    if (!v) {
      setError('Paste a claim, a question, or a link to an article.');
      return;
    }

    const isUrl = looksLikeUrl(v);
    if (isUrl) {
      const triage = triageUrl(v);
      if (!triage.ok) {
        setError(triage.message);
        return;
      }
    } else {
      if (v.length < MIN_CHARS) {
        setError('A little more, please — at least ten characters.');
        return;
      }
      if (v.length > MAX_CHARS) {
        setError(
          `Keep it under ${MAX_CHARS.toLocaleString('en-GB')} characters — for a whole article, paste its link instead.`,
        );
        return;
      }
      const triage = triageText(v);
      if (!triage.ok) {
        setError(triage.message);
        return;
      }
    }

    // Saved in both paths: it is the hand-off when signed out, and the
    // console's prefill if a signed-in create fails and we send them there.
    if (!saveClaimIntent(isUrl ? 'url' : 'text', v)) {
      // sessionStorage unavailable (locked-down browser). The console form is
      // one click away; say so rather than silently dropping the claim.
      setError('Your browser blocked the hand-off — open Start a check and paste it there.');
      return;
    }

    const inputType = isUrl ? 'url' : v.endsWith('?') ? 'question' : 'text';
    setError(null);
    setBusy(true);
    // Never the claim text — only its shape.
    capture('claim_field_submit', { surface, input_type: inputType, signed_in: Boolean(isSignedIn) });

    if (!isSignedIn) {
      router.push(CLAIM_FIELD_DESTINATION);
      return;
    }

    // Signed in: create the check from here and go straight to it.
    setStatus('Starting your check');
    capture('check_submitted', { input_type: inputType, surface });
    const go = (checkId: string) => {
      clearClaimIntent();
      window.location.href = `/dashboard/check/${checkId}?fresh=true`;
    };
    const fail = (message?: string) => {
      // Limit / access problems have their own explanation on the console form,
      // which the saved intent will prefill. Anything else is said here.
      if (message && /402|403|limit|beta/i.test(message)) {
        router.push('/dashboard/new-check');
        return;
      }
      setBusy(false);
      setStatus(null);
      setError(message || 'Could not start the check. Please try again.');
    };
    try {
      const token = await getToken();
      const result = await apiClient.createCheckStreaming(
        isUrl ? { input_type: 'url', url: v } : { input_type: 'text', content: v },
        token,
        {
          onConnected: go,
          onComplete: (checkId) => {
            if (checkId) go(checkId);
          },
          onError: (message, checkId) => {
            if (checkId) go(checkId);
            else fail(message);
          },
        },
      );
      if (result?.checkId) go(result.checkId);
    } catch (err) {
      fail(err instanceof Error ? err.message : undefined);
    }
  };

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    // Enter submits, Shift+Enter breaks a line — the convention of every
    // single-purpose field a visitor has already used today.
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      void submit();
    }
  };

  const errorId = `${id}-error`;

  return (
    <form onSubmit={(e) => void submit(e)} noValidate className="w-full max-w-[960px] mx-auto">
      <div className="tru8-field">
        <div className="tru8-halo" aria-hidden="true" />
        <div className="tru8-ring">
          <div className="tru8-well flex items-center gap-4 md:gap-5 py-[18px] pr-[18px] pl-5 md:pl-[26px] min-h-[96px]">
            <label htmlFor={id} className="sr-only">
              Claim, question or article link
            </label>
            <textarea
              id={id}
              rows={2}
              value={value}
              onChange={(e) => {
                setValue(e.target.value);
                if (error) setError(null);
              }}
              onKeyDown={onKeyDown}
              placeholder="Paste a claim or a question — the evidence for and against, organised"
              autoFocus={autoFocus}
              disabled={busy}
              maxLength={MAX_CHARS + 500}
              aria-invalid={error ? true : undefined}
              aria-describedby={error ? errorId : undefined}
              spellCheck
              className="flex-grow min-w-0 resize-none bg-transparent border-0 outline-none p-0 text-base md:text-xl font-medium leading-normal text-zinc-900 placeholder:text-zinc-400 disabled:opacity-60"
            />
            <button
              type="submit"
              aria-label="Start a check"
              title="Start a check"
              disabled={busy}
              className="tru8-go shrink-0 inline-flex items-center justify-center w-[54px] h-[75px] rounded-lg bg-[#0a0a0a] shadow-[0_1px_2px_rgba(0,0,0,0.18)] disabled:opacity-70 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-zinc-900"
            >
              {/* The mark is the button. Generated dark build of the ONE logo —
                  design/mobius-mark/build_assets.py, DARK_ASSETS. */}
              {/* eslint-disable-next-line @next/next/no-img-element -- generated SVG art */}
              <img
                src="/brand/tru8-mark-dark.svg"
                alt=""
                aria-hidden="true"
                draggable={false}
                className="h-[71px] w-auto motion-reduce:hidden"
              />
              {/* eslint-disable-next-line @next/next/no-img-element -- see above */}
              <img
                src="/brand/tru8-mark-dark-static.svg"
                alt=""
                aria-hidden="true"
                draggable={false}
                className="h-[71px] w-auto hidden motion-reduce:block"
              />
            </button>
          </div>
        </div>
      </div>

      {error ? (
        <p
          id={errorId}
          role="alert"
          className="mt-3 font-mono text-[10px] tracking-[0.2em] uppercase text-accent"
        >
          {error}
        </p>
      ) : status ? (
        <p
          role="status"
          aria-live="polite"
          className="mt-3 font-mono text-[10px] tracking-[0.2em] uppercase text-zinc-500"
        >
          <span aria-hidden="true" className="inline-block w-1.5 h-1.5 bg-accent rotate-45 mr-2 align-middle" />
          {status}
        </p>
      ) : null}

      {/* Footer row — one style for all three cells (founder, 2026-09-01) */}
      <div className="mt-6 grid grid-cols-1 sm:grid-cols-3 items-center gap-3 sm:gap-6 px-0.5 font-mono text-[10px] tracking-[0.2em] uppercase text-zinc-400 text-center">
        <span className="sm:text-left whitespace-nowrap">· Free to try ·</span>
        <span className="whitespace-nowrap">· We organise; you decide ·</span>
        <a
          href={SAMPLE_REPORT_PATH}
          target="_blank"
          rel="noopener"
          onClick={() => capture('view_sample_click', { surface })}
          className="group inline-flex items-center justify-center sm:justify-end gap-2 whitespace-nowrap hover:text-zinc-900 transition-colors"
        >
          <span>See a sample record</span>
          <ArrowUpRight
            size={14}
            className="transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5"
          />
        </a>
      </div>
    </form>
  );
}
