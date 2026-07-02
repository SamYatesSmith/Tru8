/**
 * Social Share Card OG Image Endpoint
 *
 * GET /api/og/social/[id]
 * Returns the 1200x630 PNG used as the Open Graph / Twitter preview for the
 * public report at /r/[id]. Rendered as a Tru8 "Record" card (record-card.tsx).
 *
 * Stance + tier numbers are aggregated with the SAME shared-utils helpers the
 * report UI uses (relationshipByEvidence / stanceCounts / tierCounts), so the
 * card matches exactly what a viewer sees on the report.
 */

import { ImageResponse } from '@vercel/og';
import { RecordCard } from '../../_components/record-card';
import {
  relationshipByEvidence,
  stanceCounts,
  tierCounts,
  extractDomain,
  cleanTitle,
} from '@/components/evidence-views/shared-utils';

export const runtime = 'edge';
export const revalidate = 3600;

// Fonts (bundled, loaded once per module instance). Inter for the claim/CTA,
// JetBrains Mono for all the spec-sheet metadata.
const fonts = Promise.all([
  fetch(new URL('../../_fonts/Inter-Regular.ttf', import.meta.url)).then((r) => r.arrayBuffer()),
  fetch(new URL('../../_fonts/Inter-SemiBold.ttf', import.meta.url)).then((r) => r.arrayBuffer()),
  fetch(new URL('../../_fonts/JetBrainsMono-Regular.ttf', import.meta.url)).then((r) => r.arrayBuffer()),
  fetch(new URL('../../_fonts/JetBrainsMono-Bold.ttf', import.meta.url)).then((r) => r.arrayBuffer()),
]).then(([interReg, interSemi, monoReg, monoBold]) => [
  { name: 'Inter', data: interReg, weight: 400 as const, style: 'normal' as const },
  { name: 'Inter', data: interSemi, weight: 600 as const, style: 'normal' as const },
  { name: 'JetBrains Mono', data: monoReg, weight: 400 as const, style: 'normal' as const },
  { name: 'JetBrains Mono', data: monoBold, weight: 700 as const, style: 'normal' as const },
]);

function fallback(message: string) {
  return new ImageResponse(
    (
      <div
        style={{
          width: '1200px',
          height: '630px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: '#ffffff',
          color: '#111827',
          fontSize: 32,
        }}
      >
        {message}
      </div>
    ),
    { width: 1200, height: 630 }
  );
}

interface EvidenceRef { evidenceId: string; relationship: 'supports' | 'challenges' | 'context' }
interface DetailedCheck {
  id: string;
  title?: string;
  sourceDomain?: string;
  claims?: Array<{
    claimMap?: { elements?: Array<{ evidenceRefs?: EvidenceRef[] }> } | null;
    evidence?: Array<{ id: string; evidenceId?: string; url?: string; tier?: 'primary' | 'reporting' | 'commentary' | null; receiptStatus?: string }>;
  }>;
}

export async function GET(request: Request, { params }: { params: Promise<{ id: string }> }) {
  try {
    const { id } = await params;
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    const response = await fetch(`${apiUrl}/api/v1/checks/public/${id}?detailed=true`, {
      headers: { 'Content-Type': 'application/json' },
      next: { revalidate: 300 },
    });

    if (!response.ok) return fallback('Report not found');
    const check: DetailedCheck = await response.json();

    // Aggregate stance + tier across all claims, mirroring ClaimSummaryPanel.
    const stance = { supports: 0, context: 0, challenges: 0, total: 0 };
    const tiers = { primary: 0, reporting: 0, commentary: 0 };
    let elementCount = 0;
    const domainCounts = new Map<string, number>();

    for (const claim of check.claims || []) {
      const elements = claim.claimMap?.elements || [];
      const evidence = (claim.evidence || []).filter((ev) => ev.receiptStatus !== 'excluded');
      const relMap = relationshipByEvidence(elements);
      const c = stanceCounts(evidence, relMap);
      stance.supports += c.supports;
      stance.context += c.context;
      stance.challenges += c.challenges;
      stance.total += c.total;
      const t = tierCounts(evidence);
      tiers.primary += t.primary;
      tiers.reporting += t.reporting;
      tiers.commentary += t.commentary;
      elementCount += elements.length;
      for (const ev of evidence) {
        const d = ev.url ? extractDomain(ev.url) : '';
        if (d) domainCounts.set(d, (domainCounts.get(d) || 0) + 1);
      }
    }

    const rankedDomains = Array.from(domainCounts.entries()).sort((a, b) => b[1] - a[1]).map(([d]) => d);
    const topDomains = rankedDomains.slice(0, 3);
    const moreCount = Math.max(0, rankedDomains.length - topDomains.length);

    const rawId = String(check.id || id).replace(/[^a-zA-Z0-9]/g, '').slice(0, 8).toLowerCase();
    const chkId = `chk_${rawId || 'record'}`;
    // Strip the endpoint's lazy trailing ellipsis / orphaned site suffix so the
    // quoted claim reads cleanly ("…COVID-19 vaccine" not "…vaccine ...").
    const title = cleanTitle(check.title) || 'Evidence Record';

    return new ImageResponse(
      (
        <RecordCard
          chkId={chkId}
          title={title}
          sourceDomain={check.sourceDomain}
          stance={stance}
          tiers={tiers}
          elementCount={elementCount}
          topDomains={topDomains}
          moreCount={moreCount}
        />
      ),
      { width: 1200, height: 630, fonts: await fonts }
    );
  } catch (error) {
    console.error('Social OG image generation error:', error);
    return fallback('Unable to generate image');
  }
}
