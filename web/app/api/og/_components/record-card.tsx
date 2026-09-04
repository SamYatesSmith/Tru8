/**
 * Record Card — the social share card for /r/[id] public reports.
 *
 * A "RECORD artifact" in the Tru8 spec-sheet design language: 2px orange
 * top-rule (the identity marker from ClaimSummaryPanel), JetBrains Mono
 * metadata, Inter display claim, sharp corners, hairline zinc borders.
 *
 * The hero device is the neutral evidence-stance distribution bar (supports /
 * context / challenges) — no verdict colour — plus the tier mix. Numbers are
 * aggregated in the route via the SAME shared-utils helpers the report uses,
 * so the card matches exactly what a viewer sees on /r/[id].
 *
 * Satori/@vercel/og constraints: inline styles only, every multi-child element
 * carries display:flex, no CSS classes, sharp corners (no border-radius per the
 * design system anyway).
 */

const C = {
  bg: '#ffffff',
  text: '#111827',
  text2: '#6b7280',
  muted: '#9ca3af',
  border: '#e5e7eb',
  accent: '#EA580C',
  // stance bands (neutral, no verdict colour) — mirrors STANCE_META in ClaimSummaryPanel
  supBg: '#27272a', supFg: '#ffffff',
  ctxBg: '#d4d4d8', ctxFg: '#27272a',
  chlBg: '#52525b', chlFg: '#ffffff',
};

const MONO = 'JetBrains Mono';
const SANS = 'Inter';

// Dotted-grid ground rendered as ONE full-canvas SVG layer (resvg renders the
// <pattern> internally) — avoids Satori's unreliable tiled background-size.
const DOT_SVG =
  'data:image/svg+xml,' +
  encodeURIComponent(
    "<svg xmlns='http://www.w3.org/2000/svg' width='1200' height='630'>" +
      "<defs><pattern id='d' width='24' height='24' patternUnits='userSpaceOnUse'>" +
      "<circle cx='2' cy='2' r='1.15' fill='#e5e7eb'/></pattern></defs>" +
      "<rect width='1200' height='630' fill='url(#d)'/></svg>"
  );

export interface RecordCardProps {
  chkId: string;
  title: string;
  sourceDomain?: string;
  stance: { supports: number; context: number; challenges: number; total: number };
  tiers: { primary: number; reporting: number; commentary: number };
  elementCount: number;
  topDomains: string[];
  moreCount: number;
}

function Diamond({ size = 9, color = C.accent }: { size?: number; color?: string }) {
  return <div style={{ width: size, height: size, backgroundColor: color, transform: 'rotate(45deg)', display: 'flex' }} />;
}

function claimFontSize(len: number): number {
  if (len <= 46) return 48;
  if (len <= 78) return 42;
  if (len <= 116) return 36;
  if (len <= 170) return 31;
  return 28;
}

// 2026-09-04: the API stopped cutting a text check's title at 70 chars, so the
// card now receives the whole claim. The console caps a claim at 200 chars;
// clamp there, not at 150 — a 156-char claim was losing its last word while
// the card had a spare line beneath it. Above 170 the 28px tier keeps four
// lines inside the block.
const TITLE_CLAMP = 200;

