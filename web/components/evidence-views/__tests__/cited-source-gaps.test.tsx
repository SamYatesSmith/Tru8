import { describe, expect, it, vi } from 'vitest';
import { render, waitFor } from '@testing-library/react';
import type { Claim, ClaimElement } from '@shared/types';
import { citedSourceGaps, evidenceCoverage } from '@/lib/evidence-coverage';

// Cited-source gap note (Build B, audit/2026-10-05_cited_source_lane_design.md §17).

const api = vi.hoisted(() => ({
  getUsage: vi.fn(() => Promise.resolve({ creditsPerPeriod: 200, periodCreditsUsed: 0 })),
  getExploreData: vi.fn(() => Promise.resolve({ relatedClaims: [] })),
}));
vi.mock('@/lib/api', () => ({ apiClient: api }));
vi.mock('@/lib/analytics', () => ({ capture: vi.fn() }));
vi.mock('../seeker/BountyField', () => ({ BountyField: () => null }));
vi.mock('../seeker/ResearchButton', () => ({ ResearchButton: () => null }));
import { SeekerView } from '../seeker/SeekerView';
import { ClaimSummaryPanel } from '../ClaimSummaryPanel';

const BLOOMBERG = { name: 'Bloomberg', cue: 'a new Bloomberg analysis finds Trump made nearly 28,700 trades' };
const EFFIS = { name: 'European Forest Fire Information System', cue: 'data collected by the European Forest Fire Information System (EFFIS)' };

function covered(): ClaimElement {
  return {
    elementId: 'e1', description: 'Trades question', state: 'supported',
    evidenceRefs: [{ evidenceId: 'ev-1', relationship: 'supports' }],
  } as ClaimElement;
}

function claimWith(missing: unknown, elements: ClaimElement[] = [covered()]): Claim {
  return {
    id: 'c1', text: 'A claim.',
    evidence: [{ id: 'ev-1', evidenceId: 'ev-1', url: 'https://example.com/a', title: 'A', receiptStatus: 'shown' }],
    claimMap: { elements, metadata: { citedSources: { names: [], missing } } },
  } as unknown as Claim;
}

const ROW = 'Sources here attribute this to Bloomberg ("a new Bloomberg analysis finds Trump made nearly 28,700 trades"); that source is not in this record.';

describe('cited-source gap note — the shared coverage measure', () => {
  it('counts cited originals as gaps but leaves element coverage alone', () => {
    const elements = [covered()];
    expect(evidenceCoverage(elements, [BLOOMBERG])).toEqual({
      gaps: 1, elementGaps: 0, citedMissing: 1, needsReview: 0, coverage: 100, withEvidence: 1,
    });
  });

  it('reads only well-formed entries and treats an absent field as none', () => {
    expect(citedSourceGaps(claimWith([BLOOMBERG, { name: 'X' }, { name: '', cue: 'c' }, null]).claimMap)).toEqual([BLOOMBERG]);
    expect(citedSourceGaps(claimWith(undefined).claimMap)).toEqual([]);
    expect(citedSourceGaps(null)).toEqual([]);
  });
});

// Both hosts render SeekerView: /r/ read-only, the dashboard with a session.
const HOSTS: [string, (claim: Claim) => JSX.Element][] = [
  ['public /r/', (claim) => <SeekerView claim={claim} readOnly />],
  ['dashboard', (claim) => <SeekerView claim={claim} checkId="chk" token="tok" />],
];

describe.each(HOSTS)('cited-source gap note — %s', (_host, view) => {
  it('lists each cited original under its own heading, verbatim', async () => {
    const { container, getAllByTestId, getByText } = render(view(claimWith([BLOOMBERG])));
    expect(getByText('Cited but not in this record')).toBeTruthy();
    const rows = getAllByTestId('cited-source-gap');
    expect(rows.map((r) => r.textContent)).toEqual([ROW]);
    // Phone width: the row wraps, nothing truncated, nothing hover-only.
    expect(rows[0].className).toContain('break-words');
    expect(rows[0].className).not.toMatch(/truncate|line-clamp/);
    expect(rows[0].querySelector('[title]')).toBeNull();
    // The Gaps counter includes it.
    expect(container.textContent).toMatch(/Gaps1Needs review0/);
    // Never claims a search happened, never a verdict.
    expect(container.textContent).not.toMatch(/searched|not found|false|misleading|debunk/i);
    await waitFor(() => undefined);
  });

  it('rewords the all-covered state for one cited original', async () => {
    const { container } = render(view(claimWith([BLOOMBERG])));
    expect(container.textContent).toContain(
      'Each element has evidence mapped; one cited original is not in this record.',
    );
    expect(container.textContent).not.toContain('Each element has supporting evidence mapped.');
    await waitFor(() => undefined);
  });

  it('pluralises for more than one', async () => {
    const { container, getAllByTestId } = render(view(claimWith([BLOOMBERG, EFFIS])));
    expect(getAllByTestId('cited-source-gap')).toHaveLength(2);
    expect(container.textContent).toContain(
      'Each element has evidence mapped; two cited originals are not in this record.',
    );
    await waitFor(() => undefined);
  });

  it('renders nothing new without a note', async () => {
    const { container, queryByText } = render(view(claimWith(undefined)));
    expect(queryByText('Cited but not in this record')).toBeNull();
    expect(container.textContent).toContain('Each element has supporting evidence mapped.');
    expect(container.textContent).not.toContain('cited original');
    await waitFor(() => undefined);
  });
});

describe('cited-source gap note — summary panel', () => {
  it('counts the cited original in the Gaps link, not in element coverage', () => {
    const { getByRole, container } = render(
      <ClaimSummaryPanel claim={claimWith([BLOOMBERG])} position={0} onNavigate={() => {}} />,
    );
    expect(getByRole('button', { name: 'Open Gaps lens' }).textContent).toMatch(/^1 gap — open the Gaps lens/);
    expect(container.textContent).not.toMatch(/elements have evidence/);
  });
});

// Verification 2026-10-06 (audit/2026-10-06_cited_source_gap_note_verification.md).
describe('cited-source gap note — verification fixes', () => {
  it('LOW-3: a note never hides Adjacent investigations on the dashboard', async () => {
    api.getExploreData.mockResolvedValueOnce({
      relatedClaims: [{ normalisedClaim: 'A related claim', claimType: null, elements: [], consensus: null, entityOverlap: [] }],
    } as never);
    const { findByText, getByText } = render(
      <SeekerView claim={claimWith([BLOOMBERG])} checkId="chk" token="tok" />,
    );
    expect(await findByText('Adjacent investigations')).toBeTruthy();
    expect(getByText('Cited but not in this record')).toBeTruthy();
  });

  it.each(HOSTS)('LOW-4: an elementless claim still shows its note (%s)', async (_host, view) => {
    const { getAllByTestId, getByText } = render(view(claimWith([BLOOMBERG], [])));
    expect(getByText('No elements available for this claim')).toBeTruthy();
    expect(getAllByTestId('cited-source-gap').map((r) => r.textContent)).toEqual([ROW]);
    await waitFor(() => undefined);
  });
});
