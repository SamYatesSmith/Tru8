'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import type {
  Claim,
  Comparison,
  ComparisonBudget,
  Evidence,
} from '@shared/types';
import { apiClient } from '@/lib/api';
import { capture } from '@/lib/analytics';
import { ComparisonSlot } from './ComparisonSlot';
import { SourcePicker } from './SourcePicker';
import { ComparisonResult } from './ComparisonResult';
import { extractDomain } from '../shared-utils';

/**
 * COMPARE — pick two sources, one model call, three prose fields plus a
 * mechanical collision table. Design: audit/2026-08-26_compare_tab_design.md.
 *
 * Load-bearing decisions enforced here:
 * - THE USER picks the pairing. The suggestion button is never the default
 *   and is ABSENT (not disabled) when no opposing pair exists (§5.4).
 * - Slots are A and B, unconstrained by relationship (§5.3).
 * - Click-to-place is the primary path; drag is desktop sugar (§5.2).
 * - readOnly (/r/) renders stored comparisons only — no picker, no spend.
 * - Pre-flight advisories (no shared elements / same wire story) are
 *   advisory, never blocking (§5.4b).
 */

type MachineState = 'idle' | 'ready' | 'running' | 'done' | 'error' | 'exhausted';

interface CompareViewProps {
  claim: Claim;
  checkId: string;
  readOnly?: boolean;
  /** Fetched per request — Clerk tokens expire in ~60s, so a token captured
   *  at mount 401s on any comparison started later (found 2026-08-26). */
  getToken?: () => Promise<string | null>;
}

const TIER_ORDER: Record<string, number> = {
  primary: 0,
  reporting: 1,
  commentary: 2,
};

