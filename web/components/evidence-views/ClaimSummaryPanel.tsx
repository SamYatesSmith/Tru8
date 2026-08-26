'use client';

/**
 * ClaimSummaryPanel — the Evidence Digest: the first-glance answer for a focused
 * claim (results-UX redesign 2026-06-30; C2 clarity pass 2026-07-09). Shared
 * by the dashboard check detail and the public `/r/` report so both surfaces get
 * the same digest.
 *
 * C2 rule: EVERY FACT GETS EXACTLY ONE HOME. Reads, top to bottom: identity →
 * claim → the lean line (mechanical orientation, BLUF) → ONE stat line (sources ·
 * directly-relevant count · element coverage only when partial) → ELEMENTS
 * EXAMINED (the roster — one-line intro, not a paragraph) → SOURCES MAPPED (the
 * neutral stance distribution bar; click a band → filtered Evidence) → NOTABLES
 * (the labelled most-relevant support/challenge cards; top-relevance rows only
 * as a fallback when no directional card exists) → footer, the single numeric
 * register (elements · sources — tier mix). Section titles carry the accent
 * diamond so they can't be missed. It doubles as navigation: the bar, notables
 * and gaps all deep-link into the relevant lens via the same `go(view, {rel,
 * element})` contract — nothing interactive lost.
 *
 * No-verdict lock: stance is shown by icon + word + position, NEVER colour
 * (no green/red); the lean sentence's subject is the EVIDENCE, never the claim.
 * Orange is used only as a wayfinding/interaction accent (rule, diamonds, hover),
 * never on stance. Tier classification colour is legitimate (classification ≠
 * verdict).
 *
 * Null-safe: a completed check can carry a null claimMap per-claim (partial
 * decompose) and nullable evidence tier — both guarded.
 */

import { Claim, Evidence, InputType, EvidenceRelationship } from '@shared/types';
import { isOrientationSuppressed } from '@/lib/orientation';
import { Plus, Minus, Dot, ArrowRight, ArrowUpRight } from 'lucide-react';
import {
  getTierColor,
  tierCounts,
  relationshipByEvidence,
  hasRelationship,
  stanceCounts,
  extractDomain,
  getFaviconUrl,
  cleanTitle,
} from './shared-utils';
import { capture } from '@/lib/analytics';
import { ElementList, TopUpCapability } from './ElementList';
import { TopUpButton } from './TopUpButton';
import { thinElementCount } from '@/lib/support-structure';

const TYPE_LABELS: Record<string, string> = {
  empirical: 'Empirical',
  definitional: 'Definitional',
  causal_interpretive: 'Causal',
  predictive: 'Predictive',
  normative_flagged: 'Normative',
};

// Stance display — neutral palette (no verdict colour). Differentiated by tonal
// weight + icon + word + position only. Orange is reserved for interaction.
const STANCE_META: Record<EvidenceRelationship, { label: string; fill: string; glyph: React.ReactNode }> = {
  supports: { label: 'Supports', fill: 'bg-zinc-800', glyph: <Plus size={13} /> },
  context: { label: 'Context', fill: 'bg-zinc-300', glyph: <Dot size={16} /> },
  challenges: { label: 'Challenges', fill: 'bg-zinc-600', glyph: <Minus size={13} /> },
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
   * scrolls. Lens values match ViewSelector (`librarian`, `compare`,
   * `chronologist`, `seeker`, `cartographer`, `projectionist`).
   */
  onNavigate?: (view: string, params?: { rel?: EvidenceRelationship[]; element?: string }) => void;
  /** Retained for call-site compatibility (was the Explore-rail hide list). */
  hiddenViews?: string[];
  /**
   * Dashboard-only: enables "top up a thin claim" triggers (per-element +
   * claim-level). Absent on the read-only public `/r/` report, so no trigger
   * ever renders there.
   */
  topUp?: TopUpCapability;
}

