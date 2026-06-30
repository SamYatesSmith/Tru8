'use client';

/**
 * ClaimSummaryPanel — the Evidence Digest: the first-glance answer for a focused
 * claim (results-UX redesign 2026-06-30, evolving the S3 summary panel). Shared
 * by the dashboard check detail and the public `/r/` report so both surfaces get
 * the same digest.
 *
 * Reads, top to bottom: identity → claim → the lean line (mechanical orientation,
 * BLUF) → a confidence/coverage line (kept SEPARATE from the lean, GRADE-style) →
 * a neutral evidence-stance DISTRIBUTION BAR (click a band → filtered Evidence) →
 * KEY FINDINGS (top sources by relevance) → STRONGEST support / challenge → a
 * source-mix-by-tier line and the named gaps. It doubles as navigation: the bar,
 * findings, strongest cards and gaps all deep-link into the relevant lens via the
 * same `go(view, {rel, element})` contract used before — nothing interactive lost.
 *
 * No-verdict lock: stance is shown by icon + word + position, NEVER colour
 * (no green/red); the lean sentence's subject is the EVIDENCE, never the claim.
 * Orange is used only as a wayfinding/interaction accent (hover, links), never on
 * stance. Tier classification colour is legitimate (classification ≠ verdict).
 *
 * Null-safe: a completed check can carry a null claimMap per-claim (partial
 * decompose) and nullable evidence tier — both guarded.
 */

import { Claim, Evidence, InputType, EvidenceRelationship } from '@shared/types';
import { Plus, Minus, Dot, ArrowRight, ArrowUpRight } from 'lucide-react';
import {
  getTierColor,
  tierCounts,
  relationshipByEvidence,
  hasRelationship,
  stanceCounts,
  extractDomain,
  getFaviconUrl,
} from './shared-utils';
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

// Stance display — neutral palette (no verdict colour). Differentiated by tonal
// weight + icon + word + position only. Orange is reserved for interaction.
const STANCE_META: Record<EvidenceRelationship, { label: string; band: string; glyph: React.ReactNode }> = {
  supports: { label: 'Supports', band: 'bg-zinc-800 text-white', glyph: <Plus size={13} /> },
  context: { label: 'Context', band: 'bg-zinc-300 text-zinc-800', glyph: <Dot size={16} /> },
  challenges: { label: 'Challenges', band: 'bg-zinc-600 text-white', glyph: <Minus size={13} /> },
};

interface ClaimSummaryPanelProps {
  claim: Claim;
  position: number;
  inputType?: InputType;
  /**
   * Rank indicator shown before the context badge. Per-surface (D-R3):
   * `undefined` → zero-padded position (dashboard "02"); a string → custom
   * (public report "Claim 2 of 5"); `null` → hidden.
   */
  rankLabel?: string | null;
  /**
   * Switch the active lens (summary-as-navigation). The panel fires
   * `view_opened {source:'summary'}` itself; the client switches the lens +
   * scrolls. Lens values match ViewSelector (`librarian`, `correspondent`,
   * `chronologist`, `seeker`, `cartographer`, `projectionist`).
   */
  onNavigate?: (view: string, params?: { rel?: EvidenceRelationship[]; element?: string }) => void;
  /** Retained for call-site compatibility (was the Explore-rail hide list). */
  hiddenViews?: string[];
}

