'use client';

/**
 * ClaimSummaryPanel — the persistent, first-glance answer for a focused claim
 * (results-page reframe S3, D-R2). Shared by the dashboard check detail and the
 * public `/r/` report so both surfaces get the same summary.
 *
 * Keeps the prior claim header (rank · context · type · claim text · coloured
 * state counts · orientation line) and ADDS source-mix-by-tier + a gaps-named
 * list. Neutral, no-verdict; element states are muted claim-context indicators,
 * never page-level verdicts (Stitch colour lock).
 *
 * Null-safe by design: a completed check can carry a null claimMap per-claim
 * (partial decompose), and evidence `tier` is nullable — both are guarded.
 * Prev/next claim nav is intentionally OUT of scope here (surface-specific).
 */

import { Claim, InputType } from '@shared/types';
import { DiagnosticFlag } from './DiagnosticFlag';
import { ELEMENT_STATE } from './ElementStateBadge';
import { getTierColor, tierCounts } from './shared-utils';

const CONTEXT_LABELS: Record<string, string> = {
  url: 'Extracted Claim',
  text: 'Submitted Claim',
};

const TYPE_LABELS: Record<string, string> = {
  empirical: 'Empirical',
  definitional: 'Definitional',
  causal_interpretive: 'Causal',
  predictive: 'Predictive',
  normative_flagged: 'Normative',
};

interface ClaimSummaryPanelProps {
  claim: Claim;
  position: number;
  inputType?: InputType;
  /**
   * Rank indicator shown before the context badge. Per-surface (D-R3 decision):
   * `undefined` → zero-padded position (dashboard "02"); a string → custom
   * (public report "Claim 2 of 5"); `null` → hidden (public single-claim).
   */
  rankLabel?: string | null;
  /** Switch the active lens to the Gaps (Seeker) view from the gaps-named list. */
  onNavigateToGaps?: () => void;
}

