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

import { Claim, InputType, EvidenceRelationship } from '@shared/types';
import { DiagnosticFlag } from './DiagnosticFlag';
import { ELEMENT_STATE } from './ElementStateBadge';
import { getTierColor, tierCounts } from './shared-utils';
import { ALL_TABS } from './ViewSelector';
import { capture } from '@/lib/analytics';

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
  /**
   * Switch the active lens (Slice 0a — summary as a navigation hub). The panel
   * fires `view_opened {source:'summary'}` itself; the client just switches the
   * lens + scrolls it into view. Lens values match `ViewSelector` (`librarian`,
   * `correspondent`, `chronologist`, `seeker`, `cartographer`, `projectionist`).
   */
  onNavigate?: (view: string, params?: { rel?: EvidenceRelationship[]; element?: string }) => void;
  /** Lens values to hide from the Explore rail (e.g. `['projectionist']` when no videos). */
  hiddenViews?: string[];
}

/**
 * A footer metric rendered as a QOL link into a lens when navigation is wired,
 * or as plain text otherwise (public single-claim with no handler). Affordance:
 * hover-darken + a trailing arrow that appears on hover; accessible label.
 */
function MetricLink({
  enabled,
  view,
  label,
  go,
  children,
}: {
  enabled: boolean;
  view: string;
  label: string;
  go: (view: string) => void;
  children: React.ReactNode;
}) {
  if (!enabled) {
    return <span className="inline-flex items-center gap-1">{children}</span>;
  }
  return (
    <button
      type="button"
      onClick={() => go(view)}
      aria-label={`Open ${label} lens`}
      className="group inline-flex items-center gap-1 hover:text-zinc-900 transition-colors cursor-pointer"
    >
      {children}
      <span aria-hidden className="opacity-0 group-hover:opacity-100 transition-opacity">&rarr;</span>
    </button>
  );
}

/**
 * A claim element-state count, rendered as a QOL deep-link into the filtered
 * Evidence lens when navigation is wired, or plain coloured text otherwise.
 * Keeps the muted element-state colour (an element-context indicator, never a
 * page-level verdict — Stitch colour lock).
 */
function StateChip({
  enabled,
  colorClass,
  count,
  label,
  ariaLabel,
  onClick,
}: {
  enabled: boolean;
  colorClass: string;
  count: number;
  label: string;
  ariaLabel: string;
  onClick: () => void;
}) {
  if (!enabled) {
    return <span className={`font-mono text-[11px] ${colorClass}`}>{count} {label}</span>;
  }
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={ariaLabel}
      className={`group font-mono text-[11px] ${colorClass} inline-flex items-center gap-1 cursor-pointer transition-colors hover:underline`}
    >
      {count} {label}
      <span aria-hidden className="opacity-0 group-hover:opacity-100 transition-opacity">&rarr;</span>
    </button>
  );
}