export function CompareView({ claim, checkId, readOnly, getToken }: CompareViewProps) {
  const [slotIds, setSlotIds] = useState<(string | null)[]>([null, null]);
  const [focusedSlot, setFocusedSlot] = useState<0 | 1 | null>(null);
  const [machine, setMachine] = useState<MachineState>('idle');
  const [comparisons, setComparisons] = useState<Comparison[]>([]);
  const [activeResult, setActiveResult] = useState<Comparison | null>(null);
  const [budget, setBudget] = useState<ComparisonBudget | null>(null);
  const [errorText, setErrorText] = useState<string | null>(null);

  // ---- derived data -------------------------------------------------------

  const shownEvidence = useMemo(
    () =>
      (claim.evidence || []).filter(
        (ev) => (ev.receiptStatus || 'shown') === 'shown'
      ),
    [claim.evidence]
  );

  const evidenceById = useMemo(() => {
    const map = new Map<string, Evidence>();
    for (const ev of shownEvidence) map.set(ev.evidenceId || ev.id, ev);
    return map;
  }, [shownEvidence]);

  const { evidenceElementMap, evidenceRelMap, elementDescriptions } = useMemo(() => {
    const evidenceElementMap = new Map<string, string[]>();
    const evidenceRelMap = new Map<string, Map<string, string>>();
    const elementDescriptions = new Map<string, string>();
    for (const element of claim.claimMap?.elements || []) {
      elementDescriptions.set(element.elementId, element.description || '');
      for (const ref of element.evidenceRefs || []) {
        const ids = evidenceElementMap.get(ref.evidenceId) || [];
        if (!ids.includes(element.elementId)) ids.push(element.elementId);
        evidenceElementMap.set(ref.evidenceId, ids);
        const rels = evidenceRelMap.get(ref.evidenceId) || new Map<string, string>();
        rels.set(element.elementId, ref.relationship);
        evidenceRelMap.set(ref.evidenceId, rels);
      }
    }
    return { evidenceElementMap, evidenceRelMap, elementDescriptions };
  }, [claim.claimMap?.elements]);

  // Mechanical suggestion (§10.4): most opposed elements, then better
  // combined tier, then more shared elements, then lexicographic (stable
  // across page loads — a suggestion that changes on refresh reads as a bug).
  const suggestedPair = useMemo(() => {
    const ids = Array.from(evidenceById.keys());
    let best: {
      pair: [string, string];
      opposed: number;
      tierSum: number;
      shared: number;
    } | null = null;
    for (let i = 0; i < ids.length; i++) {
      for (let j = i + 1; j < ids.length; j++) {
        const [a, b] = [ids[i], ids[j]].sort() as [string, string];
        const relsA = evidenceRelMap.get(a);
        const relsB = evidenceRelMap.get(b);
        if (!relsA || !relsB) continue;
        let opposed = 0;
        let shared = 0;
        relsA.forEach((relA, elementId) => {
          const relB = relsB.get(elementId);
          if (!relB) return;
          shared++;
          const pair = [relA, relB].sort().join('|');
          if (pair === 'challenges|supports') opposed++;
        });
        if (opposed === 0) continue;
        const tierSum =
          (TIER_ORDER[evidenceById.get(a)?.tier || 'commentary'] ?? 2) +
          (TIER_ORDER[evidenceById.get(b)?.tier || 'commentary'] ?? 2);
        const candidate = { pair: [a, b] as [string, string], opposed, tierSum, shared };
        if (
          !best ||
          candidate.opposed > best.opposed ||
          (candidate.opposed === best.opposed &&
            (candidate.tierSum < best.tierSum ||
              (candidate.tierSum === best.tierSum &&
                (candidate.shared > best.shared ||
                  (candidate.shared === best.shared &&
                    candidate.pair.join() < best.pair.join())))))
        ) {
          best = candidate;
        }
      }
    }
    return best?.pair || null;
  }, [evidenceById, evidenceRelMap]);

  const [idA, idB] = slotIds;
  const evidenceA = idA ? evidenceById.get(idA) || null : null;
  const evidenceB = idB ? evidenceById.get(idB) || null : null;

  // Pre-flight advisories (§5.4b) — advisory, never blocking.
  const preflightNote = useMemo(() => {
    if (!idA || !idB) return null;
    const a = evidenceById.get(idA);
    const b = evidenceById.get(idB);
    if (
      a?.corroborationGroupId != null &&
      a.corroborationGroupId === b?.corroborationGroupId
    ) {
      return 'These two appear to carry the same source story — a comparison may find no difference.';
    }
    const elementsA = evidenceElementMap.get(idA) || [];
    const elementsB = new Set(evidenceElementMap.get(idB) || []);
    if (elementsA.length && elementsB.size && !elementsA.some((e) => elementsB.has(e))) {
      return 'These two address different parts of the claim — a comparison may find little to say.';
    }
    return null;
  }, [idA, idB, evidenceById, evidenceElementMap]);

  const cachedForPair = useMemo(() => {
    if (!idA || !idB) return null;
    const [a, b] = [idA, idB].sort();
    return (
      comparisons.find((c) => c.evidenceA === a && c.evidenceB === b) || null
    );
  }, [idA, idB, comparisons]);

  // ---- data load ----------------------------------------------------------

  useEffect(() => {
    let cancelled = false;
    const load = readOnly
      ? apiClient.getPublicComparisons(checkId, claim.id)
      : (getToken ? getToken() : Promise.resolve(null)).then((t) =>
          apiClient.getComparisons(checkId, claim.id, t)
        );
    load
      .then((data) => {
        if (cancelled) return;
        setComparisons(data.comparisons || []);
        if (data.budget) setBudget(data.budget);
        if (readOnly && (data.comparisons || []).length > 0) {
          capture('comparison_viewed_readonly', { claimId: claim.id });
        }
      })
      .catch(() => {
        // Non-critical: an empty tab is a valid state; create still works.
      });
    return () => {
      cancelled = true;
    };
  }, [checkId, claim.id, readOnly, getToken]);

  // ---- state machine ------------------------------------------------------

  const bothFilled = Boolean(idA && idB);
  const exhausted = Boolean(budget && budget.used >= budget.limit);
  const effective: MachineState =
    machine === 'running'
      ? 'running'
      : machine === 'done' && activeResult
        ? 'done'
        : machine === 'error'
          ? 'error'
          : !bothFilled
            ? 'idle'
            : exhausted && !cachedForPair
              ? 'exhausted'
              : 'ready';

  const place = useCallback(
    (evidenceId: string) => {
      setActiveResult(null);
      setErrorText(null);
      setMachine('idle');
      setSlotIds((prev) => {
        if (prev.includes(evidenceId)) return prev;
        const next: (string | null)[] = [...prev];
        if (focusedSlot !== null && next[focusedSlot] === null) {
          next[focusedSlot] = evidenceId;
        } else if (next[0] === null) {
          next[0] = evidenceId;
        } else if (next[1] === null) {
          next[1] = evidenceId;
        } else {
          return prev; // both full — remove first
        }
        return next;
      });
      setFocusedSlot(null);
    },
    [focusedSlot]
  );

  const removeSlot = useCallback((index: 0 | 1) => {
    setActiveResult(null);
    setErrorText(null);
    setMachine('idle');
    setSlotIds((prev) => {
      const next: (string | null)[] = [...prev];
      next[index] = null;
      return next;
    });
  }, []);

  const applySuggestion = useCallback(() => {
    if (!suggestedPair) return;
    setActiveResult(null);
    setErrorText(null);
    setMachine('idle');
    setSlotIds([suggestedPair[0], suggestedPair[1]]);
    capture('comparison_suggested_used', { claimId: claim.id });
  }, [suggestedPair, claim.id]);

  const runCompare = useCallback(async () => {
    if (!idA || !idB || machine === 'running') return;
    // A cached pair re-views for free, budget or no budget.
    if (cachedForPair) {
      setActiveResult(cachedForPair);
      setMachine('done');
      return;
    }
    setMachine('running');
    setErrorText(null);
    try {
      const freshToken = getToken ? await getToken() : null;
      const result = await apiClient.createComparison(
        checkId,
        claim.id,
        idA,
        idB,
        freshToken
      );
      setActiveResult(result);
      setBudget(result.budget);
      if (!result.cached) {
        setComparisons((prev) => [...prev, result]);
      }
      setMachine('done');
      capture('comparison_run', {
        claimId: claim.id,
        cached: result.cached,
        budgetUsed: result.budget.used,
      });
    } catch (e) {
      const message = e instanceof Error ? e.message : '';
      if (message.includes('budget_exhausted')) {
        setBudget((prev) =>
          prev ? { ...prev, used: prev.limit } : { used: 3, limit: 3 }
        );
        setMachine('idle'); // effective state becomes 'exhausted'
      } else {
        setErrorText(
          message.includes('fetch_failed')
            ? 'Neither source could be read — nothing was charged.'
            : 'The comparison failed — nothing was charged. Try again.'
        );
        setMachine('error');
        capture('comparison_failed', {
          claimId: claim.id,
          reason: message || 'unknown',
        });
      }
    }
  }, [idA, idB, machine, cachedForPair, checkId, claim.id, getToken]);

  // ---- read-only (/r/) ----------------------------------------------------

  if (readOnly) {
    if (comparisons.length === 0) {
      // Host pages hide the tab when empty; this is the belt-and-braces
      // render if reached directly.
      return (
        <div className="border border-dashed border-zinc-200 p-8 text-center">
          <span className="font-mono text-[11px] text-zinc-400">
            No comparisons on this claim
          </span>
        </div>
      );
    }
    return (
      <div className="space-y-10">
        {comparisons.map((comparison) => {
          const a = evidenceById.get(comparison.evidenceA);
          const b = evidenceById.get(comparison.evidenceB);
          return (
            <ComparisonResult
              key={comparison.id}
              comparison={comparison}
              domainA={a ? extractDomain(a.url) : comparison.evidenceA}
              domainB={b ? extractDomain(b.url) : comparison.evidenceB}
              urlA={a?.url}
              urlB={b?.url}
              elementDescriptions={elementDescriptions}
            />
          );
        })}
      </div>
    );
  }

  // ---- interactive (dashboard) --------------------------------------------

  return (
    <div>
      {/* Slots */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
        <ComparisonSlot
          slot="A"
          evidence={evidenceA}
          onRemove={() => removeSlot(0)}
          onSelectEmpty={() => setFocusedSlot(0)}
          onDropEvidence={place}
          disabled={machine === 'running'}
        />
        <ComparisonSlot
          slot="B"
          evidence={evidenceB}
          onRemove={() => removeSlot(1)}
          onSelectEmpty={() => setFocusedSlot(1)}
          onDropEvidence={place}
          disabled={machine === 'running'}
        />
      </div>

      {/* Pre-flight advisory — never blocking (§5.4b) */}
      {preflightNote && effective !== 'done' && (
        <div className="flex items-start gap-1.5 mb-4">
          <span aria-hidden className="font-mono text-[10px] text-zinc-400 pt-px">
            &#9651;
          </span>
          <span className="font-mono text-[10px] text-zinc-500">{preflightNote}</span>
        </div>
      )}

      {/* Controls */}
      <div className="flex flex-wrap items-center gap-4 mb-8">
        <button
          type="button"
          onClick={runCompare}
          disabled={effective !== 'ready'}
          className={`px-5 py-2 font-mono text-[11px] font-bold uppercase tracking-[0.12em] border transition-colors ${
            effective === 'ready'
              ? 'bg-zinc-900 text-white border-zinc-900 cursor-pointer hover:bg-zinc-700'
              : 'bg-zinc-50 text-zinc-300 border-zinc-200 cursor-default'
          }`}
        >
          {machine === 'running' ? 'Comparing…' : 'Compare'}
        </button>

        {budget && (
          <span className="font-mono text-[10px] text-zinc-400">
            {budget.used} of {budget.limit} used
            {cachedForPair && effective !== 'done' && ' · this pair is already compared — free to view'}
          </span>
        )}

        {/* Suggest a pair: ABSENT, not disabled, when nothing opposes (§5.4). */}
        {suggestedPair && effective !== 'running' && (
          <button
            type="button"
            onClick={applySuggestion}
            className="px-3 py-1.5 border border-zinc-200 font-mono text-[10px] uppercase tracking-widest text-zinc-400 hover:text-zinc-600 transition-colors cursor-pointer"
          >
            Suggest a pair
          </button>
        )}
      </div>

      {/* Exhausted note */}
      {effective === 'exhausted' && (
        <div className="border-l-2 border-zinc-400 pl-4 py-1.5 mb-8">
          <div className="font-mono text-[9px] font-bold uppercase tracking-[0.25em] text-zinc-500 mb-1">
            Budget spent
          </div>
          <p className="text-sm text-zinc-700 leading-relaxed">
            All {budget?.limit} comparisons for this check are used. A re-search
            adds one more. Already-compared pairs stay free to view.
          </p>
        </div>
      )}

      {/* Error */}
      {effective === 'error' && errorText && (
        <div className="border-l-2 border-zinc-400 pl-4 py-1.5 mb-8">
          <div className="font-mono text-[9px] font-bold uppercase tracking-[0.25em] text-zinc-500 mb-1">
            Comparison failed
          </div>
          <p className="text-sm text-zinc-700 leading-relaxed">{errorText}</p>
        </div>
      )}

      {/* Running skeleton — headers stay visible in the slots above */}
      {machine === 'running' && (
        <div className="mb-8" aria-live="polite">
          <div className="flex items-center gap-3 mb-4">
            <div className="flex-1 h-px bg-zinc-200" />
            <span className="font-mono text-[10px] font-bold uppercase tracking-[0.25em] text-zinc-400">
              Reading both sources&hellip;
            </span>
            <div className="flex-1 h-px bg-zinc-200" />
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="space-y-2">
              <div className="h-3 bg-zinc-100 animate-pulse" />
              <div className="h-3 bg-zinc-100 animate-pulse w-5/6" />
              <div className="h-3 bg-zinc-100 animate-pulse w-4/6" />
            </div>
            <div className="space-y-2">
              <div className="h-3 bg-zinc-100 animate-pulse" />
              <div className="h-3 bg-zinc-100 animate-pulse w-5/6" />
              <div className="h-3 bg-zinc-100 animate-pulse w-4/6" />
            </div>
          </div>
        </div>
      )}

      {/* Result. Domains resolve from the comparison's OWN ids — the backend
          stores the pair sorted, so slot A may be the result's evidenceB;
          resolving from the slots would caption the summaries wrongly. */}
      {effective === 'done' && activeResult && (
        <div className="mb-10">
          {(() => {
            const resultA = evidenceById.get(activeResult.evidenceA);
            const resultB = evidenceById.get(activeResult.evidenceB);
            return (
              <ComparisonResult
                comparison={activeResult}
                domainA={resultA ? extractDomain(resultA.url) : activeResult.evidenceA}
                domainB={resultB ? extractDomain(resultB.url) : activeResult.evidenceB}
                urlA={resultA?.url}
                urlB={resultB?.url}
                elementDescriptions={elementDescriptions}
              />
            );
          })()}
        </div>
      )}

      {/* Picker */}
      <SourcePicker
        evidence={shownEvidence}
        evidenceElementMap={evidenceElementMap}
        elementDescriptions={elementDescriptions}
        placedIds={slotIds}
        disabled={machine === 'running'}
        onPlace={place}
      />
    </div>
  );
}