export function ClaimSummaryPanel({ claim, position, inputType, rankLabel, onNavigateToGaps }: ClaimSummaryPanelProps) {
  const claimMap = claim.claimMap;
  const elements = claimMap?.elements || [];
  const evidence = claim.evidence || [];
  const evidenceCount = evidence.length;
  const orientation = claimMap?.orientation;
  const claimType = claimMap?.claimType || claim.claimType;

  const rankText = rankLabel === undefined ? String(position + 1).padStart(2, '0') : rankLabel;
  const contextLabel = CONTEXT_LABELS[inputType || ''] || 'Submitted Claim';

  // Element state tally (2026-05-12: contextual elements carry context-tier
  // evidence — they're not a gap). Null/unset state falls through to gap.
  const stateCounts = { supported: 0, disputed: 0, contextual: 0, gap: 0 };
  for (const el of elements) {
    if (el.state === 'supported') stateCounts.supported++;
    else if (el.state === 'disputed') stateCounts.disputed++;
    else if (el.state === 'contextual') stateCounts.contextual++;
    else stateCounts.gap++;
  }
  const hasStates =
    stateCounts.supported > 0 || stateCounts.disputed > 0 || stateCounts.contextual > 0 || stateCounts.gap > 0;

  // Source mix by tier (S3) — nullable tier defaults to commentary in the helper.
  const tiers = tierCounts(evidence);

  // Gaps named (S3) — unresolved/unstated elements, named for the reader.
  const gapElements = elements.filter((el) => !el.state || el.state === 'unresolved');

  return (
    // The panel owns its frame (single source of truth for both surfaces): a
    // raised-surface card with a 2px orange top rule marking it as the page's
    // first-glance answer. Accent is a rule, never a fill (Stitch colour lock).
    <div
      className="border border-zinc-200 border-t-2 bg-[var(--surface-raised)] p-6"
      style={{ borderTopColor: 'var(--accent)' }}
    >
      {/* Zone 1 — identity: position + context label + type badge */}
      <div className="flex items-center gap-3 mb-2">
        {rankText !== null && (
          <span className="font-mono text-xs font-bold text-zinc-300">{rankText}</span>
        )}
        <span className="px-2.5 py-0.5 bg-zinc-50 border border-zinc-200 text-[9px] font-mono font-bold uppercase tracking-wider text-zinc-500">
          {contextLabel}
        </span>
        {claimType && (
          <span className="px-2.5 py-0.5 bg-zinc-50 border border-zinc-200 text-[9px] font-mono font-bold uppercase tracking-wider text-zinc-400">
            {TYPE_LABELS[claimType] || claimType}
          </span>
        )}
      </div>

      {/* Claim text */}
      <h2 className="text-xl font-medium text-zinc-900 leading-relaxed mb-3">
        {claim.text}
      </h2>

      {/* Zone 2 — the answer: element states at a glance (coloured counts) +
          the mechanically-derived orientation read, promoted directly under
          the claim. States stay MUTED context indicators, never verdicts. */}
      {hasStates && (
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mb-3">
          {stateCounts.supported > 0 && (
            <span className={`font-mono text-[11px] ${ELEMENT_STATE.supported.text}`}>
              {stateCounts.supported} supported
            </span>
          )}
          {stateCounts.disputed > 0 && (
            <span className={`font-mono text-[11px] ${ELEMENT_STATE.disputed.text}`}>
              {stateCounts.disputed} disputed
            </span>
          )}
          {stateCounts.contextual > 0 && (
            <span className={`font-mono text-[11px] ${ELEMENT_STATE.contextual.text}`}>
              {stateCounts.contextual} contextual
            </span>
          )}
          {stateCounts.gap > 0 && (
            <span className="font-mono text-[11px] text-zinc-400">
              {stateCounts.gap} {stateCounts.gap === 1 ? 'gap' : 'gaps'}
            </span>
          )}
        </div>
      )}

      {orientation && (
        <DiagnosticFlag label="Orientation">{orientation}</DiagnosticFlag>
      )}

      {/* Zone 3 — plumbing footer (demoted below a hairline): the merged
          element/source line with tier mix, then the named gaps list. */}
      <div className="mt-4 pt-4 border-t border-zinc-200 space-y-2">
        <div className="font-mono text-[10px] text-zinc-400 flex flex-wrap items-center gap-x-2 gap-y-1">
          <span>Elements {elements.length}</span>
          <span className="text-zinc-200">&middot;</span>
          <span>Sources {evidenceCount}</span>
          {evidenceCount > 0 && (
            <>
              <span className="text-zinc-300">&mdash;</span>
              <span style={{ color: getTierColor('primary') }}>{tiers.primary} primary</span>
              <span className="text-zinc-200">&middot;</span>
              <span style={{ color: getTierColor('reporting') }}>{tiers.reporting} reporting</span>
              <span className="text-zinc-200">&middot;</span>
              <span style={{ color: getTierColor('commentary') }}>{tiers.commentary} commentary</span>
            </>
          )}
        </div>

        {gapElements.length > 0 && (
          <div className="flex items-start gap-2">
            <span className="font-mono text-[10px] uppercase tracking-wider text-zinc-400 w-16 shrink-0 pt-0.5">Gaps</span>
            <div className="flex-grow">
              <ul className="space-y-0.5">
                {gapElements.map((el) => (
                  <li key={el.elementId} className="font-mono text-[10px] text-zinc-500 flex items-start gap-1.5">
                    <span className="text-zinc-300 shrink-0">&bull;</span>
                    <span>{el.description}</span>
                  </li>
                ))}
              </ul>
              {onNavigateToGaps && (
                <button
                  onClick={onNavigateToGaps}
                  className="mt-1 font-mono text-[10px] text-zinc-400 hover:text-zinc-900 transition-colors inline-flex items-center gap-1"
                >
                  Open Gaps lens &rarr;
                </button>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