export function ClaimSummaryPanel({ claim, position, inputType, rankLabel, onNavigate, hiddenViews = [] }: ClaimSummaryPanelProps) {
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

  // Slice 0a — summary as a navigation hub. Each link attributes the lens
  // switch to the summary so we can see it driving the truth journey, then
  // hands off to the client to switch the lens + scroll it into view.
  const go = (view: string, params?: { rel?: EvidenceRelationship[]; element?: string }) => {
    if (!onNavigate) return;
    capture('view_opened', { view, source: 'summary', ...(params?.rel ? { rel: params.rel.join(',') } : {}) });
    onNavigate(view, params);
  };
  const exploreTabs = ALL_TABS.filter((t) => !hiddenViews.includes(t.value));

  // For the disputed state-count deep link: focus the disputed element when
  // exactly one element is disputed (otherwise just filter Evidence to challenges).
  const disputedElementIds = elements.filter((el) => el.state === 'disputed').map((el) => el.elementId);

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

      {/* Claim text — the headline (the question being answered). */}
      <h2 className="text-2xl font-medium text-zinc-900 leading-snug mb-3">
        {claim.text}
      </h2>

      {/* Zone 2 — the answer: element states at a glance (coloured counts) +
          the mechanically-derived orientation read, promoted directly under
          the claim. States stay MUTED context indicators, never verdicts. */}
      {hasStates && (
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mb-3">
          {stateCounts.supported > 0 && (
            <StateChip
              enabled={!!onNavigate}
              colorClass={ELEMENT_STATE.supported.text}
              count={stateCounts.supported}
              label="supported"
              ariaLabel="Show supporting evidence"
              onClick={() => go('librarian', { rel: ['supports'] })}
            />
          )}
          {stateCounts.disputed > 0 && (
            <StateChip
              enabled={!!onNavigate}
              colorClass={ELEMENT_STATE.disputed.text}
              count={stateCounts.disputed}
              label="disputed"
              ariaLabel="Show challenging evidence"
              onClick={() =>
                go('librarian', {
                  rel: ['challenges'],
                  ...(disputedElementIds.length === 1 ? { element: disputedElementIds[0] } : {}),
                })
              }
            />
          )}
          {stateCounts.contextual > 0 && (
            <StateChip
              enabled={!!onNavigate}
              colorClass={ELEMENT_STATE.contextual.text}
              count={stateCounts.contextual}
              label="contextual"
              ariaLabel="Show context evidence"
              onClick={() => go('librarian', { rel: ['context'] })}
            />
          )}
          {stateCounts.gap > 0 && (
            <StateChip
              enabled={!!onNavigate}
              colorClass="text-zinc-400"
              count={stateCounts.gap}
              label={stateCounts.gap === 1 ? 'gap' : 'gaps'}
              ariaLabel="Show gaps"
              onClick={() => go('seeker')}
            />
          )}
        </div>
      )}

      {orientation && (
        <DiagnosticFlag label="Orientation">{orientation}</DiagnosticFlag>
      )}

      {/* Zone 3 — plumbing footer (demoted below a hairline): the merged
          element/source line with tier mix (each a QOL link into its lens),
          then the named gaps list. */}
      <div className="mt-4 pt-4 border-t border-zinc-200 space-y-2">
        <div className="font-mono text-[10px] text-zinc-400 flex flex-wrap items-center gap-x-2 gap-y-1">
          {/* Elements → Sources (Correspondent: who's addressing each element). */}
          <MetricLink enabled={!!onNavigate} view="correspondent" label="Sources" go={go}>
            <span>Elements {elements.length}</span>
          </MetricLink>
          <span className="text-zinc-200">&middot;</span>
          {/* Sources + tier mix → Evidence (Librarian: the full classified set). */}
          <MetricLink enabled={!!onNavigate} view="librarian" label="Evidence" go={go}>
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
          </MetricLink>
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
              {onNavigate && (
                <button
                  type="button"
                  onClick={() => go('seeker')}
                  aria-label="Open Gaps lens"
                  className="mt-1 font-mono text-[10px] text-zinc-400 hover:text-zinc-900 transition-colors inline-flex items-center gap-1 cursor-pointer"
                >
                  Open Gaps lens &rarr;
                </button>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Explore rail — the persistent launchpad: one-click QOL links into every
          relevant lens for the reader's truth journey. Hidden lenses (e.g. Video
          when no videos) are dropped. Only rendered when navigation is wired. */}
      {onNavigate && exploreTabs.length > 0 && (
        <nav
          aria-label="Explore evidence views"
          className="mt-4 pt-4 border-t border-zinc-200 flex flex-wrap items-center gap-x-4 gap-y-2"
        >
          <span className="font-mono text-[9px] uppercase tracking-widest text-zinc-400">Explore</span>
          {exploreTabs.map((t) => (
            <button
              key={t.value}
              type="button"
              onClick={() => go(t.value)}
              aria-label={`Open ${t.label} lens`}
              className="group font-mono text-[10px] font-bold uppercase tracking-wider text-zinc-400 hover:text-zinc-900 transition-colors inline-flex items-center gap-1 cursor-pointer"
            >
              {t.label}
              <span aria-hidden className="text-zinc-300 group-hover:text-[var(--accent)] transition-colors">&rarr;</span>
            </button>
          ))}
        </nav>
      )}
    </div>
  );
}