export function ClaimSummaryPanel({ claim, position, inputType, rankLabel, onNavigate }: ClaimSummaryPanelProps) {
  const claimMap = claim.claimMap;
  const elements = claimMap?.elements || [];
  // Match the Evidence lens, which shows only non-excluded sources, so a band's
  // count equals the filtered list it links to (excluded-but-mapped items would
  // otherwise inflate the digest above what the click shows).
  const evidence = (claim.evidence || []).filter((ev) => ev.receiptStatus !== 'excluded');
  const evidenceCount = evidence.length;
  const orientation = claimMap?.orientation;
  const claimType = claimMap?.claimType || claim.claimType;

  const rankText = rankLabel === undefined ? String(position + 1).padStart(2, '0') : rankLabel;
  const contextLabel = CONTEXT_LABELS[inputType || ''] || 'Submitted Claim';

  // ── Evidence-stance distribution (the bar) — mirrors Librarian's join. ──
  const relMap = relationshipByEvidence(elements);
  const counts = stanceCounts(evidence, relMap);
  const barTotal = counts.total; // distinct mapped sources (header label)
  const bandSum = counts.supports + counts.context + counts.challenges; // width denominator

  // Coverage: elements that carry a resolved state (gap = no/unresolved state).
  const coveredElements = elements.filter((el) => el.state && el.state !== 'unresolved').length;
  const gapElements = elements.filter((el) => !el.state || el.state === 'unresolved');

  // Source mix by tier (nullable tier → commentary in the helper).
  const tiers = tierCounts(evidence);

  // Confidence-in-the-lean, kept SEPARATE from direction (GRADE). Describes
  // breadth of the set + element coverage, never the claim's truth.
  // Breadth describes the gathered set (evidenceCount), not just the mapped
  // subset — so it can never contradict the "Sources N" footer.
  const breadth = evidenceCount >= 15 ? 'a broad set' : evidenceCount >= 6 ? 'a moderate set' : evidenceCount > 0 ? 'a small set' : 'few sources';
  const confidenceLine =
    elements.length > 0
      ? `Based on ${breadth} of sources · ${coveredElements} of ${elements.length} elements covered.`
      : `Based on ${breadth} of sources.`;

  // ── Relevance ranking for findings/strongest (selection by membership, so a
  // "strongest support" is the top-relevance item carrying a supports ref). ──
  const relsOf = (ev: Evidence) => relMap.get(ev.evidenceId || ev.id);
  const mappedEvidence = evidence.filter((ev) => (relsOf(ev)?.length ?? 0) > 0);
  const byRelevance = [...mappedEvidence].sort((a, b) => (b.relevanceScore ?? 0) - (a.relevanceScore ?? 0));
  const strongestSupport = byRelevance.find((ev) => hasRelationship(relsOf(ev), 'supports'));
  const strongestChallenge = byRelevance.find((ev) => hasRelationship(relsOf(ev), 'challenges'));
  const featuredIds = new Set(
    [strongestSupport?.evidenceId || strongestSupport?.id, strongestChallenge?.evidenceId || strongestChallenge?.id].filter(Boolean)
  );
  const keyFindings = byRelevance.filter((ev) => !featuredIds.has(ev.evidenceId || ev.id)).slice(0, 3);

  // summary-as-navigation: attribute the lens switch to the summary.
  const go = (view: string, params?: { rel?: EvidenceRelationship[]; element?: string }) => {
    if (!onNavigate) return;
    capture('view_opened', { view, source: 'summary', ...(params?.rel ? { rel: params.rel.join(',') } : {}) });
    onNavigate(view, params);
  };
  const nav = !!onNavigate;

  const STANCE_ORDER: EvidenceRelationship[] = ['supports', 'context', 'challenges'];
  // Band count = items carrying that relationship = exactly the filtered Evidence
  // list this jump lands on (no element-focus, so the count and the list match).
  const goStance = (s: EvidenceRelationship) => go('librarian', { rel: [s] });

  return (
    // The panel owns its frame: raised surface + 2px orange top rule marking it
    // as the page's first-glance answer (accent = rule, never a stance fill).
    <div
      className="border border-zinc-200 border-t-2 bg-[var(--surface-raised)] p-5 md:p-6"
      style={{ borderTopColor: 'var(--accent)' }}
    >
      {/* Zone 1 — identity */}
      <div className="flex items-center gap-3 mb-2">
        {rankText !== null && <span className="font-mono text-xs font-bold text-zinc-500">{rankText}</span>}
        <span className="px-2.5 py-0.5 bg-zinc-50 border border-zinc-200 text-[9px] font-mono font-bold uppercase tracking-wider text-zinc-500">
          {contextLabel}
        </span>
        {claimType && (
          <span className="px-2.5 py-0.5 bg-zinc-50 border border-zinc-200 text-[9px] font-mono font-bold uppercase tracking-wider text-zinc-500">
            {TYPE_LABELS[claimType] || claimType}
          </span>
        )}
      </div>

      {/* Claim restated neutrally — prefer the pipeline's normalised wording over
          the article's loaded phrasing (BLUF #1). */}
      <h2 className="text-xl md:text-2xl font-medium text-zinc-900 leading-snug mb-3">
        {claimMap?.normalisedClaim || claim.text}
      </h2>

      {/* The lean (BLUF) — subject is the evidence, never the claim — + confidence (separate).
          Null orientation gets an explicit line, never a blank where the answer should be. */}
      {orientation ? (
        <p className="text-base md:text-lg text-zinc-900 leading-snug">{orientation}</p>
      ) : evidenceCount > 0 ? (
        <p className="text-base md:text-lg text-zinc-900 leading-snug">
          {barTotal === 0
            ? `${evidenceCount} ${evidenceCount === 1 ? 'source' : 'sources'} gathered — not yet mapped to the claim's elements.`
            : 'The gathered evidence doesn’t clearly lean either way — elements remain unresolved.'}
        </p>
      ) : null}
      <p className="text-sm text-zinc-500 mt-1">{confidenceLine}</p>

      {/* Distribution bar — click a band → filtered Evidence */}
      {barTotal > 0 && (
        <div className="mt-4">
          <div className="flex items-center justify-between mb-1.5">
            <span className="font-mono text-[10px] tracking-[0.2em] uppercase text-zinc-500">
              {barTotal < evidenceCount
                ? `${barTotal} of ${evidenceCount} sources mapped`
                : `${barTotal} ${barTotal === 1 ? 'source' : 'sources'} mapped`}
            </span>
            {nav && <span className="font-mono text-[10px] text-zinc-400">click a band &rarr;</span>}
          </div>
          <div className="flex w-full h-10 overflow-hidden border border-zinc-200">
            {STANCE_ORDER.map((s) => {
              const n = counts[s];
              if (n === 0) return null;
              const meta = STANCE_META[s];
              // flex-grow proportional (not explicit width%) so bands fill the
              // track exactly and the dominant band is never clipped on a skew.
              const flex = { flexGrow: n, flexBasis: 0 } as const;
              const inner = (
                <>
                  <span className="shrink-0">{meta.glyph}</span>
                  <span className="truncate text-xs font-medium tracking-wide">{meta.label} {n}</span>
                </>
              );
              return nav ? (
                <button
                  key={s}
                  onClick={() => goStance(s)}
                  style={flex}
                  title={`${meta.label} — ${n} ${n === 1 ? 'source' : 'sources'}`}
                  aria-label={`Show the ${n} ${meta.label.toLowerCase()} sources`}
                  className={`group flex items-center gap-1.5 px-2 min-w-[1.5rem] cursor-pointer transition-all hover:ring-2 hover:ring-inset hover:ring-[var(--accent)] ${meta.band}`}
                >
                  {inner}
                </button>
              ) : (
                <span key={s} style={flex} className={`flex items-center gap-1.5 px-2 min-w-[1.5rem] ${meta.band}`}>
                  {inner}
                </span>
              );
            })}
          </div>
          <p className="mt-1.5 text-[11px] text-zinc-400">
            Proportions describe the sources gathered — not a verdict on the claim.
            {bandSum > barTotal && ' Some sources address more than one side.'}
          </p>
        </div>
      )}

      {/* Key findings — top sources by relevance, each linking out to the source */}
      {keyFindings.length > 0 && (
        <div className="mt-5 pt-4 border-t border-zinc-100">
          <span className="font-mono text-[10px] tracking-[0.2em] uppercase text-zinc-500">Key findings</span>
          <ul className="mt-2.5 space-y-2">
            {keyFindings.map((ev) => (
              <li key={ev.evidenceId || ev.id} className="flex items-start gap-2 text-sm text-zinc-700">
                <span aria-hidden className="mt-2 w-1 h-1 bg-zinc-400 shrink-0" />
                {/* Source title, not the raw snippet — source-platforming invariant
                    (relevance summaries drive visits; never reproduce article content). */}
                <span className="flex-1 leading-snug line-clamp-2">{ev.title || extractDomain(ev.url)}</span>
                <a
                  href={ev.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="shrink-0 inline-flex items-center gap-1 text-xs text-zinc-500 hover:text-[var(--accent)] transition-colors"
                >
                  <img
                    src={getFaviconUrl(ev.url)}
                    alt=""
                    width={12}
                    height={12}
                    loading="lazy"
                    className="w-3 h-3 shrink-0 rounded-sm"
                    onError={(e) => { e.currentTarget.style.visibility = 'hidden'; }}
                  />
                  {extractDomain(ev.url)} <ArrowUpRight size={12} />
                </a>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Most relevant support / challenge — labelled by direction, link into Evidence.
          Two cards sit side by side; a lone card takes the FULL width so the article
          title has room to print (no empty half, no needless truncation). */}
      {(strongestSupport || strongestChallenge) && (
        <div className={`mt-4 grid gap-3 ${strongestSupport && strongestChallenge ? 'grid-cols-1 md:grid-cols-2' : 'grid-cols-1'}`}>
          {strongestSupport && <PointCard kind="supports" title={strongestSupport.title} url={strongestSupport.url} nav={nav} onOpen={() => goStance('supports')} />}
          {strongestChallenge && <PointCard kind="challenges" title={strongestChallenge.title} url={strongestChallenge.url} nav={nav} onOpen={() => goStance('challenges')} />}
        </div>
      )}

      {/* Footer — source mix by tier (classification colour restored) + gaps */}
      <div className="mt-5 pt-4 border-t border-zinc-200 space-y-2">
        <div className="font-mono text-[10px] text-zinc-500 flex flex-wrap items-center gap-x-2 gap-y-1">
          <FooterLink nav={nav} label="Map" onClick={() => go('cartographer')}>
            <span>Elements {elements.length}</span>
          </FooterLink>
          <span className="text-zinc-200">&middot;</span>
          <FooterLink nav={nav} label="Evidence" onClick={() => go('librarian')}>
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
          </FooterLink>
        </div>

        {gapElements.length > 0 && (
          <div className="flex items-start gap-2">
            <span className="font-mono text-[10px] uppercase tracking-wider text-zinc-500 w-16 shrink-0 pt-0.5">Gaps</span>
            <div className="flex-grow">
              <ul className="space-y-0.5">
                {gapElements.map((el) => {
                  const u = el.uncertainty?.trim();
                  const showU = u && !['null', 'none', 'n/a'].includes(u.toLowerCase());
                  return (
                    <li key={el.elementId} className="font-mono text-[10px] text-zinc-500 flex items-start gap-1.5">
                      <span className="text-zinc-300 shrink-0">&bull;</span>
                      <span>
                        {el.description}
                        {showU && <span className="text-zinc-400"> — {u}</span>}
                      </span>
                    </li>
                  );
                })}
              </ul>
              {nav && (
                <button
                  type="button"
                  onClick={() => go('seeker')}
                  aria-label="Open Gaps lens"
                  className="mt-1 font-mono text-[10px] text-zinc-500 hover:text-[var(--accent)] transition-colors inline-flex items-center gap-1 cursor-pointer"
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

function PointCard({ kind, title, url, nav, onOpen }: { kind: EvidenceRelationship; title: string; url: string; nav: boolean; onOpen: () => void }) {
  const meta = STANCE_META[kind];
  // "Most relevant", not "strongest" — ranked by topical relevance, which carries
  // NO source authority (invariant), so "strongest" would overclaim evidential weight.
  const adj = kind === 'supports' ? 'supporting' : kind === 'challenges' ? 'challenging' : 'context';
  const body = (
    <>
      <span className="inline-flex items-center gap-1.5 text-xs font-medium text-zinc-600">
        {meta.glyph} Most relevant {adj} source
      </span>
      <p className="mt-1.5 text-sm text-zinc-900 leading-snug">{title}</p>
      <p className="mt-1 inline-flex items-center gap-1 text-xs text-zinc-500">
        <img
          src={getFaviconUrl(url)}
          alt=""
          width={12}
          height={12}
          loading="lazy"
          className="w-3 h-3 shrink-0 rounded-sm"
          onError={(e) => { e.currentTarget.style.visibility = 'hidden'; }}
        />
        {extractDomain(url)}
      </p>
      {nav && (
        <span className="mt-2 inline-flex items-center gap-1 text-xs text-zinc-500 group-hover:text-[var(--accent)] transition-colors">
          see in evidence <ArrowRight size={12} />
        </span>
      )}
    </>
  );
  return nav ? (
    <button onClick={onOpen} className="text-left border border-zinc-200 hover:border-[var(--accent)] transition-colors p-4 group">
      {body}
    </button>
  ) : (
    <div className="border border-zinc-200 p-4">{body}</div>
  );
}

function FooterLink({ nav, label, onClick, children }: { nav: boolean; label: string; onClick: () => void; children: React.ReactNode }) {
  if (!nav) return <span className="inline-flex items-center gap-1">{children}</span>;
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={`Open ${label} lens`}
      className="group inline-flex items-center gap-1 hover:text-zinc-900 transition-colors cursor-pointer"
    >
      {children}
      <span aria-hidden className="opacity-0 group-hover:opacity-100 transition-opacity text-[var(--accent)]">&rarr;</span>
    </button>
  );
}