export function ClaimSummaryPanel({ claim, position, inputType, rankLabel, onNavigate, topUp }: ClaimSummaryPanelProps) {
  const claimMap = claim.claimMap;
  const elements = claimMap?.elements || [];
  // Match the Evidence lens, which shows only non-excluded sources, so a band's
  // count equals the filtered list it links to (excluded-but-mapped items would
  // otherwise inflate the digest above what the click shows).
  const evidence = (claim.evidence || []).filter((ev) => ev.receiptStatus !== 'excluded');
  const evidenceCount = evidence.length;
  const orientation = claimMap?.orientation;
  const orientationSuppressed = isOrientationSuppressed(claimMap);
  const claimType = claimMap?.claimType || claim.claimType;

  const rankText = rankLabel === undefined ? String(position + 1).padStart(2, '0') : rankLabel;
  // R1 — provenance chip only where it informs: a URL check EXTRACTED the claim
  // (worth saying); on a text check "Submitted Claim" restates the obvious.
  const contextLabel = inputType === 'url' ? 'Extracted Claim' : null;

  // ── Evidence-stance distribution (the bar) — mirrors Librarian's join. ──
  const relMap = relationshipByEvidence(elements);
  const counts = stanceCounts(evidence, relMap);
  const barTotal = counts.total; // distinct mapped sources (header label)
  const bandSum = counts.supports + counts.context + counts.challenges; // width denominator

  // Coverage: elements that carry a resolved state (gap = no/unresolved state).
  const coveredElements = elements.filter((el) => el.state && el.state !== 'unresolved').length;
  const gapElements = elements.filter((el) => !el.state || el.state === 'unresolved');
  // Thin elements the signed-in user can top up (dashboard-only capability).
  const thinCount = topUp ? thinElementCount(elements) : 0;

  // Source mix by tier (nullable tier → commentary in the helper).
  const tiers = tierCounts(evidence);

  // F6 — topical-relevance coverage. How many SHOWN sources bear directly on the
  // claim = llmRelevanceScore >= 4 ("directly/strongly addresses", scorer rubric).
  // A COUNT, not a per-source score — topical proximity, never source quality
  // (classify-don't-score). Hidden when nothing is scored (pre-scorer/older
  // checks or all over-cap), so it never shows a misleading "0 of N".
  const scoredCount = evidence.filter((ev) => typeof ev.llmRelevanceScore === 'number').length;
  const directCount = evidence.filter((ev) => (ev.llmRelevanceScore ?? 0) >= 4).length;
  const showCoverage = scoredCount > 0 && evidenceCount > 0;

  // R2 — ONE stat line under the lean (replaces the qualitative "broad set"
  // confidence line + the separate F6 line). Element coverage prints ONLY when
  // partial — "3 of 3 covered" says nothing. Totals otherwise live in the footer.
  const statParts: string[] = [];
  if (evidenceCount > 0) {
    statParts.push(`${evidenceCount} ${evidenceCount === 1 ? 'source' : 'sources'}`);
  }
  if (showCoverage) {
    statParts.push(`${directCount} ${directCount === 1 ? 'bears' : 'bear'} directly on the claim`);
  }
  if (elements.length > 0 && coveredElements < elements.length) {
    statParts.push(`${coveredElements} of ${elements.length} elements covered`);
  }
  const statLine = statParts.length > 0 ? `${statParts.join(' · ')}.` : null;

  // ── Relevance ranking for the Notables (selection by membership, so a
  // "most relevant support" is the top-relevance item carrying a supports ref). ──
  const relsOf = (ev: Evidence) => relMap.get(ev.evidenceId || ev.id);
  const mappedEvidence = evidence.filter((ev) => (relsOf(ev)?.length ?? 0) > 0);
  const byRelevance = [...mappedEvidence].sort((a, b) => (b.relevanceScore ?? 0) - (a.relevanceScore ?? 0));
  const strongestSupport = byRelevance.find((ev) => hasRelationship(relsOf(ev), 'supports'));
  const strongestChallenge = byRelevance.find((ev) => hasRelationship(relsOf(ev), 'challenges'));
  // R5 fallback ONLY: when no directional card exists (e.g. all-context claims),
  // the top-relevance rows keep the Notables section from going empty.
  const fallbackFindings = !strongestSupport && !strongestChallenge ? byRelevance.slice(0, 3) : [];

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
      {/* Zone 1 — identity (skipped entirely when every part is absent — e.g. a
          public single-claim text check with no claimType — no empty spacer). */}
      {(rankText !== null || contextLabel || claimType) && (
      <div className="flex items-center gap-3 mb-2">
        {rankText !== null && <span className="font-mono text-xs font-bold text-zinc-500">{rankText}</span>}
        {contextLabel && (
          <span className="px-2.5 py-0.5 bg-zinc-50 border border-zinc-200 text-[9px] font-mono font-bold uppercase tracking-wider text-zinc-500">
            {contextLabel}
          </span>
        )}
        {claimType && (
          <span className="px-2.5 py-0.5 bg-zinc-50 border border-zinc-200 text-[9px] font-mono font-bold uppercase tracking-wider text-zinc-500">
            {TYPE_LABELS[claimType] || claimType}
          </span>
        )}
      </div>
      )}

      {/* Claim restated neutrally — prefer the pipeline's normalised wording over
          the article's loaded phrasing (BLUF #1). */}
      <h2 className="text-xl md:text-2xl font-medium text-zinc-900 leading-snug mb-3">
        {claimMap?.normalisedClaim || claim.text}
      </h2>

      {/* The lean (BLUF) — subject is the evidence, never the claim.
          Null orientation gets an explicit line, never a blank where the answer should be.
          EXCEPT when suppressed (opinion claim, 2026-07-27): this slot is
          cleared deliberately, so the fallback must NOT fire. It reads "the
          gathered evidence doesn't clearly lean either way", which would put
          false balance exactly where we removed a false verdict — the same
          invariant breach in the other direction. Render nothing; the elements
          below carry the content. */}
      {orientationSuppressed ? null : orientation ? (
        <p className="text-base md:text-lg text-zinc-900 leading-snug">{orientation}</p>
      ) : evidenceCount > 0 ? (
        <p className="text-base md:text-lg text-zinc-900 leading-snug">
          {barTotal === 0
            ? `${evidenceCount} ${evidenceCount === 1 ? 'source' : 'sources'} gathered — not yet mapped to the claim's elements.`
            : 'The gathered evidence doesn’t clearly lean either way — elements remain unresolved.'}
        </p>
      ) : null}
      {statLine && <p className="text-sm text-zinc-500 mt-1">{statLine}</p>}

      {/* The elements — the reference frame the rest of the report cites. */}
      {elements.length > 0 && (
        <div className="mt-5 pt-4 border-t border-zinc-100">
          <SectionTitle>Elements examined</SectionTitle>
          <p className="mt-1.5 text-xs text-zinc-400 leading-relaxed">
            The claim, restated neutrally and broken into its checkable parts.
          </p>
          <div className="mt-3">
            <ElementList elements={elements} topUp={topUp} />
          </div>
          {/* Claim-level top-up: strengthen ALL thin elements in one run (dashboard-only). */}
          {topUp && thinCount > 0 && (
            <div className="mt-3">
              <TopUpButton
                mode="claim"
                checkId={topUp.checkId}
                claimId={topUp.claimId}
                token={topUp.token}
                thinCount={thinCount}
                onComplete={topUp.onComplete}
              />
            </div>
          )}
          {nav && gapElements.length > 0 && (
            <button
              type="button"
              onClick={() => go('seeker')}
              aria-label="Open Gaps lens"
              className="mt-2 font-mono text-[10px] text-zinc-500 hover:text-[var(--accent)] transition-colors inline-flex items-center gap-1 cursor-pointer"
            >
              {gapElements.length} {gapElements.length === 1 ? 'gap' : 'gaps'} — open the Gaps lens &rarr;
            </button>
          )}
        </div>
      )}

      {/* Distribution bar — click a band → filtered Evidence. R4: titled section;
          the count only prints when it differs from the shown set (partial mapping). */}
      {barTotal > 0 && (
        <div className="mt-5 pt-4 border-t border-zinc-100">
          <div className="flex items-center justify-between mb-1.5">
            <SectionTitle>
              {barTotal < evidenceCount ? `${barTotal} of ${evidenceCount} sources mapped` : 'Sources mapped'}
            </SectionTitle>
            {nav && <span className="font-mono text-[10px] text-zinc-400">click a bar &rarr;</span>}
          </div>
          {/* Three labelled bars, one per stance, on a shared scale (longest =
              the largest count). Label + count sit OUTSIDE the fill so a skewed
              distribution can never clip them off screen — the 2026-08-26
              partner finding that retired the single stacked band. A zero
              stance renders as an empty track rather than vanishing: absence
              is information, and a one-sided claim should look one-sided. */}
          <div className="space-y-1.5">
            {STANCE_ORDER.map((s) => {
              const n = counts[s];
              const meta = STANCE_META[s];
              const maxCount = Math.max(counts.supports, counts.context, counts.challenges, 1);
              const track = (
                <span className="flex-1 h-7 border border-zinc-200 min-w-0">
                  {n > 0 && (
                    <span
                      className={`block h-full min-w-[3px] ${meta.fill}`}
                      style={{ width: `${(n / maxCount) * 100}%` }}
                    />
                  )}
                </span>
              );
              const label = (
                <span className={`flex items-center gap-1.5 w-24 md:w-28 shrink-0 text-xs font-medium ${n > 0 ? 'text-zinc-700' : 'text-zinc-400'}`}>
                  <span className="shrink-0">{meta.glyph}</span>
                  {meta.label}
                </span>
              );
              const count = (
                <span className={`w-7 shrink-0 text-right font-mono text-xs ${n > 0 ? 'text-zinc-700' : 'text-zinc-400'}`}>{n}</span>
              );
              return nav && n > 0 ? (
                <button
                  key={s}
                  onClick={() => goStance(s)}
                  title={`${meta.label} — ${n} ${n === 1 ? 'source' : 'sources'}`}
                  aria-label={`Show the ${n} ${meta.label.toLowerCase()} sources`}
                  className="group flex items-center gap-2 w-full cursor-pointer [&>span:nth-child(2)]:transition-all hover:[&>span:nth-child(2)]:ring-1 hover:[&>span:nth-child(2)]:ring-inset hover:[&>span:nth-child(2)]:ring-[var(--accent)]"
                >
                  {label}
                  {track}
                  {count}
                </button>
              ) : (
                <div key={s} className="flex items-center gap-2 w-full">
                  {label}
                  {track}
                  {count}
                </div>
              );
            })}
          </div>
          <p className="mt-1.5 text-[11px] text-zinc-400">
            Bar lengths compare the sources gathered — not a verdict on the claim.
            {bandSum > barTotal && ' Some sources address more than one side.'}
          </p>
        </div>
      )}

      {/* Notables (R5) — the labelled most-relevant support/challenge cards carry
          the section; unlabelled top-relevance rows appear ONLY as a fallback when
          no directional card exists. The full classified set is one click away. */}
      {(strongestSupport || strongestChallenge || fallbackFindings.length > 0) && (
        <div className="mt-5 pt-4 border-t border-zinc-100">
          <SectionTitle>Notables</SectionTitle>
          {strongestSupport || strongestChallenge ? (
            <div className={`mt-3 grid gap-3 ${strongestSupport && strongestChallenge ? 'grid-cols-1 md:grid-cols-2' : 'grid-cols-1'}`}>
              {strongestSupport && <PointCard kind="supports" title={strongestSupport.title} url={strongestSupport.url} nav={nav} onOpen={() => goStance('supports')} />}
              {strongestChallenge && <PointCard kind="challenges" title={strongestChallenge.title} url={strongestChallenge.url} nav={nav} onOpen={() => goStance('challenges')} />}
            </div>
          ) : (
            <ul className="mt-2.5 space-y-2">
              {fallbackFindings.map((ev) => (
                <li key={ev.evidenceId || ev.id} className="flex items-start gap-2 text-sm text-zinc-700">
                  <span aria-hidden className="mt-2 w-1 h-1 bg-zinc-400 shrink-0" />
                  {/* Source title, not the raw snippet — source-platforming invariant
                      (relevance summaries drive visits; never reproduce article content). */}
                  <span className="flex-1 leading-snug line-clamp-2">{cleanTitle(ev.title) || extractDomain(ev.url)}</span>
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
          )}
          {nav && evidenceCount > 0 && (
            // Visible text is the accessible name (WCAG 2.5.3 label-in-name) —
            // no aria-label override needed.
            <button
              type="button"
              onClick={() => go('librarian')}
              className="mt-2.5 font-mono text-[10px] text-zinc-500 hover:text-[var(--accent)] transition-colors inline-flex items-center gap-1 cursor-pointer"
            >
              All {evidenceCount}, classified and filterable, in the Evidence lens &rarr;
            </button>
          )}
        </div>
      )}

      {/* Footer (R6) — the single numeric register: elements · sources — tier mix
          (classification colour restored). Gaps live in the roster above. */}
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
      </div>
    </div>
  );
}

/** R3 — section titles that can't be missed: accent diamond + darker mono weight
 *  (the marketing SheetHeader idiom, miniaturised). The diamond is wayfinding
 *  accent, never stance. */
function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <span className="inline-flex items-center gap-2 font-mono text-[10px] font-bold tracking-[0.2em] uppercase text-zinc-700">
      <span aria-hidden className="w-1.5 h-1.5 bg-[var(--accent)] rotate-45 shrink-0" />
      <span>{children}</span>
    </span>
  );
}