export function RecordCard({ chkId, title, sourceDomain, stance, tiers, elementCount, topDomains, moreCount }: RecordCardProps) {
  const bandSum = stance.supports + stance.context + stance.challenges;
  const bands = [
    { key: 'sup', n: stance.supports, glyph: '+', label: 'support', bg: C.supBg, fg: C.supFg },
    { key: 'ctx', n: stance.context, glyph: '·', label: 'context', bg: C.ctxBg, fg: C.ctxFg },
    { key: 'chl', n: stance.challenges, glyph: '–', label: 'challenge', bg: C.chlBg, fg: C.chlFg },
  ].filter((b) => b.n > 0);

  const tierBadges = [
    { n: tiers.primary, label: 'Primary', bg: '#fff7ed', bd: '#fed7aa', fg: '#b45309' },
    { n: tiers.reporting, label: 'Reporting', bg: '#f4f4f5', bd: '#d4d4d8', fg: '#3f3f46' },
    { n: tiers.commentary, label: 'Commentary', bg: '#fafafa', bd: '#e5e7eb', fg: '#a1a1aa' },
  ].filter((t) => t.n > 0);

  const displayTitle = title.length > TITLE_CLAMP ? title.slice(0, TITLE_CLAMP - 3) + '…' : title;

  return (
    <div style={{ width: 1200, height: 630, display: 'flex', flexDirection: 'column', backgroundColor: C.bg, backgroundImage: `url("${DOT_SVG}")`, backgroundRepeat: 'no-repeat', backgroundSize: '1200px 630px', fontFamily: SANS }}>
      {/* 2px orange top-rule (identity marker), scaled for the large canvas */}
      <div style={{ width: 1200, height: 6, backgroundColor: C.accent, display: 'flex' }} />

      <div style={{ display: 'flex', flexDirection: 'column', flexGrow: 1, padding: '46px 56px 44px' }}>
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontFamily: MONO, fontSize: 16, letterSpacing: '0.12em', textTransform: 'uppercase' }}>
          <div style={{ display: 'flex', alignItems: 'center', color: C.text2 }}>
            <Diamond />
            <span style={{ marginLeft: 13 }}>{chkId}</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center' }}>
            <span style={{ color: C.accent }}>Signed</span>
            <span style={{ color: C.muted, marginLeft: 10 }}>· Evidence Record</span>
          </div>
        </div>

        {/* Eyebrow */}
        <div style={{ display: 'flex', fontFamily: MONO, fontSize: 14, letterSpacing: '0.2em', textTransform: 'uppercase', color: C.muted, marginTop: 36, marginBottom: 16 }}>
          {sourceDomain ? `From  ${sourceDomain}` : 'Evidence record'}
        </div>

        {/* Claim */}
        <div style={{ display: 'flex', color: C.text, fontSize: claimFontSize(displayTitle.length), fontWeight: 600, lineHeight: 1.1, letterSpacing: '-0.02em', maxWidth: 1060 }}>
          {'“' + displayTitle + '”'}
        </div>

        {/* Stance section (pinned toward the lower half) */}
        <div style={{ display: 'flex', flexDirection: 'column', marginTop: 'auto' }}>
          <div style={{ display: 'flex', fontFamily: MONO, fontSize: 13, letterSpacing: '0.2em', textTransform: 'uppercase', color: C.muted, marginBottom: 12 }}>
            {bandSum > 0
              ? `Evidence  ·  ${stance.total} mapped across ${elementCount} element${elementCount === 1 ? '' : 's'}`
              : `Evidence  ·  ${elementCount} element${elementCount === 1 ? '' : 's'}`}
          </div>

          {bandSum > 0 && (
            <div style={{ display: 'flex', height: 54, width: '100%', border: `1px solid ${C.border}`, overflow: 'hidden' }}>
              {bands.map((b) => (
                <div key={b.key} style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', flexGrow: b.n, flexBasis: 0, minWidth: 44, backgroundColor: b.bg, color: b.fg, fontFamily: MONO, fontSize: 19, overflow: 'hidden' }}>
                  <span style={{ fontSize: 22, marginRight: 8 }}>{b.glyph}</span>
                  <span>{b.n}</span>
                </div>
              ))}
            </div>
          )}

          {bandSum > 0 && (
            <div style={{ display: 'flex', alignItems: 'center', marginTop: 14, fontFamily: MONO, fontSize: 15, color: C.text2 }}>
              {bands.map((b, i) => (
                <div key={b.key} style={{ display: 'flex', alignItems: 'center', marginRight: 26 }}>
                  <div style={{ width: 11, height: 11, backgroundColor: b.bg, marginRight: 9, display: 'flex' }} />
                  <span>{b.label === 'support' ? 'Supports' : b.label === 'context' ? 'Context' : 'Challenges'}</span>
                </div>
              ))}
              <span style={{ color: C.muted }}>— you decide</span>
            </div>
          )}
        </div>

        {/* Sources + tier mix */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 30 }}>
          <div style={{ display: 'flex', alignItems: 'center' }}>
            <span style={{ fontFamily: MONO, fontSize: 12, letterSpacing: '0.2em', textTransform: 'uppercase', color: C.muted, marginRight: 14 }}>Sources</span>
            {topDomains.map((d) => (
              <div key={d} style={{ display: 'flex', alignItems: 'center', border: `1px solid ${C.border}`, backgroundColor: '#fff', padding: '7px 13px 7px 9px', marginRight: 10 }}>
                <img src={`https://www.google.com/s2/favicons?domain=${d}&sz=64`} width={20} height={20} style={{ marginRight: 9 }} />
                <span style={{ fontFamily: MONO, fontSize: 16, color: '#3f3f46' }}>{d}</span>
              </div>
            ))}
            {moreCount > 0 && <span style={{ fontFamily: MONO, fontSize: 15, color: C.muted }}>+{moreCount} more</span>}
          </div>
          <div style={{ display: 'flex', alignItems: 'center' }}>
            {tierBadges.map((t) => (
              <div key={t.label} style={{ display: 'flex', backgroundColor: t.bg, border: `1px solid ${t.bd}`, padding: '6px 11px', marginLeft: 8 }}>
                <span style={{ fontFamily: MONO, fontSize: 12, fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', color: t.fg }}>{t.n} {t.label}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Footer */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 30, paddingTop: 24, borderTop: `1px solid ${C.border}` }}>
          <span style={{ fontFamily: MONO, fontSize: 14, letterSpacing: '0.04em', color: C.muted }}>hmac-sha256 · verify at trueight.com/verify</span>
          <div style={{ display: 'flex', alignItems: 'center' }}>
            <span style={{ fontSize: 21, fontWeight: 600, letterSpacing: '-0.01em', color: C.text, marginRight: 12 }}>Read the full record</span>
            <Diamond size={10} />
          </div>
        </div>
      </div>
    </div>
  );
}