function PointCard({ kind, title, url, nav, onOpen }: { kind: EvidenceRelationship; title: string; url: string; nav: boolean; onOpen: () => void }) {
  const meta = STANCE_META[kind];
  // "Most relevant", not "strongest" — ranked by topical relevance, which carries
  // NO source authority (invariant), so "strongest" would overclaim evidential weight.
  const adj = kind === 'supports' ? 'supporting' : kind === 'challenges' ? 'challenging' : 'context';
  // Two distinct affordances (2026-08-26 partner finding), so the card is a
  // plain div — a link inside a button is invalid HTML. The domain visits the
  // source (works on /r/ too, same idiom as the fallback rows); "see in
  // evidence" locates it in the grid (dashboard/nav only).
  return (
    <div className="border border-zinc-200 p-4">
      <span className="inline-flex items-center gap-1.5 text-xs font-medium text-zinc-600">
        {meta.glyph} Most relevant {adj} source
      </span>
      <p className="mt-1.5 text-sm text-zinc-900 leading-snug">{cleanTitle(title)}</p>
      <div className="mt-2 flex items-center justify-between gap-3">
        <a
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 text-xs text-zinc-500 hover:text-[var(--accent)] transition-colors min-w-0"
        >
          <img
            src={getFaviconUrl(url)}
            alt=""
            width={12}
            height={12}
            loading="lazy"
            className="w-3 h-3 shrink-0 rounded-sm"
            onError={(e) => { e.currentTarget.style.visibility = 'hidden'; }}
          />
          <span className="truncate">{extractDomain(url)}</span>
          <ArrowUpRight size={12} className="shrink-0" />
        </a>
        {nav && (
          <button
            type="button"
            onClick={onOpen}
            className="shrink-0 inline-flex items-center gap-1 text-xs text-zinc-500 hover:text-[var(--accent)] transition-colors cursor-pointer"
          >
            see in evidence <ArrowRight size={12} />
          </button>
        )}
      </div>
    </div>
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
